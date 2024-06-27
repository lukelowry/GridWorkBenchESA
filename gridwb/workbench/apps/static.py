# Data Structure Imports
import warnings
import pandas as pd
from numpy import NaN, exp, abs
from numpy.random import random
from gridwb.workbench.core import Context

from gridwb.workbench.grid.components import Contingency, Gen, Load, Bus

# WorkBench Imports
from ..core.powerworld import PowerWorldIO
from ..utils.metric import Metric
from .app import PWApp, griditer
from numpy import where, array

# Annoying FutureWarnings
warnings.simplefilter(action="ignore", category=FutureWarning)


# Dynamics App (Simulation, Model, etc.)
class Statics(PWApp):
    io: PowerWorldIO

    def __init__(self, context: Context) -> None:
        super().__init__(context)

        gens = self.dm.get_df(Gen)
        buses = self.dm.get_df(Bus)
        loads = self.dm.get_df(Load)
        

        # Slack Bus Q Limits
        self.slack_max = gens['GenMVRMax'][0] # Can't assume slack bus is first record TODO
        self.slack_min = gens['GenMVRMin'][0]

        # Create DF that stores loads for all buses
        l = buses[['BusNum']].merge(loads, how='left')
        l = l[['BusNum', 'LoadID', 'BusName_NomVolt','LoadIMVR', 'LoadSMVR', 'LoadSMW', 'LoadStatus']]
        l['LoadID'] = 1
        l['LoadStatus'] = 'Closed'
        l = l.fillna(0)
        self.io.upload({Load: l})
        self.bus_loads = l

        # Smaller DF just for updating Constant Power at Buses for Injection Interface Functions
        self.DispatchPQ = l[['BusNum', 'LoadID', 'LoadSMW', 'LoadSMVR']].copy()
        self.P0 = l['LoadSMW'].to_numpy().copy()
        self.Q0 = l['LoadSMVR'].to_numpy().copy()

        # Initial Gen Settings and Bus Voltages
        self.G0 = self.dm.get_df(Gen)[Gen.keys + ['GenMW', 'GenMVR', 'GenAVRAble', 'GenAGCAble']].copy() # Initial Gen Settings
        self.B0 = self.dm.get_df(Bus)[['BusNum', 'BusPUVolt']].copy()
    

    # Configuration Extraction TODO Way to Prevent Mis-Type Errors
    @PWApp.configuration.setter
    def configuration(self, config):
        self._configuration = config
        self.metric: Metric = config["Field"]

    load_nom = None
    load_df = None

    def randload(self, scale=1, sigma=0.1):
        '''Temporarily Change the Load with random variation and scale'''

        if self.load_nom is None or self.load_df is None:
            self.load_df = self.io.get_quick(Load, 'LoadMW')
            self.load_nom = self.load_df['LoadMW']
            
        self.load_df['LoadMW'] = scale*self.load_nom* exp(sigma*random(len(self.load_nom)))
        self.io.upload({Load: self.load_df})


    @griditer
    def solve(self, ctgs: list[Contingency] = None):
        # Cast to List
        if ctgs is None:
            ctgs = ["SimOnly"]
        if not isinstance(ctgs, list):
            ctgs: list[Contingency] = [ctgs]

        # Prepare Data Fields
        gtype = self.metric["Type"]
        field = self.metric["Static"]
        keyFields = self.io.keys(gtype)

        # Get Keys OR Values
        def get(field: str = None) -> pd.DataFrame:
            if field is None:
                data = self.io.get(gtype)
            else:
                self.io.pflow()
                data = self.io.get(gtype, [field])
                data.rename(columns={field: "Value"}, inplace=True)
                data.drop(columns=keyFields, inplace=True)

            return data

        # Initialize DFs
        meta = pd.DataFrame(columns=["Object", "ID-A", "ID-B", "Metric", "Contingency"])
        df = pd.DataFrame(columns=["Value", "Reference"])
        keys = get()

        # Add All Meta Records
        for ctg in ctgs:
            ctgMeta = pd.DataFrame(
                {
                    "Object": gtype,
                    "ID-A": keys.iloc[:, 0],
                    "ID-B": keys.iloc[:, 1] if len(keys.columns) > 1 else NaN,
                    "Metric": self.metric["Units"],
                    "Contingency": ctg,
                }
            )
            meta = pd.concat([meta, ctgMeta], ignore_index=True)

        # If Base Case Does not Solve, Return N/A vals
        try:
            refSol = get(field)

            # Set Reference (i.e. No CTG) and Solve
            self.io.esa.RunScriptCommand(f"CTGSetAsReference;")
        except:
            print("Loading Does Not Converge.")
            df = pd.DataFrame(
                NaN, index=["Value", "Reference"], columns=range(len(ctgs))
            )
            return (meta, df)

        # For Each CTG
        for ctg in ctgs:
            # Empty DF
            data = pd.DataFrame(columns=["Value", "Reference"])

            # Apply CTG
            if ctg != "SimOnly":
                self.io.esa.RunScriptCommand(f"CTGApply({ctg})")

            # Solve, Drop Keys
            try:
                data["Value"] = get(field)
            except:
                data["Value"] = NaN

            # Set Reference Values
            data["Reference"] = refSol

            # Un-Apply CTG
            self.io.esa.RunScriptCommand(f"CTGRestoreReference;")

            # Add Data to Main
            df = pd.concat([df, data], ignore_index=True)

        return (meta, df.T)
    
    def resetgens(self, G0 = None):
        ''' Reset All Gen values to initial values'''
        self.io.upload({Gen:self.G0 if G0 is None else G0})

    def resetV(self,B0 = None):
        '''Set Bus Voltage Magnitudes'''
        self.io.upload({Bus: self.B0 if B0 is None else B0})


    # NOTE TODO slack is not necessarily the first
    def slackIsMaxQ(self, q=None, lBound=True, uBound=True):
        '''Returns wether or not slack bus is at or above Q limits (args =False ignore up or low violation)'''
        if q is None:
            q = self.io.get_quick(Gen, 'GenMVR')['GenMVR']
        qslack = q[0]
        return (qslack >= self.slack_max and uBound) or (qslack <= self.slack_min and lBound)


    # Slightly Updated Continutation PF function - if it does not work use previous file (Continutation Power Flow.ipynb)
    # TODO upper bound should be able to 'slide' up
    # TODO speed up by reducing memory usange and PW commands
    def continuation_pf(self, injvec, initialmw = 0, minstep=1, maxstep=50, maxiter=50, qdrop=0.1, nrtol=0.0001, backstepPercent=0.25,return_hist=False):
        ''' Continuation Power Flow. Will Find the maximum INjection MW through an interface alpha
        minstep: Accuracy in Max Injection MW
        maxstep: largest jump in MW
        return_hist: return final answer or history of solution process
        initial_mw: starting interface MW. Could speed up convergence if you know a lower limit
        nrtol: Newton rhapston MVA tolerance
        qdrop: should be more than NR tolerance'''

        if qdrop < nrtol:
            print('UNACCEPTABLE Q. MUST BE LARGER THAN NRTOL')

        # Set NR Tolerance in MVA
        self.io.set_mva_tol(nrtol)

        loads_only = where(injvec<0, injvec, 0)

        # Reset and Do Power Flow
        self.resetgens()
        self.resetV()
        
        # Original Load
        self.DispatchPQ.loc[:,'LoadSMW'] = self.P0
        self.DispatchPQ.loc[:,'LoadSMVR'] = self.Q0
        self.io.upload({Load:self.DispatchPQ})

        # Base Case PF
        self.io.pflow()

        # Aggregate History
        Vall,TotalInj = ([], [])
        Vmin, Pmax = (None, None)
        
        Pinj = initialmw # Current Interface MW
        lbound = initialmw
        ubound = None

        i = 0
        qprev = self.io.get_quick(Gen, 'GenMVR')['GenMVR']
        while  (ubound is None or abs(ubound-lbound)>=minstep) and i<maxiter:
            
            # Set Injection for this iteration
            self.DispatchPQ.loc[:,'LoadSMW'] = self.P0 - Pinj*injvec
            self.DispatchPQ.loc[:,'LoadSMVR'] = self.Q0 - Pinj*loads_only*0.5
            self.io.upload({Load:self.DispatchPQ})

            try:
                # Do Power Flow
                self.io.pflow() 
                
                if return_hist:
                    V = self.io.get_quick(Bus, 'BusPUVolt')['BusPUVolt']
                else:
                    Vmin = self.io.get_min_volt()
                    

                qnow = self.io.get_quick(Gen, 'GenMVR')['GenMVR']
                
                # Fail if all gens at max or Q decreases on any gen
                #TODO better to jsut check if all gens are at max
                if  self.slackIsMaxQ(qnow) or (qnow<qprev-qdrop).any():
                    raise Exception
                
                lbound = Pinj
                
                # q prev will always be the lower bound q output
                qprev = qnow
            
                self.io.esa.RunScriptCommand('EnterMode(RUN);')
                self.io.esa.RunScriptCommand('StoreState(PREV);')

                if return_hist:
                    Vall.append(V)
                    TotalInj.append(Pinj)
                else:
                    Vmin = Vmin
                    Pmax = Pinj

                
            # Catch Power Flow Failure, All Gens at Limit, and 'Fake' continutations
            except Exception as e: 

                ubound = Pinj

                # Load lower bound state
                self.io.esa.RunScriptCommand('EnterMode(RUN);')
                self.io.esa.RunScriptCommand('RestoreState(USER,PREV);')
                
            # The setting is to go backward 3/4 of the way to lbound
            # The larger the step backward the more accurate likely to be
            # Steps forward to large could make the calculated limit less than actual
            if ubound is not None:
                Pinj = lbound + (ubound - lbound)*backstepPercent
            else:
                Pinj += maxstep
            
            i += 1
            #print(f'[{lbound}, {0 if ubound is None else ubound}]')
                
        # Return all history or just max alpha star
        if return_hist:
            return array(TotalInj), array(Vall)
        
        return Pmax, Vmin 
