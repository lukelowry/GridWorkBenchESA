import pypsa
import numpy as np

from gridwb.workbench.grid.components import *



def toPyPsa(buses: list[Bus], lines: list[Branch], gens: list[Gen], loads: list[Load]):
    network = pypsa.Network()

    for bus in buses:
        network.add(
            "Bus",
            name=f"Bus {bus.BusNum}",
            v_nom=bus.BusNomVolt,
        )

    for line in lines:
        network.add(
            "Line",
            name=f"Line {line.BusNum} {line.BusNum__1} {line.LineCircuit}",
            bus0=f"Bus {line.BusNum}",
            bus1=f"Bus {line.BusNum__1}",
            x=line.LineX,
            r=line.LineR,
        )

    for gen in gens:
        network.add(
            "Generator",
            name=f"Gen {gen.BusNum} {gen.GenID}",
            bus=f"Bus {gen.BusNum}",
            p_set=gen.GenMW,
            control="PQ",
        )

    for load in loads:
        network.add(
            "Load",
            name=f"Load {load.BusNum} {load.LoadID}",
            bus=f"Bus {load.BusNum}",
            p_set=load.LoadMW,
            q_set=load.LoadMVR,
        )

    return network
