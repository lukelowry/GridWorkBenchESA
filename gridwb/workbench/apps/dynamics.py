import numpy as np
import pandas as pd
from typing import Any, Type
from gridwb.workbench.grid.components import TSContingency

from gridwb.workbench.plugins.powerworld import PowerWorldIO

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
        self.metric: Type[Metric] = config["Field"]
        self._configuration = config

    # TODO Everything works, just make it so you can select some objs of type not all
    def fields(self, metric):
        objs = self.io.get(metric["Type"])
        flist = []
        for i in objs.index:
            keys = [str(objs.loc[i, key]) for key in objs]
            keys = " ".join(keys)
            flist.append(f"{objs.gtype} {keys} | {metric['Dynamic']}")
        return flist

    # Set Run Time for list of contingencies
    def setRuntime(self, sec):
        ctgs = self.io.get(TSContingency)
        ctgs["StartTime"] = 0
        ctgs["EndTime"] = sec
        self.io.update(ctgs)

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
        objFields = self.fields(self.metric)

        # Prepare Memory
        self.io.clearram()
        self.io.saveinram(self.metric)

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

            # Custom Fields, Add CTG, Append to Main
            metaSim.drop(columns=["Label", "VariableName"], inplace=True)
            metaSim.rename(
                columns={
                    "ObjectType": "Object",
                    "ColHeader": "Metric",
                    "PrimaryKey": "ID-A",
                    "SecondaryKey": "ID-B",
                },
                inplace=True,
            )
            metaSim["Metric"] = self.metric["Units"]
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
