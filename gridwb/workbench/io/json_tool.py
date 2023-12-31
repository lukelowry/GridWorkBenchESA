# JSON Tool: Capability to read and write a GridWorkbench object to JSON
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 2/1/2022 ABB Initial version
#
import json
import math
from ..utils import *
from ..grid import *

def make_value_json(value):
    if type(value) == float:
        if math.isnan(value):
            return None
    elif type(value) not in [int, str, bool]:
        return None
    return value

def json_save_gen(gen):
    gen_obj = {}
    for property, value in vars(gen).items():
        if property == "_node":
            continue
        else:
            gen_obj[property] = make_value_json(value)
    return gen_obj

def json_save_load(load):
    load_obj = {}
    for property, value in vars(load).items():
        if property == "_node":
            continue
        else:
            load_obj[property] = make_value_json(value)
    return load_obj

def json_save_shunt(shunt):
    shunt_obj = {}
    for property, value in vars(shunt).items():
        if property == "_node":
            continue
        else:
            shunt_obj[property] = make_value_json(value)
    return shunt_obj

def json_save_node(node):
    node_obj = {}
    for property, value in vars(node).items():
        if property == "_bus":
            continue
        elif property == "_gen_map":
            node_obj["_gen_map"] = []
            for gen in value.values():
                node_obj["_gen_map"].append(json_save_gen(gen))
        elif property == "_load_map":
            node_obj["_load_map"] = []
            for load in value.values():
                node_obj["_load_map"].append(json_save_load(load))
        elif property == "_shunt_map":
            node_obj["_shunt_map"] = []
            for shunt in value.values():
                node_obj["_shunt_map"].append(json_save_shunt(shunt))
        elif property == "_branch_from_map":
            continue
        elif property == "_branch_to_map":
            continue
        else:
            node_obj[property] = make_value_json(value)
    return node_obj

def json_save_bus(bus):
    bus_obj = {}
    for property, value in vars(bus).items():
        if property == "_sub":
            continue
        elif property == "_node_map":
            bus_obj["_node_map"] = []
            for node in value.values():
                bus_obj["_node_map"].append(json_save_node(node))
        else:
            bus_obj[property] = make_value_json(value)
    return bus_obj

def json_save_sub(sub):
    sub_obj = {}
    for property, value in vars(sub).items():
        if property == "_area":
            continue
        elif property == "_bus_map":
            sub_obj["_bus_map"] = []
            for bus in value.values():
                sub_obj["_bus_map"].append(json_save_bus(bus))
        else:
            sub_obj[property] = make_value_json(value)
    return sub_obj

def json_save_area(area):
    area_obj = {}
    for property, value in vars(area).items():
        if property == "_region":
            continue
        elif property == "_sub_map":
            area_obj["_sub_map"] = []
            for sub in value.values():
                area_obj["_sub_map"].append(json_save_sub(sub))
        else:
            area_obj[property] = make_value_json(value)
    return area_obj

def json_save_region(region):
    region_obj = {}
    for property, value in vars(region).items():
        if property == "_wb":
            continue
        elif property == "_area_map":
            region_obj["_area_map"] = []
            for area in value.values():
                region_obj["_area_map"].append(json_save_area(area))
        else:
            region_obj[property] = make_value_json(value)
    return region_obj

def json_save_branch(branch):
    branch_obj = {}
    for property, value in vars(branch).items():
        if property == "_from_node":
            branch_obj[property] = value.number
        elif property == "_to_node":
            branch_obj[property] = value.number
        else:
            branch_obj[property] = make_value_json(value)
    return branch_obj

def json_save(self, fname):
    obj = {"workbench":{}}
    wb = obj["workbench"]
    wb["_region_map"] = []
    for region in self.regions:
        wb["_region_map"].append(json_save_region(region))
    wb["_branch_list"] = []
    for branch in self.branches:
        wb["_branch_list"].append(json_save_branch(branch))
    wb["dyn_models"] = []
    for mod in self.dyn_models:
        mod_obj = [mod.__class__.__name__, list(vars(mod).items())]
        wb["dyn_models"].append(mod_obj)
    with open(fname, "w") as f:
        f.write(json.dumps(obj))

def json_open_branch(wb, obj_branch):
    from_node = wb.node(obj_branch["_from_node"])
    to_node = wb.node(obj_branch["_to_node"])
    id = obj_branch["_id"]
    branch = Branch(from_node, to_node, id)
    for key, value in obj_branch.items():
        if key == "_id" or key == "_from_node" or key == "_to_node":
            continue
        else:
            setattr(branch, key, value)
    return branch

def json_open_shunt(node, obj_shunt):
    id = obj_shunt["_id"]
    shunt = Shunt(node, id)
    for key, value in obj_shunt.items():
        if key == "_id":
            continue
        else:
            setattr(shunt, key, value)
    return shunt

def json_open_load(node, obj_load):
    id = obj_load["_id"]
    load = Load(node, id)
    for key, value in obj_load.items():
        if key == "_id":
            continue
        else:
            setattr(load, key, value)
    return load

def json_open_gen(node, obj_gen):
    id = obj_gen["_id"]
    gen = Gen(node, id)
    for key, value in obj_gen.items():
        if key == "_id":
            continue
        else:
            setattr(gen, key, value)
    return gen

def json_open_node(bus, obj_node):
    number = obj_node["_number"]
    node = Node(bus, number)
    for key, value in obj_node.items():
        if key == "_number":
            continue
        elif key == "_gen_map":
            for obj_gen in value:
                json_open_gen(node, obj_gen)
        elif key == "_load_map":
            for obj_load in value:
                json_open_load(node, obj_load)
        elif key == "_shunt_map":
            for obj_shunt in value:
                json_open_shunt(node, obj_shunt)
        elif key == "_branch_map":
            continue
        else:
            setattr(node, key, value)
    return node

def json_open_bus(sub, obj_bus):
    number = obj_bus["_number"]
    bus = Bus(sub, number)
    for key, value in obj_bus.items():
        if key == "_number":
            continue
        elif key == "_node_map":
            for obj_node in value:
                json_open_node(bus, obj_node)
        else:
            setattr(bus, key, value)
    return sub

def json_open_sub(area, obj_sub):
    number = obj_sub["_number"]
    sub = Sub(area, number)
    for key, value in obj_sub.items():
        if key == "_number":
            continue
        elif key == "_bus_map":
            for obj_bus in value:
                json_open_bus(sub, obj_bus)
        else:
            setattr(sub, key, value)
    return sub

def json_open_area(region, obj_area):
    number = obj_area["_number"]
    area = Area(region, number)
    for key, value in obj_area.items():
        if key == "_number":
            continue
        elif key == "_sub_map":
            for obj_sub in value:
                json_open_sub(area, obj_sub)
        else:
            setattr(area, key, value)
    return area

def json_open_region(wb, obj_region):
    number = obj_region["_number"]
    region = Region(wb, number)
    for key, value in obj_region.items():
        if key == "_number":
            continue
        elif key == "_area_map":
            for obj_area in value:
                json_open_area(region, obj_area)
        else:
            setattr(region, key, value)
    return region

def json_open(self, fname):
    with open(fname, "r") as f:
        obj = json.loads(f.read())
    self.clear()
    for key, value in obj["workbench"].items():
        if key == "_region_map":
            for obj_region in value:
                json_open_region(self, obj_region)
        elif key == "_branch_list":
            for obj_branch in value:
                json_open_branch(self, obj_branch)
        elif key == "dyn_models":
            self.dyn_models = []
            for mod_obj in value:
                mod = globals()[mod_obj[0]]()
                for key, value in mod_obj[1]:
                    setattr(mod, key, value)
                self.dyn_models.append(mod)