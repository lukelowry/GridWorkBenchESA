import numpy as np
import pandas as pd
from typing import Any, Type

# WorkBench Imports
from .app import PWApp, griditer
from gridwb.workbench.grid.components import GIC_Options_Value, GICInputVoltObject, TSContingency
from gridwb.workbench.plugins.powerworld import PowerWorldIO

fcmd = lambda obj, fields, data: f"SetData({obj}, {fields}, {data})".replace("'","")
gicoption = lambda option, choice: fcmd("GIC_Options_Value",['VariableName', 'ValueField'], [option, choice])

# Dynamics App (Simulation, Model, etc.)
class GIC(PWApp):
    io: PowerWorldIO

    def settings(self, value=None):
        '''View Settings or pass a DF to Change Settings'''
        if value is None:
            return self.io.esa.GetParametersMultipleElement(
                GIC_Options_Value.TYPE, 
                GIC_Options_Value.fields
            )[['VariableName', 'ValueField']]
        else:
            self.io.upload({GIC_Options_Value: value})

    def calc_mode(self, mode: str):
        """GIC Calculation Mode (Either SnapShot, TimeVarying, 
        NonUniformTimeVarying, or SpatiallyUniformTimeVarying)"""

        self.io.esa.RunScriptCommand(gicoption("CalcMode",mode))

    def pf_include(self, include=True):
        '''Enable GIC for Power Flow Calculations'''
        self.io.esa.RunScriptCommand(gicoption("IncludeInPowerFlow",include))

    def ts_include(self, include=True):
        '''Enable GIC for Time Domain'''
        self.io.esa.RunScriptCommand(gicoption("IncludeTimeDomain",include))


    def timevary_csv(self, fpath):
        '''Pass a CSV filepath to upload Time Varying 
        Series Voltage Inputs for GIC
        
        Format Example

        Time In Seconds, 1, 2, 3
        Branch '1' '2' '1', 0.1, 0.11, 0.14
        Branch '1' '2' '2', 0.1, 0.11, 0.14
        Branch '1' '2' '3', 0.1, 0.11, 0.14
        
        '''

        # Get CSV Data
        csv = pd.read_csv(fpath, header=None)

        # Format for PW
        obj = GICInputVoltObject.TYPE
        fields = ['WhoAmI'] + [f'GICObjectInputDCVolt:{i+1}' for i in range(csv.columns.size-1)]

        # Send Field Data
        for row in csv.to_records(False):
            cmd = fcmd(obj, fields, list(row)).replace("'", "")
            self.io.esa.RunScriptCommand(cmd)

        print("GIC Time Varying Data Uploaded")
