from typing import Type
from pandas import DataFrame
from os import path
from numpy import unique

from .datamaintainer import GridDataMaintainer
from ..grid.components import *
from ..utils.decorators import timing
from ..io.model import IModelIO
from ...saw import SAW # NOTE Should be the only file importing SAW


# Helper Function to parse Python Syntax/Field Syntax outliers
# Example: fexcept('ThreeWindingTransformer') -> '3WindingTransformer
fexcept = lambda t: "3" + t[5:] if t[:5] == "Three" else t

# Power World Read/Write
class PowerWorldIO(IModelIO):
    esa: SAW
    dm: DataMaintainer

    def TSInit(self):
        ''' Initialize Transient Stability Parameters '''
        try:
            self.esa.RunScriptCommand("TSInitialize()")
        except:
            print("Failed to Initialize TS Values")

    @timing
    def open(self):
        # Validate Path Name
        if not path.isabs(self.fname):
            self.fname = path.abspath(self.fname)

        # ESA Object & Transient Sim
        self.esa = SAW(self.fname, CreateIfNotFound=True, early_bind=True)

        # Attempt and Initialize TS so we get initial values
        self.TSInit()

    @timing
    def download(self, set: list[Type[GObject]]) -> GridDataMaintainer:
        '''
        Get all Data from PW. What data is downloaded
        depends on the selected Set.
        '''
        self.dm = GridDataMaintainer({gclass: self.get(gclass) for gclass in set})
        return self.dm

    def upload(self, model: dict[Type[GObject], DataFrame]) -> bool:
        '''
        Send All WB DataFrame Data to PW
        WARNING: Be careful what is passed to this function.

        Parameters:
        model: A dictionary with Object Types as keys. The dat associated with this key
            is a Dataframe holding data with atleast respective keys.
        '''
        self.esa.RunScriptCommand("EnterMode(EDIT);")
        for gclass, gset in model.items():
            # Only Pass Params That are Editable
            #df = gset[gset.columns.intersection(gclass.editable)].copy()
            df = gset[gset.columns].copy()
            try:
                self.esa.change_parameters_multiple_element_df(gclass.TYPE, df)
            except:
                print(f"Failed to Write Data for {gclass.TYPE}")
    
    def __getitem__(self, index):
        '''Retrieve Data frome Power world with Indexor Notation
        
        
        Examples:
        wb.pw[Bus] # Get Primary Keys of PW Buses
        wb.pw[Bus, 'BusPUVolt'] # Get Voltage Magnitudes
        wb.pw[Bus, ['SubNum', 'BusPUVolt']] # Get Two Fields
        wb.pw[Bus, :] # Get all fields
        '''
        
        if isinstance(index, tuple): 
            gtype, fields = index
            if isinstance(fields, str): fields = fields,
            elif isinstance(fields, slice): fields = gtype.fields
        else: 
            gtype, fields = index, ()

        keys = gtype.keys
        dfields = [f for f in fields if f not in keys]

        df = self.esa.GetParametersMultipleElement(gtype.TYPE, [*keys, *dfields])
        df.set_index(keys, inplace=True)
        
        return df
    
    def __setitem__(self, args, value):
        '''Set grid data using indexors directly to Power World
        Must be atleast 2 args: Type & Field

        Examples:
        wb.pw[Bus, 'BusPUVolt'] = 1
        wb.pw[Bus, v<1, 'BusPUVolt'] = arr
        wb.pw[Bus, p>10, [xxx,xxx,xxx]] = [arr1, arr2, arr3]
        '''

        # Extract Arguments depending on Index Method
        if len(args)==2:   gtype, where, fields = args[0], None, args[1]
        elif len(args)==3: gtype, where, fields = args

        # Format as list
        if isinstance(fields, str): fields = fields,
        
        # Retrieve active power world record keys 
        base = self[gtype]

        # Assign Values
        if where is not None: base.loc[where, fields] = value
        else: base.loc[:,fields] = value
            
        # Send to Power World
        self.esa.change_parameters_multiple_element_df(gtype.TYPE, base.reset_index())


    def save(self):
        '''
        Save all Open Changes to PWB File.
        Note: only data/settings written back to PowerWorld will be saved.
        '''
        return self.esa.SaveCase()

    def get(self, gtype: Type[GObject], keysonly=False):
        '''
        Get all Objects of specified type from PowerWorld.
        
        Parameters:
        gtype: Object type to retrieve data,
        keysonly: Specifiy if GWB should retrieve just key data or ALL data of object type.
        '''

        # Option Handling (.fields includes keys)
        if keysonly:
            fields = [fexcept(f) for f in gtype.keys]
        else:
            fields = [fexcept(f) for f in gtype.fields]

        # Get Data from SimAuto
        df = None
        try:
            # Successful retrieval of data and requested fields as DataFrame
            df = self.esa.GetParametersMultipleElement(gtype.TYPE, fields)
        except:
            # Failure. Create empty dataframe with expected indecies.
            print(f"Failed to read {gtype.TYPE} data.")
        
        # Creates Empty DF is PW has done of specified object.
        if df is None:
            df = DataFrame(columns=fields)

        # Set Name of DF to datatype TODO remove this weird implementation. I think I use .Name for transient data retrieval?
        df.Name = gtype.TYPE

        return df
    
    def get_quick(self, gtype: Type[GObject], fieldname: str | list[str]):
        '''
        Helper Function that will retrieve one field from all objects of specified type.
        Intended for repeated data retrieval.
        
        Parameters:
        gtype: Object type to retrieve data,
        fieldname: Power-World Compatible Field Name (string)

        Example: get_quick(Bus, 'BusPUVolt')
        '''

        # Keys of Object type are required to get data
        request = [fexcept(f) for f in gtype.keys]

        # transformer field name to list if single given
        if type(fieldname) is str: 
            fieldname = [fieldname]

        # Add field to search index if not already a key..
        for fn in fieldname:
            if fn not in request:
                request.append(fn)

        # Get Data from Power World 
        df = None
        try:
            df = self.esa.GetParametersMultipleElement(gtype.TYPE, request)
        except:
            print(f"Failed to read {gtype.TYPE} data.")
        
        return df

    # Solve Power Flow
    def pflow(self, retry=True):
        '''
        Executes Power Flow in PowerWorld. 
        
        If retry is set True, it will reset PF and try one additional time.
        '''
        try:
            self.esa.SolvePowerFlow()
        except:
            if retry:
                self.flatstart()
                self.esa.SolvePowerFlow()

    def flatstart(self):
        '''
        Call to reset PF to a flat start.
        '''
        self.esa.RunScriptCommand("ResetToFlatStart()")


    # Skip Contingencies
    def skipallbut(self, ctgs):
        ctgset = self.get(TSContingency)

        # Set Skip if not in ctg list
        ctgset["CTGSkip"] = "YES"
        ctgset.loc[ctgset["TSCTGName"].isin(ctgs), "CTGSkip"] = "NO"

        self.upload({TSContingency: ctgset})

    # Execute Dynamic Simulation for Non-Skipped Contingencies
    def TSSolveAll(self):
        self.esa.RunScriptCommand("TSSolveAll()")

    def clearram(self):
        # Disable RAM storage & Delete Existing Data in RAM
        self.esa.RunScriptCommand("TSResultStorageSetAll(ALL, NO)")
        self.esa.RunScriptCommand("TSClearResultsFromRAM(ALL,YES,YES,YES,YES,YES)")


    savemap = {
        'TSGenDelta': 'TSSaveGenDelta',
        'TSGenMachineState:1': 'TSSaveGenMachine', # Delta
        'TSGenMachineState:2': 'TSSaveGenMachine', # Speed Deviation
        'TSGenMachineState:3': 'TSSaveGenMachine', # Eqp
        'TSGenMachineState:4': 'TSSaveGenMachine', # Psidp
        'TSGenMachineState:5': 'TSSaveGenMachine', # Psippq
        'TSGenExciterState:1': 'TSSaveGenExciter', # Efd
        'TSGenExciterState:2': 'TSSaveGenExciter', # ?
        'TSGenExciterState:3': 'TSSaveGenExciter', # Vr
        'TSGenExciterState:4': 'TSSaveGenExciter', # Vf
        'TSBusRad': 'TSSaveBusDeg',
    }

    def saveinram(self, objdf, datafields):
        '''
        Save Specified Fields for TS
        '''

        # Get Respective Data
        savefields = []
        for field in datafields:
            if field in self.savemap: 
                savefield = self.savemap[field]
            else:
                savefield = 'TSSave' + field[2:]
            
            objdf[savefield] = 'YES'
            savefields.append(savefield)

        # First three 
        keys = list(objdf.columns[:2])

        # Unique Save Fields
        savefields = np.unique(savefields)

        # Write to PW
        self.esa.change_and_confirm_params_multiple_element(
            ObjectType=objdf.Name,
            command_df=objdf[np.concatenate([keys,savefields])].copy(),
        )

    def set_mva_tol(self, tol=0.1):
        '''
        Sets the MVA Tolerance for NR Convergence
        '''
        settings = self.dm.get_df(Sim_Solution_Options)
        settings['ConvergenceTol:2'] = tol
        self.upload({
            Sim_Solution_Options: settings
        })

    def get_min_volt(self):
        '''
        Retrieve the active minmimum bus voltage in p.u.
        '''
        return self.get_quick(PWCaseInformation,'BusPUVolt:1').iloc[0,0]

    def save_state(self, statename="GWB"):
        '''
        Store a state under an alias and restore it later.
        '''
        self.esa.RunScriptCommand('EnterMode(RUN);')
        self.esa.RunScriptCommand(f'StoreState({statename});')

    def restore_state(self, statename="GWB"):
        '''
        Restore a saved state.
        '''
        self.esa.RunScriptCommand('EnterMode(RUN);')
        self.esa.RunScriptCommand(f'RestoreState(USER,{statename});')

    def delete_state(self, statename="GWB"):
        '''
        Restore a saved state.
        '''
        self.esa.RunScriptCommand('EnterMode(RUN);')
        self.esa.RunScriptCommand(f'DeleteState(USER,{statename});')
                
    def __set_sol_opts(self, name, value):
        settings = self.dm.get_df(Sim_Solution_Options)
        settings['name'] = value
        self.upload({
            Sim_Solution_Options: settings
        })

    '''Sim Solution Options'''

    def max_iterations(self, n: int):
        self.__set_sol_opts('MaxItr', n)

    def zbr_threshold(self, v: float):
        self.__set_sol_opts('ZBRThreshold', v)

    