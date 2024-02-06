from dataclasses import fields as dcfields
from typing import Type
from pandas import DataFrame
from gridwb.workbench.grid.components import *

from gridwb.workbench.utils.metric import Metric
from ..utils.decorators import timing
from ..io.model import IModelIO
from ...saw import SAW

from os import path


# Power World Read/Write
class PowerWorldIO(IModelIO):
    esa: SAW

    @timing
    def open(self):
        # Validate Path Name
        if not path.isabs(self.fname):
            self.fname = path.abspath(self.fname)

        # ESA Object & Transient Sim
        self.esa = SAW(self.fname, CreateIfNotFound=True, early_bind=True)

    @timing
    def download(self, set: list[Type[GObject]]) -> dict[Type[GObject], DataFrame]:
        return {gclass: self.getallof(gclass) for gclass in set}

    def upload(self, model: dict[Type[GObject], DataFrame]) -> bool:
        self.esa.RunScriptCommand("EnterMode(EDIT);")
        for gclass, gset in model.items():
            # Only Pass Params That are Editable
            df = gset[gset.columns.intersection(gclass.editable)].copy()
            self.esa.change_parameters_multiple_element_df(gclass.TYPE, df)
            try:
                self.esa.change_parameters_multiple_element_df(gclass.TYPE, df)
            except:
                print(f"Failed to Write Data for {gclass.TYPE}")

    # Save all Open Changes to PWB File
    def save(self):
        return self.esa.SaveCase()

    def getallof(self, gtype: Type[GObject]):
        # Formatting Outlier
        fexcept = lambda t: "3" + t[5:] if t[:5] == "Three" else t
        fields = [fexcept(f) for f in gtype.fields]

        # Get Data from SimAuto
        df = None
        try:
            df = self.esa.GetParametersMultipleElement(gtype.TYPE, fields)
        except:
            print(f"Failed to read {gtype.TYPE} data.")

        # I chose to Drop Data that is NaN for all Objects,
        # since Volume of Fields is generally High
        if df is None:
            df = DataFrame(columns=fields)
        df.dropna(axis=1, how="all", inplace=True)

        return df

    # Solve Power Flow
    def pflow(self):
        self.esa.SolvePowerFlow()

    # Skip Contingencies
    def skipallbut(self, ctgs):
        ctgset = self.get(TSContingency)

        # Set Skip if not in ctg list
        ctgset["CTGSkip"] = "YES"
        ctgset.loc[ctgset["TSCTGName"].isin(ctgs), "CTGSkip"] = "NO"

        self.update(ctgset)

    # Execute Dynamic Simulation for Non-Skipped Contingencies
    def TSSolveAll(self):
        self.esa.RunScriptCommand("TSSolveAll()")

    def clearram(self):
        # Disable RAM storage & Delete Existing Data in RAM
        self.esa.RunScriptCommand("TSResultStorageSetAll(ALL, NO)")
        self.esa.RunScriptCommand("TSClearResultsFromRAM(ALL,YES,YES,YES,YES,YES)")

    def saveinram(self, metric: Metric):
        o = self.get(metric["Type"])
        o[metric["RAM"]] = "YES"

        # Enable RAM Storage in PW
        self.esa.change_and_confirm_params_multiple_element(
            ObjectType=metric["Type"],
            command_df=o,
        )
