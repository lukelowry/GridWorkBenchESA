
import numpy as np
import pandas 	as pd
from typing import Any, Type

# WorkBench Imports
from ....saw 	import CommandNotRespectedError
from ...grid import GridObject, TSContingency
from ...utils.metric import Metric
from ..app import PWApp, griditer

# Dynamics App (Simulation, Model, etc.)
class Dynamics(PWApp):

    
    # Configuration Extraction TODO Way to Prevent Mis-Type Errors
    @PWApp.configuration.setter
    def configuration(self, config):
        self.runtime		: int 			        = config['Time']
        self.grid_objects	: list[GridObject]      = config['Objects']
        self.metricType		: Type[Metric]		    = config['Metric']
        self._configuration = config

    # Helper Functions for Transient Object-Field Formats
    def field(self, obj: GridObject, field: str): return f"{obj.text} '{obj.id}' | {field}"
    def fields(self, obj, fields): return [self.field(obj,f) for f in fields]

    def changeCTGs(self, ctgs: list[TSContingency], param: Any, val: Any):

        self.esa.change_and_confirm_params_multiple_element(
            ObjectType = 'TSContingency',
            command_df = pd.DataFrame({
                'TSCTGName': [c.name for c in ctgs],
                param : val
            })
        )

    # Skip Simulation of list of Contingencues
    def skip(self, ctgs: list[TSContingency], skip=True):
        self.changeCTGs(ctgs, "CTGSkip", 'YES' if skip else 'NO')

    #Clears All Transient Data from RAM
    def clearram(self):
        self.esa.RunScriptCommand('TSClearResultsFromRAM(ALL,YES,YES,YES,YES,YES)')


    # TODO Only works for obj with 1 key (e.g. no loads, gen, etc)
    def saveinram(self, objs: list[GridObject], metric: Metric):

        for obj in objs:

            #TODO Multiple Keys
            ramField = {metric.RAM[type(obj)]: 'YES'}
            keys = {self.esa.get_key_field_list(obj.text)[0]: [obj.id]}

            # Enable RAM Storage
            self.esa.change_and_confirm_params_multiple_element(
                ObjectType = obj.text,
                command_df = pd.DataFrame(dict(**keys, **ramField))
            )

    # Set Run Time for list of contingencies
    def setRuntime(self, ctgs, sec):
        self.changeCTGs(ctgs, "StartTime", 0)
        self.changeCTGs(ctgs, "EndTime", sec)
    
    # Create 'SimOnly' contingency if it does not exist
    def simonly(self):
        try:
            self.esa.change_and_confirm_params_multiple_element(
                ObjectType = 'TSContingency',
                command_df = pd.DataFrame({'TSCTGName': ['SimOnly']})#, 'SchedValue': [baseLoad]})
            )
        except(CommandNotRespectedError):
            print("Failure to create 'SimOnly' Contingency")
        else:
            print("Contingency 'SimOnly' Initialized")

    @griditer 
    # Execute Transient Simulation for given Contingency(s)
    def solve(self, ctgs: TSContingency | list[TSContingency] = None):

        # Cast To List  
        if not isinstance(ctgs, list): ctgs = [ctgs]
        if not isinstance(self.grid_objects, list): self.grid_objects = [self.grid_objects]

        # Metric to Calculate
        metric = self.metricType

        # Unique List of Fields to Request From PW
        objFields = list({self.field(obj, metric.Dynamic[type(obj)]) for obj in self.grid_objects})

        # Prepare -----------------------------------------------------

        # Clear RAM
        self.clearram()

        # Disable RAM storage for all fields
        self.esa.RunScriptCommand('TSResultStorageSetAll(ALL, NO)')
        
        # Mark Fields for Saving in RAM
        self.saveinram(self.grid_objects, metric)

        # Sim Only (No Contingency)
        if ctgs is None:
            self.simonly()
            ctgs = ['SimOnly']

        # Set skip=false for target ctgs only
        self.skip(self.case.tsctgs) #TODO Check that this is workin
        self.skip(ctgs, False)

        # Set Runtime for Simulation
        self.setRuntime(ctgs, self.runtime)

        # Solve all specified Contingencies
        self.esa.RunScriptCommand('TSSolveAll()')

        # Data Retrieval -------------------------------------------------

        # Run sim and store as combined Data Frame
        meta, df = (None, None)
        for ctg in ctgs:

            # Extract incoming Dataframe
            metaSim, dfSim = self.esa.TSGetContingencyResults(ctg.name, objFields)

            # Custom Fields, Add CTG, Append to Main
            metaSim.drop(columns=['Label', 'VariableName'], inplace=True)
            metaSim.rename(columns={"ObjectType":"Object","ColHeader": "Metric", "PrimaryKey":"ID-A", 'SecondaryKey': "ID-B"}, inplace=True)
            metaSim['Metric'] = metric.units
            metaSim['Contingency'] = ctg.name
            meta = pd.concat([metaSim] if meta is None else[meta, metaSim], axis = 0, ignore_index=True)

            # Trim Data Size, Index by Time, Append to Main
            dfSim = dfSim.astype(np.float32)
            dfSim.set_index('time', inplace=True)
            df = pd.concat([dfSim] if df is None else[df, dfSim], axis=1, ignore_index=True)

        # Clean Up -------------------------------------------------------

        # Hard Copy Before Wiping RAM
        meta = meta.copy(deep=True)
        df = df.copy(deep=True)

        # Clear RAM in PW
        self.clearram()
            
        # Disable RAM storage for all fields
        self.esa.RunScriptCommand('TSResultStorageSetAll(ALL, NO)')

        # Return as meta/data tuple
        return (meta, df)
