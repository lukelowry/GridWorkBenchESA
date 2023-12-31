
# Data Structure Imports
import pandas 	as pd
from numpy import NaN

# WorkBench Imports
from ...grid import GridObject
from ...grid.components.contingency import Contingency
from ...io.pwb import PowerWorldIO
from ...utils.metric import Metric
from ..app import PWApp, griditer


# Dynamics App (Simulation, Model, etc.)
class Statics(PWApp):

    # Configuration Extraction TODO Way to Prevent Mis-Type Errors
    @PWApp.configuration.setter
    def configuration(self, config):
        self._configuration       = config
        self.objType: GridObject  = config["Object"]
        self.metric : Metric      = config["Metric"] 

    @griditer
    def solve(self, ctgs: Contingency | list[Contingency]=None):

        # Cast to List
        if not isinstance(ctgs, list): ctgs: list[Contingency] = [ctgs]

        # Prepare Data Fields
        otype = self.objType.text
        keyFields  = self.esa.get_key_field_list(otype)
        field = self.metric.Static[self.objType]

        # Get Keys OR Values
        def get(field:str=None) -> pd.DataFrame:
            
            if field is None:
                df = self.esa.GetParametersMultipleElement(otype, keyFields)
            else:
                self.esa.SolvePowerFlow()
                df = self.esa.GetParametersMultipleElement(otype, keyFields+[field])
                df = df.rename(columns={field: "Value"})
                df = df.drop(columns=keyFields)

            return df
        
        # Initialize DFs
        meta = pd.DataFrame(columns=["Object", "ID-A", "ID-B", "Metric", "Contingency"])
        df = pd.DataFrame(columns=["Value", "Reference"])
        keys = get()

        # Add All Meta Records
        for ctg in ctgs:
            ctgMeta = pd.DataFrame({
                'Object'     : otype,
                'ID-A'       : keys.iloc[:,0],
                'ID-B'       : keys.iloc[:,1] if len(keys.columns)>1 else NaN,
                'Metric'     : self.metric.units,
                'Contingency': ctg.name
            })
            meta = pd.concat([meta,ctgMeta], ignore_index=True)

        # Set Reference (i.e. No CTG) and Solve
        self.esa.RunScriptCommand(f'CTGSetAsReference;')

        # If Base Case Does not Solve, Return N/A vals
        try:
            refSol = get(field)
        except:
            df = pd.DataFrame(NaN, index=["Value", "Reference"], columns=range(len(ctgs)))
            return (meta, df)

        # For Each CTG
        for ctg in ctgs:

            # Empty DF
            data = pd.DataFrame(columns=["Value", "Reference"])

            # Apply CTG 
            self.esa.RunScriptCommand(f'CTGApply({ctg.name})')

            # Solve, Drop Keys
            try:
                data["Value"] = get(field)
            except:
                data["Value"] = NaN

            # Set Reference Values    
            data["Reference"] = refSol

            # Add Data to Main
            df = pd.concat([df,data], ignore_index=True)

            # Un-Apply CTG
            self.esa.RunScriptCommand(f'CTGRestoreReference;')

        return (meta, df.T)
