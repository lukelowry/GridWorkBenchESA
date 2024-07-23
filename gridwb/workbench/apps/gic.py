from numpy import array, ones, zeros, zeros_like, ones_like, diagflat, arange, eye
from numpy import min, max, sign, nan, pi, sqrt, abs, sin, cos, isnan
from numpy import unique, concatenate, sort, all, diag_indices, diff, expand_dims, repeat
from numpy import any, delete, where, argwhere, argmax, sum, percentile, array_equal
from numpy import errstate, vectorize
from numpy.linalg import inv

from pandas import DataFrame, read_csv, MultiIndex
from scipy.sparse import coo_matrix, lil_matrix
from enum import Enum, auto
from itertools import product

# WorkBench Imports
from .app import PWApp
from ..grid.components import GIC_Options_Value, GICInputVoltObject
from ..grid.components import GICXFormer, Branch, Substation, Bus, Gen
from ..core.powerworld import PowerWorldIO
from ..utils.datawiz import jac_decomp


from scipy.sparse.linalg import inv as sinv 

fcmd = lambda obj, fields, data: f"SetData({obj}, {fields}, {data})".replace("'","")
gicoption = lambda option, choice: fcmd("GIC_Options_Value",['VariableName', 'ValueField'], [option, choice])

# Dynamics App (Simulation, Model, etc.)
class GIC(PWApp):
    io: PowerWorldIO

    def gictool(self, calc_all_windings = False):
        '''Returns a new instance of GICTool, which creates various matricies and metrics regarding GICs.
        Don't set calc_all_windings=True unless you must
        '''

        gicxfmrs = self.dm.get_df(GICXFormer)
        branches = self.dm.get_df(Branch)
        gens = self.dm.get_df(Gen)
        subs = self.dm.get_df(Substation)
        buses = self.dm.get_df(Bus)

        return GICTool(gicxfmrs, branches, gens, subs, buses, customcalcs=calc_all_windings)


    def storm(self, maxfield: float, direction: float, solvepf=True) -> None:
        '''Configure Synthetic Storm with uniform Electric Field to be used in power flow.

        Parameters
        maxfield: Maximum Electric Field magnitude in Volts/km
        direction: Storm direction in Degrees (0-360)
        solvepf: Use produced results in Power Flow
        '''

        self.io.esa.RunScriptCommand(f"GICCalculate({maxfield}, {direction}, {'YES' if solvepf else 'NO'})")

    def cleargic(self):
        '''Clear the GIC Calculations'''
        self.io.esa.RunScriptCommand(f"GICClear;")

    def loadb3d(self, ftype, fname, setuponload=True):
        '''Load B3D File for an Electric Field'''
        b = "YES" if setuponload else "NO"
        self.io.esa.RunScriptCommand(f"GICLoad3DEfield({ftype},{fname},{b})")

    def minkv(self, kv):
        '''Set the minimum KV of lines to contribute to GIC Calculations'''
        pass

    def multiline(self):
        # TODO a function to do things to multi-lines
        pass

    def dBounddI(eta, J, V):
        ''' Interface Sensitivity w.r.t Transformer GIC Currents
        Parameters:
        - eta: (nx1) Numpy Vector of Injection
        - J: (nxn) Full AC Powerflow Jacobian at Boundary
        - V: (nx1) Bus Voltage Magnitudes
        Returns:
        - (1xn) Numpy Array of Sensitivites
        '''

        PT, PV, QT, QV = jac_decomp(J)
        QVi = sinv(QV.tocsc())
        return eta.T@PV@QVi@diagflat(V)
    
    def dIdE(dBdI, PX, Hx, Hy, Ex, Ey):
        '''Returns tuple (Ex Sensitivities, Ey Sensitivities) w.r.t Bus GIC load model
        which is presumed to be constant reactive current. Differential 1-Form
        Parameters:
        - dBdI: (nx1) Interface Sensitivity to Bus GIC Loads
        - Px: (ixn) Permutation Matrix Mapping XFMRs to GIC-Bearing Bus
        - Hx: (nxk) Flattened Tessalized Ex -> Signed XFMR GIC Matrix
        - Hy: (nxk) Flattened Tessalized Ey -> Signed XFMR GIC Matrix
        - Ex: (kx1) Flattened Tessalized Ex Magnitudes
        - Ey: (kx1) Flattened Tessalized Ey Magnitudes
        Returns:
        - ((1xn) , (1xn)) Tuple of sensitivities of XFMR GICs to Ex and Ey
        '''

        '''
        Old, do not modify
        sf0 = sign(Hx@Ex + Hy@Ey)
        signBound = sign(dBdI@Px).T
        F = diagflat(sf0*signBound)
        return (dBdI@Px@F@Hx).T, (dBdI@Px@F@Hy).T
        '''
    
        # The sign of function inside absolute value at this solution point
        sf0 = sign(Hx@Ex + Hy@Ey) # NOTE possible issue here ahhhh I need the individual signs of Ex and Ey
  
        # dBound/dXFMR Signs
        g0 = dBdI@PX
        signBound = sign(g0).T

        # Sign flipper for abs (flip if gradient and function sign disagree)
        F = diagflat(sf0*signBound)

        # 1-Form Differential as tuple
        return (g0@F@Hx).T, (g0@F@Hy).T
    

    # BELOW IS FOR ADVANCED SETTINGS

    def settings(self, value=None):
        '''View Settings or pass a DF to Change Settings'''
        if value is None:
            return self.io.esa.GetParametersMultipleElement(
                GIC_Options_Value.TYPE, 
                GIC_Options_Value.fields
            )[['VariableName', 'ValueField']]
        else:
            self.io.upload({GIC_Options_Value: value})


    def calc_mode(self, mode: str):
        """GIC Calculation Mode (Either SnapShot, TimeVarying, 
        NonUniformTimeVarying, or SpatiallyUniformTimeVarying)"""

        self.io.esa.RunScriptCommand(gicoption("CalcMode",mode))

    def pf_include(self, include=True):
        '''Enable GIC for Power Flow Calculations'''
        self.io.esa.RunScriptCommand(gicoption("IncludeInPowerFlow",include))

    def ts_include(self, include=True):
        '''Enable GIC for Time Domain'''
        self.io.esa.RunScriptCommand(gicoption("IncludeTimeDomain",include))

    def timevary_csv(self, fpath):
        '''Pass a CSV filepath to upload Time Varying 
        Series Voltage Inputs for GIC
        
        Format Example

        Time In Seconds, 1, 2, 3
        Branch '1' '2' '1', 0.1, 0.11, 0.14
        Branch '1' '2' '2', 0.1, 0.11, 0.14
        Branch '1' '2' '3', 0.1, 0.11, 0.14
        
        '''

        # Get CSV Data
        csv = read_csv(fpath, header=None)

        # Format for PW
        obj = GICInputVoltObject.TYPE
        fields = ['WhoAmI'] + [f'GICObjectInputDCVolt:{i+1}' for i in range(csv.columns.size-1)]

        # Send Field Data
        for row in csv.to_records(False):
            cmd = fcmd(obj, fields, list(row)).replace("'", "")
            self.io.esa.RunScriptCommand(cmd)

        print("GIC Time Varying Data Uploaded")
    
    def divergence(u, v):

        divx = diff(u[:,:1],axis=0) + diff(u[:,:-1],axis=0) 
        divy = diff(v[1:],axis=1) + diff(v[:-1],axis=1) 
        
        return divx + divy

    def curl(u, v):
        
        a = diff(u,axis=0) #(dy)u
        b = (a[:,:-1] + a[:,1:])/2 # (mux)(dy)(u)

        c = diff(v,axis=1) #(dx)v
        d = (c[:-1] + c[1:])/2 #(muy)(dx)v

        return d-b



class XFWiringType(Enum):
    GWYE = auto()
    WYE = auto()
    DELTA = auto()

    @staticmethod
    def from_str(label):
        label = label.lower()
        if label in ('gwye'):
            return XFWiringType.GWYE
        elif label in ('wye'):
            return XFWiringType.WYE
        elif label in ('delta'):
            return XFWiringType.DELTA
        else:
            raise NotImplementedError

# Custom Winding Class
class Winding:

    def __init__(self, busnum: int, subnum: int, R: float, cfg, nomvolt: float):

        # Winding Resistance and Conductance
        self.R = R
        self.G = 1/R

        # Substation Number and Bus Number (Convert to int if string)
        self.subnum = int(subnum)
        self.busnum = int(busnum)

        # Wiring
        self.wiring = self.__ascfg(cfg)

        # Voltage kV
        self.nomvolt = nomvolt
    
    
    def __ascfg(self, val):

        if type(val) is XFWiringType:
            return val
        else:
            return XFWiringType.from_str(val)

class ParsingXFMR:

    def __init__(self, id, hv_winding: Winding, lv_winding: Winding, isauto, isblocked, mvabase, kparam, primarybus, secondarybus):

        self.id = id

        self.hv_winding = hv_winding
        self.lv_winding = lv_winding

        self.highnomv = hv_winding.nomvolt
        self.tapratio = hv_winding.nomvolt/lv_winding.nomvolt

        self.isauto = self.__asbool(isauto)
        self.isblocked = self.__asbool(isblocked)

        self.mvabase = mvabase
        self.kparam = kparam

        self.primarybus = primarybus 
        self.secondarybus = secondarybus

    def __asbool(self, val):
        
        vtype = type(val)
        
        if vtype is bool:
            return val 
        elif vtype is str:
            return val.lower()=='yes'
        else:
            return 0


class GICTool:
    '''Generatic GIC Helper Object that creates common matricies and calculations'''

    # TODO branch removal if un-needed

    def __init__(self, gicxfmrs, branches, gens, substations, buses, customcalcs=False) -> None:
        
        # Now Return Incidence and branch info
        self.gicxfmrs: DataFrame = gicxfmrs.copy()
        self.branches: DataFrame = branches
        self.gens: DataFrame = gens
        self.subs: DataFrame = substations
        self.buses: DataFrame = buses

        # Self-Calculate Windings:
        # It works but no gaurentee on reliability
        self.customcalcs = customcalcs

        # Bus mapping only for final loss assignment
        busmap = {n: i for i, n in enumerate(buses['BusNum'])}
        self.busmap = vectorize(lambda n: busmap[n])
        self.nallbus = len(busmap)

        # Formatted in Managable Way
        self.cleaned_xfmrs: list[ParsingXFMR] = self.init_xfmr_data()

        # Go Through windings and 'turn them into' branches
        self.winding_data = self.init_windings()

        # Extract (Line, Series Cap, etc) Non XFMR data
        self.line_data = self.init_normal_branches(branches) 

        # Generator Stepup conductance
        self.gen_stepup_data = self.init_genstepup()

        # Incidence matrix! 
        self.init_incidence()

        # Tap Ratios, Bases, Etc
        self.init_xfmr_params()

        # Branch Permutation selector for low and high XFMR flows
        self.init_PLH()

        # Get Relevant Substation Grounding
        self.init_substation()

        # Create Full Conductance matrix
        self.init_gmatrix()

    def init_xfmr_data(self):

        # Will Calculate GIC Coils if needed
        if self.customcalcs:
            self.init_calc_windings()

        # Divide R by 3 to get the 3-phase resistance
        self.gicxfmrs['GICXFCoilR1'] /= 3 # HV Resistance
        self.gicxfmrs['GICXFCoilR1:1'] /= 3 # LV Resistance

        
        '''Cleans Transformer Data for GIC use'''
        
        winding_fields = ['BusNum3W', 
                          'SubNum', 
                          'GICXFCoilR1', 
                          'XFConfiguration', 
                          'BusNomVolt']
        common_fields = ['XFIsAutoXF', 
                         'GICBlockDevice', 
                         'GICXFMVABase',
                         'GICModelKUsed',
                         'BusNum3W:4', 
                         'BusNum3W:5'
                         ]

        hv_fields = winding_fields
        lv_fields = [f + ':1' for f in winding_fields]

        

        # Iterate Through Transformers
        formatted_xfmrs = []
        for index, xfmr in self.gicxfmrs.iterrows():
            
            # Create HV and LV Windings
            hw = Winding(*xfmr[hv_fields])
            lw = Winding(*xfmr[lv_fields])

            # Create XFMR
            formatted_xfmrs.append(ParsingXFMR(index, hw, lw,*xfmr[common_fields]))
        
        self.nxfmrs = len(formatted_xfmrs)

        return formatted_xfmrs

    def init_calc_windings(self):
        '''Manual Winding Calculations - Redundant but helps with PW verification'''

        # The following calculates winding resistances for transformers with no manual GIC data
        isXFMR = self.branches['BranchDeviceType']=='Transformer'
        xfmrs = self.branches[isXFMR].copy()

        fromV = xfmrs['BusNomVolt']
        toV = xfmrs['BusNomVolt:1']
        hv = max([fromV, toV],axis=0)
        lv = min([fromV, toV],axis=0)

        xfmrs['N'] = hv/lv
        xfmrs['LowBase'] = lv**2/xfmrs['XFMVABase']
        xfmrs['HighBase'] = hv**2/xfmrs['XFMVABase']

        
        # HV Assignment (Where equal, use primary/FROM)
        xfmrs.loc[:,'BusNum3W'] = where(fromV>toV, xfmrs['BusNum'], xfmrs['BusNum:1']) 
        xfmrs.loc[fromV==toV,'BusNum3W'] = xfmrs.loc[fromV==toV,'BusNum'] 

        # LV Assignment (Where voltages equal, use secondary/TO)
        xfmrs.loc[:,'BusNum3W:1'] = where(fromV<toV, xfmrs['BusNum'], xfmrs['BusNum:1'])
        xfmrs.loc[fromV==toV,'BusNum3W:1'] = xfmrs.loc[fromV==toV,'BusNum:1']

        # Tertiary Asssigment
        xfmrs.loc[:,'BusNum3W:2'] = 0 # NOTE - THIS ONLY WORKS IF THERE ARE NO THREE WINDING XFMRS

        # Set Multi Index Between DFs so they can be compared
        mergekeys = GICXFormer.keys + ['LineCircuit']
        xfmrs.set_index(mergekeys, inplace=True)
        self.gicxfmrs.set_index(mergekeys, inplace=True)

        manualGIC = self.gicxfmrs['GICManualCoilR']=='No'
        replaceFields = ['N', 'LowBase', 'HighBase', 'LineR:1']
        self.gicxfmrs.loc[manualGIC,replaceFields] = nan 
        self.gicxfmrs = self.gicxfmrs.combine_first(xfmrs[replaceFields])
        self.gicxfmrs.reset_index(inplace=True)

        g = self.gicxfmrs
        # LineR:1 is R on xfmr base
        isAuto = g['XFIsAutoXF']=='Yes'
        isDeltaHigh_WyeLow = (g['XFConfiguration']=='Delta') & (g['XFConfiguration:1']=='Gwye')
        base = where(isDeltaHigh_WyeLow & isAuto, g['LowBase'], g['HighBase'])

        RHigh = g['LineR:1']*base/2 #< ---- HV R Calc (Works for HV Side for Delta-Wye)
        RLow = RHigh/(g['N']-1)**2 # < --- LV Calc

        # Ohms (Per Phase) 
        # For Auto transformers of GWye-Delta or Delta-GWye, select the primary as high
        g['GICXFCoilR1'] = where(isDeltaHigh_WyeLow & isAuto, RLow, RHigh) # HV Resistance
        g['GICXFCoilR1:1'] = where(isDeltaHigh_WyeLow & isAuto, RHigh, RLow) # LV Resistance

    def init_windings(self):
        '''Substation Branch Connections are represented as negative integers'''

        # Substations are the first group of nodes
        tonodes = []
        fromnodes = []
        Gbranch = []
        self.n_windings_added = 0

        def addWinding(fromnode, tonode, G):
            fromnodes.append(fromnode)
            tonodes.append(tonode)
            Gbranch.append(G)
            self.n_windings_added += 1


        self.LVMap = ([],[],[])
        self.HVMap = ([],[],[])

        def addLow(xfmrid, offset=0, val=1):
            x, y, data = self.LVMap
            x.append(xfmrid)
            y.append(self.n_windings_added+offset)
            data.append(val)

        def addHigh(xfmrid, offset=0, val=1):
            x, y, data = self.HVMap
            x.append(xfmrid)
            y.append(self.n_windings_added+offset)
            data.append(val)
        

        for i, xfmr in enumerate(self.cleaned_xfmrs):

            lw = xfmr.lv_winding
            hw = xfmr.hv_winding

            if not xfmr.isblocked:

                # Non-Auto, Non-Blocked
                if not xfmr.isauto:

                    if lw.wiring is XFWiringType.GWYE:
                        addLow(i)
                        addWinding(lw.busnum, -lw.subnum, lw.G)
                        
                    if hw.wiring is XFWiringType.GWYE:
                        addHigh(i)
                        addWinding(hw.busnum, -hw.subnum, hw.G)
                        
                # Auto, Non-Blocked
                else:

                    # Edge case where N = 1
                    if lw.G==0 or hw.G==0:

                        # Wye-Wye NOTE DO NOT DELETE somehow it works lol
                        if hw.wiring is XFWiringType.GWYE and lw.wiring is XFWiringType.GWYE:

                            addLow(i)
                            addLow(i, offset=1)
                            addWinding(lw.busnum, -lw.subnum, hw.G)

                            addHigh(i, val=-1)
                            addWinding(lw.busnum, hw.busnum, hw.G)

                    # When N != 1
                    else:

                        # High Wye - Low Delta
                        if hw.wiring is XFWiringType.GWYE and lw.wiring is XFWiringType.DELTA:

                            addHigh(i)
                            addWinding(hw.busnum, -hw.subnum, hw.G)

                        # High Delta - Low Wye
                        if hw.wiring is XFWiringType.DELTA and lw.wiring is XFWiringType.GWYE:

                            addLow(i)
                            addWinding(lw.busnum, -lw.subnum, lw.G)
                        
                        # Wye - Wye Auto
                        if hw.wiring is XFWiringType.GWYE and lw.wiring is XFWiringType.GWYE:

                            addLow(i)
                            addLow(i, offset=1)
                            addWinding(lw.busnum, -lw.subnum, lw.G)

                            addHigh(i, val=-1)
                            addWinding(lw.busnum, hw.busnum, hw.G)
                    
            # Blocked Transformers 
            else:

                # Auto, Blocked
                if xfmr.isauto:

                    # Only Add AutoXFMRS that are gic blocked -Common Coil Only (HV)
                    addHigh(i)
                    addWinding(hw.busnum, -hw.subnum, lw.G)
        
    
        return (fromnodes, tonodes, Gbranch)
 
    def init_normal_branches(self, branches):

        isXFMR = branches['BranchDeviceType']=='Transformer'
        xfmrs = branches[isXFMR]

        # Stupid GIC Object doesn't store FROM bus so doing this
        fields = ['BusNomVolt', 'BusNomVolt:1', 'BusNum', 'BusNum:1', 'LineCircuit']
        xfmrs = xfmrs[fields].copy()
        xfmrs.columns = ['FromV', 'ToV', 'FromBus', 'ToBus', 'LineCircuit']
        fromV = xfmrs['FromV']
        toV = xfmrs['ToV']
        xfmrs['BusNum3W'] = where(fromV>=toV, xfmrs['FromBus'], xfmrs['ToBus'])
        xfmrs['BusNum3W:1'] = where(fromV<toV, xfmrs['FromBus'], xfmrs['ToBus'])
        mapFrom = xfmrs[['FromBus', 'BusNum3W', 'BusNum3W:1', 'LineCircuit']]
        mapFrom = mapFrom.sort_values(['BusNum3W', 'BusNum3W:1','LineCircuit'])
        self.mapFrom = mapFrom

        # Branch Information
        self.lines = branches[~isXFMR]
        gic_branch_data = self.lines[['BusNum', 'BusNum:1', 'GICConductance']]

        fromBus = gic_branch_data['BusNum'].to_numpy()
        toBus = gic_branch_data['BusNum:1'].to_numpy()
        
        # Determine what GIC Conductance to Use
        # NO = Normal Resistance                  YES = Custom GIC Value
        GIC_G = self.lines['GICConductance'] # Manually Entered GIC Resistance
        PF_G = 1/self.lines['GICLinePFR1'] # From Normal Model, per=phase resistance in ohms (MUST CONVERT FROM p.u.) 
        isCustomGIC = self.lines['GICLineUsePFR']=='NO'
        GBranch = 3*where(isCustomGIC, GIC_G, PF_G).astype(float)

        # Line Length and Angle For Tesselations
        self.line_km = self.lines['GICLineDistance:1'].fillna(0).to_numpy()
        self.line_ang = self.lines['GICLineAngle'].fillna(0).to_numpy()*pi/180 # North 0 Degrees
        self.nlines = len(self.lines)

        return (fromBus, toBus, GBranch)
    
    def init_genstepup(self):

        gstu = self.gens[['GICConductance', 'SubNum', 'BusNum']]
        gstu = gstu[gstu['GICConductance']!=0]

        # From Sub, To Bus, Stepup G
        return -gstu['SubNum'].to_numpy(), gstu['BusNum'].to_numpy(), gstu['GICConductance'].to_numpy() #TODO the x3 vs /3 choices are not consisitant between windings, branch and gens

    def init_incidence(self):

        wFrom, wTo, wG = self.winding_data
        lFrom, lTo, lG = self.line_data
        genFrom, genTo, genG = self.gen_stepup_data

        allnodes = unique(concatenate([wFrom, wTo, lFrom, lTo, genFrom, genTo]))

        subIDs = sort(allnodes[allnodes<0])[::-1]
        busIDs = sort(allnodes[allnodes>0])

        nsubs = len(subIDs)
        nbus = len(busIDs)
        nnodes = nsubs + nbus
        nbranchtot= len(wFrom) + len(lFrom) + len(genFrom)

        # Node Map to new Index (Substations are first, then buses)
        nodemap = {n: i for i, n in enumerate(subIDs)}
        for i, n in enumerate(busIDs):
            nodemap[n] = i+nsubs
        vec_nodemap = vectorize(lambda n: nodemap[n])

        # Merge XFMR and Lines and use new mapping
        # NOTE ORDER: Windings, GSU, Lines
        branchIDs = arange(nbranchtot)
        fromNodes = vec_nodemap(concatenate([wFrom, genFrom, lFrom]))
        toNodes = vec_nodemap(concatenate([wTo, genTo, lTo]))

        # Branch Diagonal Matrix Values (3x for single phase equivilent)
        self.GbranchDiag= diagflat(concatenate([wG, genG, lG])) #Hmmmmmmmmm the 3* is not consistant

        # Incidence Matrix (Without Floating Removal)
        self.Ainc = lil_matrix((nbranchtot, nnodes))
        self.Ainc[branchIDs,fromNodes] = 1
        self.Ainc[branchIDs,toNodes] = -1

        # Add to Object
        self.nwinds = len(wG)
        self.ngsu = len(genG)
        self.nsubs = nsubs 
        self.nbus = nbus
        self.subIDs = subIDs
        self.busIDs = busIDs
        self.subIDX = vec_nodemap(subIDs)
        self.busIDX = vec_nodemap(busIDs)

        self.nbranchtot = nbranchtot

    def init_substation(self):
        
        # Get Ground Conductance
        subG = self.subs[['SubNum', 'GICSubGroundOhms']].copy().set_index('SubNum')
        subG = 1/subG
        
        # Get Only values usedDs)
        self.subG = subG.loc[-self.subIDs]['GICSubGroundOhms']

    def init_gmatrix(self):

        # Laplacian Branches
        A = self.Ainc
        G = self.GbranchDiag
        GLap = A.T@G@A 

        # Add Self Loops
        di = diag_indices(len(self.subIDs))
        GLap[di] += self.subG

        self.GLap = GLap
    
    def init_PLH(self):

        shp = (self.nxfmrs,self.nbranchtot)

        x, y, data = self.LVMap
        self.PL = coo_matrix((data,(x,y)), shape=shp)
        
        x, y, data = self.HVMap
        self.PH = coo_matrix((data,(x,y)), shape=shp)

    def init_xfmr_params(self):

        # Tap Ratios
        tr = [xfmr.tapratio for xfmr in self.cleaned_xfmrs]
        self.TR = diagflat(tr)

        # DC Current Base
        bases = [xfmr.mvabase * 1e3 * sqrt(2/3) /xfmr.highnomv for xfmr in self.cleaned_xfmrs]
        self.Ibase = diagflat(bases)

        # K model values
        k = [xfmr.kparam for xfmr in self.cleaned_xfmrs]
        self.Kdiag = diagflat(k)

        # Map XFMR Loss to Buses (From for XFMRS)
        self.fromIDX = self.busmap(self.mapFrom['FromBus'])
        self.xfmrIDs = arange(self.nxfmrs)
        ONE = ones_like(self.xfmrIDs)

        shp = (self.nallbus, self.nxfmrs)
        self.PX = coo_matrix((ONE, (self.fromIDX,self.xfmrIDs)), shape=shp)
        
    # Below are accessing tools (Don't know best way yet)
    # Final step causes some problems, summing on busses

    def Hmat(self, reduceXFMR=True):
        '''
        Returns H Matrix, which maps line voltages to transformer GICS scaled by K (pre-absolute value)
        If the induced XFMR winginds are zero due to no length we can reduce matrix'''

        Gd = self.GbranchDiag
        A = self.Ainc
        Gmat = self.GLap
        Gi = inv(Gmat)
        PL = self.PL # Low Flow Selector
        PH = self.PH # High Flow Selector
        TRi = inv(self.TR) # Tap Ratios Inverse
        Ibasei = inv(self.Ibase)
        K = self.Kdiag
    
        H = K@Ibasei@(PH + TRi@PL)@(Gd@A@Gi@A.T@Gd - Gd)/3
        if reduceXFMR:
            H = H[:,-self.nlines:]

        return H.A
    
    def IeffMat(self, reduceXFMR=True):
        '''
        Returns a matrix, which maps line voltages to per-unit transformer effective currents (pre-absolute value)
        '''

        Gd = self.GbranchDiag
        A = self.Ainc
        Gmat = self.GLap
        Gi = inv(Gmat)
        PL = self.PL # Low Flow Selector
        PH = self.PH # High Flow Selector
        TRi = inv(self.TR) # Tap Ratios Inverse
        Ibasei = inv(self.Ibase)
    
        M = Ibasei@(PH + TRi@PL)@(Gd@A@Gi@A.T@Gd - Gd)/3
        if reduceXFMR:
            M = M[:,-self.nlines:]
            
        return M.A
    
    def inputvec(self, include_all=False):
        '''Returns vector with default induced voltages (lines only unless specified)'''

        if include_all:
            vec = zeros((self.GbranchDiag.shape[0],1))
            vec[-self.nlines:,0] = self.lines['GICObjectInputDCVolt']
        else:
            vec = zeros((self.nlines,1))
            vec[:,0] = self.lines['GICObjectInputDCVolt']
        return vec
    
    def corner_factory(self):
        '''Return a GICCorner Object that parses possible Efields'''

        H = self.Hmat()
        self.H = H

        # Line Lengths
        line_km = self.lines['GICLineDistance:1'].fillna(0)
        L = diagflat(line_km)
        self.L = L

        # Line Angles
        #line_ang = gictool.lines['GICLineAngle'].fillna(0)*pi/180 # North 0 Degrees
        #ANG = line_ang.to_numpy()

        E = eye(L.shape[0])
        self.E = E

        return GICCorners(H, L, E)

    def tesselations(self, tilewidth=0.5):
        '''Return Tessalized forms of the H matrix for Ex and Ey.'''

        line_km = self.line_km
        line_ang = self.line_ang

        # Seperated by X, Y
        cX = self.lines[['Longitude', 'Longitude:1']].copy().to_numpy()
        cY = self.lines[['Latitude', 'Latitude:1']].copy().to_numpy()

        # Generate Tile Intervals
        W = tilewidth
        X = arange(cX.min(axis=None), cX.max(axis=None)+W, W) 
        Y = arange(cY.min(axis=None), cY.max(axis=None)+W, W)

        # Save for reference if needed
        self.tile_info = X, Y, W

        '''Tile Segment Assignment Matrix'''

        # Store X/Y length in line by line
        # Dim0: X or Y data , Dim 1: Line ID, Dim 2: X Tile, Dim 3: Y Tile
        R = zeros((2, self.lines.index.size, X.size-1, Y.size-1))

        # Approximation of Coords -> KM conversion
        LX = abs(sin(line_ang)*line_km) # 0 is north so sin() is X
        LY = abs(cos(line_ang)*line_km)

        # 'Length' in coordinates
        CLX, CLY = diff(cX),  diff(cY)

        # Intentional -> 'Right' and 'Up' should be positive direction, Converts coords to KM
        with errstate(divide='ignore', invalid='ignore'):
            coord_to_km = concatenate([[LX/CLX[:,0]], [LY/CLY[:,0]]],axis=0)
        coord_to_km[isnan(coord_to_km)] = 0
        coord_to_km = expand_dims(coord_to_km,axis=2)

        # Spanned Area of Line
        lminx = cX.min(axis=1,keepdims=True)
        lmaxx = cX.max(axis=1,keepdims=True)
        lminy = cY.min(axis=1,keepdims=True)
        lmaxy = cY.max(axis=1,keepdims=True)

        # Calculate points of line & tile intersection
        Vx = repeat([X],lminx.size,axis=0)
        Vx[(Vx<=lminx) | (Vx>=lmaxx)] = nan
        with errstate(divide='ignore', invalid='ignore'):
            Vy = CLY/CLX*(Vx-cX[:,[0]]) + cY[:,[0]]

        Hy = repeat([Y],lminx.size,axis=0)
        Hy[(Hy<=lminy) | (Hy >= lmaxy)] = nan
        with errstate(divide='ignore', invalid='ignore'):
            Hx = (Hy-cY[:,[0]])*CLX/CLY + cX[:,[0]]

        # All Segment Points per Line
        pntsX = concatenate([cX, Vx, Hx],axis=1)
        pntsY = concatenate([cY, Vy, Hy],axis=1)

        # Sort Points so segments can be calculated
        sortSeg = pntsX.argsort(axis=1)
        sortLine = arange(lminx.size).reshape(-1,1)
        pntsX = pntsX[sortLine,sortSeg]
        pntsY = pntsY[sortLine,sortSeg]

        # Take line segments and determine tile assignemnt
        allpnts = concatenate([[pntsX],[pntsY]],axis=0)
        mdpnts = (allpnts[:,:,1:] +allpnts[:,:,:-1])/2 # Midpoints of each segment
        isData = argwhere(~isnan(mdpnts)).T # Data Cleaning
        refpnt = array([X.min(),Y.min()]).reshape(2,1,1) # Grid ref point
        tile_ids = (mdpnts-refpnt)//W # Tile Index Floor Divide
        self.tile_ids = tile_ids
        seg_lens = coord_to_km*abs(diff(allpnts,axis=2)) # Length in Tile
        
        # Final Data Format
        R[*isData[:-1],*tile_ids[:,*isData[1:]].astype(int)] = seg_lens[*isData]
        R = R.reshape((2, R.shape[1], R.shape[2]*R.shape[3]), order='F')

        # Ex and Ey Flattened Tile -> Xfmr Matrix
        Rx = R[0]
        Ry = R[1]

        # God Tier H-Matrix
        H = self.Hmat()
        self.Hx, self.Hy = H@Rx, H@Ry

        # Return Tessalised matricies
        return self.Hx, self.Hy # TODO slow, use sparse matricies?
    
    def tesselation_as_df(self):
        '''GICTool.tesselations() must have already been called. Get Index DF Version of Hx, Hy'''

        X, Y, W = self.tile_info
        tile_cols = MultiIndex.from_product(
            [arange(len(X)-1), arange(len(Y)-1)], 
            names=['TileX', 'TileY']
            )
        Xdf = DataFrame(self.Hx, columns = tile_cols)
        Ydf = DataFrame(self.Hy, columns = tile_cols)
        Xdf.index.name = 'XFMR'
        Ydf.index.name = 'XFMR'
        return Xdf, Ydf

class GICCorners:

    def __init__(self, H, L, E) -> None:
        '''
        H: GIC matrix mapping line voltage to transformer currents
        L: Line Lengths in km (Diagonal Matrix)
        E: Electric Field Magnitude Max per line (Diagonal Matrix)
        '''

        # Needed GIC Matricies
        self.H = H
        self.L = L
        self.E = E
        self.HLE = H@L@E

        # Signs of H
        zero_tol = 1e-15
        self.signH = sign(H)
        self.signH[abs(H)<zero_tol] = 0 # Level of tolerance to be considered zero

        # Unique Rows Only - Remove all zero rows
        shu = unique(self.signH,axis=0)
        self.signHUnique = shu[~all(shu==0,axis=1)]
        self.nSHU = self.signHUnique.shape[0]

        # Not necessary unless all corners are wanted
        self.corner_matrix = None

        # Flip matrix takes a while to compute so don't do so unless neeeded
        self._flip_matrix = None

    def corners(self):
        '''Returns Matrix of Corner Permutations or creates it if non-existant'''

        if self.corner_matrix is None:
           
            # Find unique Sign Groups of Columns of H
            PGROUPS = self.find_equivalent_columns(self.HLE)
            nPgroups = len(PGROUPS)

            # CRNR - Group Combinations (Maps Permutation to Sign Group)
            CRNR = zeros((nPgroups,2**nPgroups)) 

            # JOIN - Assigns Combinations to Lines (Maps Sign Group to Lines)
            nlines = self.L.shape[0]
            JOIN = zeros((nlines, nPgroups))

            ''' FILL CORNER DATA '''

            # Creating +- polarity matrix (Columns = Different Possibilities, Rows = Group Sign)
            for i, perm in enumerate(product(*[(1,-1)]*nPgroups)):
                CRNR[:, i] = array(perm)

            # Removing SECOND half of these permutations removes exact negative:
            CRNR = self.remove_negative_columns(CRNR)

            # Creating JOIN - Mapping Group to a Line or leaving out entirely
            for grp, lineIDs in enumerate(PGROUPS):
                refLine = self.signH[:,lineIDs[0]]
                JOIN[lineIDs, grp] = 1

                # Re-Polarize anti-columns
                for id in lineIDs:
                    if (refLine==-self.signH[:,id]).all():
                        JOIN[id, grp] *= -1

            nCRNR = CRNR.shape[1]
            self.corner_matrix = JOIN@CRNR
            print(f'Corners: {nCRNR}')
            
        return self.corner_matrix

    def topology(self, remove_strictly_small = False, top_losses_only = False):
        """
        Calculates the XFMR losses of every corner
        params:
        - remove_strictly_small: Removes any corners that have strictly less losses than some other corner
        - top_losses_only: Returns only corners in the top 10% of net losses
        returns: 
            Matrix (nXFMR x nCorners)
        """

        HLE = self.HLE
        C = self.corner_matrix
        TOPOLOGY = (HLE@C).T

        # Determine if remove corners that are obviously obsolete
        # Remove Corners that are absolutely less than another
        if remove_strictly_small:
            toremove = set()
            TA = abs(TOPOLOGY)
            for i, corner in enumerate(TA):
                isLessThan = all(corner <= TA, axis=1)
                isLessThan[i] = False

                # If there is a corner strictly greater than this one
                if any(isLessThan):
                    toremove.update([i])

            CRNR = delete(CRNR,list(toremove),axis=1)
            TOPOLOGY = delete(TOPOLOGY, list(toremove), axis=0)
            nCRNR = len(TOPOLOGY)

        # Top Percentile
        if top_losses_only:
            NET = sum(abs(TOPOLOGY),axis=1)
            TOP = percentile(NET, q=90)
            TOPI = NET>TOP
            TOPOLOGY = TOPOLOGY[TOPI]

        return TOPOLOGY
    
    @property
    def flip_matrix(self):

        if self._flip_matrix is not None:
            return self._flip_matrix 
        
        '''Return Matrix that performs applicable edge flips'''
        PGROUPS_INITIAL = self.find_equivalent_columns(self.signH)
        PGROUPS = []
        for group in PGROUPS_INITIAL:
            gC = abs(self.HLE[:,group]) # Abs Group Columns
            gC = gC[:,gC[0,:].argsort()]

            # Split group if not strictly increasing
            for i in range(gC.shape[1]-1):
                if (gC[:,i]>gC[:,i+1]).any():
                    PGROUPS += [[g] for g in group]
                    break 
            # Otherwise Preserve
            else:
                PGROUPS += [group]

        FLIP_MATRIX = ones((self.signH.shape[1],len(PGROUPS)))
        for i, group in enumerate(PGROUPS):
            FLIP_MATRIX[group,i] = -1

        self._flip_matrix = (FLIP_MATRIX == -1)
        return self._flip_matrix


    def find_local_max_hist(self, p):
        '''Generative Method to find largest local maximum'''

        lss = sum(abs(self.HLE@p))
        p_n = p*where(self.flip_matrix,-1,1)

        yield (lss, p)

        while True:
            
            NEIGHBIR_LOSSES = sum(abs(self.HLE@p_n),axis=0)
            maxidx = argmax(NEIGHBIR_LOSSES)

            # NOTE I changed this from > to >= - verify it works
            if lss >= (lss := NEIGHBIR_LOSSES[maxidx]):
                break

            #print(NEIGHBIR_LOSSES, end='  ')
            #print(f'{lss:.2f}')
            # Yield is right here so that on last iteration it has maxidx but doesn't return a false positive
            yield (lss, p_n[:,maxidx].copy()) # TODO the memory ref here could be wrong

            # Rapid Update of Adjacent Edges based on path choice
            p_n[self.flip_matrix[:,maxidx],:] *= -1

            # Update Loss of bew location
            #lss = NEIGHBIR_LOSSES[maxidx]

    def greedy_search(self, verbose=True):
        '''Return the total GICs and polarity vector results of greedy search.
        The returned matrix will be similar to the shape of H.
        Columns represent different lines.
        Each row represents the initial guess of a unique row in signH, the set of polairties that
        maximize the GICs on that row's transformer.'''

        totalGICS = zeros(self.nSHU)
        pmaxs = zeros_like(self.signHUnique)

        for i, p in enumerate(self.signHUnique):

            *_,sol = self.find_local_max_hist(p.reshape((-1,1)))
            lss, pmax = sol 

            totalGICS[i] = 100*lss
            pmaxs[i,:] = pmax

            if verbose:
                print(f' Row ({i:03d}/{self.nSHU}) --- Max:{100*lss:.2f}')
        
        return totalGICS, pmaxs

    def remove_negative_columns(self, matrix):
        # Transpose the matrix to make it easier to compare columns
        transposed_matrix = matrix.T
        
        # List to keep columns that are not negatives of others
        columns_to_keep = []
        
        # Set to keep track of indices of columns to be removed
        columns_to_remove = set()
        
        # Iterate over the columns of the transposed matrix
        for i, col in enumerate(transposed_matrix):
            if i not in columns_to_remove:
                for j in range(i + 1, transposed_matrix.shape[0]):
                    if array_equal(col, -transposed_matrix[j]):
                        columns_to_remove.add(j)
        
        # Collect columns that are not in the remove set
        for i in range(transposed_matrix.shape[0]):
            if i not in columns_to_remove:
                columns_to_keep.append(transposed_matrix[i])
        
        # Reconstruct the matrix from the columns to keep
        new_matrix = array(columns_to_keep).T
        
        return new_matrix


    def find_equivalent_columns(self, matrix, tolerance=1e-10):
        '''Tolerance is for identifying zero columns so they are not added'''

        # Transpose the matrix to make it easier to compare columns
        transposed_matrix = matrix.T
        
        # Create a list to store sets of equivalent columns
        equivalent_columns_sets = []
        
        # Create a set to track columns that have already been identified
        identified_columns = set()
        
        # Iterate over the columns of the transposed matrix
        for i, col in enumerate(transposed_matrix):
            if i not in identified_columns and not all(abs(col) < tolerance):
        
                # Find all columns that are identical to the current column and not negatives
                colI = transposed_matrix[i]
                equivalent_columns = []
                
                for j in range(transposed_matrix.shape[0]):
                    colJ = transposed_matrix[j]
            
                    if (colI == colJ).all() or  (colI == -colJ).all():
                        equivalent_columns.append(j)

                # Add the set of equivalent columns to the list
                equivalent_columns_sets.append(equivalent_columns)
                # Mark these columns as identified
                identified_columns.update(equivalent_columns)
        
        return equivalent_columns_sets

