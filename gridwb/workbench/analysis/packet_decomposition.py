# Packet Decomposition: Decomposing power flow into packets of energy routing
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 4/22/2022 ABB Converting over prior code from January
# 
from ..utils import *

class FlowPacket:

    def __init__(self, p, type, dest) -> None:
        self.type = type # 0 Load, 1 Loss, 2 Cycle, 3 Negative Generator, 4 Mismatch
        self.orig = None
        self.dest = dest
        self.path = []
        self.p = p

    def split(self, p): # Splitting from prior one
        pk = FlowPacket(p, self.type, self.dest)
        pk.orig = self.orig
        pk.path = []
        for branch in self.path:
            pk.path.append(branch)
        self.p -= p
        return pk

    def addpath(self, branch):
        self.path.append(branch)


def packet_decomposition(wb, output_fname=None):

    # Initialize all branches with cycle  
    for branch in wb.branches:
        branch.is_cycle_branch = False
        branch.cycle_membership = []
    all_cycles = []

    # DFS, marking cycle branches until no cycle branches each
    found_cycle = True
    while found_cycle:
        buses = list(wb.buses)
        ordered_buses = []
        found_cycle = False 
        for bus in buses:
            bus.visited = False
            bus.on_current_tree = False
            bus.ordered = False
            bus.parent = None
            bus.parentbr = None
            bus.adj = []
            bus.adjbr = []
            for branch in sorted(bus.branches, key=lambda br:-abs(br.p1)):
                if branch.from_bus == bus and branch.p1 > 0 and branch.p2 < 0 and not branch.is_cycle_branch:
                    bus.adjbr.append(branch)
                    bus.adj.append(branch.to_bus)
                elif branch.to_bus == bus and branch.p2 > 0 and branch.p1 < 0 and not branch.is_cycle_branch:
                    bus.adjbr.append(branch)
                    bus.adj.append(branch.from_bus)
        for rbus in buses:
            if found_cycle:
                break
            stack = []
            if rbus.ordered:
                continue
            stack.append(rbus)
            while stack and not found_cycle:
                bus = stack[-1]
                if bus.ordered: # Forget it, we got this one another way
                    stack.pop()
                elif bus.visited: # Great, we successfully ordered all the descendants
                    ordered_buses.append(bus)
                    bus.ordered = True
                    bus.on_current_tree = False
                    stack.pop()
                else: # We need to look through 
                    bus.visited = True
                    bus.on_current_tree = True
                    for bus2, br in zip(bus.adj, bus.adjbr):
                        if bus2.on_current_tree:
                            cycle = []
                            bus3 = bus
                            while bus3 is not None and bus3 != bus2:
                                cycle.append(bus3.parentbr)
                                bus3 = bus3.parent
                            cycle.append(br)
                            branch_order = sorted(cycle, key=lambda b:(-min(b.p1, b.p2) - sum([all_cycles[i][1] for i in b.cycle_membership])))
                            cycle_branch = branch_order[0]
                            cycle_branch.is_cycle_branch = True
                            cycle_number = len(all_cycles)
                            cycle_mw = -min(cycle_branch.p1, cycle_branch.p2) - sum([all_cycles[i][1] for i in cycle_branch.cycle_membership])
                            for branch in cycle:
                                branch.cycle_membership.append(cycle_number)
                            all_cycles.append((cycle_number, cycle_mw, cycle_branch, cycle))
                            print(f"Found cycle {cycle_number} length {len(cycle)} mw {cycle_mw} opening {cycle_branch}")
                            found_cycle = True
                            break
                        if not bus2.visited:
                            bus2.parent = bus
                            bus2.parentbr = br
                            stack.append(bus2)

    for branch in wb.branches:
        branch.cfl = sum([all_cycles[i][1] for i in branch.cycle_membership])

    for branch in wb.branches:
        branch.packets = []

    tol = 0.2
    packets = []
    for c in all_cycles:
        pk = FlowPacket(c[1], 2, f"Cycle {c[0]}")
        pk.orig = f"Cycle {c[0]}"
        pk.path = list(c[3])
        packets.append(pk)
    for bus in ordered_buses:
        #print(f"WORKING ON BUS {bus.number} {bus.vang}")
        plist = [] # list of packets at this bus

        # Process all outgoing power into packets
        for load in bus.loads:
            if load.p > 0:
                pk = FlowPacket(load.p, 0, load)
                plist.append(pk)
        for gen in bus.gens:
            if gen.p < 0:
                plist.append(FlowPacket(-gen.p, 3, gen))
        for branch in bus.branches:
            p_out = branch.p1 if branch.from_bus == bus else branch.p2
            p_in = branch.p2 if branch.from_bus == bus else branch.p1
            if p_out > 0:
                p_loss = p_out if p_in > 0 else p_out + p_in
                p_cycle = branch.cfl
                p_mism = p_out - (p_cycle + p_loss)
                p_load = sum([pk.p for pk in branch.packets])
                for pk in branch.packets:
                    plist.append(pk)
                    p_mism -= pk.p
                loss_pk = FlowPacket(p_loss, 1, branch)
                plist.append(loss_pk)
                if abs(p_mism) > tol:
                    raise Exception(f"{branch} mismatch issue {p_mism}")

        plist.sort(key=lambda pk:-pk.p) # Supply packets smallest to largest to keep numbers down

        mismatch = sum([-b.p1 - b.cfl for b in bus.branches_from if b.p1 < 0]) \
            + sum([-b.p2 - b.cfl for b in bus.branches_to if b.p2 < 0]) \
            + sum([-load.p for load in bus.loads if load.p < 0]) \
            + sum([gen.p for gen in bus.gens if gen.p > 0]) \
            - sum([pk.p for pk in plist])
        if mismatch > tol:
            print(f"Mismatch demand {bus} {mismatch}")
            plist.insert(0, FlowPacket(mismatch, 4, bus))
        for load in bus.loads:
            p = -load.p
            while plist and p > 0:
                pk = plist[-1]
                pk.orig = load
                if p > pk.p:
                    p -= pk.p
                    plist.pop()
                    packets.append(pk)
                else:
                    pk2 = pk.split(p)
                    packets.append(pk2)
                    p -= pk2.p
            if p > .2:
                raise Exception(f"Extra supply {load} {p}")
        for gen in bus.gens:
            p = gen.p
            while plist and p > 0:
                pk = plist[-1]
                pk.orig = gen
                if p > pk.p:
                    p -= pk.p
                    plist.pop()
                    packets.append(pk)
                else:
                    pk2 = pk.split(p)
                    packets.append(pk2)
                    p -= pk2.p
            if p > tol:
                raise Exception(f"Extra supply {gen} {p}")
        for branch in sorted(bus.branches, key=lambda br:abs(br.p1)):
            p = (-branch.p1 if branch.from_bus == bus else -branch.p2) - branch.cfl
            while plist and p > 0:
                pk = plist[-1]
                if p > pk.p:
                    p -= pk.p
                    plist.pop()
                    branch.packets.append(pk)
                    pk.path.insert(0,branch)
                else:
                    pk2 = pk.split(p)
                    branch.packets.append(pk2)
                    pk2.path.insert(0,branch)
                    p -= pk2.p
            if p > tol:
                raise Exception(f"Extra supply {branch} {p}")
        for pk in plist:
            if pk.p > tol:
                print(f"Mismatch supply {bus} {pk.p}")
                pk.orig = bus
                packets.append(pk)

    # Check packets
    for bus in wb.buses:
        bus.packets = []
    for load in wb.loads:
        load.packets = []
    for gen in wb.gens:
        gen.packets = []
    for branch in wb.branches:
        branch.packets = []
    for packet in packets:
        if type(packet.orig) in [GridType.Bus, GridType.Load, GridType.Gen, GridType.Line]:
            packet.orig.packets.append(packet)
        if type(packet.dest) in [GridType.Bus, GridType.Load, GridType.Gen, GridType.Line]:
            packet.dest.packets.append(packet)
        for branch in packet.path:
            branch.packets.append(packet)
    for bus in wb.buses:
        ptotal = 0
        for packet in bus.packets:
            if bus == packet.orig:
                ptotal += packet.p
            elif bus == packet.dest:
                ptotal -= packet.p
        if abs(ptotal) > 0.2:
            print(f"{bus} mismatch packets: {ptotal}")
    for load in wb.loads:
        ptotal = load.p
        for packet in load.packets:
            if load == packet.orig:
                ptotal += packet.p
            elif load == packet.dest:
                ptotal -= packet.p
        if abs(ptotal) > 0.2:
            print(f"{load} mismatch {ptotal}")
    for gen in wb.gens:
        ptotal = gen.p
        for packet in gen.packets:
            if gen == packet.orig:
                ptotal -= packet.p
            elif gen == packet.dest:
                ptotal += packet.p
        if abs(ptotal) > 0.2:
            print(f"{gen} mismatch {ptotal}")
    for branch in wb.branches:
        p_flow = abs(branch.p1 - branch.p2)
        p_loss = branch.p1 + branch.p2
        p_out = branch.p1 if branch.from_bus == bus else branch.p2
        p_in = branch.p2 if branch.from_bus == bus else branch.p1
        for packet in branch.packets:
            if branch == packet.dest:
                p_loss -= packet.p
        if abs(ptotal) > 0.2:
            print(f"{branch} mismatch {ptotal}")

    if output_fname is not None:
        with open(output_fname,"w") as f:
            f.write("Number,MW,Type,Origin,Destination")
            for i in range(max([len(pk.path) for pk in packets])):
                f.write(f",Path{i}")
            f.write("\n")
            for i, pk in enumerate(packets):
                f.write(f"{i},{pk.p},{pk.type},{pk.orig},{pk.dest}")
                for br in pk.path:
                    f.write(f",'{br.from_bus.number}-{br.to_bus.number}-{br.id}")
                f.write("\n")
    
    return packets