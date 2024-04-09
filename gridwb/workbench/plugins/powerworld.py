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

        # Attempt and Initialize TS so we get initial values
        try:
            self.esa.RunScriptCommand("TSInitialize()")
        except:
            print("Failed to Initialize TS Values")

    @timing
    def download(self, set: list[Type[GObject]]) -> dict[Type[GObject], DataFrame]:
        '''Get all Data from PW. What data is downloaded
        depends on the selected Set'''
        return {gclass: self.get(gclass) for gclass in set}

    def upload(self, model: dict[Type[GObject], DataFrame]) -> bool:
        '''Send All WB DataFrame Data to PW'''
        self.esa.RunScriptCommand("EnterMode(EDIT);")
        for gclass, gset in model.items():
            # Only Pass Params That are Editable
            #df = gset[gset.columns.intersection(gclass.editable)].copy()
            df = gset[gset.columns].copy()
            try:
                self.esa.change_parameters_multiple_element_df(gclass.TYPE, df)
            except:
                print(f"Failed to Write Data for {gclass.TYPE}")

    def save(self):
        '''Save all Open Changes to PWB File'''
        return self.esa.SaveCase()

    def get(self, gtype: Type[GObject], keysonly=False):
        '''Get all Objects of Respective Type from PW'''
        fexcept = lambda t: "3" + t[5:] if t[:5] == "Three" else t
        if keysonly:
            fields = [fexcept(f) for f in gtype.keys]
        else:
            fields = [fexcept(f) for f in gtype.fields]

        # Get Data from SimAuto
        df = None
        try:
            df = self.esa.GetParametersMultipleElement(gtype.TYPE, fields)
        except:
            print(f"Failed to read {gtype.TYPE} data.")

        # Empty DF Otherwise
        if df is None:
            df = DataFrame(columns=fields)

        # Set Name of DF to datatype
        df.Name = gtype.TYPE

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

        self.upload({TSContingency: ctgset})

    # Execute Dynamic Simulation for Non-Skipped Contingencies
    def TSSolveAll(self):
        self.esa.RunScriptCommand("TSSolveAll()")

    def clearram(self):
        # Disable RAM storage & Delete Existing Data in RAM
        self.esa.RunScriptCommand("TSResultStorageSetAll(ALL, NO)")
        self.esa.RunScriptCommand("TSClearResultsFromRAM(ALL,YES,YES,YES,YES,YES)")

    '''
    Depricated
    def saveinram(self, metric: Metric):

        # Get Respective Data
        gtype = metric['Type']
        cfg = self.get(gtype, keysonly=True) # TODO Use local IDs

        # Set TSSave to Yes
        cfg[metric["RAM"]] = "YES"

        # Write to PW
        self.esa.change_and_confirm_params_multiple_element(
            ObjectType=gtype.TYPE,
            command_df=cfg,
        )
    '''

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
        '''Save Specified Fields for TS'''

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
