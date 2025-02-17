from numpy import array, ones, zeros, zeros_like, ones_like, diagflat, arange, eye
from numpy import min, max, sign, nan, pi, sqrt, abs, sin, cos, isnan
from numpy import unique, concatenate, sort, all, diag_indices, diff, expand_dims, repeat
from numpy import any, delete, where, argwhere, argmax, sum, percentile, array_equal
from numpy import errstate, vectorize
from numpy.linalg import inv
from numpy import concatenate as conc
import numpy as np # TODO there is so much usage just import whole module

from pandas import DataFrame, read_csv, MultiIndex
from scipy.sparse import coo_matrix, lil_matrix, hstack, vstack, bmat, diags, block_diag
from enum import Enum, auto
from itertools import product

# WorkBench Imports
from .app import PWApp
from ..grid.components import GIC_Options_Value, GICInputVoltObject
from ..grid.components import GICXFormer, Branch, Substation, Bus, Gen
from ..core.powerworld import PowerWorldIO
from ..utils.datawiz import jac_decomp
from ..io.b3d import B3D


from scipy.sparse.linalg import inv as sinv 

fcmd = lambda obj, fields, data: f"SetData({obj}, {fields}, {data})".replace("'","")
gicoption = lambda option, choice: fcmd("GIC_Options_Value",['VariableName', 'ValueField'], [option, choice])


class GICModel:

    '''A model class that holds all associated GIC matricies. Model instantiation requires proper
    data input format. If using ESA, use GIC.model() to automatically generate an instance.'''

    def __init__(self, subs: DataFrame, buses: DataFrame, lines: DataFrame, xfmrs: DataFrame, gens: DataFrame) -> None:

        # Helper Functions & Constants
        MOHM = 1e6
        iv = lambda A: sinv(A.tocsc())
        
        # Manifest Node IDs
        self.nbus, self.nsubs, self.nlines, self.nxfmr, self.ngens = len(buses), len(subs), len(lines), len(xfmrs), len(gens)

        # High and Low Winding, Line, GUS, and Substation Conductance
        GH , GL, Gline, Ggen, RSUB = xfmrs['HighG'].to_numpy(), xfmrs['LowG'].to_numpy(), lines['G'].to_numpy(), gens['G'].to_numpy(), subs['SubR'].to_numpy()

        # Wiring Configuration and Device-Based Indexers
        HWYE, LWYE = xfmrs['CFGHigh']=='Gwye', xfmrs['CFGLow']=='Gwye'
        AUTO, BD = xfmrs['Auto'].to_numpy(bool), xfmrs['BD'].to_numpy(bool)

        ''' INCIDENCE MAPPING '''

        def nodeperm(data, field, mount):
            obj = subs if mount=='SubNum' else buses
            m, n = len(data), len(obj)
            idx = obj.reset_index().set_index(mount).loc[data[field], 'index'].to_numpy()
            return coo_matrix((np.ones(m), (np.arange(m), idx)), shape=(m, n))

        # Line and GSU Incidence Matrix 
        Aline = hstack([
            lil_matrix((self.nlines, self.nsubs)), 
            nodeperm(lines, 'FromBus', 'BusNum') - nodeperm(lines, 'ToBus', 'BusNum')
        ])
        Agen = hstack([nodeperm(gens, 'BusNum', 'SubNum'), -nodeperm(gens, 'BusNum', 'BusNum')])
        
        # Determine Wnd Map (Substation, High and Low Bus Mounts)
        SUB, BH, BL = nodeperm(xfmrs, 'SubNum', 'SubNum'), nodeperm(xfmrs, 'HighBus', 'BusNum'), nodeperm(xfmrs, 'LowBus', 'BusNum')

        # Gwye (From B  ->  Sub Nuet.)    Auto - High (High Bus -> Low Bus), Low (Low Bus -> Sub Nuet.) 
        A_WYE_HIGH , A_WYE_LOW  = hstack([-SUB, BH]).tolil(), hstack([-SUB , BL]).tolil() 
        A_AUTO_HIGH, A_AUTO_LOW = hstack([lil_matrix((self.nxfmr, self.nsubs)), BH-BL]).tolil(), hstack([SUB, -BL]).tolil()

        # Merge Wiring Configurations 
        A_WYE_HIGH[~HWYE|AUTO], A_WYE_LOW[~LWYE|AUTO] = 0, 0
        A_AUTO_HIGH[~AUTO]    , A_AUTO_LOW[~AUTO]     = 0, 0
        AH, AL = A_WYE_HIGH + A_AUTO_HIGH, A_WYE_LOW + A_AUTO_LOW

        # Create Total Incidence (High Wnd, Low Wnd, Lines/Other Branches)
        A = vstack([AH, AL, Aline, Agen])

        ''' BRANCH CONDUCTANCE '''

        # GIC Blocking Device (1 Mega Ohm in Series) 
        GH[BD&~AUTO], GL[BD], Gline[Gline==0], Ggen[Ggen==0], RSUB[RSUB==0] = 1/MOHM, 1/MOHM, 1/MOHM, 1/MOHM, MOHM 

        # Total Branch Conductances (3-phase) & Substation Grounding Conductance
        Gd, Gs = 3*diags(conc([GH, GL, Gline, Ggen])), diags(1/conc([RSUB, MOHM*np.ones(self.nbus)]))

        ''' EFFECTIVE GICS, PER-UNIT, LOSSES '''

        # Determine Effective GIC extraction, Equivilent to (Ph + N^(-1) Pl)
        Eff = hstack([
            eye(self.nxfmr), 
            diags(1/xfmrs['TurnsRatio']), 
            lil_matrix((self.nxfmr, self.nlines))
        ])

        # DC Current Base & K model values
        base  = diags(1e3 * xfmrs['MVA'] * np.sqrt(2/3) / xfmrs['HighV'])
        K, Px = diags(xfmrs['K']), nodeperm(xfmrs, 'FromBus', 'BusNum').T # Bus Assignment for PF modeling

        ''' FORMATTED CALCULATIONS '''

        # Conductance Laplacian & Hmatrix 
        G    = A.T@Gd@A + Gs
        H    = Eff@(Gd-Gd@A@iv(G)@A.T@Gd)/3
        zeta = K@iv(base)@H 

        # User Retrieval & Cache for other functions
        # TODO eliminate dimensions where it is not needed (i.e. at the end when getting windings)
        self._A, self._G, self._H  = A, G, H
        self._eff, self._base = Eff, base
        self._zeta, self._Px = zeta, Px
        
    @property
    def A(self):
        '''
        The General incidence Matrix of the GIC Network. The first N  columns are substation nuetral buses, and
        the remaining M are bus nodes. The first 2X rows are High and Low Windings, and the remaining are non-winding branches.
        
        Returns:
        (N+M)x(N+M) sparse matrix
        '''
        return self._A
    
    @property
    def G(self):
        '''
        Conductance Laplacian of the GIC Network. The first N nodes are substation nuetral buses, and
        the remaining M nodes are bus nodes.
        
        Returns:
        (N+M)x(N+M) sparse matrix
        '''
        return self._G
    
    @property
    def H(self):
        '''
        Linear GIC Function Matrix. This matrix maps induced line voltages to (signed) effective transformer GICs.
        Actual Current, not in per-unit.
        Returns:
        XXX
        '''
        return self._H
    
    @property
    def zeta(self):
        '''
        Linear GIC Model. Returns the constant-current load (prior to absolute value) in per unit, for eahc bus.
        This matrix is provided as the fastest option to model GICs in power flow.

        In Per-Unit.
        
        Returns:
        XXX
        '''
        # TODO multiply by K and do per-unit
        return self._zeta
    
    @property
    def Px(self):
        '''
        Permutation matrix mapping each transformer to the bus used to model losses (default: from-bus)
        '''
        return self._Px

    @property
    def eff(self):
        '''
        Effective GIC operator matrix. Calculates the effective transformer GICs when applied to the vector of branch GICs.
        (This includes non-winding branches, trim the dimension for a quicker product).
        
        Returns:
        XXX
        '''
        # TODO multiply by K and do per-unit
        return self._eff

class GICFactory:

    '''A helper class to assist in loading data for the GIC model. Mostly intended for use when not using Power World.
    
    If a Power World case is being used, we recommend you use the GIC.model() function.'''

    def __init__(self) -> None:

        self.subdf = DataFrame(columns=['SubNum', 'SubR', 'Long', 'Lat'])
        self.busdf = DataFrame(columns=['BusNum', 'NomVolt', 'SubNum'])
        self.linedf = DataFrame(columns=['FromBus', 'ToBus', 'G'])
        self.xfmrdf = DataFrame(columns=['SubNum', 'FromBus', 'ToBus', 'CFG1', 'CFG2', 'G1', 'G2', 'BD', 'Auto', 'MVA', 'K'])
        self.gendf = DataFrame(columns=['BusNum', 'G'])

    def substation(self, subnum, subR, long, lat) -> None:
        '''Substation ID, Earth Resistance, Longitude, Latitude'''
        self.subdf.loc[len(self.subdf)] =  [subnum, subR, long, lat]
    
    def bus(self, busnum, nomvolt, subnum) -> None:
        self.busdf.loc[len(self.busdf)] =  [busnum, nomvolt, subnum]

    def line(self, fbus, tbus, g) -> None:
        self.linedf.loc[len(self.linedf)] = [fbus, tbus, g]

    def xfmr(self, subnum, fbus, tbus, cfg1, cfg2, g1, g2, blocked, isauto, mva=100, k=1) -> None:
        self.xfmrdf.loc[len(self.xfmrdf)] = [subnum, fbus, tbus, cfg1, cfg2, g1, g2, blocked, isauto, mva, k]

    def gen(self, busnum, g) -> None:
        self.gendf.loc[len(self.gendf)] = [busnum, g]

    def make(self) -> GICModel:
        '''Execute the passed data and synthesize a GIC model.'''

        self.subdf = self.subdf.astype({
            'SubNum':'int64',
            'SubR':'float64', 
            'Long':'float64', 
            'Lat':'float64', 
        })
        self.busdf = self.busdf.astype({
            'BusNum':'int64',
            'NomVolt':'float64',
            'SubNum':'int64',
        })
        self.linedf = self.linedf.astype({
            'FromBus':'int64', 
            'ToBus':'int64', 
            'G':'float64'
        })
        self.xfmrdf = self.xfmrdf.astype({
            'SubNum':'int64',
            'FromBus':'int64', 
            'ToBus':'int64', 
            'CFG1':'string', 
            'CFG2':'string', 
            'G1': 'float64', 
            'G2':'float64',
            'BD':'boolean', 
            'Auto':'boolean',
            'MVA':'float64',
            'K':'float64'
        })
        self.gendf = self.gendf.astype({
            'BusNum':'int64', 
            'G':'float64'
        })

        b, x = self.busdf, self.xfmrdf

        # Determine High/Low Windings and Turns Ratio
        getBusV = lambda terminal: b.set_index('BusNum').loc[x[terminal],'NomVolt'].reset_index(drop=True)
        x['FromV'], x['ToV'] = getBusV('FromBus'), getBusV('ToBus')
        fromIsHigh = x['FromV']>x['ToV']
        x['HighV']      = x[['FromV', 'ToV']].max(axis=1)
        x['LowV']       = x[['FromV', 'ToV']].min(axis=1)
        x['TurnsRatio'] = x['HighV']/x['LowV']
        x['HighBus']    = np.where(fromIsHigh , x['FromBus'],  x['ToBus'])
        x['LowBus']     = np.where(~fromIsHigh, x['FromBus'],  x['ToBus'])
        x['CFGHigh']    = np.where(fromIsHigh , x['CFG1']   ,  x['CFG2'])
        x['CFGLow']     = np.where(~fromIsHigh, x['CFG1']   ,  x['CFG2'])
        x['HighG']      = np.where(fromIsHigh , x['G1']     ,  x['G2'])
        x['LowG']       = np.where(~fromIsHigh, x['G1']     ,  x['G2'])

        return GICModel(self.subdf.copy(), b.copy(), self.linedf.copy(), x.copy(), self.gendf.copy())

#  GWB App
class GIC(PWApp):

    io: PowerWorldIO

    def gictool(self, calc_all_windings = False):
        '''Returns a new instance of GICTool, which creates various matricies and metrics regarding GICs.
        Don't set calc_all_windings=True unless you must
        '''

        gicxfmrs = self.io[GICXFormer,:]
        branches = self.io[Branch,:]
        gens = self.io[Gen,:]
        subs = self.io[Substation,:]
        buses = self.io[Bus,:]

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
        '''Clear the Power World Manual GIC Calculations. '''
        self.io.esa.RunScriptCommand(f"GICClear;")

    def loadb3d(self, ftype, fname, setuponload=True):
        '''Load B3D File for an Electric Field'''
        b = "YES" if setuponload else "NO"
        self.io.esa.RunScriptCommand(f"GICLoad3DEfield({ftype},{fname},{b})")

    def minkv(self, kv):
        '''Set the minimum KV of lines to contribute to GIC Calculations'''
        pass

    def dBounddI(self, eta, PX, J, V):
        ''' Interface Sensitivity w.r.t Transformer GIC Currents.
        Parameters:
        - eta: (nx1) Numpy Vector of Injection
        - PX: (nxm) Transformer to loaded-bus mapping
        - J: (nxn) Full AC Powerflow Jacobian at Boundary
        - V: (nx1) Bus Voltage Magnitudes
        Returns:
        - (1xn) Numpy Array of Sensitivites
        '''

        # Category Selectors
        buscat = self.io[Bus,['BusCat']]['BusCat']
        slk = buscat=='Slack'
        pv = buscat=='PV'
        pq = ~(slk | pv) # I think this is the best way
        dPdT, dPdV, dQdT, dQdV = jac_decomp(J)   
        
        # P & Q Equations ( Include Slack in row just for dimensionality - Techniqly should not be included)
        A = hstack([dPdT[:,~slk], dPdV[:,pq]])
        B = hstack([dQdT[pq][:,~slk], dQdV[pq][:,pq]])

        # PQ Voltage Diagonal
        Vdiag = diagflat(V[pq])

        # Psuedo Inverse (for eta and B) Sensitivity (N Buses) x (N XFMRs)
        return (1/(eta.T@eta))@eta.T@A@B.T@sinv((B@B.T).tocsc())@Vdiag@PX[pq]

        # Without eta Psuedo
        #return eta.T@A@B.T@sinv((B@B.T).tocsc())@Vdiag@PX[pq]


        # NOTE Part of me thinks I can just DO this with the jacobian at the base case.... That would be powerful
        # NOTE Then I could do multiple interfaces AT THE SAME TIME
        # NOTE It would be like 'Trasporting' the solution down an interface without increasing any active power

        #return eta.T@dPdQ@diagflat(V[1:])

    def dIdE(self, H, E=None, i=None):
        '''
        Compute the Jacobean between a mesh Efield 
        and (absolute) Transformer GICs

        Pass H and one other parameter:
        - Electric field OR Signed Nuetral XFMR Currents

        Return Jacobean (Rows -> i, Cols -> E)
        '''

        # E passed
        if E is not None:
            if i is None: i = H@E
            else: print('(E) and (i) passed. Using (i) only.')

        # E not passed
        else:
            if i is None: raise Exception

        # Piece Wise Emulator
        F = self.signdiag(i) 
    
        return F@H
    
    def signdiag(self, x):
        '''Return a diagonal matrix of the sign of a vector'''
        return np.diagflat(np.sign(x)) 
        
    
    def dIdEOLD(dBdI, PX, Hx, Hy, Ex, Ey):
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
    
    def model(self) -> GICModel:
        '''Generate the common linear GIC model with Power World Data.'''

        # If done with a 'Direct' approach this iterative method would not be necessary. However, it is fast regardless
        # and done so that users with non Power World data can easily use GICModel.
        
        gicsubs = self.io[Substation, ["SubNum", "GICSubGroundOhms", "Longitude", "Latitude"]]
        gicbus = self.io[Bus,["BusNum", "BusNomVolt", "SubNum"]]

        linefields = ["BusNum", "BusNum:1", "GICConductance"]
        xfmrfields = ["SubNum", "BusNum", "BusNum:1", "XFConfiguration", "GICCoilRFrom", "GICCoilRTo", 'GICBlockDevice', 'XFIsAutoXF', 'XFMVABase', 'GICModelKUsed']
        
        branches = self.io[Branch,linefields+xfmrfields+['BranchDeviceType']]
        isXFMR = branches['BranchDeviceType']=='Transformer'
        gicbranch = branches.loc[~isXFMR,linefields]
        gicxfmr   = branches.loc[isXFMR,xfmrfields]

        gf = GICFactory()

        # Feed Substation Data
        for rec in gicsubs.to_records():
            i, *data = rec
            gf.substation(*data)

        # Feed Bus Data
        for rec in gicbus.to_records():
            i, *data = rec
            gf.bus(*data)

        # Feed Branch (Not Transformers !) Data
        for rec in gicbranch.to_records():
            i, *data = rec
            gf.line(*data)

        # Feed Transformer Data
        for rec in gicxfmr.to_records():
            i, subnum, fbus, tbus, config, g1, g2, isblocked, isauto, mva, k = rec
            gf.xfmr(subnum, fbus, tbus, *config.split(" - "), 1/g1, 1/g2, isblocked=='YES', isauto=='Yes', mva, k)

        return gf.make()


'''
TODO - REMOVE ALL OF THE BELOW, bad practices and clunky. GICModel class to be used in future.
The following three classes are helper-classes to help create GIC data. Not ideal formatting, but it works. Do not touch.
'''


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

# TODO
# - More General Implementation of Below
# - I want to give this to people for general use

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
        self.PX = coo_matrix((ONE, (self.fromIDX,self.xfmrIDs)), shape=shp).tolil()
        
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

    def tesselations(self, tilewidth=0.5, num_spacers=1):
        '''Return Tessalized forms of the H matrix for Ex and Ey.'''

        line_km = self.line_km
        line_ang = self.line_ang

        # Seperated by X, Y
        cX = self.lines[['Longitude', 'Longitude:1']].copy().to_numpy()
        cY = self.lines[['Latitude', 'Latitude:1']].copy().to_numpy()

        # Generate Tile Intervals
        W = tilewidth
        margin = num_spacers*W
        X = arange(cX.min(axis=None) -margin, cX.max(axis=None)+W+margin, W) 
        Y = arange(cY.min(axis=None) -margin, cY.max(axis=None)+W+margin, W) # TODO  Change to be one extra cell in x and y direction for SLACK VARIABLE IN E FIELD during optimization

        # Save for reference if needed
        self.tile_info = X, Y, W
        self.tile_count = len(X)-1, len(Y)-1, (len(X)-1)*(len(Y)-1)

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

    def to_b3d(self, EX, EY):
        '''Convert Electric Field data associated with a tesselation to a B3D Object.'''
        X, Y, W = self.tile_info
        return B3D.from_mesh(X[:-1]+W/2, Y[:-1]+W/2, EX, EY)
