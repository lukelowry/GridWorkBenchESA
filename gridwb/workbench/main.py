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
import shlex

import numpy as np
from .grid.builders import GridType, ObjectFactory
from .plugins.powerworld import PowerWorldIO
from .apps import Dynamics, Statics


class GridWorkBench:
    def __init__(self, fname=None):
        # PW Interface
        self.io = PowerWorldIO(fname)

        # Applications
        self.dyn = Dynamics(self.io)
        self.statics = Statics(self.io)

        # Read Data into Case
        if fname is not None:
            self.io.open()
            self.objs = self.io.down()
            # self.objs = ObjectFactory.makeFrom(self.io)

    def pflow(self):
        self.io.pflow()

        # Update all static params after solve
        self.objs = self.io.down()

    # Return All of Type
    @property
    def ieeeg1(self):
        return self.objs[GridType.IEEEG1]

    @property
    def ggov1(self):
        return self.objs[GridType.GGOV1]

    @property
    def reeca1(self):
        return self.objs[GridType.REECA1]

    @property
    def ieeest(self):
        return self.objs[GridType.IEEEST]

    @property
    def wt4t(self):
        return self.objs[GridType.WT4T]

    @property
    def regions(self):
        return self.objs[GridType.Region]

    @property
    def areas(self):
        return self.objs[GridType.Area]

    @property
    def subs(self):
        return self.objs[GridType.Sub]

    @property
    def buses(self):
        return self.objs[GridType.Bus]

    @property
    def loads(self):
        return self.objs[GridType.Load]

    @property
    def gens(self):
        return self.objs[GridType.Gen]

    @property
    def shunts(self):
        return self.objs[GridType.Shunt]

    @property
    def ctgs(self):
        return self.objs[GridType.Contingency]

    @property
    def tsctgs(self):
        return self.objs[GridType.TSContingency]

    @property
    def lines(self):
        return self.objs[GridType.Line]

    def find(self, otype: GridType, *keyvals):
        for o in self.objs:
            if o._type is otype and tuple(o._keys.values()) == keyvals:
                return o

    # Return Type Given Specifier
    def region(self, name: str):
        return self.find(GridType.Region, name)

    def area(self, num: int):
        return self.find(GridType.Area, num)

    def sub(self, num: int):
        return self.find(GridType.Sub, num)

    def bus(self, num: int):
        return self.find(GridType.Bus, num)

    def gen(self, id, bus):
        return self.find(GridType.Gen, id, bus)

    def load(self, id, bus):
        return self.find(GridType.Load, id, bus)

    def shunt(self, id, bus):
        return self.find(GridType.Shunt, id, bus)

    # This could potentially miss a connection
    def branch(self, from_bus: GridType.Bus, to_bus: GridType.Bus):
        for branch in self.branches:
            if branch.from_bus is from_bus and branch.to_bus is to_bus:
                return branch

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

        self.io.update(GridType.Bus, self.buses[["BusNum", "BusPUVolt", "BusAngle"]])

    @property
    def ybus(self):
        return self.io.esa.get_ybus(True)

    # Get Grid Obj from contingency string
    def findCTGObject(self, findObjText: str):
        # Try and Cast to int for key fields
        keys = []
        for part in shlex.split(findObjText):
            try:
                keys += [int(part)]
            except:
                keys += [part]

        # Try and find Type
        try:
            oType = self.textToType[keys[0].capitalize()]
        except:
            print(f"WARNING: CTG Obj not supported {findObjText}")
            return None

        # Find from id or branch
        try:
            if len(keys) == 2:
                id = keys[1]
                return self.H.get(oType, id)

            if len(keys) == 4:
                from_bus = self.H.get(GridType.Bus, keys[1])
                to_bus = self.H.get(GridType.Bus, keys[2])
                return self.branch(from_bus, to_bus)
        except:
            print(f"Warning: CTG Unassigned {findObjText}")

        return None
