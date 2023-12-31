

import shlex
from networkx import *

from ..utils.exceptions import GridObjDNE

from .components import *
from .relations import GridNetwork, Hierarchy

from ...saw import SAW

FT = TypeVar('FT')
def all_subclasses(cls: Type[FT]) -> list[Type[FT]]:
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

# Case to hold interconnections between Grid Objects
class Case:

    def __init__(self, io) -> None:

        self.io = io

        # Heirarchy (Region, Area, Sub Ownership)
        self.H = Hierarchy()

        # Grid (How branches connect)
        self.G = GridNetwork()
        self.G.setHierarchy(self.H)

        # List of Contingencies
        self.ctgs   : list[Contingency]   = []
        self.tsctgs : list[TSContingency] = []

        # List of Branches
        self.branches : list[Branch] = []

        # Generate Text->Object Type Map Automatically (e.g. 'Bus' to Bus Type)
        self.textToType = {o.text: o for o in all_subclasses(GridObject)}

    @property
    def esa(self) -> SAW:
        # We define Application ESA this way so that it always references up-to-date case ESA
        return self.io.esa

    # Get Transient CTG by name
    def tsctg(self, name) -> TSContingency:
        for ctg in self.tsctgs:
            if ctg.name == name:
                return ctg
        raise GridObjDNE
    
    # Get Static CTG by name
    def ctg(self, name) -> Contingency: 
        for ctg in self.ctgs:
            if ctg.name == name:
                return ctg
        raise GridObjDNE
    
    # This could potentially miss a connection
    def branch(self, from_bus: Bus, to_bus: Bus):
        for branch in self.branches:
            if branch.from_bus is from_bus and branch.to_bus is to_bus:
                return branch
        raise GridObjDNE
    
    # Get Grid Obj from contingency string
    def findCTGObject(self, findObjText: str):

        #Try and Cast to int for key fields
        keys = []
        for part in shlex.split(findObjText):
            try: keys += [int(part)]
            except: keys += [part]

        # Try and find Type
        try:
            oType = self.textToType[keys[0].capitalize()]
        except:
            print(f"WARNING: CTG Obj not supported {findObjText}")
            return None
        
        # Find from id or branch
        try:
            if len(keys) == 2:
                id    = keys[1]
                return self.H.get(oType, id)
            
            if len(keys) == 4:
                from_bus = self.H.get(Bus, keys[1])
                to_bus   = self.H.get(Bus, keys[2])
                return self.branch(from_bus, to_bus)
        except:
            print(f"Warning: CTG Unassigned {findObjText}")

        return None

    # Handles adding all types of Grid Objects
    def add(self, obj: GridObject):

        # Add to Hierarchy
        if isinstance(obj, TieredObject):
            self.H.add(obj)

        # Add to Connections
        elif isinstance(obj, Branch):

            obj.from_bus = self.H.get(Bus, obj.from_bus_num)
            obj.to_bus = self.H.get(Bus, obj.to_bus_num)

            # Add to Graph and case Branch List
            self.G.addBranch(obj)
            self.branches.append(obj)
                
        # Continengencies
        elif isinstance(obj, Contingency):
            self.ctgs.append(obj)

        elif isinstance(obj, TSContingency):
            self.tsctgs.append(obj)

        
        # Contingency Actions
        elif isinstance(obj, ContingencyAction):
            obj.object = self.findCTGObject(obj.objectDesc)
            self.ctg(obj.ctgname).add(obj)
        
        elif isinstance(obj, TSContingencyAction):
            obj.object = self.findCTGObject(obj.objectDesc)
            self.tsctg(obj.ctgname).add(obj)
        

        
    # Draw Grid Network (G)
    def drawG(self, ax):

        # Plotting Attributes
        ax.axis('off')

        self.G.draw(ax)

    # Draw Heirarchical Network (H)
    def drawH(self, ax, color_key=Sub):

        # Plotting Attributes
        ax.axis('off')

        # Draw on ax
        self.H.draw(ax)

    #compose() would draw G with H
    #Useful? confusing?