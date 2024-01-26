from dataclasses import fields as dcfields
from typing import Type
from pandas import DataFrame
from gridwb.workbench.grid.components import *

from gridwb.workbench.utils.metric import Metric
from ..utils.decorators import timing
from ..io.model import IModelIO
from ...saw import SAW

from os import path


# Power World Read/Write
class PowerWorldIO(IModelIO):
    esa: SAW

    @timing
    def open(self):
        # Validate Path Name
        if not path.isabs(self.fname):
            self.fname = path.abspath(self.fname)

        # ESA Object & Transient Sim
        self.esa = SAW(self.fname, CreateIfNotFound=True, early_bind=True)

    @timing
    def download(self, set: list[Type[GObject]]) -> dict[Type[GObject], DataFrame]:
        return {gclass: self.getall(gclass) for gclass in set}

    def upload(self, model: dict[Type[GObject], DataFrame]) -> bool:
        self.esa.RunScriptCommand("EnterMode(EDIT);")
        for gclass, gset in model.items():
            # Only Pass Params That are Editable
            df = gset[gset.columns.intersection(gclass.editable)].copy()
            try:
                self.esa.change_parameters_multiple_element_df(gclass.TYPE, df)
            except:
                print(f"Failed to Write Data for {gclass.TYPE}")

    # Save all Open Changes to PWB File
    def save(self):
        return self.esa.SaveCase()

    def getall(self, gtype: Type[GObject]):

        fexcept = lambda t: "3" + t[5:] if t[:5]=="Three" else t

        fields = [fexcept(f) for f in gtype.fields]

        df = self.esa.GetParametersMultipleElement(gtype.TYPE, fields)

        if df is None:
            df = DataFrame(columns=fields)

        df.dropna(axis=1, how="all", inplace=True)
        
        return df

    def pflow(self):
        self.esa.SolvePowerFlow()

    def skipallbut(self, ctgs):
        ctgset = self.get(TSContingency)

        # Set Skip if not in ctg list
        ctgset["CTGSkip"] = "YES"
        ctgset.loc[ctgset["TSCTGName"].isin(ctgs), "CTGSkip"] = "NO"

        self.update(ctgset)

    def TSSolveAll(self):
        self.esa.RunScriptCommand("TSSolveAll()")

    def clearram(self):
        # Disable RAM storage & Delete Existing Data in RAM
        self.esa.RunScriptCommand("TSResultStorageSetAll(ALL, NO)")
        self.esa.RunScriptCommand("TSClearResultsFromRAM(ALL,YES,YES,YES,YES,YES)")

    def saveinram(self, metric: Metric):
        o = self.get(metric["Type"])
        o[metric["RAM"]] = "YES"

        # Enable RAM Storage in PW
        self.esa.change_and_confirm_params_multiple_element(
            ObjectType=metric["Type"],
            command_df=o,
        )


def pw_bool(val):
    v = str(val).lower()
    a = v == "connected"
    b = v == "closed"
    c = v == "yes"
    return a or b or c


r"""
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
"""
