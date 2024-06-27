import numpy as np
import pandas as pd
from typing import Any, Type
from scipy.sparse import coo_matrix, lil_matrix
from enum import Enum, auto


# WorkBench Imports
from .app import PWApp, griditer
from gridwb.workbench.grid.components import GIC_Options_Value, GICInputVoltObject, TSContingency
from gridwb.workbench.plugins.powerworld import PowerWorldIO

fcmd = lambda obj, fields, data: f"SetData({obj}, {fields}, {data})".replace("'","")
gicoption = lambda option, choice: fcmd("GIC_Options_Value",['VariableName', 'ValueField'], [option, choice])

# Dynamics App (Simulation, Model, etc.)
class GIC(PWApp):
    io: PowerWorldIO


    def storm(self, maxfield: float, direction: float, solvepf=True) -> None:
        '''Configure Synthetic Storm with uniform Electric Field to be used in power flow.

        Parameters
        maxfield: Maximum Electric Field magnitude in Volts/km
        direction: Storm direction in Degrees (0-360)
        solvepf: Use produced results in Power Flow
        '''

        self.io.esa.RunScriptCommand(f"GICCalculate({maxfield}, {direction}, {'YES' if solvepf else 'NO'})")

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
        csv = pd.read_csv(fpath, header=None)

        # Format for PW
        obj = GICInputVoltObject.TYPE
        fields = ['WhoAmI'] + [f'GICObjectInputDCVolt:{i+1}' for i in range(csv.columns.size-1)]

        # Send Field Data
        for row in csv.to_records(False):
            cmd = fcmd(obj, fields, list(row)).replace("'", "")
            self.io.esa.RunScriptCommand(cmd)

        print("GIC Time Varying Data Uploaded")


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

    # TODO branch removal if un-needed
    # TODO ABS Q Loss Problem 
    # - We could place Q on either to/from and it shouldn't make a diff
    # - It just won't Align with PW

    def __init__(self, gicxfmrs, branches, substations, buses) -> None:
        
        # Now Return Incidence and branch info
        self.gicxfmrs = gicxfmrs
        self.branches = branches
        self.subs = substations
        self.buses = buses

        # Bus mapping only for final loss assignment
        busmap = {n: i for i, n in enumerate(buses['BusNum'])}
        self.busmap = np.vectorize(lambda n: busmap[n])
        self.nallbus = len(busmap)

        # Formatted in Managable Way
        self.cleaned_xfmrs: list[ParsingXFMR] = self.init_xfmr_data(gicxfmrs)

        # Go Through windings and 'turn them into' branches
        self.winding_data = self.init_windings()

        # Extract (Line, Series Cap, etc) Non XFMR data
        self.line_data = self.init_normal_branches(branches) 

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

    def init_xfmr_data(self, gicxfmrs):
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
                         'BusNum3W:5',
                         ]

        hv_fields = winding_fields
        lv_fields = [f + ':1' for f in winding_fields]

        # Iterate Through Transformers
        formatted_xfmrs = []
        for index, xfmr in gicxfmrs.iterrows():
            
            # Create HV and LV Windings
            hw = Winding(*xfmr[hv_fields])
            lw = Winding(*xfmr[lv_fields])

            # Create XFMR
            formatted_xfmrs.append(ParsingXFMR(index, hw, lw,*xfmr[common_fields]))
        
        self.nxfmrs = len(formatted_xfmrs)

        return formatted_xfmrs

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

                # Traditional GWYE Windings
                if not xfmr.isauto:

                    if lw.wiring is XFWiringType.GWYE:
                        addLow(i)
                        addWinding(lw.busnum, -lw.subnum, lw.G)
                        

                    if hw.wiring is XFWiringType.GWYE:
                        addHigh(i)
                        addWinding(hw.busnum, -hw.subnum, hw.G)
                        

                # Auto Transformers
                else:

                    # Low Coil (Goes to Substation)
                    addLow(i)
                    addLow(i, offset=1)
                    addWinding(lw.busnum, -lw.subnum, lw.G)
                    

                    # Common Coil (Uses HV Winding)
                    addHigh(i, val=-1)
                    addWinding(lw.busnum, hw.busnum, hw.G)
                    
            # Blocked Versions 
            else:

                # Only Add AutoXFMRS that are gic blocked
                if xfmr.isauto:

                    # Common Coil Only (HV)
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
        xfmrs['BusNum3W'] = np.where(fromV>toV, xfmrs['FromBus'], xfmrs['ToBus'])
        xfmrs['BusNum3W:1'] = np.where(fromV<toV, xfmrs['FromBus'], xfmrs['ToBus'])
        mapFrom = xfmrs[['FromBus', 'BusNum3W', 'BusNum3W:1', 'LineCircuit']]
        mapFrom = mapFrom.sort_values(['BusNum3W', 'BusNum3W:1','LineCircuit'])
        self.mapFrom = mapFrom

        # Branch Information
        branches = branches[~isXFMR]
        gic_branch_data = branches[['BusNum', 'BusNum:1', 'GICConductance']]

        fromBus = gic_branch_data['BusNum'].to_numpy()
        toBus = gic_branch_data['BusNum:1'].to_numpy()
        Gbranch = gic_branch_data['GICConductance'].to_numpy()

        self.nlines = len(branches)

        return (fromBus, toBus, Gbranch)
    
    def init_incidence(self):

        wFrom, wTo, wG = self.winding_data
        lFrom, lTo, lG = self.line_data

        allnodes = np.unique(np.concatenate([wFrom, wTo, lFrom, lTo]))

        subIDs = np.sort(allnodes[allnodes<0])[::-1]
        busIDs = np.sort(allnodes[allnodes>0])

        nsubs = len(subIDs)
        nbus = len(busIDs)
        nnodes = nsubs + nbus
        nbranchtot= len(wFrom) + len(lFrom)

        # Node Map to new Index (Substations are first, then buses)
        nodemap = {n: i for i, n in enumerate(subIDs)}
        for i, n in enumerate(busIDs):
            nodemap[n] = i+nsubs
        vec_nodemap = np.vectorize(lambda n: nodemap[n])

        # Merge XFMR and Lines and use new mapping
        branchIDs = np.arange(nbranchtot)
        fromNodes = vec_nodemap(np.concatenate([wFrom,lFrom]))
        toNodes = vec_nodemap(np.concatenate([wTo,lTo]))

        # Branch Diagonal Matrix Values (3x for single phase equivilent)
        self.GbranchDiag= 3*np.diagflat(np.concatenate([wG, lG]))

        # Incidence Matrix (Without Floating Removal)
        self.Ainc = lil_matrix((nbranchtot, nnodes))
        self.Ainc[branchIDs,fromNodes] = 1
        self.Ainc[branchIDs,toNodes] = -1

        # Add to Object
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
        di = np.diag_indices(len(self.subIDs))
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
        self.TR = np.diagflat(tr)

        # DC Current Base
        bases = [xfmr.mvabase * 1e3 * np.sqrt(2/3) /xfmr.highnomv for xfmr in self.cleaned_xfmrs]
        self.Ibase = np.diagflat(bases)

        # K model values
        k = [xfmr.kparam for xfmr in self.cleaned_xfmrs]
        self.Kdiag = np.diagflat(k)

        # Map XFMR Loss to Buses (From for XFMRS)
        self.fromIDX = self.busmap(self.mapFrom['FromBus'])
        self.xfmrIDs = np.arange(self.nxfmrs)
        ONE = np.ones_like(self.xfmrIDs)

        shp = (self.nallbus, self.nxfmrs)
        self.PX = coo_matrix((ONE, (self.fromIDX,self.xfmrIDs)), shape=shp)
        
    # Below are accessing tools (Don't know best way yet)
    # Final step causes some problems, summing on busses

    def Hmat(self, reduceXFMR=True):
        '''
        Returns H Matrix, which maps line voltages to transformer losses (pre-absolute value)
        If the induced XFMR winginds are zero due to no length we can reduce matrix'''

        Gd = self.GbranchDiag
        A = self.Ainc
        Gmat = self.GLap
        Gi = np.linalg.inv(Gmat)
        PL = self.PL # Low Flow Selector
        PH = self.PH # High Flow Selector
        TRi = np.linalg.inv(self.TR) # Tap Ratios Inverse
        Ibasei = np.linalg.inv(self.Ibase)
        K = self.Kdiag
    
        H = K@Ibasei@(PH + TRi@PL)@(Gd@A@Gi@A.T@Gd - Gd)/3
        if reduceXFMR:
            H = H[:,-self.nlines:]

        return H.A