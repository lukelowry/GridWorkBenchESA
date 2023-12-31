# GridEngine: Capability to connect with low-level GridEngine for solving power
# flow and contingency analysis and OPF
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 4/1/2022 ABB Initial version
# 8/18/22 ABB Refactoring for new name "GridEngine"
#
import os
from cmath import pi
from ctypes import *

from ..analysis.contingencies import ContingencySet, ContingencyViolation
from ..utils import *

GRNG_ERR_BAD_ID_LOW =101
GRNG_ERR_BAD_ID_HIGH =102
GRNG_ERR_BAD_ID_FREED =103
GRNG_ERR_RAW_FILE_NOT_OPENED =1100
GRNG_ERR_RAW_FILE_TOO_FEW_LINE_PARTS =1101
GRNG_ERR_RAW_FILE_BUS_LINK_NOT_FOUND =1102
GRNG_ERR_INL_FILE_NOT_OPENED =1103
GRNG_ERR_INL_VALIDATION =1104
GRNG_ERR_INL_GEN_LINK_NOT_FOUND =1105
GRNG_ERR_CON_UNKNOWN_CTG_ACTION =1106
ENGINE_LOG_SIZE =1000000
OBJ_BUS =0x0001
OBJ_BRANCH =0x0002
BRANCH_STATUS_OPEN =0x0000
BRANCH_STATUS_CLOSED =0x0001
OBJ_GEN =0x0003
GEN_STATUS_OPEN =0x0000
GEN_STATUS_FIXED_P_Q =0x0001
GEN_STATUS_FIXED_P =0x0002
GEN_STATUS_FIXED_Q =0x0003
GEN_STATUS_VAR_PQ =0x0004
GEN_STATUS_SHUNT_OPEN =0x000A
GEN_STATUS_SHUNT_CONTINUOUS =0x000D
OBJ_AREA =0x0008
OBJ_SUB =0x0009
OBJ_CTG = 0x0005
OBJ_CTGELEM =0x0004
CTGELEM_CODE_PFIXED =0x0000
CTGELEM_CODE_QFIXED =0x0001
CTGELEM_CODE_QSHUNT =0x0002
CTGELEM_CODE_GEN_OPEN =0x0003
CTGELEM_CODE_BRANCH_OPEN =0x0004
OBJ_CTGVIO =0x0006
CTGVIO_CODE_NOT_SOLVED =0x0000
CTGVIO_CODE_BRANCH_MVA =0x0001
CTGVIO_CODE_BUS_HIGHV =0x0002
CTGVIO_CODE_BUS_LOWV =0x0003
STEADY_MODELING_AC =0x0000
STEADY_MODELING_DC_KLU =0x0001
STEADY_MODELING_DC_CHOLMOD =0x0002
OBJ_LINCOST =0x0007
LP_MAX_BREAKS =10
LP_TOL =1e-8
LP_EXIT_MAX_ITERATIONS =0
LP_EXIT_OPTIMUM_REACHED =1
LP_EXIT_INFEASIBLE =2
LP_EXIT_UNBOUNDED =3

class GRNG_Bus(Structure):
    _fields_ = [("del", c_char), ("id", c_int), ("area", c_int), ("label", c_int), 
    ("sub", c_int), ("mag", c_double), ("angle", c_double), ("psload", c_double), 
    ("qsload", c_double), ("qshunt", c_double), ("basekv", c_double), 
    ("lmp", c_double)]

c_char3 = c_char*3
class GRNG_Branch(Structure):
    _fields_ = [("del", c_char), ("bus1", c_int), ("bus2", c_int), ("status", c_int), 
    ("label", c_int), ("x", c_double), ("r", c_double), ("b", c_double), 
    ("g", c_double), ("tap", c_double), ("phase", c_double), ("p1", c_double), 
    ("q1", c_double), ("p2", c_double), ("q2", c_double), ("slimit", c_double),
     ("smaxctg", c_double), ("ckt", c_char3)]
    
class GRNG_Gen(Structure):
    _fields_ = [("del", c_char), ("id", c_char3), ("bus", c_int), 
    ("status", c_int), ("busreg", c_int), ("costtable", c_int), ("label", c_int), 
    ("p", c_double), ("q", c_double), ("pmin", c_double), ("pmax", c_double), 
    ("qmin", c_double), ("qmax", c_double), ("vset", c_double), 
    ("partfac", c_double), ("regfac", c_double)]
    
class GRNG_Area(Structure):
    _fields_ = [("del", c_char), ("id", c_int), ("label", c_int)]
    
class GRNG_Sub(Structure):
    _fields_ = [("del", c_char), ("id", c_int), ("label", c_int), 
    ("latitude", c_double), ("longitude", c_double)]
    
class GRNG_Network(Structure):
    _fields_ = [("mva_base", c_double), ("buses", POINTER(GRNG_Bus)), 
    ("branches", POINTER(GRNG_Branch)), ("gens", POINTER(GRNG_Gen)), 
    ("areas", POINTER(GRNG_Area)), ("subs", POINTER(GRNG_Sub))]
    
class GRNG_Ctgelem(Structure):
    _fields_ = [("del", c_char), ("code", c_int), ("id", c_int), ("ctg", c_int), 
    ("label", c_int), ("val", c_double)]

class GRNG_Ctg(Structure):
    _fields_ = [("del", c_char), ("pce", c_int), ("nvios", c_int), ("solved", c_int), 
    ("nislands", c_int), ("rebuild_flag", c_int), ("regulation_stuck_flag", c_int), 
    ("label", c_int), ("unserved_load", c_double)]
    
class GRNG_Ctgvio(Structure):
    _fields_ = [("del", c_char), ("code", c_int), ("id", c_int), ("ctg", c_int), 
    ("label", c_int), ("value", c_double)]
    
class GRNG_Steadystate(Structure):
    _fields_ = [("modeling", c_int), ("dcslack", c_int), 
    ("max_nr_iterations", c_int), ("max_avr_iterations", c_int), 
    ("max_agc_iterations", c_int), ("dishonest_iterations", c_int), 
    ("enforce_limits", c_int), ("agc_max_hit_limit", c_int), ("log_detail", c_int), 
    ("nvmax", c_int), ("nr_tolerance", c_double), ("agc_tolerance = 1e-2", c_double), 
    ("ctgelems", POINTER(GRNG_Ctgelem)), ("ctgs", POINTER(GRNG_Ctg)), 
    ("ctgvios", POINTER(GRNG_Ctgvio))]
    
c_double10 = c_double*10
class GRNG_Lincost(Structure):
    _fields_ = [("del", c_char), ("npoints", c_int), ("label", c_int), 
    ("x", c_double10), ("y", c_double10)]

class GRNG_Optimization(Structure):
    _fields_ = [("talk_detail", c_int), ("max_ctg_run", c_int), 
    ("do_sequential", c_int), ("ignore_ctg", c_int), ("ignore_violations", c_int), 
    ("ctg_maintain_base_voltage", c_int), ("save_stats", c_int), 
    ("total_ctgs", c_int), ("tableau_ctgs", c_int), ("binding_ctgs", c_int), 
    ("niterations", c_int), ("nr_iteration_count", c_int), ("lmp_min", c_double), 
    ("lmp_avg", c_double), ("lmp_max", c_double), 
    ("lincosts", POINTER(GRNG_Lincost))]

class GRNG_Workbench(Structure):
    _fields_ = [("eng", POINTER(None)), ("net", GRNG_Network), 
    ("steady", GRNG_Steadystate), ("opt", GRNG_Optimization)]

class GRNG_LP_Variable(Structure):
    _fields_ = [("nsegs", c_int), ("basis_index", c_int), 
    ("marginal_cost", c_double), ("vals", c_double10), ("costs", c_double10), 
    ("val", c_double)]

class GridEngine():

    def __init__(self, gwb, engine_dll_fname):
        self.wb = gwb
        self.ewb = None
        self.lib = CDLL(engine_dll_fname)
        self.lib.create_workbench.argtypes = []
        self.lib.create_workbench.restype = POINTER(GRNG_Workbench)
        self.lib.destroy_workbench.argtypes = [POINTER(GRNG_Workbench)]
        self.lib.destroy_workbench.restype = POINTER(GRNG_Workbench)
        self.lib.count_object.argtypes = [POINTER(GRNG_Workbench), c_int]
        self.lib.count_object.restype = c_int
        self.lib.add_object.argtypes = [POINTER(GRNG_Workbench), c_int]
        self.lib.add_object.restype = c_bool
        self.lib.clear_object.argtypes = [POINTER(GRNG_Workbench), c_int]
        self.lib.clear_object.restype = c_bool
        self.lib.delete_object.argtypes = [POINTER(GRNG_Workbench), c_int]
        self.lib.delete_object.restype = c_bool
        self.lib.set_label.argtypes = [POINTER(GRNG_Workbench), c_int, c_int, 
            c_char_p]
        self.lib.set_label.restype = None
        self.lib.get_label.argtypes = [POINTER(GRNG_Workbench), c_int, c_int]
        self.lib.get_label.restype = c_char_p
        self.lib.steadystate_solve_base.argtypes = [POINTER(GRNG_Workbench)]
        self.lib.steadystate_solve_base.restype = c_int
        self.lib.steadystate_solve_single_ctg.argtypes = [POINTER(GRNG_Workbench), 
            c_int]
        self.lib.steadystate_solve_single_ctg.restype = c_int
        self.lib.steadystate_solve_all_ctg.argtypes = [POINTER(GRNG_Workbench)]
        self.lib.steadystate_solve_all_ctg.restype = c_int
        self.lib.solve_linear_program_simplex.argtypes = [POINTER(GRNG_Workbench), 
            c_int, c_int, POINTER(GRNG_LP_Variable), POINTER(c_double), 
            POINTER(c_double)]
        self.lib.solve_linear_program_simplex.restype = c_int
        self.lib.do_scopf.argtypes = [POINTER(GRNG_Workbench), c_char_p]
        self.lib.do_scopf.restype = c_int
        self.lib.do_planning_sensitivity.argtypes = [POINTER(GRNG_Workbench), c_int,
            c_int, POINTER(c_int), c_int, POINTER(c_int), POINTER(c_int), 
            POINTER(c_double)]
        self.lib.do_planning_sensitivity.restype = c_int
        self.lib.get_planning_limits.argtypes = [POINTER(GRNG_Workbench), 
            POINTER(c_double), POINTER(c_double)]
        self.lib.get_planning_limits.restype = c_int
        self.lib.read_engine_log.argtypes = [POINTER(GRNG_Workbench), c_char_p,
            c_int]
        self.lib.read_engine_log.restype = c_int
        self.lib.flat_system.argtypes = [POINTER(GRNG_Workbench)]
        self.lib.flat_system.restype = None
        self.lib.write_dcpf_matrix.argtypes = [POINTER(GRNG_Workbench), c_char_p]
        self.lib.write_dcpf_matrix.restype = c_int
        self.lib.do_delaunay.argtypes = [c_int, POINTER(c_double), POINTER(c_double),
            c_int, POINTER(c_int), POINTER(c_int)]
        self.lib.do_delaunay.restype = c_int

    def initialize(self):
        if self.ewb is not None:
            self.lib.destroy_workbench(self.ewb)
            self.ewb = None
        self.ewb = self.lib.create_workbench()
        for i, bus in enumerate(self.wb.buses):
            bus.GRNG_idx = i
            self.lib.add_object(self.ewb, OBJ_BUS)
        for i, branch in enumerate(self.wb.branches):
            branch.GRNG_idx = i
            self.lib.add_object(self.ewb, OBJ_BRANCH)
        for i, gen in enumerate(self.wb.gens):
            gen.GRNG_idx = i
            self.lib.add_object(self.ewb, OBJ_GEN)
        for i, area in enumerate(self.wb.areas):
            area.GRNG_idx = i
            self.lib.add_object(self.ewb, OBJ_AREA)
        for i, sub in enumerate(self.wb.subs):
            sub.GRNG_idx = i
            self.lib.add_object(self.ewb, OBJ_SUB)
        if hasattr(self.wb, "ctg_set"):
            ielem = 0
            for i, ctg in enumerate(self.wb.ctg_set.contingencies):
                ctg.GRNG_idx = i
                self.lib.add_object(self.ewb, OBJ_CTG)
                for action in ctg.actions:
                    action.GRNG_idx = ielem
                    ielem += 1
                    self.lib.add_object(self.ewb, OBJ_CTGELEM)

    def send_data(self):
        if self.ewb == None:
            return
        
        na = self.lib.count_object(self.ewb, OBJ_AREA)
        for area in self.wb.areas:
            if hasattr(area, "GRNG_idx") and 0 <= area.GRNG_idx < na:
                self.ewb.contents.net.areas[area.GRNG_idx].id = area.number

        nsu = self.lib.count_object(self.ewb, OBJ_SUB)
        for sub in self.wb.subs:
            if hasattr(sub, "GRNG_idx") and 0 <= sub.GRNG_idx < nsu:
                GRNG_sub = self.ewb.contents.net.subs[sub.GRNG_idx]
                GRNG_sub.id = sub.number
                GRNG_sub.latitude = sub.latitude
                GRNG_sub.longitude = sub.longitude

        nb = self.lib.count_object(self.ewb, OBJ_BUS)
        for bus in self.wb.buses:
            if hasattr(bus, "GRNG_idx") and 0 <= bus.GRNG_idx < nb:
                GRNG_bus = self.ewb.contents.net.buses[bus.GRNG_idx]
                GRNG_bus.id = bus.number
                GRNG_bus.angle = bus.vang * pi / 180.0
                GRNG_bus.mag = bus.vpu
                GRNG_bus.area = bus.area.GRNG_idx
                GRNG_bus.psload = sum(ld.ps for ld in bus.loads) / 100.0
                GRNG_bus.qsload = sum(ld.qs for ld in bus.loads) / 100.0
                GRNG_bus.qshunt = sum(sh.qnom for sh in bus.shunts) / 100.0
                GRNG_bus.basekv = bus.nominal_kv
                GRNG_bus.lmp = 0
        
        nbr = self.lib.count_object(self.ewb, OBJ_BRANCH)
        for br in self.wb.branches:
            if hasattr(br, "GRNG_idx") and 0 <= br.GRNG_idx < nbr:
                GRNG_br = self.ewb.contents.net.branches[br.GRNG_idx]
                GRNG_br.bus1 = br.from_bus.GRNG_idx
                GRNG_br.bus2 = br.to_bus.GRNG_idx
                GRNG_br.status = 1 if br.status else 0
                GRNG_br.x = br.X
                GRNG_br.r = br.R
                GRNG_br.b = br.B
                GRNG_br.g = br.G
                GRNG_br.tap = br.tap
                GRNG_br.phase = br.phase / 180.0 * pi
                GRNG_br.slimit = br.MVA_Limit_A / 100.0
                GRNG_br.ckt = br.id.encode("ascii")

        ng = self.lib.count_object(self.ewb, OBJ_GEN)
        for gen in self.wb.gens:
            if hasattr(gen, "GRNG_idx") and 0 <= gen.GRNG_idx < ng:
                GRNG_gen = self.ewb.contents.net.gens[gen.GRNG_idx]
                GRNG_gen.id = gen.id.encode("ascii")
                GRNG_gen.bus = gen.bus.GRNG_idx
                GRNG_gen.status = GEN_STATUS_VAR_PQ if gen.status else \
                    GEN_STATUS_OPEN
                GRNG_gen.busreg = self.wb.bus(gen.reg_bus_num).GRNG_idx
                GRNG_gen.p = gen.p / 100.0
                GRNG_gen.q = gen.q / 100.0
                GRNG_gen.pmin = gen.pmin / 100.0
                GRNG_gen.pmax = gen.pmax / 100.0
                GRNG_gen.qmin = gen.qmin / 100.0
                GRNG_gen.qmax = gen.qmax / 100.0
                GRNG_gen.vset = gen.reg_pu_v
                GRNG_gen.partfac = gen.sbase
                GRNG_gen.costtable = -1
                GRNG_gen.regfac = 1

        nc = self.lib.count_object(self.ewb, OBJ_CTG)
        nce = self.lib.count_object(self.ewb, OBJ_CTGELEM)
        ice = 0
        if hasattr(self.wb, "ctg_set"):
            for ic in range(nc):
                GRNG_ctg = self.ewb.contents.steady.ctgs[ic]
                gwb_ctg = self.wb.ctg_set.contingencies[ic]
                GRNG_ctg.nislands = -1
                GRNG_ctg.nvios = 0
                GRNG_ctg.rebuild_flag = -1
                GRNG_ctg.regulation_stuck_flag = -1
                GRNG_ctg.solved = -1
                GRNG_ctg.unserved_load = 0
                for action in gwb_ctg.actions:
                    command = action.command.split()
                    obj = action.object.split()
                    GRNG_ctg_elem = self.ewb.contents.steady.ctgelems[ice]
                    GRNG_ctg_elem.ctg = ic
                    if command[0] == "OPEN" and obj[0] == "BRANCH":
                        GRNG_ctg_elem.code = 4
                        GRNG_ctg_elem.id = self.wb.branch(int(obj[1]), int(obj[2]), 
                            obj[3]).GRNG_idx
                        GRNG_ctg_elem.val = 0
                    elif command[0] == "OPEN" and obj[0] == "GEN":
                        GRNG_ctg_elem.code = 3
                        GRNG_ctg_elem.id = self.wb.gen(int(obj[1]), obj[2]).GRNG_idx
                        GRNG_ctg_elem.val = 0
                    else:
                        GRNG_ctg_elem.code = 0
                        GRNG_ctg_elem.id = 0
                        GRNG_ctg_elem.val = 0
                    ice += 1
                GRNG_ctg.pce = ice

    def get_data(self): # Note: this only retrieves the relevant power flow solution
        if self.ewb == None:
            return
        
        #na = self.lib.count_object(self.ewb, OBJ_AREA)
        #for area in self.wb.areas:
        #    if hasattr(area, "GRNG_idx") and 0 <= area.GRNG_idx < na:
        #        #self.ewb.contents.net.areas[area.GRNG_idx].id = area.number
        #        pass # No data to retrieve from areas

        #nsu = self.lib.count_object(self.ewb, OBJ_SUB)
        #for sub in self.wb.subs:
        #    if hasattr(sub, "GRNG_idx") and 0 <= sub.GRNG_idx < nsu:
        #        GRNG_sub = self.ewb.contents.net.subs[sub.GRNG_idx]
        #        #GRNG_sub.id = sub.number
        #        #GRNG_sub.latitude = sub.latitude
        #        #GRNG_sub.longitude = sub.longitude

        nb = self.lib.count_object(self.ewb, OBJ_BUS)
        for bus in self.wb.buses:
            if hasattr(bus, "GRNG_idx") and 0 <= bus.GRNG_idx < nb:
                GRNG_bus = self.ewb.contents.net.buses[bus.GRNG_idx]
                #GRNG_bus.id = bus.number
                bus.vang = 180.0 / pi * GRNG_bus.angle
                bus.vpu = GRNG_bus.mag
                #GRNG_bus.area = bus.area.GRNG_idx
                #GRNG_bus.psload = sum(ld.ps for ld in bus.loads) / 100.0
                #GRNG_bus.qsload = sum(ld.qs for ld in bus.loads) / 100.0
                #GRNG_bus.qshunt = sum(sh.qnom for sh in bus.shunts) / 100.0
                #GRNG_bus.basekv = bus.nominal_kv
                bus.lmp = GRNG_bus.lmp
        
        nbr = self.lib.count_object(self.ewb, OBJ_BRANCH)
        for br in self.wb.branches:
            if hasattr(br, "GRNG_idx") and 0 <= br.GRNG_idx < nbr:
                GRNG_br = self.ewb.contents.net.branches[br.GRNG_idx]
                br.p1 = GRNG_br.p1 * 100.0
                br.q1 = GRNG_br.q1 * 100.0
                br.p2 = GRNG_br.p2 * 100.0
                br.q2 = GRNG_br.q2 * 100.0
                br.smaxctg = GRNG_br.smaxctg * 100.0
                #GRNG_br.bus1 = br.from_bus.GRNG_idx
                #GRNG_br.bus2 = br.to_bus.GRNG_idx
                #GRNG_br.status = 1 if br.status else 0
                #GRNG_br.x = br.X
                #GRNG_br.r = br.R
                #GRNG_br.b = br.B
                #GRNG_br.g = br.G
                #GRNG_br.tap = br.tap
                #GRNG_br.phase = br.phase / 180.0 * pi
                #GRNG_br.slimit = br.MVA_Limit_A
                #GRNG_br.ckt = br.id.encode("ascii")

        ng = self.lib.count_object(self.ewb, OBJ_GEN)
        for gen in self.wb.gens:
            if hasattr(gen, "GRNG_idx") and 0 <= gen.GRNG_idx < ng:
                GRNG_gen = self.ewb.contents.net.gens[gen.GRNG_idx]
                #GRNG_gen.id = gen.id.encode("ascii")
                #GRNG_gen.bus = gen.bus.GRNG_idx
                #GRNG_gen.status = GEN_STATUS_VAR_PQ if gen.status else GEN_STATUS_OPEN
                #GRNG_gen.busreg = self.wb.bus(gen.reg_bus_num).GRNG_idx
                gen.p = 100.0*GRNG_gen.p
                gen.q = 100.0*GRNG_gen.q
                #GRNG_gen.pmin = gen.pmin / 100.0
                #GRNG_gen.pmax = gen.pmax / 100.0
                #GRNG_gen.qmin = gen.qmin / 100.0
                #GRNG_gen.qmax = gen.qmax / 100.0
                #GRNG_gen.vset = gen.reg_pu_v
                #GRNG_gen.partfac = gen.sbase
                #GRNG_gen.costtable = -1
                #GRNG_gen.regfac = 1

        nv = self.lib.count_object(self.ewb, OBJ_CTGVIO)
        vlist = self.wb.grid_engine.ewb[0].steady.ctgvios
        branches = list(self.wb.branches)
        buses = list(self.wb.buses)
        if self.wb.ctg_set is not None:
            self.wb.ctg_set.base_vios = []
            for ctg in self.wb.ctg_set.contingencies:
                ctg.violations = []
            for iv in range(nv):
                v = ContingencyViolation()
                v.value = vlist[iv].value
                if vlist[iv].code == CTGVIO_CODE_NOT_SOLVED:
                    v.type = "NOTSOLVED"
                    v.obj = None
                elif vlist[iv].code == CTGVIO_CODE_BRANCH_MVA:
                    v.type = "BRANCHMVA"
                    v.obj = branches[vlist[iv].id]
                    v.value *= 100.0
                elif vlist[iv].code == CTGVIO_CODE_BUS_HIGHV:
                    v.type = "HIGHV"
                    v.obj = buses[vlist[iv].id]
                elif vlist[iv].code == CTGVIO_CODE_BUS_LOWV:
                    v.type = "LOWV"
                    v.obj = buses[vlist[iv].id]
                if vlist[iv].ctg == -1:
                    self.wb.ctg_set.base_vios.append(v)
                else:
                    c = self.wb.ctg_set.contingencies[vlist[iv].ctg]
                    c.violations.append(v)
                    v.contingency = c

    # Need to implement shunts with continuous control capability
    # Still need to implement solution tools as nice functions

    def solve_base(self):
        return self.lib.steadystate_solve_base(self.ewb)

    def solve_single_ctg(self, ictg):
        return self.lib.steadystate_solve_single_ctg(self.ewb, ictg)

    def solve_all_ctg(self):
        return self.lib.steadystate_solve_all_ctg(self.ewb)

    def planning_sensitivity(self, ctg, monitor, add):
        # ctg must be a single contingency object
        # monitor must be a list with n branches to monitor
        # add must be a list with m branches to add
        # sets the sensitivity variable for the branch
        mon_array = (c_int * len(monitor))()
        for i, br in enumerate(monitor):
            mon_array[i] = br.GRNG_idx
        add1 = (c_int * len(add))()
        add2 =  (c_int * len(add))()
        for i, a in enumerate(add):
            add1[i] = a.from_bus.GRNG_idx
            add2[i] = a.to_bus.GRNG_idx
        sensitivity = (c_double * len(add))()
        self.lib.do_planning_sensitivity(self.ewb, ctg.GRNG_idx, len(monitor),
            mon_array, len(add), add1, add2, sensitivity)
        return [float(s) for s in sensitivity]

    def planning_limits(self):
        ng = self.lib.count_object(self.ewb, OBJ_GEN)
        gmin = (c_double*ng)()
        gmax = (c_double*ng)()
        self.lib.get_planning_limits(self.ewb, byref(gmin), byref(gmax))
        for i in range(ng):
            self.wb.gens[i].GRNG_planning_qmin = gmin[i]*100
            self.wb.gens[i].GRNG_planning_qmax = gmax[i]*100

    def __del__(self):
        if self.ewb is not None:
            self.lib.destroy_workbench(self.ewb)
            self.ewb = None

def setup_engine(self, engine_dll_fname=None):
    if engine_dll_fname is None:
        engine_dll_fname = \
            os.path.abspath(r"..\GridEngine\x64\Release\GridEngine.dll")
        if not os.path.exists(engine_dll_fname):
            engine_dll_fname = os.path.abspath(r".\engine_library\GridEngine.dll")
        if not os.path.exists(engine_dll_fname):
            engine_dll_fname = os.path.abspath(os.path.abspath(
                os.path.dirname(__file__))+"\..\engine_library\GridEngine.dll")
    self.grid_engine = GridEngine(self, engine_dll_fname)
    if not hasattr(self, "ctg_set"):
        self.ctg_set = ContingencySet()
    

    