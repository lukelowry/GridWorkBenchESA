
# Data Structure Imports
import warnings
import pandas 	as pd
from numpy import NaN

# WorkBench Imports
from ..plugins.powerworld import PowerWorldIO
from ..grid.parts import GridType
from ..utils.metric import Metric
from .app import PWApp, griditer

# Annoying FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)


# Dynamics App (Simulation, Model, etc.)
class Statics(PWApp):

    io: PowerWorldIO

    # Configuration Extraction TODO Way to Prevent Mis-Type Errors
    @PWApp.configuration.setter
    def configuration(self, config):
        self._configuration       = config
        self.objType: GridType  = config["Object"]
        self.metric : Metric      = config["Metric"] 

    @griditer
    def solve(self, ctgs: list[GridType.Contingency]=None):

        # Cast to List
        if not isinstance(ctgs, list): ctgs: list[GridType.Contingency] = [ctgs]

        # Prepare Data Fields
        otype = self.io.otypemap[self.objType]
        keyFields  = self.io.esa.get_key_field_list(otype)
        field = self.metric.Static[self.objType]

        # Get Keys OR Values
        def get(field:str=None) -> pd.DataFrame:
            
            if field is None:
                df = self.io.esa.GetParametersMultipleElement(otype, keyFields)
            else:
                self.io.esa.SolvePowerFlow()
                df = self.io.esa.GetParametersMultipleElement(otype, keyFields+[field])
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
                'Object'     : self.objType.name,
                'ID-A'       : keys.iloc[:,0],
                'ID-B'       : keys.iloc[:,1] if len(keys.columns)>1 else NaN,
                'Metric'     : self.metric.units,
                'Contingency': ctg.CTGLabel
            })
            meta = pd.concat([meta,ctgMeta], ignore_index=True)

        # If Base Case Does not Solve, Return N/A vals
        try:
            refSol = get(field)

            # Set Reference (i.e. No CTG) and Solve
            self.io.esa.RunScriptCommand(f'CTGSetAsReference;')
        except:
            print('Loading Does Not Converge.')
            df = pd.DataFrame(NaN, index=["Value", "Reference"], columns=range(len(ctgs)))
            return (meta, df)

        # For Each CTG
        for ctg in ctgs:

            # Empty DF
            data = pd.DataFrame(columns=["Value", "Reference"])

            # Apply CTG 
            self.io.esa.RunScriptCommand(f'CTGApply({ctg.CTGLabel})')

            # Solve, Drop Keys
            try:
                data["Value"] = get(field)
            except:
                data["Value"] = NaN

            # Set Reference Values    
            data["Reference"] = refSol

            
            # Un-Apply CTG
            self.io.esa.RunScriptCommand(f'CTGRestoreReference;')

            # Add Data to Main
            df = pd.concat([df,data], ignore_index=True)

        return (meta, df.T)
