from dataclasses import dataclass
from typing import Any, Callable, Type, TypeVar
from ...utils.exceptions import FieldDataException

# Generic Element within the Grid
class GridObject:

    # This field shall equal the PW text of a given object
    text = "Object"

    # Class var passed by IO, depends on application
    iomap = None

    def __init__(self, **kwargs: dict[str, Any]):
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def __str__(self):
        if hasattr(self, 'id'):
            return f"{self.text} ID: {self.id}"
        if hasattr(self, 'name'):
            return f"{self.text} Name: {self.name}"
        return f'{self.text}'

    def __repr__(self):
        return str(self)
    

    # ID (Unique to Obj Type, Exception: Device)
    @property
    def id(self) -> int | str:
        return self._id
    
    @id.setter
    def id(self, value: int | str):
        try:
            value = int(value) # We try int first because PW somtimes passes ID as str
        except ValueError:
            try: 
                value = str(value)
            except:
                raise FieldDataException("Invalid Object ID")
        self._id = value
    
class TieredObject(GridObject):

    # ID of Predecessor in Hierarchy
    container_id: int | str = None

    # Tier Precedence assigned by Hierarchy
    tier: int = None
    
    # Name (Not for device)
    name: str = None

# NOT IN USE: here for compiling reference errors, might use in future
class Node():
    pass