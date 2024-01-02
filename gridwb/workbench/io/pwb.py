# PWB Analysis: The functions for sending PowerWorld data to and from the 
# GridWorkbench using Easy SimAuto
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 9/29/2021 Initial version, rearranged from prior draft so that most object fields
#   are only listed in one place, the PW_Fields table. Now to add a field you just
#   need to add it in that list.
# 11/2/2021 Renamed this file to core and added fuel type object
# 1/22/22 Split out all device types
# 1/25/22 Split out this PWB file
# 8/10/2022 We need createifnotfound to be true
# 8/18/2022 Make sure all objects are allowed not to exist
#

from abc import ABC, abstractmethod
import os
import pandas as pd
from typing import Any

from gridwb.workbench.grid.builders import GridType, ObjectFactory
from ...saw import SAW

from ..utils.decorators import timing
from ..grid             import *

# Abstract Interface For Reading/Writing Grid Data
class IO(ABC):
    
    @abstractmethod
    def open(self, fname):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def read(self, case):
        pass

    @abstractmethod
    def write(self, case):
        pass

class PWIO2(IO):

    def __init__(self) -> None:
        self.esa    : SAW = None

    # Establish Connection to PW  TODO json & aux support
    @timing
    def open(self, fname):

        # Validate Path Name
        if not os.path.isabs(fname):
            fname = os.path.abspath(fname)

        # ESA Object & Transient Sim
        self.esa = SAW(fname, CreateIfNotFound=True, early_bind=True)

    def close(self):
        self.esa.CloseCase()

    def read(self):
        return self.esa.GetFieldList('bus')

    def write(self, case):
        pass

class PowerWorldIO(IO):

    def __init__(self) -> None:
        self.esa    : SAW = None

    def pw_bool(val):
        v = str(val).lower()
        a = v == "connected"
        b = v == "closed"
        c = v == "yes"
        return a or b or c

    # Attibute Name: (PWName, DataType, KeyField)
    iomap: dict[GridObject, Any] = {
        GridType.Region: {
            "name" : ("SAName",  str, False)
        },
        GridType.Area: {
            "id"           : ("AreaNum"         , int, False),
            "container_id" : ("SAName"          , str, False),
            "name"         : ("AreaName"        , str, False),
        },
        GridType.Sub: {
            "id"           : ("SubNum"          , int, False),            
            "container_id" : ("AreaNum"         , int, False),            
            "name"         : ("SubName"         , str, False),            
            "latitude"     : ("Latitude"        , float, False),          
            "longitude"    : ("Longitude"       , float, False),          
        },
        GridType.Bus: {
            "id"           : ("BusNum"          , int, True),            
            "container_id" : ("SubNum"          , int, False),            
            "name"         : ("BusName"         , str, False),            
            "nominal_kv"   : ("BusNomVolt"      , float, False),          
            "vpu"          : ("BusPUVolt"       , float, False),          
            "vang"         : ("BusAngle"        , float, False),          
            "status"       : ("BusStatus"       , pw_bool, False),        
            "zone_number"  : ("ZoneNum"         , int, False),            
        },
        GridType.Gen: {
            "id"           : ("GenID"           , int, False),            
            "container_id" : ("BusNum"          , str, False),            
            "status"       : ("GenStatus"       , pw_bool, False),        
            "p"            : ("GenMW"           , float, False),          
            "q"            : ("GenMVR"          , float, False),          
            "pset"         : ("GenMWSetPoint"   , float, False),          
            "qset"         : ("GenMvrSetPoint"  , float, False),          
            "pmax"         : ("GenMWMax"        , str, False),            
            "pmin"         : ("GenMWMin"        , str, False),            
            "qmax"         : ("GenMVRMax"       , str, False),            
            "qmin"         : ("GenMVRMin"       , str, False),            
            "reg_bus_num"  : ("GenRegNum"       , str, False),            
            "reg_pu_v"     : ("GenVoltSet"      , str, False),            
            "p_auto_status": ("GenAGCAble"      , pw_bool, False),        
            "q_auto_status": ("GenAVRAble"      , pw_bool, False),        
            "ramp_rate"    : ("GenMWRampLimit"  , str, False),            
            "crank_p"      : ("CustomFloat"     , str, False),            
            "crank_t"      : ("CustomFloat:1"   , str, False),            
            "availability" : ("CustomFloat:2"   , str, False),            
            "fuel_type"    : ("GenFuelType"     , str, False),            
            "fuel_cost"    : ("GenFuelCost"     , str, False),            
            "sbase"        : ("GenMVABase"      , float, False),          
        },
        GridType.Load: {
            "id"           : ("LoadID"      ,  int, False),              
            "container_id" : ("BusNum"      ,  int, False),              
            "status"       : ("LoadStatus"  ,  pw_bool, False),          
            "p"            : ("LoadMW"      ,  float, False),            
            "q"            : ("LoadMVR"     ,  float, False),            
            "ps"           : ("LoadSMW"     ,  float, False),            
            "qs"           : ("LoadSMVR"    ,  float, False),            
            "benefit"      : ("GenBidMWHR"  ,  float, False),            
        },
        GridType.Shunt: {
            "id"           : ("ShuntID"         ,  str, False),            
            "container_id" : ("BusNum"          ,  str, False),           
            "status"       : ("SSStatus"        ,  pw_bool, False),        
            "qnom"         : ("SSNMVR"          ,  float, False),          
            "q"            : ("SSAMVR"          ,  float, False),          
            "availability" : ("CustomInteger"   ,  str, False),            
        },
        GridType.Line: {
            "id"           : ("LineCircuit"     ,  int, False),              
            "from_bus_num" : ("BusNum"          ,  int, False),              
            "to_bus_num"   : ("BusNum:1"        ,  int, False),              
            "status"       : ("LineStatus"      ,  pw_bool, False),          
            "R"            : ("LineR"           ,  float, False),            
            "X"            : ("LineX"           ,  float, False),            
            "B"            : ("LineC"           ,  float, False),            
            "G"            : ("LineG"           ,  float, False),            
            "MVA_Limit_A"  : ("LineAMVA"        ,  float, False),            
            "MVA_Limit_B"  : ("LineAMVA:1"      ,  float, False),            
            "MVA_Limit_C"  : ("LineAMVA:2"      ,  float, False),            
            "p1"           : ("LineMW"          ,  float, False),            
            "q1"           : ("LineMVR"         ,  float, False),            
            "p2"           : ("LineMW:1"        ,  float, False),            
            "q2"           : ("LineMVR:1"       ,  float, False),            
            "length"       : ("GICLineDistance" ,  float, False),            
            "availability" : ("CustomInteger"   ,  float, False),            
        },
        # TODO Make Transient
        GridType.Contingency: {
            "name"         : ("TSCTGName"               ,  str, False),            
            "duration"     : ("TSTimeInSeconds"         ,  float, False),          
            "timestep"     : ("TimeStep"                ,  float, False),          
            "category"     : ("Category"                ,  str, False),            
            "skip"         : ("CTGSkip"                 ,  pw_bool, False),        
            "viol"         : ("CTGViol"                 ,  str, False),            
            "mw_tripped"   : ("TSTotalLoadMWTripped"    ,  float, False),          
            "mw_islanded"  : ("TSTotalLoadMWIslanded"   ,  float, False),          
        },
        # TODO Make Transient
        GridType.ContingencyAction: {
            "ctgname"     : ("TSCTGName"        ,  str, True),            
            "action"      : ("TSEventString"    ,  str, False),            
            "objectDesc"  : ("WhoAmI"           ,  str, False),            
            "time"        : ("TSTimeInSeconds"  ,  float, False),          
        },
        GridType.Contingency: {
            "name"         : ("CTGLabel" , str, True),            
            "skip"         : ("CTGSkip"  , pw_bool, False),            
            "violations"   : ("CTGViol"  , int, False),            
        },
        GridType.ContingencyAction: {
            "ctgname"   : ("CTGLabel" , str, True),            
            "action"    : ("Action"   , str, False),            
            "objectDesc": ("Object"   , str, False),            
            "actionDesc": ("WhoAmI"   , str, False),            
        }
        
    }

    # Attibute Name: (PWName, DataType, KeyField)
    fieldMap: dict[GridObject, Any] = {
        GridType.Region: [
            "SAName"
        ],
        GridType.Area: [
            "AreaNum"         , 
            "SAName"          , 
            "AreaName"        , 
        ],
        GridType.Sub: [
            "SubNum"          ,             
            "AreaNum"         ,             
            "SubName"         ,             
            "Latitude"        ,         
            "Longitude"       ,         
        ],
        GridType.Bus: [
            "BusNum"          ,          
            "SubNum"          ,             
            "BusName"         ,             
            "BusNomVolt"      ,         
            "BusPUVolt"       ,         
            "BusAngle"        ,         
            "BusStatus"       ,      
            "ZoneNum"         ,             
        ],
        GridType.Gen: [
            "GenID"           ,             
            "BusNum"          ,             
            "GenStatus"       ,         
            "GenMW"           ,         
            "GenMVR"          ,         
            "GenMWSetPoint"   ,         
            "GenMvrSetPoint"  ,         
            "GenMWMax"        ,             
            "GenMWMin"        ,             
            "GenMVRMax"       ,             
            "GenMVRMin"       ,             
            "GenRegNum"       ,             
            "GenVoltSet"      ,             
            "GenAGCAble"      ,       
            "GenAVRAble"      ,        
            "GenMWRampLimit"  ,             
            "CustomFloat"     ,             
            "CustomFloat:1"   ,             
            "CustomFloat:2"   ,             
            "GenFuelType"     ,             
            "GenFuelCost"     ,             
            "GenMVABase"      ,         
        ],
        GridType.Load: [
            "LoadID"      ,                
            "BusNum"      ,                
            "LoadStatus"  ,           
            "LoadMW"      ,            
            "LoadMVR"     ,            
            "LoadSMW"     ,            
            "LoadSMVR"    ,            
            "GenBidMWHR"  ,            
        ],
        GridType.Shunt: [
            "ShuntID"         ,              
            "BusNum"          ,             
            "SSStatus"        ,         
            "SSNMVR"          ,          
            "SSAMVR"          ,          
            "CustomInteger"   ,              
        ],
        GridType.Line: [
            "LineCircuit"     ,                
            "BusNum"          ,                
            "BusNum:1"        ,                
            "LineStatus"      ,          
            "LineR"           ,            
            "LineX"           ,            
            "LineC"           ,            
            "LineG"           ,            
            "LineAMVA"        ,            
            "LineAMVA:1"      ,            
            "LineAMVA:2"      ,            
            "LineMW"          ,            
            "LineMVR"         ,            
            "LineMW:1"        ,            
            "LineMVR:1"       ,             
            "GICLineDistance" ,          
            "CustomInteger",           
        ],
        # TODO Make Transient
        GridType.Contingency: [
            "TSCTGName",        
            "TSTimeInSeconds",         
            "TimeStep",          
            "Category",           
            "CTGSkip",       
            "CTGViol",         
            "TSTotalLoadMWTripped",      
            "TSTotalLoadMWIslanded"         
        ],
        # TODO Make Transient
        GridType.ContingencyAction: [
            "TSCTGName"        ,          
            "TSEventString"    ,           
            "WhoAmI"           ,           
            "TSTimeInSeconds"  ,         
        ],
        GridType.Contingency: [
            "CTGLabel",           
            "CTGSkip",           
            "CTGViol"         
        ],
        GridType.ContingencyAction: [
            "CTGLabel" ,           
            "Action"   ,           
            "Object"   ,            
            "WhoAmI"          
        ]
        
    }

    otypemap = {
        GridType.Region : 'superarea',
        GridType.Area   : 'area',
        GridType.Sub    : 'substation',
        GridType.Bus    : 'bus',
        GridType.Gen    : 'gen',
        GridType.Load   : 'load',
        GridType.Shunt  : 'shunt',
        GridType.Line   : 'branch',
        GridType.XFMR   : 'xfmr',
        GridType.Contingency       : 'contingency',
        GridType.ContingencyAction : 'contingencyelement',
    }

    # Establish Connection to PW  TODO json & aux support
    @timing
    def open(self, fname):

        # Validate Path Name
        if not os.path.isabs(fname):
            fname = os.path.abspath(fname)

        # ESA Object & Transient Sim
        self.esa = SAW(fname, CreateIfNotFound=True, early_bind=True)

    def close(self):
        self.esa.CloseCase()

    @timing
    def read(self, case:Case):
       
        allobjs: list[GridObject] = []

        # For each object type (e.g. Region, Sub, Load, etc.)
        for otype, fields in self.iomap.items():

            df = self.esa.GetParametersMultipleElement(
                self.otypemap[otype],
                self.fieldMap[otype]
            )

            # Rename fields here

            allobjs += ObjectFactory.make(otype, df)

            #df.columns = list(fields)
            
            # Add Each Instance to Case
            #for record in df.to_dict('records'):
                #r = {f: fields[f][1](v) for f, v in record.items()} # Type Cast
                #o = ObjectFactory.make(otype.text, **r)
                #objs.append(o)
                #case.add(otype(**r))
        
        return allobjs

    def write(self, case:Case):
        pass

def pwb_write_all(self, s=None):
    if s is None:
        s = self.esa
    self.pwb_write_data(s, regions=self.regions, areas=self.areas, subs=self.subs,
        buses=self.buses, loads=self.loads, gens=self.gens, shunts=self.shunts,
        branches=self.branches)

def pwb_write_data(self, s=None, regions=None, areas=None, subs=None, buses=None, 
    loads=None, gens=None, shunts=None, branches=None):
    if s is None:
        s = self.esa
    
    if regions is not None:
        regions = tuple(regions)
        sa_data = {
            f[1]:[getattr(region, f[0]) for region in regions]
            for f in self.sa_pw_fields
        }
        sa_data["SAName"] = [region.name for region in regions]
        sa_df = pd.DataFrame.from_dict(sa_data)
        s.change_parameters_multiple_element_df("superarea", sa_df)
    
    if areas is not None:
        areas = tuple(areas)
        area_data = {
            f[1]:[getattr(area, f[0]) for area in areas]
            for f in self.area_pw_fields
        }
        area_data["AreaNum"] = [area.number for area in areas]
        area_df = pd.DataFrame.from_dict(area_data)
        s.change_parameters_multiple_element_df("area", area_df)
            
    if subs is not None:
        subs = tuple(subs)
        sub_data = {
            f[1]:[getattr(sub, f[0]) for sub in subs]
            for f in self.sub_pw_fields
        }
        sub_data["SubNum"] = [sub.number for sub in subs]
        sub_df = pd.DataFrame.from_dict(sub_data)
        s.change_parameters_multiple_element_df("substation", sub_df)
            
    if buses is not None:
        buses = tuple(buses)
        bus_data = {
            f[1]:[getattr(bus, f[0]) for bus in buses]
            for f in self.bus_pw_fields
        }
        bus_data["BusNum"] = [bus.number for bus in buses]
        bus_df = pd.DataFrame.from_dict(bus_data)
        s.change_parameters_multiple_element_df("bus", bus_df)

    if gens is not None:
        gens = tuple(gens)
        gen_data = {
            f[1]:[getattr(gen, f[0]) for gen in gens]
            for f in self.gen_pw_fields
        }
        gen_data["BusNum"] = [gen.bus.number for gen in gens]
        gen_data["GenID"] = [gen.id for gen in gens]
        gen_df = pd.DataFrame.from_dict(gen_data)
        s.change_parameters_multiple_element_df("gen", gen_df)

    if loads is not None:
        loads = tuple(loads)
        load_data = {
            f[1]:[getattr(load, f[0]) for load in loads]
            for f in self.load_pw_fields
        }
        load_data["BusNum"] = [load.bus.number for load in loads]
        load_data["LoadID"] = [load.id for load in loads]
        load_df = pd.DataFrame.from_dict(load_data)
        s.change_parameters_multiple_element_df("load", load_df)

    if branches is not None:
        branches = tuple(branches)
        branch_data = {
            f[1]:[getattr(branch, f[0]) for branch in branches]
            for f in self.branch_pw_fields
        }
        branch_data["BusNum"] = [branch.from_bus.number for branch in branches]
        branch_data["BusNum:1"] = [branch.to_bus.number for branch in branches]
        branch_data["LineCircuit"] = [branch.id for branch in branches]
        branch_df = pd.DataFrame.from_dict(branch_data)
        s.change_parameters_multiple_element_df("branch", branch_df)

    if shunts is not None:
        shunts = tuple(shunts)
        shunt_data = {
            f[1]:[getattr(shunt, f[0]) for shunt in shunts]
            for f in self.shunt_pw_fields
        }
        shunt_data["BusNum"] = [shunt.bus.number for shunt in shunts]
        shunt_data["ShuntID"] = [shunt.id for shunt in shunts]
        shunt_df = pd.DataFrame.from_dict(shunt_data)
        s.change_parameters_multiple_element_df("shunt", shunt_df)

    # TODO: Export contingencies
        
# TODO Merge With Above
def setup_dyn_fields():
    models = []
    fields = {}
    models = [("gencls", "MachineModel_GENCLS"),("genrou", "MachineModel_GENROU"),
        ("exc_ieeet1", "Exciter_IEEET1"), ("gov_tgov1", "Governor_TGOV1")]
    fields["gencls"] = [ ("node_num", "BusNum"), ("gen_id", "GenID"), ("status", "TSDeviceStatus"),
        ("H", "TSH"), ("D", "TSD"), ("Ra", "TSRa"), ("Xdp", "TSXd:1"),
        ("Rcomp", "TSRcomp"), ("Xcomp", "TSXcomp")]
    fields["genrou"] = [ ("node_num", "BusNum"), ("gen_id", "GenID"), ("status", "TSDeviceStatus"),
        ("H", "TSH"), ("D", "TSD"), ("Ra", "TSRa"), ("Xd", "TSXd"), ("Xq", "TSXq"), 
        ("Xdp", "TSXd:1"), ("Xqp", "TSXq:1"), ("Xdpp", "TSXd:2"), ("Xl", "TSXl"), 
        ("Tdop", "TSTdo"), ("Tqop", "TSTqo"), ("Tdopp", "TSTdo:1"), ("Tqopp", "TSTqo:1"), 
        ("S1", "TSS1"), ("S12", "TSS1:1"), ("Rcomp", "TSRcomp"), ("Xcomp", "TSXcomp")]
    fields["exc_ieeet1"] = [("node_num", "BusNum"), ("gen_id", "GenID"), 
        ("status", "TSDeviceStatus"), ("Tr", "TSTr"), ("Ka", "TSKa"), ("Ta", "TSTa"),
        ("Vrmax", "TSVrMax"), ("Vrmin", "TSVrMin"), ("Ke", "TSKe"), ("Te", "TSTe"), ("Kf", "TSKf"),
        ("Tf", "TSTf"), ("Switch", "TSwitch"), ("E1", "TSE"), ("SE1", "TSSE"), ("E2", "TSE:1"),
        ("SE2", "TSSE:1"), ("Spdmlt", "TSSpdmlt")]
    fields["gov_tgov1"] = [("node_num", "BusNum"), ("gen_id", "GenID"), 
        ("status", "TSDeviceStatus"),("R", "TSR"), ("T1", "TST:1"), ("Vmax", "TSVmax"), 
        ("Vmin", "TSVmin"), ("T2", "TST:2"), ("T3", "TST:3"), ("Dt", "TSDt"), ("Trate", "TSTrate")]
    return models, fields

# TODO Merge With Above
def pwb_read_dyn(self, s=None):
    if s is None:
        s = self.esa

    self.dyn_models = []

    models, fields = setup_dyn_fields()
    
    for mod, mpw in models:
        print(f"Reading {mod}")
        df = s.GetParametersMultipleElement(mpw,
            [f[1] for f in fields[mod]])
        if df is not None:
            df = df.to_dict("records")
            for i in range(len(df)):
                model_info = df[i]
                model_class = globals()[mod]
                model_obj = model_class()
                for field_wb, field_pw in fields[mod]:
                    setattr(model_obj, field_wb, model_info[field_pw])
                self.dyn_models.append(model_obj)
    
r'''
self.make_default_pw_instructions()
if isinstance(fname, str) and len(fname) >= 4 and \
        fname[-4:].lower() == '.pwb':
    self.open_pwb(fname)
    self.pwb_read_all(hush=True)
elif isinstance(fname, str) and len(fname) >= 4 and \
        fname[-4:].lower() == '.aux':
    self.import_aux(fname, hush=True)
elif isinstance(fname, str) and len(fname) >= 5 and \
        fname[-5:].lower() == '.json':
    self.json_open(fname)
elif fname is not None:
    raise NameError(f'Do not understand {fname} to open')
'''