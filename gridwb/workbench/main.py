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

# POSSIBLE MODULE NAMES:
# - gridwb
# - powerpy
# - pygrid


# Imports
from .grid import *
from .apps.dyn import *
from .apps.static import *
from .utils.conditions import *
from .io.pwb import PowerWorldIO

class GridWorkBench:

    def __init__(self, fname=None):

        # PW Interface
        self.io = PowerWorldIO()

        # Main Model
        self.case = Case(self.io)

        # Applications
        self.dyn  = Dynamics(self.case)
        self.statics = Statics(self.case)

        # Read Data into Case
        if fname is not None:
            self.io.open(fname)
            self.io.read(self.case)
        
    @property
    def esa(self):
        return self.io.esa
        
    # Return Type Given Specifier
    def region(self, name: str)         : return self.case.H.get(Region, name)
    def area(self, idOrName: int | str) : return self.case.H.get(Area, idOrName)
    def sub(self, idOrName: int | str)  : return self.case.H.get(Sub, idOrName)
    def bus(self, idOrName: int | str)  : return self.case.H.get(Bus, idOrName)
    def gen(self, idOrName: int | str)  : return self.case.H.get(Gen, idOrName)
    def shunt(self, idOrName: int | str): return self.case.H.get(Shunt, idOrName)
    def ctg(self, name)     : return self.case.ctg(name)
    def tsctg(self, name)   : return self.case.tsctg(name)

    # Return All of Type
    def regions(self)   : return list(self.case.H.getAll(Region))
    def areas(self)     : return list(self.case.H.getAll(Area))
    def subs(self)      : return list(self.case.H.getAll(Sub))
    def buses(self)     : return list(self.case.H.getAll(Bus))
    def loads(self)     : return list(self.case.H.getAll(Load))
    def gens(self)      : return list(self.case.H.getAll(Gen))
    def shunts(self)    : return list(self.case.H.getAll(Shunt))
    def ctgs(self)      : return self.case.ctgs
    def tsctgs(self)    : return self.case.tsctgs