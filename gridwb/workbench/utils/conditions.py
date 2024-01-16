import numpy 				as np
import pandas 				as pd

from abc 		import ABC, abstractmethod
from ...saw    import SAW
"""
Conditions to Implement:
 - Zone-Load Differential MW (Zones w/ High Load difference)
 - Load P/Q Ratio
 - Bus Shunts (G/Cap/Reactor)
 - Injection Groups
 - IBR % (Ratio of IBR to SG)
 - Zoned IBR/SG Differential (e.g. Large Inertial Zone & Small IBR Zone)
 - Contingencies (is this useful though?) - Maybe be a user-only loop
 - Alterntaive Grid Topologies
 - Control System Parameters
 
"""
# Inclusive Version of np.arange
def trange(min, max, n):
	if n < 2:
		raise Exception("trange: N Steps must be >= 2")
	res = (max-min)/(n-1)
	return np.arange(min, max+res/2, res)

# Initialization and Implmentation for a Generic Grid Conditon
class Condition(ABC):

	text = "Condition"

    # TODO Remove
	def __str__(self) -> str:
		return self.text

	# Default Value: Single Value in a list (i.e. [1.2])
	@property
	@abstractmethod
	def default():
		pass
      
	# Implement PW Elements if Needed (e.g. Load Characteristic may not exist)
	@staticmethod
	@abstractmethod
	def prepare(esa: SAW):
		pass

	# Implementation of condition through ESA
    # All other scenario conditiosn are given incase it is needed.
	@staticmethod
	@abstractmethod
	def apply(esa: SAW, conditions):
		pass

# Default Base Load & Implmentation Method
class BaseLoad(Condition):

    text = "Base Load MW Mult"
    default = [1]
	
    # TODO Make Sure Zone exists and is all-encompassing
    def prepare(esa: SAW):
        pass

    def apply(esa: SAW, conditions):

        baseLoad = conditions[BaseLoad]

        esa.change_and_confirm_params_multiple_element(
            ObjectType = 'Zone',
            command_df = pd.DataFrame({'ZoneNum': [1], 'SchedValue': [baseLoad]})
        )

# Default Ramp Rate & Implmentation Method
class RampRate(Condition):

    text = "Ramp Rate"
    default = [0]

    # TODO Load Characyeristic Must exist
    def prepare(esa: SAW):
        r''' 
        CREATE Zone Load Characteristic - REturn message if not done
        load change Will not work without assigning sched to LC
        load_char = {
            "ObjectType": ["Zone"],
            "BusNum": ["Nan"],
            "LoadID": [""],
            "TSFlag": [1], # Enable Here
        }
        load_char = pd.DataFrame(load_char)
        self.esa.change_and_confirm_params_multiple_element(
            ObjectType='LoadCharacteristic_LoadTimeSchedule',
            command_df=load_char
        )
        '''
        pass

    def apply(esa: SAW, conditions):
		
        baseLF = conditions[BaseLoad]
        ramprate = conditions[RampRate] # MW per min
		
        ramptime = 100000
        end = (baseLF*1136 + ramprate/60*ramptime)/(baseLF*1136) 
		
        # At T=0, LoadMult MUST be 1 for DSTimeSched, scale is relative to baseload
        sched = "WB_SCHED"
        esa.change_and_confirm_params_multiple_element(
            ObjectType='DSTimeScheduleTimePoint',
            command_df=pd.DataFrame({
				'DSTimeSchedName': [sched, sched],
				'DSTimeSchedTime': [0, ramptime],
				'DSTimeSchedValue': [1, end]
			})
        )
