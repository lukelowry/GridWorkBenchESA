from abc import ABC, abstractproperty

from gridwb.workbench.grid.parts import GridType

class Metric(ABC):

    @abstractproperty
    def units(self): 
        pass

    @abstractproperty
    def Static(self) -> dict[GridType, str]: 
        pass
    
    @abstractproperty
    def Dynamic(self)-> dict[GridType, str]: 
        pass
    
    @abstractproperty
    def RAM(self) -> dict[GridType, str]: 
        pass
    
class Voltage(Metric):

    units = "V p.u."
    
    Static = {
        GridType.Bus: "BusPUVolt"
    }

    Dynamic = {
        GridType.Bus: "TSBusVPU"
    }

    RAM = {
        GridType.Bus: "TSSaveBusVPU"
    }

class Freq(Metric):

    units = "Freq p.u."
    
    Static = {
        GridType.Bus: "TBD"
    }

    Dynamic = {
        GridType.Bus: "TSFrequencyinPU"
    }

    RAM = {
        GridType.Bus: "TSSaveBusFreq"
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



