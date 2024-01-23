import numpy as np
import pandas as pd
from typing import Any, Type

from gridwb.workbench.grid.parts import GridObject, GridType
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
        self.metricType: Type[Metric] = config["Metric"]
        self._configuration = config

    # Helper Functions for Transient Object-Field Formats
    def fields(self, metric):
        o = self.io.get(self.io.otypemap[metric["Type"]])
        return [f"Bus '{str(o.iloc[i,0])}' | {metric['Dynamic']}" for i in o.index]

    def changeCTGs(self, ctgs: list[GridType.TSContingency], param: Any, val: Any):
        self.io.esa.change_and_confirm_params_multiple_element(
            ObjectType="TSContingency",
            command_df=pd.DataFrame({"TSCTGName": ctgs, param: val}),
        )

    # Clears All Transient Data from RAM
    def clearram(self):
        self.io.esa.RunScriptCommand("TSClearResultsFromRAM(ALL,YES,YES,YES,YES,YES)")

    # TODO Only works for obj with 1 key (e.g. no loads, gen, etc)
    def saveinram(self, metric: Metric):
        o = self.io.get(self.io.otypemap[metric["Type"]])
        o[metric["RAM"]] = "YES"

        # Enable RAM Storage
        conf = self.io.esa.change_and_confirm_params_multiple_element(
            ObjectType=PowerWorldIO.otypemap[metric["Type"]],
            command_df=o,
        )

    # Set Run Time for list of contingencies
    def setRuntime(self, ctgs, sec):
        self.changeCTGs(ctgs, "StartTime", 0)
        self.changeCTGs(ctgs, "EndTime", sec)

    # Create 'SimOnly' contingency if it does not exist
    def simonly(self):
        try:
            self.io.esa.change_and_confirm_params_multiple_element(
                ObjectType="TSContingency",
                command_df=pd.DataFrame(
                    {"TSCTGName": ["SimOnly"]}
                ),  # , 'SchedValue': [baseLoad]})
            )
        except CommandNotRespectedError:
            print("Failure to create 'SimOnly' Contingency")
        else:
            print("Contingency 'SimOnly' Initialized")

    @griditer
    # Execute Transient Simulation for given Contingency(s)
    def solve(self, ctgs: list[str] = None):
        # Metric to Calculate
        metric = self.metricType

        # Unique List of Fields to Request From PW
        objFields = self.fields(metric)

        # Clear RAM
        self.clearram()

        # Disable RAM storage for all fields
        self.io.esa.RunScriptCommand("TSResultStorageSetAll(ALL, NO)")

        # Mark Fields for Saving in RAM
        self.saveinram(metric)

        # Sim Only (No Contingency)
        if ctgs is None:
            self.simonly()
            ctgs = ["SimOnly"]
        # Cast To List
        if not isinstance(ctgs, list):
            ctgs = [ctgs]

        # Only Sim Requested
        self.io.skipallbut(ctgs)  # Up TO here!!!!!!!!!!!!!!!!

        # Set Runtime for Simulation
        self.setRuntime(ctgs, self.runtime)

        # Solve all specified Contingencies
        self.io.esa.RunScriptCommand("TSSolveAll()")

        # Data Retrieval -------------------------------------------------

        # Run sim and store as combined Data Frame
        meta, df = (None, None)
        for ctg in ctgs:
            # Extract incoming Dataframe
            metaSim, dfSim = self.io.esa.TSGetContingencyResults(ctg, objFields)

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
            metaSim["Metric"] = metric["Units"]
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
        self.clearram()

        # Disable RAM storage for all fields
        self.io.esa.RunScriptCommand("TSResultStorageSetAll(ALL, NO)")

        # Return as meta/data tuple
        return (meta, df)
