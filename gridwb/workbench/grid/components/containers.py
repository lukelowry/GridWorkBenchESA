from .structures import TieredObject
from .devices import *


# Region child to none
class Region(TieredObject):
    text = "SuperArea"

    #Exception for Region - TODO make this not needed
    @property
    def id(self):
        return self.name
    
# Area child of Region
class Area(TieredObject):
    text = "Area"

# Substation Child of Area
class Sub(TieredObject):
    text = "Substation"

    longitude: float
    latitude: float

# Bus child of Substation
class Bus(TieredObject):
    text = "Bus"

    MWGen = "BusGenMW"
    MVARGen = "BusGenMVR"

    MWLoad = "BusLoadMW"
    MVARLoad = "BusLoadMVR"

    Voltage = "BusPUVolt"


    
