
from ..utils.decorators import timing
from ..grid.builders import GridType
from ..io.model import IModelIO
from ...saw import SAW

from os import path
from pandas import DataFrame, concat, to_numeric

# PW Fields to Retrieve
fieldMap: dict[GridType, list[str]] = {
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
        "BranchNum"       ,
        "BusNetMW"        ,
        "BusNetMVR"       , 
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
        "CustomInteger"   ,    
        "PartOfCkt"       
    ],
    # TODO Find way to Standardize
    GridType.TSContingency: [
        "TSCTGName",        
        "TSTimeInSeconds",         
        "TimeStep",          
        "Category",           
        "CTGSkip",       
        "CTGViol",         
        "TSTotalLoadMWTripped",      
        "TSTotalLoadMWIslanded"         
    ],
    GridType.TSContingencyAction: [
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

# Power World Read/Write
class PowerWorldIO(IModelIO):

    # Map GWB Types to PW Obj Type
    otypemap: dict[GridType, str] = {
        GridType.Region : 'superarea',
        GridType.Area   : 'area',
        GridType.Sub    :'substation',
        GridType.Bus    :'bus',
        GridType.Gen    :'gen',
        GridType.Load   :'load',
        GridType.Shunt  :'shunt',
        GridType.Line   :'branch',
        GridType.XFMR   :'xfmr',
        GridType.Contingency         : 'contingency',
        GridType.ContingencyAction   : 'contingencyelement',
        GridType.TSContingency       : 'tscontingency',
        GridType.TSContingencyAction : 'tscontingencyelement',
    }

    @timing
    def open(self):
        
        # Validate Path Name
        if not path.isabs(self.fname):
            self.fname = path.abspath(self.fname)

        # ESA Object & Transient Sim
        self.esa = SAW(self.fname, CreateIfNotFound=True, early_bind=True)

    @timing
    def download(self):

        # Create Empty DF
        data = super().Template.copy()

        # For Each GridObject
        for otype in fieldMap:

            # TODO might not need field list aabove with this
            keys = self.esa.get_key_field_list(self.otypemap[otype])

            # Get & Format Data for Objs of Specific Type
            df = self.esa.GetParametersMultipleElement(
                self.otypemap[otype],
                fieldMap[otype]
            ).stack(dropna=False).reset_index().rename(columns={
                'level_0' : 'ObjectID',
                'level_1' : 'Field',
                0         : 'Value'
            })

            # Added/Modify Fields
            if len(data) > 0:
                df['ObjectID'] += data['ObjectID'].max() + 1
            df['ObjectType'] = otype
            df['IsKey'] = df['Field'].isin(keys)

            # Merge With Previous Request
            data = concat([data,df], ignore_index=True)

        # PW Sucks
        data = data.apply(to_numeric, errors = 'ignore')

        return data

    @timing
    def upload(self, df) -> bool:

        #TODO not useful atm

        self.esa.change_and_confirm_params_multiple_element(
            ObjectType = 'TSContingency',
            command_df = DataFrame({'TSCTGName': ['SimOnly']})
        )
        
        return True
    
    @timing
    def update(self, otype: GridType, df: DataFrame | dict) -> bool:

        stat = self.esa.change_and_confirm_params_multiple_element(
            ObjectType = self.otypemap[otype],
            command_df = DataFrame(df)
        )
        
        return stat
    
    
    # Will Save all Open Changes
    def save(self):

        return self.esa.SaveCase()

    def skipallbut(self, ctgs):


        df = self.esa.GetParametersMultipleElement(
            'tscontingency',
            ['TSCTGName'],
        )
        
        # Assign
        names = [ctg.TSCTGName for ctg in ctgs]
        df['CTGSkip'] = 'YES'
        df.loc[df['TSCTGName'].isin(names), 'CTGSkip'] = 'NO'

        self.esa.change_and_confirm_params_multiple_element(
            ObjectType = 'TSContingency',
            command_df = df
        )

def pw_bool(val):
        v = str(val).lower()
        a = v == "connected"
        b = v == "closed"
        c = v == "yes"
        return a or b or c

r'''
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