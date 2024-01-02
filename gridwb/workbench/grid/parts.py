from enum import Enum, auto
from typing import Self


class GridType(Enum):
    
    Region  = auto()
    Area    = auto()
    Sub     = auto()
    Bus     = auto()

    Gen     = auto()
    Load    = auto()
    Shunt   = auto()

    Line    = auto()
    XFMR    = auto()

    Contingency = auto()
    ContingencyAction = auto()

    TSContingency = auto()
    TSContingencyAction = auto()

class GridObject:

    def __init__(self, gridtype: GridType) -> None:
        self._type = gridtype
        self._keys = {}
        self._associatedObjs: list[Self] = []

    def __str__(self) -> str:
        return f'{self._type.name}: ({self._keys_to_str()})'
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def _keys_to_str(self):
        return ', '.join(f"{k}: {v}" for k, v in self._keys.items())
    
    def fields(self):
        return [a for a in dir(self) if a[0]!='_']

    @property
    def regions(self) -> list[Self]: 
        return [o for o in self._associatedObjs if o._type is GridType.Region]

    @property
    def areas(self) -> list[Self]:
        return [o for o in self._associatedObjs if o._type is GridType.Area]
    
    @property
    def buses(self) -> list[Self]:
        return [o for o in self._associatedObjs if o._type is GridType.Bus]

    @property
    def subs(self) -> list[Self]:
        return [o for o in self._associatedObjs if o._type is GridType.Sub]

    @property
    def xfmrs(self) -> list[Self]: 
        return [o for o in self._associatedObjs if o._type is GridType.XFMR]

    @property
    def lines(self) -> list[Self]:
        return [o for o in self._associatedObjs if o._type is GridType.Line]

    @property
    def loads(self) -> list[Self]: 
        return [o for o in self._associatedObjs if o._type is GridType.Load]

    @property
    def gens(self) -> list[Self]: 
        return [o for o in self._associatedObjs if o._type is GridType.Gen]

    @property
    def shunts(self) -> list[Self]: 
        return [o for o in self._associatedObjs if o._type is GridType.Shunt]