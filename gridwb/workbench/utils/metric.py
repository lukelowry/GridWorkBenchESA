from abc import ABC, abstractproperty

from gridwb.workbench.grid.parts import GridType


class Metric(ABC):
    @abstractproperty
    def units(self):
        pass


class Voltage(Metric):
    Bus = {
        "Type": GridType.Bus,
        "Units": "V p.u",
        "Static": "BusPUVolt",
        "Dynamic": "TSBusVPU",
        "RAM": "TSSaveBusVPU",
    }


class Freq(Metric):
    units = "Freq p.u."

    Static = {GridType.Bus: "TBD"}

    Dynamic = {GridType.Bus: "TSFrequencyinPU"}

    RAM = {GridType.Bus: "TSSaveBusFreq"}


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
