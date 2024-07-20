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

        zipfields = ['LoadSMW', 'LoadSMVR','LoadIMW', 'LoadIMVR','LoadZMW', 'LoadZMVR']
        
        # Gen Q Limits
        self.genqmax = gens['GenMVRMax']
        self.genqmin = gens['GenMVRMin']

        # Gen P Limits
        self.genpmax = gens['GenMWMax']
        self.genpmin = gens['GenMWMin']

        # Create DF that stores loads for all buses
        l = buses[['BusNum', 'BusName_NomVolt']].copy()#.merge(loads, how='left')
        l.loc[:,zipfields] = 0.0
        l['LoadID'] = 99 # NOTE Random Large ID so that it does not interfere
        l['LoadStatus'] = 'Closed'
        l = l.fillna(0)
        self.io.upload({Load: l})
        self.bus_loads = l

        # Smaller DF just for updating Constant Power at Buses for Injection Interface Functions
        self.DispatchPQ = l[['BusNum', 'LoadID'] + zipfields].copy()

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
    
    def gensAtMaxP(self, p=None, tol=0.1):
        '''Returns True if any CLOSED gens are outside P limits. Active function.'''
        if p is None:
            p = self.io.get_quick(Gen, 'GenMW')['GenMW']

        isHigh = p > self.genpmax + tol
        isLow = p < self.genpmin - tol
        isClosed = self.io.get_quick(Gen, 'GenStatus')['GenStatus'] =='Closed'
        violation = isClosed & (isHigh | isLow)

        return any(violation)
        #return any(p > self.genpmax + tol) or any(p < self.genpmin - tol)
    
    def gensAtMaxQ(self, q=None, tol=0.1):
        '''Returns True if any CLOSED gens are outside Q limits. Active function.'''
        if q is None:
            q = self.io.get_quick(Gen, 'GenMVR')['GenMVR']

        isHigh = q > self.genqmax + tol
        isLow = q < self.genqmin - tol
        isClosed = self.io.get_quick(Gen, 'GenStatus')['GenStatus'] =='Closed'
        violation = isClosed & (isHigh | isLow)

        return any(violation)
        #return any(q > self.genqmax + tol) or any(q < self.genqmin - tol)

    
    ''' 
    
    
    REMOVING::::: 
    
    
    
    Keep for one push - This attempt at CPF tried to use a secondary metric
    to determine the boundary. It was a nice attempt but more trouble than
    it was worth in the end. The simpler function is better.
    
    
    
    def continuation_pf_old(self, interface, initialmw = 0, minstep=1, maxstep=50, maxiter=200, nrtol=0.0001, verbose=False, boundary_func=None):
        
        
        # Helper Function since this is common
        def log(x,**kwargs): 
            if verbose: print(x,**kwargs)
        def getq():
            return self.io.get_quick(Gen, 'GenMVR')['GenMVR']
        
        # 1. Solved -> Last Solved Solution,     2. Stable -> Known HV Solution    
        self.io.save_state('BACKUP')
        self.chain(2)
        
        # Set NR Tolerance in MVA
        self.io.set_mva_tol(nrtol)

        # Outer Try - Should only catch scenarios not considered during development
        try:

            log(f'\n\n------Init Injection-----')

            # Base Case PF, then Last-Change backup of state and prime the state chain
            while True:
                break
                try:
                    self.setload(SP=-initialmw*interface) # Initial MW
                    self.io.pflow()
                    break
                except:
                    log('Adjusting <')
                    initialmw*= 3/4
                    if initialmw < 1e-4: break

            #sss = self.io.get_quick(Shunt, 'SSAMVR')['SSAMVR']
            
            log(f'Starting Injection at:  {initialmw:.4f} MW ')
            self.pushstate()

            # Misc Iteration Tracking
            backstepPercent=0.25
            pnow, step = initialmw, maxstep # Current Interface MW, Step Size in MW
            pprev, qprev = 0, 0
            pstable, qstable = initialmw, 0
            qconsec_decr, sweepone = 0, True
            complete = False

            # Continuation Loop
            for i in arange(maxiter):

                # Set Injection for this iteration
                self.setload(SP=-pnow*interface)
                
                try: 

                    # Do Power Flow
                    log(f'PF: {pnow:>12.4f} MW\t', end='')
                    self.io.pflow() 

                    # Fail if all gens at max or Q decreases on any gen within tolerance
                    qall = getq()
                    qnow = qall.sum()

                    # TODO I am not checking generator P limits - should I?
                    # I Should for atleast the slack bus gens

                    # 'Effective' Non-Convergence, Uncommon but necessary due to power world slack overloading
                    if  self.gensAtMaxQ(qall): 
                        log(' + ')
                        raise GeneratorLimitException

                    ### STAGE ONE SWEEP ###
                    if sweepone:

                        # Detect decreases in Q output
                        if qprev > qnow: 
                            log(' v ')

                            qconsec_decr += 1
                            if qconsec_decr >= 3:
                                step = 0 
                                raise BifurcationException
                            self.istore() 
                        
                        # Push Stable Solutions
                        elif qprev != 0: 
                           
                            log(' * ')
                            self.pushstate()
                            qconsec_decr = 0
                            pstable, qstable = pprev, qprev
                            yield pnow, qnow 

                        # Push Solved Solutions (1st only really)
                        else: 
                            log(' - ')
                            self.istore()
                            yield pnow, qnow
                    
                    ### STAGE TWO SWEEP ### 
                    else:   
                        # Detect decrease in net Q
                        log(' > ')
                        if qprev-qnow>nrtol: raise BifurcationException
                        self.istore() # Don't push, we don't want to override the stable sol
                        yield pnow, qnow 

                    pprev, qprev = pnow, qnow

                except (Exception, GeneratorLimitException, BifurcationException) as e: 


                    if sweepone:

                        if isinstance(e,GeneratorLimitException): log('[Gen Q Limits Breached]')
                        elif isinstance(e,BifurcationException): log('[Bifurcation Suspected T1]')
                        else: log('XXX')

                        # Low -> Then fail is BAD
                        #if qconsec_decr >=1:
                            #step=0
                       
                        # Set new injection, decrease stepsize, and load previous solution
                        if step!=0:
                            
                            pnow = pprev
                            step *= backstepPercent
                            if pprev!=0: self.irestore()

                    else:
                        log('[Sweep 2 Complete]')
                        complete = True
                        self.irestore()
                
                # Sweep 1 Transition Code
                if sweepone and step<minstep:

                    # Restore Stable solution and become granular
                    log("[Sweep 1 Compelete]")
                    log(f'RS: {pstable:>12.4f} MW')
                    sweepone, step = False, 2*minstep
                    pnow, qprev = pstable-step, qstable
                    self.irestore(1) 

                # Exit Code
                if complete:
                    # Execute Boundary Function
                    if boundary_func is not None:
                        log(f'BD: {pprev:>12.4f} MW\t ! ')
                        log(f'Calling Boundary Function...')
                        boundary_func.X = boundary_func()
                    break

                # Advance Injection
                pnow += step

        except:
            log(f'Ill-Conditioned Scenario. Restoring backup.')
                
        finally:

            # Set Dispatch SMW to Zero
            self.setload(SP=0*interface)

            # Restore to before CPF Regardless of everything
            self.io.restore_state('BACKUP')
            log(f'-----------EXIT-----------\n\n')

    '''
            
    # This version is simpler, I think it might actually work better
    # TODO The only thing I have to do is switch slack bus to an interface bus
    # NOTE This is because we are interested in maximum POSSIBLE injection of MW. 
    # So then if all gens are at max but injection buses, one of them needs to be slack bus
    # if we want the flow values to be realistic
    def continuation_pf(self, interface, initialmw = 0, minstep=1, maxstep=50, maxiter=200, nrtol=0.0001, verbose=False, boundary_func=None):
        ''' 
        Continuation Power Flow. Will Find the maximum INjection MW through an interface. As an iterator, the last element will be the boundary value.
        The continuation will begin from the state
        params:
        -minstep: Accuracy in Max Injection MW
        -maxstep: largest jump in MW
        -initial_mw: starting interface MW. Could speed up convergence if you know a lower limit
        -nrtol: Newton rhapston MVA tolerance
        -boundary_func: Optional, pass a callable object to be called at boundary. Return of callable will be put into obj.X
        returns:
        - iterator with elements being the magnitude of interface injection. The last element is the CPF solution.
        '''
        
        # Helper Function since this is common
        def log(x,**kwargs): 
            if verbose: print(x,**kwargs)

        # 1. Solved -> Last Solved Solution,     2. Stable -> Known HV Solution    
        self.io.save_state('BACKUP')
        
        # Set NR Tolerance in MVA
        self.io.set_mva_tol(nrtol)

        log(f'Starting Injection at:  {initialmw:.4f} MW ')
        
        # Misc Iteration Tracking
        backstepPercent=0.25
        pnow, step = initialmw, maxstep # Current Interface MW, Step Size in MW
        pprev = 0

        # Continuation Loop
        for i in arange(maxiter):

            # Set Injection for this iteration
            self.setload(SP=-pnow*interface)
            
            try: 

                # Do Power Flow
                log(f'\nPF: {pnow:>12.4f} MW', end='\t')
                self.io.pflow() 

                # Check Max Power Output (NOTE not needed in GIC scenario)
                if self.gensAtMaxP(): 
                    log(' P+ ', end=' ')
                    raise GeneratorLimitException
                
                # Check Max Reactive Output
                if self.gensAtMaxQ(): 
                    log(' Q+ ', end=' ')
                    raise GeneratorLimitException
                
                # Save
                self.io.save_state('PREV')
                pprev = pnow

                yield pnow
                
            # Catch Fails, then backstep injection
            except (Exception, GeneratorLimitException, BifurcationException) as e: 

                log('XXX')
                        
                pnow = pprev
                step *= backstepPercent
                if pprev!=0: 
                    self.io.restore_state('PREV')

            if step<minstep:
                break

            # Advance Injection
            pnow += step
            
        # Execute Boundary Function
        if boundary_func is not None:
            log(f'BD: {pprev:>12.4f} MW\t ! ')
            log(f'Calling Boundary Function...')
            boundary_func.X = boundary_func()

        # Set Dispatch SMW to Zero
        self.setload(SP=0*interface)

        # Restore to before CPF Regardless of everything
        self.io.restore_state('BACKUP')
        log(f'-----------EXIT-----------\n\n')

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
            if verbose: print(f'Restoration Failure')
            raise Exception
        
        if verbose: print(f'Restore -> {self.stateidx-n}')
        
        # Restore
        self.io.restore_state(f'GWBState{self.stateidx-n}')
        
    def setload(self, SP=None, SQ=None, IP=None, IQ=None, ZP=None, ZQ=None):
        '''Set ZIP loads by bus. Vector of loads must include every bus.
        The loads set by this function are independent of existing loads.
        This serves as a functional and fast way to apply 'deltas' to base case bus loads.
        Load ID 99 is used so that it does not interfere with existing loads.
        This is a TEMPORARY load. Functions in GWB can and will override any Load ID 99.
        params:
        SP: Constant Active Power
        SQ: Constant Reactive Power
        IP: Constant Real Current
        IQ: Constant Reactive Current
        ZP: Constant Resistance
        ZQ: Constant Reactance'''

        if SP is not None:
            self.DispatchPQ.loc[:,'LoadSMW'] = SP
            self.io.upload({Load:self.DispatchPQ[['BusNum','LoadID','LoadSMW']]})
        if SQ is not None:
            self.DispatchPQ.loc[:,'LoadSMVR'] = SQ
            self.io.upload({Load:self.DispatchPQ[['BusNum','LoadID','LoadSMVR']]})
        if IP is not None:
            self.DispatchPQ.loc[:,'LoadIMW'] = IP
            self.io.upload({Load:self.DispatchPQ[['BusNum','LoadID','LoadIMW']]})
        if IQ is not None:
            self.DispatchPQ.loc[:,'LoadIMVR'] = IQ
            self.io.upload({Load:self.DispatchPQ[['BusNum','LoadID','LoadIMVR']]})
        if ZP is not None:
            self.DispatchPQ.loc[:,'LoadZMW'] = ZP
            self.io.upload({Load:self.DispatchPQ[['BusNum','LoadID','LoadZMW']]})
        if ZQ is not None:
            self.DispatchPQ.loc[:,'LoadZMVR'] = ZQ
            self.io.upload({Load:self.DispatchPQ[['BusNum','LoadID','LoadZMVR']]})

        # TODO Only send off changed/present values
        # drop rows with all zeros
        #df = df.loc[(df!=0).any(axis=1)]
        #
        #drop cols with all zeros?
        # xxx
        # Rather, select all where change is present
        # df.loc[df!=df]

        # df.loc[:] = [SP, SQ, IP, IQ, ZP, ZQ]  ??
        # I want more efficient way so I don't have to send everything

        self.io.upload({Load:self.DispatchPQ})