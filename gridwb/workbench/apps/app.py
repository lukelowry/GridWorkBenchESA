
import functools
from typing import Any
import pandas 	as pd
from itertools 	import product

from gridwb.workbench.interfaces.model import IModelIO

from ..grid.case import Case
from ..utils.conditions import *

# TODO App Features
# - TSGetVCurveData("FileName", filter);This field comapres to QV curve!
# - TSRunResultAnalyzer PW Post-transient analysis
# - Tolerance MVA
# - Need to auto create DSTimeSChedule & LoadCharacteristic for Ramp

# Application Base Class
class PWApp:

    def __init__(self, io: IModelIO) -> None:

        # Application Interface
        self.io = io

        # Conditions for griditer feature
        self.conditions: dict[Condition, list[Any]] = None

        # Default Grid Iteration Values TODO Remove
        self.defaultConditions =  {
            BaseLoad	: BaseLoad.default,
            RampRate	: RampRate.default #'step size' next
        }

    # Configuration Property
    @property
    def configuration(self):
        return self._configuration

    @configuration.setter
    def configuration(self, config):
        self._configuration = config

    # Define Condition ranges for Grid Iter Feature
    def rotate(self, conditions: dict[Condition, list[Any]]):
        self.conditions = conditions

     # Define Condition ranges for Grid Iter Feature
    def r(
            self, 
            baseload = float | list[float],
            **kwargs
        ):
        
        self.conditions = {
            BaseLoad: baseload,
            **kwargs
        }


    # Sub-Classes that want an application feature to be 'grid iterated' will use decorator @griditer

"""

Grid Iter Plug-In!

TODO Grid Iter Loading Bar
from IPython.display import clear_output 

Given a set of possible grid conditions/states,
GridIterator provides a reliable way to iterate through
all combinations of these grid states without any hasle.

Currently implmented with dynamics in mind. Could be easily used
in other contexts.
"""

# Enter Grid Pre-Iteration
def gridenter(esa: SAW):

    # Save gridstate
    if not esa.SaveState():
        print("Case backup saved for restoration.")
    else:
        print("Failed to save case state. Investigate before continuing.")

# Exit Grid Post-Iteration
def gridexit(esa: SAW):

    print("\nSimulations Finished.")

    #Revert to original state
    print("Reverting to original PF state.")
    esa.LoadState() 

# Decorator for PWApp Instance Methods
def griditer(func):

    # Sub-Class Method expected to have ESA as instance attribute
    @functools.wraps(func)
    def wrapper(self: PWApp, *args, **kwargs):

        # App Regerence
        app = self
        esa = app.io.esa

        # Act as normal App Function if no conditions
        if app.conditions is None:
            return func(app, *args, **kwargs)

        # Prepare Grid for many changes
        gridenter(esa)

        # Outer Dataframe to save iterated application data
        outer_meta  : pd.DataFrame = None
        outer_df    : pd.DataFrame = None

        # For every scenario 
        for scenarioVals in product(*app.conditions.values()): 

            # Apply Each Condition in Grid Scenario
            scenario = dict(zip(app.conditions.keys(), scenarioVals))
            for condition, value in scenario.items():
                print(condition.text+ " : " + str(round(value,2)))
                condition.apply(esa, scenario)

            # Retrieve Application Dataframe
            inner_meta, inner_df = func(app, *args, **kwargs)

            if inner_meta is None or inner_df is None:
                continue

            # Add Scenario Info
            for condition, value in scenario.items():
                inner_meta[condition.text] = value

            # Append to Main
            outer_meta  = pd.concat([inner_meta] if outer_meta is None else[outer_meta, inner_meta], axis=0, ignore_index=True)
            outer_df    = pd.concat([inner_df] if outer_df is None else[outer_df, inner_df], axis=1, ignore_index=True)
        
        # Safely reset grid to original state
        gridexit(esa)

        return (outer_meta, outer_df)

    return wrapper



