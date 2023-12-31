from abc import ABC, abstractproperty
from ..grid.components import *

class Metric(ABC):

    @abstractproperty
    def units(self): 
        pass

    @abstractproperty
    def Static(self) -> dict[GridObject, str]: 
        pass
    
    @abstractproperty
    def Dynamic(self)-> dict[GridObject, str]: 
        pass
    
    @abstractproperty
    def RAM(self) -> dict[GridObject, str]: 
        pass
    
class Voltage(Metric):

    units = "V p.u."
    
    Static = {
        Bus: "BusPUVolt"
    }

    Dynamic = {
        Bus: "TSBusVPU"
    }

    RAM = {
        Bus: "TSSaveBusVPU"
    }

class Freq(Metric):

    units = "Freq p.u."
    
    Static = {
        Bus: "TBD"
    }

    Dynamic = {
        Bus: "TSFrequencyinPU"
    }

    RAM = {
        Bus: "TSSaveBusFreq"
    }

"""
TSSaveBusDeg
TSSaveBusDegNoshift
TSSaveBusFreq
TSSaveBusGenP
TSSaveBusGenQ
TSSaveBusLoadP
TSSaveBusLoadQ
TSSaveBusROCOFHz
TSSaveBusStates
TSSaveBusStatus
TSSaveBusVPU
"""



