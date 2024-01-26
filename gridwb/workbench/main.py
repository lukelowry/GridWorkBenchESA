# GridWorkbench: A Python structure for power system data
#
# Adam Birchfield, Texas A&M University
#
# Log:
# 9/29/2021 Initial version, rearranged from prior draft so that most object fields
#   are only listed in one place, the PW_Fields table. Now to add a field you just
#   need to add it in that list.
# 11/2/2021 Renamed this file to core and added fuel type object
# 1/22/22 Split out all device types
# 8/18/22 Engine rename and throwing exceptions for non-existent items
#

# Imports
import cmath
import numpy as np
from pandas import DataFrame, concat
from dataclasses import astuple
from typing import Iterable, Type, TypeVar
from .grid.components import *
from .plugins.powerworld import PowerWorldIO
from .apps import Dynamics, Statics

class GridSet:

    Light = [Bus, Gen, Load, Branch, Shunt, Transformer]
    """Very Fast. Bare Minimum Elements for Power System Analysis. """
    Optimal = Light + [Substation, Area, SuperArea]
    """Acceptable. All Basic Data & Meta Data"""
    Dynamic = [AGCController_AGCBradley,AGCController_AGCPulseRate,AGCController_AGCSetpoint,Exciter_AC10C,Exciter_AC11C,Exciter_AC1C,Exciter_AC2C,Exciter_AC3C,Exciter_AC4C,Exciter_AC5C,Exciter_AC6A,Exciter_AC6C,Exciter_AC7B,Exciter_AC7C,Exciter_AC8B,Exciter_AC8C,Exciter_AC9C,Exciter_BBSEX1,Exciter_BPA_EA,Exciter_BPA_EB,Exciter_BPA_EC,Exciter_BPA_ED,Exciter_BPA_EE,Exciter_BPA_EF,Exciter_BPA_EG,Exciter_BPA_EJ,Exciter_BPA_EK,Exciter_BPA_FA,Exciter_BPA_FB,Exciter_BPA_FC,Exciter_BPA_FD,Exciter_BPA_FE,Exciter_BPA_FF,Exciter_BPA_FG,Exciter_BPA_FH,Exciter_BPA_FJ,Exciter_BPA_FK,Exciter_BPA_FL,Exciter_BPA_FM,Exciter_BPA_FN,Exciter_BPA_FO,Exciter_BPA_FP,Exciter_BPA_FQ,Exciter_BPA_FR,Exciter_BPA_FS,Exciter_BPA_FT,Exciter_BPA_FU,Exciter_BPA_FV,Exciter_CELIN,Exciter_DC1C,Exciter_DC2C,Exciter_DC3A,Exciter_DC4B,Exciter_DC4C,Exciter_EMAC1T,Exciter_ESAC1A,Exciter_ESAC2A,Exciter_ESAC3A,Exciter_ESAC4A,Exciter_ESAC5A,Exciter_ESAC6A,Exciter_ESAC7B,Exciter_ESAC8B_GE,Exciter_ESAC8B_PTI,Exciter_ESDC1A,Exciter_ESDC2A,Exciter_ESDC3A,Exciter_ESDC4B,Exciter_ESST1A,Exciter_ESST1A_GE,Exciter_ESST2A,Exciter_ESST3A,Exciter_ESST4B,Exciter_ESST5B,Exciter_ESST6B,Exciter_ESST7B,Exciter_ESURRY,Exciter_EWTGFC,Exciter_EX2000,Exciter_EXAC1,Exciter_EXAC1A,Exciter_EXAC2,Exciter_EXAC3,Exciter_EXAC3A,Exciter_EXAC4,Exciter_EXAC6A,Exciter_EXAC8B,Exciter_EXBAS,Exciter_EXBBC,Exciter_EXDC1,Exciter_EXDC2A,Exciter_EXDC2_GE,Exciter_EXDC2_PTI,Exciter_EXDC4,Exciter_EXELI,Exciter_EXIVO,Exciter_EXPIC1,Exciter_EXST1_GE,Exciter_EXST1_PTI,Exciter_EXST2,Exciter_EXST2A,Exciter_EXST3,Exciter_EXST3A,Exciter_EXST4B,Exciter_EXWTG1,Exciter_EXWTGE,Exciter_Generic,Exciter_IEEET1,Exciter_IEEET2,Exciter_IEEET3,Exciter_IEEET4,Exciter_IEEET5,Exciter_IEEEX1,Exciter_IEEEX2,Exciter_IEEEX3,Exciter_IEEEX4,Exciter_IEET1A,Exciter_IEET1B,Exciter_IEET5A,Exciter_IEEX2A,Exciter_IVOEX,Exciter_MEXS,Exciter_PLAYINEX,Exciter_PV1E,Exciter_REECA1,Exciter_REECB1,Exciter_REECC1,Exciter_REEC_A,Exciter_REEC_B,Exciter_REEC_C,Exciter_REEC_D,Exciter_REEC_E,Exciter_REXS,Exciter_REXSY1,Exciter_REXSYS,Exciter_SCRX,Exciter_SEXS_GE,Exciter_SEXS_PTI,Exciter_ST10C,Exciter_ST1C,Exciter_ST2C,Exciter_ST3C,Exciter_ST4C,Exciter_ST5B,Exciter_ST5C,Exciter_ST6B,Exciter_ST6C,Exciter_ST6C_PTI,Exciter_ST7B,Exciter_ST7C,Exciter_ST8C,Exciter_ST9C,Exciter_TEXS,Exciter_URST5T,Exciter_WT2E,Exciter_WT2E1,Exciter_WT3E,Exciter_WT3E1,Exciter_WT4E,Exciter_WT4E1,Governor_BBGOV1,Governor_BPA_GG,Governor_BPA_GH,Governor_BPA_GIGATB,Governor_BPA_GJGATB,Governor_BPA_GKGATB,Governor_BPA_GLTB,Governor_BPA_GSTA,Governor_BPA_GSTB,Governor_BPA_GSTC,Governor_BPA_GWTW,Governor_CCBT1,Governor_CRCMGV,Governor_DEGOV,Governor_DEGOV1,Governor_DEGOV1D,Governor_G2WSCC,Governor_GAST2A,Governor_GAST2AD,Governor_GAST2A_AIR,Governor_GASTD,Governor_GASTWD,Governor_GASTWDD,Governor_GASTWD_AIR,Governor_GAST_GE,Governor_GAST_PTI,Governor_Generic,Governor_GGOV1,Governor_GGOV1D,Governor_GGOV2,Governor_GGOV3,Governor_GPWSCC,Governor_H6E,Governor_HGBLEM,Governor_HRSGSimple,Governor_HYG3,Governor_HYGOV,Governor_HYGOV2,Governor_HYGOV2D,Governor_HYGOV4,Governor_HYGOVD,Governor_HYGOVR,Governor_HYGOVR1,Governor_HYPID,Governor_HYST1,Governor_IEEEG1,Governor_IEEEG1D,Governor_IEEEG1PID,Governor_IEEEG1_GE,Governor_IEEEG2,Governor_IEEEG3D,Governor_IEEEG3_GE,Governor_IEEEG3_PTI,Governor_IEESGO,Governor_IEESGOD,Governor_ISOGOV1,Governor_PIDGOV,Governor_PIDGOVD,Governor_PLAYINGOV,Governor_SHAF25,Governor_TGOV1,Governor_TGOV1D,Governor_TGOV2,Governor_TGOV3,Governor_TGOV3D,Governor_TGOV5,Governor_TURCZT,Governor_UCBGT,Governor_UCCPSS,Governor_UHRSG,Governor_URGS3T,Governor_W2301,Governor_WEHGOV,Governor_WESGOV,Governor_WESGOVD,Governor_WNDTGE,Governor_WNDTRB,Governor_WPIDHY,Governor_WPIDHYD,Governor_WSHYDD,Governor_WSHYGP,Governor_WSIEG1,Governor_WT12T1,Governor_WT1T,Governor_WT2T,Governor_WT3T,Governor_WT3T1,Governor_WT4T,Governor_WTDTA1,Governor_WTGT_A,Governor_WTGT_B,InjectionGroupModel_GenericInjectionGroup,InjectionGroupModel_GroupMSS,LineRelayModel_DIFFRLYG,LineRelayModel_DIFFRLYS,LineRelayModel_DIRECLEN,LineRelayModel_DISTR1,LineRelayModel_DISTRELAY,LineRelayModel_DISTRELAYITR,LineRelayModel_FACRI_SC,LineRelayModel_GenericTRLineRelay,LineRelayModel_LOCTI,LineRelayModel_OOSLEN,LineRelayModel_OOSLNQ,LineRelayModel_OOSMHO,LineRelayModel_RELODEN,LineRelayModel_RXR1,LineRelayModel_SCGAP,LineRelayModel_SCMOV,LineRelayModel_SERIESCAPRELAY,LineRelayModel_SIMPLEOC1,LineRelayModel_TIOCR1,LineRelayModel_TIOCRS,LineRelayModel_TIOCRSRF,LineRelayModel_TLIN1,LineRelayModel_UF_AK,LineRelayModel_ZDCB,LineRelayModel_ZLIN1,LineRelayModel_ZLINW,LineRelayModel_ZPOTT,LineRelayModel_ZQLIN1,LineRelayModel_ZQLIN2,LoadCharacteristic_BPA_Induction_MotorI,LoadCharacteristic_BPA_Induction_MotorL,LoadCharacteristic_BPA_Type_LA,LoadCharacteristic_BPA_Type_LB,LoadCharacteristic_BRAKE,LoadCharacteristic_CIM5,LoadCharacteristic_CIM5_PTR,LoadCharacteristic_CIM6,LoadCharacteristic_CIMW,LoadCharacteristic_CLOD,LoadCharacteristic_CMLD,LoadCharacteristic_CMPLDW,LoadCharacteristic_CMPLDWNF,LoadCharacteristic_CompLoad,LoadCharacteristic_DLIGHT,LoadCharacteristic_EXTL,LoadCharacteristic_Generic,LoadCharacteristic_IEEL,LoadCharacteristic_INDMOT1P,LoadCharacteristic_INDMOT1P_PTR,LoadCharacteristic_INDMOT3P_A,LoadCharacteristic_LD1PAC,LoadCharacteristic_LD1PAC_CMP,LoadCharacteristic_LDELEC,LoadCharacteristic_LDFR,LoadCharacteristic_LDRANDOM,LoadCharacteristic_LoadTimeSchedule,LoadCharacteristic_MOTORC,LoadCharacteristic_MOTORW,LoadCharacteristic_MOTORX,LoadCharacteristic_MOTOR_CMP,LoadCharacteristic_WSCC,PlantController_PF1,PlantController_PF2,PlantController_PLAYINREF,PlantController_REPCA1,PlantController_REPCTA1,PlantController_REPC_A,PlantController_REPC_B,PlantController_REPC_B100,PlantController_REPC_C,PlantController_VAR1,PlantController_VAR2,RelayModel_ATRRELAY,RelayModel_FRQDCAT,RelayModel_FRQTPAT,RelayModel_GENOF,RelayModel_GP1,RelayModel_GP2,RelayModel_GP3,RelayModel_GVPHZFT,RelayModel_GVPHZIT,RelayModel_LHFRT,RelayModel_LHSRT,RelayModel_LHVRT,RelayModel_VPERHZ1,RelayModel_VTGDCAT,RelayModel_VTGTPAT,UserDefinedExciter,UserDefinedGovernor]
    """Slow. All Dynamic Model Data"""

class GridWorkBench:
    def __init__(self, fname=None, set=GridSet.Light):
        # PW Interface
        self.io = PowerWorldIO(fname)

        # Applications
        self.dyn = Dynamics(self.io)
        self.statics = Statics(self.io)

        # Read Data into Case
        if fname is not None:
            self.io.open()
            self.all = self.io.download(set)

    T = TypeVar("T", bound=GObject)

    def __getitem__(self, arg: Type[T]) -> DataFrame:
        return self.all[arg]

    def __call__(self, gclass: Type[T]) -> list[T]:
        return [
            gclass.__load__(**self.cfilt(kw)) for kw in self[gclass].to_dict("records")
        ]

    # Colon Filters for Fields
    def cfilt(self, kw: dict):
        for key in kw.copy().keys():
            if ":" in key:
                kw[key.replace(":", "__")] = kw.pop(key)
        return kw

    # Add An Object to Local Database
    def add(self, *gobjs: GObject):
        for gobj in gobjs:
            gset = self.all[gobj.__class__]
            gset.loc[len(gset)] = dict(zip(gobj.fields, astuple(gobj)))

    def joint(self, type1: GObject, type2):
        return self[type1].merge(self[type2], on="BusNum")

    # Send to Remote Model (PW)
    def commit(self, gclass=None):
        self.io.upload(self.all)

    # Save Remote Model (PW)
    def save(self):
        self.io.save()

    # Dangerous! Commit and Save.
    def sudos(self):
        self.commit()
        self.save()

    # Return All of Type
    @property
    def ieeeg1(self):
        return self.objlist(Governor_IEEEG1)

    @property
    def ggov1(self):
        return self.objlist(Governor_GGOV1)

    @property
    def repca(self):
        return self.objlist(PlantController_REPC_A)

    @property
    def zones(self):
        return self.objlist(Zone)

    @property
    def regions(self):
        return self.objlist(SuperArea)

    @property
    def areas(self):
        return self.objlist(Area)

    @property
    def subs(self):
        return self.objlist(Substation)

    @property
    def buses(self):
        return self.objlist(Bus)

    @property
    def loads(self):
        return self.objlist(Load)

    @property
    def gens(self):
        return self.objlist(Gen)

    @property
    def shunts(self):
        return self.objlist(Shunt)

    @property
    def ctgs(self):
        return self.objlist(Contingency)

    @property
    def tsctgs(self):
        return self.objlist(TSContingency)

    @property
    def lines(self):
        return self.objlist(Branch)

    @property
    def xfmrs(self):
        return self.objlist(Transformer)

    # Secondary Field Helpers
    @property
    def volts(self):
        vmags = self.buses["BusPUVolt"]
        angs = np.deg2rad(self.buses["BusAngle"])
        rectv = [cmath.rect(v, ang) for v, ang in zip(vmags, angs)]

        return np.array(rectv)

    @volts.setter
    def volts(self, vals):
        mags = [cmath.polar(v)[0] for v in vals]
        angs = np.rad2deg([cmath.polar(v)[1] for v in vals])

        self.buses["BusPUVolt"] = mags
        self.buses["BusAngle"] = angs

        self.io.update(Bus, self.buses[["BusNum", "BusPUVolt", "BusAngle"]])

    def pflow(self):
        self.io.pflow()

        # Update all static params after solve
        self.all = self.io.download()

    @property
    def ybus(self):
        return self.io.esa.get_ybus(True)

    def bus(self, busnum, subnum=1, kv=138, new=False) -> DataFrame:
        if new:
            toadd = DataFrame.from_dict(
                {
                    "BusNum": [busnum],
                    "SubNum": [subnum],
                    "BusNomVolt": [kv],
                }
            )
            toadd.gtype = Bus
            return toadd
        else:
            if not isinstance(num, Iterable):
                num = [num]
            isnum = self.buses["BusNum"].isin(num)
            return self.buses.loc[isnum]

    def xfmr(self, frombus, tobus, ckt=None, new=False):
        lines = self.line(frombus, tobus, ckt, new)
        if new:
            self.all[Transformer] = concat(
                [self.all[Transformer], lines], ignore_index=True
            )

            lines.gtype = Transformer
            self.io.update(lines)
        return lines

    def line(self, frombus, tobus, ckt=None, new=False) -> DataFrame | None:
        # New Line
        if new:
            existing = self.line(frombus, tobus, ckt)

            # If No CKT specified do +1 of existing
            if ckt is None:
                ckt = len(existing["LineCircuit"]) + 1
            # Ensure it doesn't already exist
            elif len(existing) > 0:
                return existing

            fields = {
                "BusNum": [frombus],
                "BusNum:1": [tobus],
                "LineCircuit": [str(ckt)],
                "LineR": [0.00484],
                "LineX": [0.123766],
                "LineC": [0],
                "LineG": [0],
                "LineStatus": ["Closed"],
                "LineAMVA": [100],
                "LineAMVA:1": [0],
                "LineAMVA:2": [0],
            }
            df = DataFrame.from_dict(fields)
            df.gtype = Branch
            self.all[Branch] = concat([self.all[Branch], df], ignore_index=True)
            self.all[Branch].gtype = Branch
            self.io.update(self.lines)
            return df

        # Find Line
        else:
            # Cast to list for multi-creation
            if not isinstance(frombus, Iterable):
                frombus = [frombus]
            if not isinstance(tobus, Iterable):
                tobus = [tobus]
            if ckt is not None:
                if not isinstance(ckt, Iterable):
                    ckt = [ckt]
                ckt = [str(c) for c in ckt]

            isfrom = self.lines["BusNum"].isin(frombus)
            isto = self.lines["BusNum:1"].isin(tobus)

            if ckt is not None:
                isckt = self.lines["LineCircuit"].isin(ckt)
                lines = self.lines[isfrom & isto & isckt]
            else:
                lines = self.lines[isfrom & isto]

            return lines

    """
    def addline(frombus, tobus):
        linedata = {
            "BusNum": frombus,
            "BusNum:1": tobus
            "LineCircuit": 0
            "LineStatus": 'Closed'
            "LineR": 0.00484
            "LineX",
            "LineC",
            "LineG",
            "LineAMVA",
            "LineMW",
            "LineMVR",
            "GICLineDistance",
        }
        pass
    """
