

from .structures import GridObject

from numpy import unique
from typing import Any, Generic, TypeVar



# Generic CTG Action
class AbstractCTGAction(GridObject):
     ctgname   : str
     action    : str
     actionDesc: str
     objectDesc: str

     # Will be assigned when loaded in a case
     object    : GridObject = None

     def __str__(self):
          return f"{self.action} -> {self.object}"
     
# Generic CTG
CA= TypeVar('CA', bound=AbstractCTGAction)  
class AbstractCTG(GridObject, Generic[CA]):

     name: str = ""
     skip: bool

     def __init__(self, **kwargs: dict[str, Any]):
          super().__init__(**kwargs)
          self.actions: list[CA] = []
          
     def add(self, action: CA):
          self.actions.append(action)

     @property
     def objects(self):
          return list({a.object for a in self.actions})

# Transient Contingencies
class TSContingencyAction(AbstractCTGAction):
     text = "TSContingencyElement"
     time: float

     def __str__(self):
          return f"T={self.time} " + super().__str__()

class TSContingency(AbstractCTG[TSContingencyAction]):
     text = "TSContingency"

# Static Contingencies
class ContingencyAction(AbstractCTGAction):
     text = "ContingencyElement"

class Contingency(AbstractCTG[ContingencyAction]):
     text = "Contingency"
