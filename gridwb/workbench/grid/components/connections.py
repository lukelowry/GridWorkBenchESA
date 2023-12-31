
from ..components.containers import Bus
from .structures import GridObject


class ConnectionObject(GridObject):

    from_bus: Bus
    to_bus: Bus

    def __str__(self):
        return f"Bus {self.from_bus_num}-> Bus {self.to_bus_num}"

    @property
    def from_bus_num(self) -> int:
        return self._from_bus_num

    @from_bus_num.setter
    def from_bus_num(self, num: int | str):
        self._from_bus_num = int(num)

    @property
    def to_bus_num(self) -> int:
        return self._to_bus_num

    @to_bus_num.setter
    def to_bus_num(self, num: int | str):
        self._to_bus_num = int(num)

# Branch is a Single Line
class Branch(ConnectionObject):
    text = "Branch"