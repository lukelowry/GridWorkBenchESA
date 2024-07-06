# Data Structure Imports
import warnings
import pandas as pd
from numpy import NaN, exp, abs, any, argmax, arange
from numpy.random import random
from gridwb.workbench.core import Context

from gridwb.workbench.grid.components import Contingency, Gen, Load, Bus,Shunt, PWCaseInformation, Branch

# WorkBench Imports
from ..core.powerworld import PowerWorldIO
from ..utils.metric import Metric
from ..utils.exceptions import *
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
        self.genqmax = gens['GenMVRMax'] # Can't assume slack bus is first record TODO
        self.genqmin = gens['GenMVRMin']

        # Create DF that stores loads for all buses
        l = buses[['BusNum', 'BusName_NomVolt']].copy()#.merge(loads, how='left')
        l.loc[:,['LoadIMVR', 'LoadSMVR', 'LoadSMW']] = 0.0
        l['LoadID'] = 99 # NOTE Random Large ID so that it does not interfere
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

    def gensAtMaxQ(self, q=None, tol=0.1):
        '''Returns wether or not gens is at or above Q limits (args =False ignore up or low violation)'''
        if q is None:
            q = self.io.get_quick(Gen, 'GenMVR')['GenMVR']
        return any(q > self.genqmax + tol) or any(q < self.genqmin - tol)


    # Slightly Updated Continutation PF function - if it does not work use previous file (Continutation Power Flow.ipynb)
    # TODO upper bound should be able to 'slide' up
    def continuation_pf(self, interface, initialmw = 0, minstep=1, maxstep=50, maxiter=200, qdrop=0.1, nrtol=0.0001, backstepPercent=0.25,return_hist=False, verbose=False):
        ''' 
        Continuation Power Flow. Will Find the maximum INjection MW through an interface alpha.
        The continuation will begin from the state
        minstep: Accuracy in Max Injection MW
        maxstep: largest jump in MW
        return_hist: return final answer or history of solution process
        initial_mw: starting interface MW. Could speed up convergence if you know a lower limit
        nrtol: Newton rhapston MVA tolerance
        qdrop: Detection in MVAR/MW where a >0 countss as collapse detection '''

        if qdrop < nrtol:
            print('UNACCEPTABLE Q. MUST BE LARGER THAN NRTOL')
            return
        
        # Helper Function since this is common
        def getq():
            return self.io.get_quick(Gen, 'GenMVR')['GenMVR']

        # Base Case PF
        self.io.pflow()

        # Last-Change backup of state
        self.io.save_state('BACKUP')

        # Set NR Tolerance in MVA
        self.io.set_mva_tol(nrtol)

        # Aggregate History
        QSumHist,TotalInj = [], []
        Qmax, Pmax = (0, initialmw)
        Pinj = initialmw # Current Interface MW

        i = 0
        step = maxstep
        qprev = None #self.io.get_quick(Gen, 'GenMVR')['GenMVR'].sum()
        qstable = None

        while  step>=minstep and i<maxiter:
            
            # Set Injection for this iteration
            self.setload(self.P0 - Pinj*interface)
            
            try:
                # Do Power Flow
                self.io.pflow() 

                # Fail if all gens at max or Q decreases on any gen within tolerance
                qnow = getq()
                qnowsum = qnow.sum()

                # 'Effective' Non-Convergence
                if  self.gensAtMaxQ(qnow):
                    if verbose: print('Gen Q Limits Breached')
                    raise GeneratorLimitException 
                if qprev is not None and (qprev-qnowsum)/step>qdrop: # TODO only valid if |qprev-qnowsum| < tol
                    if verbose: print('Bifurcation Suspected')
                    raise BifurcationException


                # IF INCREASED
                if qprev is not None and qprev < qnowsum:
                    # Current > Prev > Stable
                    # Save Current State in TEMP
                    # Restore PREV
                    # Store in STABLE
                    # Restore TEMP
                    # Store in PREV
                    self.io.save_state('TEMP')
                    self.io.restore_state('PREV')
                    self.io.save_state('STABLE')

                    # Store Stable Injection MW and Qtotal for comparison
                    pstable = pprev
                    qstable = getq().sum()

                    self.io.restore_state('TEMP')
                    self.io.save_state('PREV')

                # IF DECREASE (Sign of birfurcation)
                else:
                    # Current > Prev
                    self.io.save_state('PREV')

                # Store 'Last' iterations valid solution
                pprev = Pinj
                qprev = qnowsum 

                print(Pinj)

                # Store Data
                if return_hist:
                    QSumHist.append(qprev) # qnowsum
                    TotalInj.append(pprev)
                
                Qmax = qprev
                Pmax = pprev

                
            # Catch Power Flow Failure, All Gens at Limit, and 'Fake' continutations
            except Exception as e: 

                Pinj -= step 
                step *= backstepPercent

                # Load previous state
                self.io.restore_state('PREV')
                
            
            Pinj += step
            i += 1

        # TODO once complete, start again from the STABLE save and move with minstep
        print(f'Last Stable: {pstable:.4f} MW')
        print(f'Absolute Max: {Pmax:.4f} MW')

        # Load Stable
        self.io.restore_state('STABLE')

        # TODO i should be able to integrate this into the above while loop
        # Assuming no collapse errors since we have been above this val
        for ppp in arange(pstable, Pmax, minstep):

            print(f'Stable Search: {ppp:.4f} MW')
            
            # Set Injection for this iteration
            self.setload(self.P0 - ppp*interface)
            
            # Do Power Flow (somehow its diverging in this region)
            try:
                self.io.pflow() 
            except:
                break

            # Fail if all gens at max or Q decreases on any gen within tolerance
            qnowsum = getq().sum()
            
            # Found boundary within tolerance
            if qprev-qnowsum > nrtol:
                break

            qprev = qnowsum

            # Store Data
            if return_hist:
                QSumHist.append(qnowsum)
                TotalInj.append(ppp)
            Qmax = qprev
            Pmax = ppp

        # Restore to before CPF
        self.io.restore_state('BACKUP')
        
        if return_hist:
            # Return up to point that has maximum Q
            #maxidx = argmax(QSumHist)
            return array(TotalInj), array(QSumHist)
            #return array(TotalInj)[:maxidx+1], array(QSumHist)[:maxidx+1]
        
        return Pmax, Qmax
    
    def setload(self, P=None, Q=None):
        '''Set constant power loads by bus. Must include full vector.'''

        if P is not None:
            self.DispatchPQ.loc[:,'LoadSMW'] = P
        if Q is not None:
            self.DispatchPQ.loc[:,'LoadSMVR'] = Q

        self.io.upload({Load:self.DispatchPQ})

    # TODO Overloaded Functions that take Const Z, I, etc.