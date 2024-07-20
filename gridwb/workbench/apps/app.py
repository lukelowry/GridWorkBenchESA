from typing import Any, Iterable
from numpy import NaN
from pandas import DataFrame, concat
from functools import wraps
from itertools import product

from ..core import Context
from ..io.model import IModelIO
from ..utils.conditions import *

# TODO App Features
# - TSGetVCurveData("FileName", filter);This field comapres to QV curve!
# - TSRunResultAnalyzer PW Post-transient analysis
# - Tolerance MVA
# - Need to auto create DSTimeSChedule & LoadCharacteristic for Ramp

# Application Base Class
class PWApp:
    def __init__(self, context: Context) -> None:
        # Application Interface
        self.io = context.getIO()
        self.dm = context.getDataMaintainer()

        # Conditions for griditer feature
        self.conditions: dict[Condition, list[Any]] = {}

        # Default Grid Iteration Values TODO Remove
        self.defaultConditions = {
            BaseLoad: BaseLoad.default,
            RampRate: RampRate.default,
            TimeStep: TimeStep.default,
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
        for c, v in conditions.items():
            if not isinstance(v, Iterable):
                self.conditions[c] = [v]
            else:
                self.conditions[c] = v

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
- Statics (Power flow, CPF, QV & PV Analysis)
- GICS
- OPF
"""


# Enter Grid Pre-Iteration
def gridenter(io: IModelIO):
    # Save gridstate
    if not io.esa.SaveState():
        print("Case backup saved for restoration.")
    else:
        print("Failed to save case state. Investigate before continuing.")


# Exit Grid Post-Iteration
def gridexit(io: IModelIO):
    print("\nSimulations Finished.")

    # Revert to original state
    print("Reverting to original PF state.")
    io.esa.LoadState()


# Decorator for PWApp Instance Methods
def griditer(func):
    # Sub-Class Method expected to have ESA as instance attribute
    @wraps(func)
    def wrapper(self: PWApp, *args, **kwargs):
        # App Regerence
        app = self

        # Act as normal App Function if no conditions
        if app.conditions is None or len(app.conditions)==0:
            return func(app, *args, **kwargs)

        # Prepare Grid for many changes
        gridenter(app.io)

        # TODO Apply default Conditions for Non-Passed?

        # Outer Dataframe to save iterated application data
        outer_meta: DataFrame = None
        outer_df: DataFrame = None

        # For every scenario
        for scenarioVals in product(*app.conditions.values()):
            # Apply Each Condition in Grid Scenario
            scenario: dict[Condition, Any] = dict(
                zip(app.conditions.keys(), scenarioVals)
            )
            for condition, value in scenario.items():
                condition.apply(app.io, scenario)

                print(condition.text + " : " + str(value))

            # Retrieve Application Dataframe
            inner_meta, inner_df = func(app, *args, **kwargs)

            if inner_meta is None or inner_df is None:
                continue

            # Add Scenario Info
            for condition, value in scenario.items():
                try:
                    inner_meta[condition.text] = value
                except:
                    inner_meta[condition.text] = str(value)

            # Append to Main
            if outer_meta is None:
                outer_meta = inner_meta
                outer_df = inner_df
            else:
                # Catch failed simulation, note: problems if first sim is bad
                if len(inner_df.index) != len(outer_df.index):
                    inner_df = DataFrame(
                        NaN, columns=inner_df.columns, index=outer_df.index
                    )

                outer_meta = concat(
                    [outer_meta, inner_meta], axis=0, ignore_index=True
                )
                outer_df = concat([outer_df, inner_df], axis=1, ignore_index=True)

        # Safely reset grid to original state
        gridexit(app.io)

        return (outer_meta, outer_df)

    return wrapper
