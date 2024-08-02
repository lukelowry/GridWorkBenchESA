
from typing import Any, Self, Type, TypeVar
from pandas import DataFrame

from ..grid.components import GObject

T = TypeVar("T", bound=GObject)

# TODO Either Remove or Improve, this is a liability. I trust pandas more.
class GridList(list[T]):
    '''Instance-Based representation of data if desired'''

    def __call__(self, **locs: Any) -> Self | T:
        """Search The List by Attributes
        Return a List if Many Found
        Return Object if One Found"""
        results = GridList[T]()
        for obj in self:
            for key in locs:
                if hasattr(obj, key) and locs[key] == getattr(obj, key):
                    continue
                else:
                    break
            else:
                results.append(obj)

        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0]
        else:
            return results

class GridDataMaintainer:
    ''' All Model-Retrieved data should be traced back to this object '''

    # TODO I want to implement a clear difference between LOCAL retrieval and EXTERNAL retrieval

    def __init__(self, all: dict[Type[GObject], DataFrame]) -> None:
        
        # Main Storage Dictionary
        self.all = all


    def get_df(self, component: Type[T]) -> DataFrame:
        '''Dataframe Accessor by type'''
        if component in self.all:
            return self.all[component]
        else:
            self.all[component] = DataFrame(columns=component.fields)
            return self.all[component]
   
   # NOTE maybe not work - I did not test this
    def __getitem__(self, index) -> DataFrame | None:
        '''Retrieve LOCAL Data with Indexor Notation

        Examples:
        wb.dm[Bus] # Get Primary Keys of PW Buses
        wb.dm[Bus, 'BusPUVolt'] # Get Voltage Magnitudes
        wb.dm[Bus, ['SubNum', 'BusPUVolt']] # Get Two Fields
        wb.dm[Bus, :] # Get all fields
        '''

        # Type checking is an anti-pattern but this is accepted within community as a necessary part of the magic function
        # >1 Argument - Objecet Type & Fields(s)
        if isinstance(index, tuple): 
            gtype, fields = index
            if isinstance(fields, str): fields = fields,
            elif isinstance(fields, slice): fields = gtype.fields
        # 1 Argument - Object Type: retrieve only key fields
        else: 
            gtype, fields = index, ()

        # Keys and then Fields
        key_fields = gtype.keys
        data_fields = [f for f in fields if f not in key_fields]
        unique_fields = [*key_fields, *data_fields]

        # If no fields (I.e. there were no keys and no data field passed)
        if len(unique_fields) < 1:
            return None

        return self.all[gtype][unique_fields]

    
