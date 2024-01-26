from ..grid import Bus, Gen


class Metric:
    pass


class Voltage(Metric):
    Bus = {
        "Type": Bus,
        "Units": "V p.u",
        "Static": "BusPUVolt",
        "Dynamic": "TSBusVPU",
        "RAM": "TSSaveBusVPU",
    }


class Freq(Metric):
    Bus = {
        "Type": Bus,
        "Units": "Freq p.u",
        "Static": "TBD",
        "Dynamic": "TSFrequencyinPU",
        "RAM": "TSSaveBusFreq",
    }


class Load(Metric):
    Bus = {
        "Type": Bus,
        "Units": "MW",
        "Static": "BusLoadMW",
        "Dynamic": "TSBusLoadP",
        "RAM": "TSSaveBusLoadP",
    }

    Gen = {
        "Type": Gen,
        "Units": "MW",
        "Static": "GenMW",
        "Dynamic": "TSGenP",
        "RAM": "TSSaveGenP",
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
