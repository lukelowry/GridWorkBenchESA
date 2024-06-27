import numpy as np
import pandas as pd
from typing import Any, Type
from gridwb.workbench.grid.components import TSContingency

from gridwb.workbench.core.powerworld import PowerWorldIO

# WorkBench Imports
from ...saw import CommandNotRespectedError
from ..utils.metric import Metric
from .app import PWApp, griditer




# Dynamics App (Simulation, Model, etc.)
class Dynamics(PWApp):

    io: PowerWorldIO

    @PWApp.configuration.setter
    def configuration(self, config):
        self.runtime: int = config["Time"]
        self.retrieve = config['Fields']
        self._configuration = config

    def fields(self, metric):
        '''Get TS Formatted Fields for Requested Objects'''
        objs = self.io.get(metric["Type"]) # TODO I don't need to retrieve from PW I have it local. Will Speed up
        os = objs['ObjectID']
        flist = [f"{str(os.loc[i])} | {metric['Dynamic']}" for i in range(len(os))]
        return flist

    # Set Run Time for list of contingencies
    def setRuntime(self, sec):
        ctgs = self.io.get(TSContingency, keysonly=True)
        ctgs["StartTime"] = 0
        ctgs["EndTime"] = sec
        self.io.upload({TSContingency: ctgs})

    # Create 'SimOnly' contingency if it does not exist
    # TODO Add TSCtgElement that closes an already closed gen at t=0
    def simonly(self):
        try:
            self.io.esa.change_and_confirm_params_multiple_element(
                ObjectType="TSContingency",
                command_df=pd.DataFrame({"TSCTGName": ["SimOnly"]}),
            )
        except CommandNotRespectedError:
            print("Failure to create 'SimOnly' Contingency")
        else:
            print("Contingency 'SimOnly' Initialized")

    @griditer
    def solve(self, ctgs: list[str] = None):
        # Unique List of Fields to Request From PW

        # Prepare Memory
        self.io.clearram()

        # Gen Obj Field list and Mark Fields for RAM storage
        objFields = []
        flatFields = []
        for objects, fields in self.retrieve:
            self.io.saveinram(objects, fields)
            for id in objects['ObjectID']:
                objFields += [f"{id} | {f}" for f in fields]
                flatFields += fields

        # Sim Only (No Contingency)
        if ctgs is None:
            self.simonly()
            ctgs = ["SimOnly"]
        # Cast To List
        if not isinstance(ctgs, list):
            ctgs = [ctgs]

        # Only Sims Requested
        self.io.skipallbut(ctgs)

        # Set Runtime for Simulation
        self.setRuntime(self.runtime)

        # Execute Dynamic Simulation for Specified CTGs - High Compute Time
        self.io.TSSolveAll()

        # Get Results
        meta, df = (None, None)
        for ctg in ctgs:
            # Extract incoming Dataframe
            metaSim, dfSim = self.io.esa.TSGetContingencyResults(ctg, objFields)
            # Weird ESA bug where if items at end are open, they don't return data :(
            # Happened Again, if last column is zero valued it removes the column. Awful

            # Proposed Fix: Will Fill in any floating columns not present in data but in meta
            fillIdx = metaSim.index[~metaSim.index.isin(dfSim.columns)]
            dfSim[fillIdx] = 0.0

            # Custom Fields, Add CTG, Append to Main
            metaSim.drop(columns=["Label", "ColHeader"], inplace=True)
            metaSim.rename(
                columns={
                    "ObjectType": "Object",
                    "PrimaryKey": "ID-A",
                    "SecondaryKey": "ID-B",
                    'VariableName': "Metric"
                },
                inplace=True,
            )
            metaSim['Metric'] = flatFields
            metaSim["Contingency"] = ctg
            meta = pd.concat(
                [metaSim] if meta is None else [meta, metaSim],
                axis=0,
                ignore_index=True,
            )

            # Won't work if first result is bad
            if len(dfSim.columns) < 2:
                dfSim = pd.DataFrame(np.NaN, columns=metaSim.index, index=[0])
                dfSim.index.name = "time"
            else:
                # Trim Data Size, Index by Time, Append to Main
                dfSim = dfSim.astype(np.float32)
                dfSim.set_index("time", inplace=True)

            #if df is not None:
                #print(df.join(dfSim,how='outer'))
            #TODO only working for same types of ctgs
            df = pd.concat(
                [dfSim] if df is None else [df, dfSim], axis=1, ignore_index=True
            )

        # Clean Up -------------------------------------------------------

        # Hard Copy Before Wiping RAM
        meta: pd.DataFrame = meta.copy(deep=True)
        df: pd.DataFrame = df.copy(deep=True)

        # Clear RAM in PW
        self.io.clearram()

        # Return as meta/data tuple
        return (meta, df)
