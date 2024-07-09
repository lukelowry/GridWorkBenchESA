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
    
    def gensAtMaxQ(self, q=None, tol=0.1):
        '''Returns True if any gens are outside Q limits. Active function.'''
        if q is None:
            q = self.io.get_quick(Gen, 'GenMVR')['GenMVR']
        return any(q > self.genqmax + tol) or any(q < self.genqmin - tol)

    
    def continuation_pf(self, interface, initialmw = 0, minstep=1, maxstep=50, maxiter=200, nrtol=0.0001, verbose=False):
        ''' 
        Continuation Power Flow. Will Find the maximum INjection MW through an interface. As an iterator, the last element will be the boundary value.
        The continuation will begin from the state
        params:
        -minstep: Accuracy in Max Injection MW
        -maxstep: largest jump in MW
        -initial_mw: starting interface MW. Could speed up convergence if you know a lower limit
        -nrtol: Newton rhapston MVA tolerance
        returns:
        - iterator with elements being the magnitude of interface injection. The last element is the CPF solution.
        '''
        
        # Helper Function since this is common
        def getq():
            return self.io.get_quick(Gen, 'GenMVR')['GenMVR']
        
        # 1. Solved -> Last Solved Solution,     2. Stable -> Known HV Solution    
        self.chain(2)
        
        # Base Case PF, then Last-Change backup of state and prime the state chain
        self.io.pflow()
        self.io.save_state('BACKUP')
        self.pushstate()

        # Set NR Tolerance in MVA
        self.io.set_mva_tol(nrtol)

        # Misc Iteration Tracking
        backstepPercent=0.25
        pnow, step = initialmw, maxstep # Current Interface MW, Step Size in MW
        pprev, qprev = 0, 0
        pstable, qstable = None, None 
        qconsec_decr, sweepone = 0, True

        # Continuation Loop
        for i in arange(maxiter):

            # Set Injection for this iteration
            self.setload(self.P0 - pnow*interface) #TODO P0 should be updated at the call of this function, since load could be changed before this :(
            
            try: 

                # Do Power Flow
                self.io.pflow() 

                # Fail if all gens at max or Q decreases on any gen within tolerance
                qall = getq()
                qnow = qall.sum()

                
                # Stage One Sweep
                if sweepone:

                    # 'Effective' Non-Convergence, Uncommon but necessary due to power world slack overloading
                    if  self.gensAtMaxQ(qall): 
                        if verbose: print('Gen Q Limits Breached')
                        raise GeneratorLimitException 

                    # Detect decreases in Q output
                    if qprev > qnow: 
                        qconsec_decr += 1
                        if qconsec_decr >= 3:
                            step = 0 
                            raise BifurcationException
                        self.istore() 

                    # Push Stable Solutions
                    elif qprev != 0: 
                        self.pushstate()
                        qconsec_decr = 0
                        pstable, qstable = pprev, qprev
                    
                    # Push Solved Solutions
                    else: self.istore() 

                # Stage Two Sweep - Detect decrease in net Q
                else:
                    
                    if qprev-qnow>nrtol:
                        raise BifurcationException
                    
                    self.istore() # Don't push, we don't want to override the stable sol

                if verbose: print(f'PF: {pnow:.4f} MW')

                # Yield and save
                yield pnow, qnow
                pprev, qprev = pnow, qnow

            except (Exception, GeneratorLimitException, BifurcationException): 

                # Either Gen Limits reached or PF Divergence
                if verbose: print(f'PFlow: {pnow:.4f} MW   -   Failed')

                # Set new injection, decrease stepsize, and load previous solution
                if step !=0:
                    pnow -= step 
                    step *= backstepPercent
                    self.irestore()
            
            # Convergence Detection
            if step<minstep:

                if not sweepone: break 

                # Restore Stable solution and become granular
                sweepone, step = False, 2*minstep
                pnow, qprev = pstable, qstable
                self.irestore(1) # Load Stable Solution

                if verbose: print(f'Searching: [{pstable:.4f}, {pprev:.4f}] -> Step {step:.4f} MW')

            # Advance Injection
            pnow += step

        # Restore to before CPF
        self.io.restore_state('BACKUP')

    '''
    The following functions probably deserve their own object or atleast be relocated
    '''
    
    def chain(self, maxstates=2):
        '''Initiate a state-chain for iterative functions that require state restoration. The data of n states will be tracked and
        managed as a queue.
        '''
        self.maxstates = maxstates
        self.stateidx = -1

        # TODO delete old states when this is called


    def pushstate(self, verbose=False):
        '''Update the PF chain queue with the current state. The n-th state will be forgotten.'''

        # Each line represents a call to push() with nmax = 3
        # 0*          <- push()  State 0 added (sidx = 0)
        # 0 1*        <- push()  State 1 added (sidx = 1)
        # 0 1 2*      <- push()  State 2 added (sidx = 2)
        #   1 2  3*    <- push()  State 3 added (sidx = 3) and 0 was deleted
        #     2  3  4* <- push()  State 4 added (sidx = 4) and 1 was deleted

        # Save current state on the right of the queue
        self.stateidx += 1
        self.io.save_state(f'GWBState{self.stateidx}')

        if verbose: print(f'Pushed States -> {self.stateidx},  Delete -> {self.stateidx-self.maxstates}')

        # Try and delete the state (nmax) behind this one
        if self.stateidx >= self.maxstates:
            self.io.delete_state(f'GWBState{self.stateidx-self.maxstates}')

    def istore(self, n:int=0, verbose=False):
        '''
        Instead of pushing a new state to the save chain, this will update the nth state in the chain.

        # Each line represents a call to push() with nmax = 3
        # 0*             <- push()  State 0 added (sidx = 0)
        # 0 1*           <- push()  State 1 added (sidx = 1)
        # 0 1 2*         <- push()  State 2 added (sidx = 2)
        #   1 2  3*      <- push()  State 3 added (sidx = 3) and 0 was deleted
        #     2  3  4*   <- push()  State 4 added (sidx = 4) and 1 was deleted
        #     2  3  4'   <- assign(0) modifies State 4
        #        3  4' 5 <- push() State 5 added (sidx = 5)
        '''

        # Can only go back number of states
        if n > self.maxstates or n > self.stateidx:
            raise Exception
        
        if verbose: print(f'Restore -> {self.stateidx-n}')
        
        # Restore
        self.io.save_state(f'GWBState{self.stateidx-n}')
        
    def irestore(self, n:int=1, verbose=False):
        '''
        Regress backward in the saved states. Consecutive calls do not affect which state is restored.
        Example:
        back(1) # Loads 2 states ago
        back(1) # Will load the same state

        # Each line represents a call to push() with nmax = 3
        # 0*          <- push()  State 0 added (sidx = 0)
        # 0 1*        <- push()  State 1 added (sidx = 1)
        # 0 1 2*      <- push()  State 2 added (sidx = 2)
        #   1 2  3*    <- push()  State 3 added (sidx = 3) and 0 was deleted
        #     2  3  4* <- push()  State 4 added (sidx = 4) and 1 was deleted
        #     2  3* 4  <- back(1) State 3 is restored
        #     2* 3  4  <- back(2) State 2 is restored
        #     2  3  4* <- back(0) State 4 is restored

        '''
        # Can only go back number of states
        if n > self.maxstates or n > self.stateidx:
            raise Exception
        
        if verbose: print(f'Restore -> {self.stateidx-n}')
        
        # Restore
        self.io.restore_state(f'GWBState{self.stateidx-n}')
        
    def setload(self, SP=None, SQ=None, IP=None, IQ=None, ZP=None, ZQ=None):
        '''Set ZIP loads by bus. Vector of loads must include every bus.
        The loads set by this function are independent of existing loads.
        This serves as a functional and fast way to apply 'deltas' to base case bus loads.
        Load ID 99 is used so that it does not interfere with existing loads.
        params:
        SP: Constant Active Power
        SQ: Constant Reactive Power
        IP: Constant Real Current
        IQ: Constant Reactive Current
        ZP: Constant Resistance
        ZQ: Constant Reactance'''

        if SP is not None:
            self.DispatchPQ.loc[:,'LoadSMW'] = SP
        if SQ is not None:
            self.DispatchPQ.loc[:,'LoadSMVR'] = SQ
        '''
        if IP is not None:
            self.DispatchPQ.loc[:,'LoadIMW'] = IP
        if IQ is not None:
            self.DispatchPQ.loc[:,'LoadIMVR'] = IQ
        if ZP is not None:
            self.DispatchPQ.loc[:,'LoadZMW'] = ZP
        if ZQ is not None:
            self.DispatchPQ.loc[:,'LoadZMVR'] = ZQ
        '''

        # TODO Only send off changed/present values
        # drop rows with all zeros
        #df = df.loc[(df!=0).any(axis=1)]
        #
        #drop cols with all zeros?
        # xxx
        # Rather, select all where change is present
        # df.loc[df!=df]

        # df.loc[:] = [SP, SQ, IP, IQ, ZP, ZQ]  ??
        # I want more efficient way 

        self.io.upload({Load:self.DispatchPQ})