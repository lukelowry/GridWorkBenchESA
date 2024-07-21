
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
        
    ''' Instance-Based Accessors'''
    # TODO REMOVE I DON"T WANT TO USE INSTANCES ANYMORE - PANDAS FOR LIFE
    def get_inst(self, component: Type[T]) -> GridList[T]:
        '''Instance Factor if this representation is preferred. Not efficient for large datasets.'''
        return GridList[T](
            [
                component.__load__(**self.cfilt(kw))
                for kw in self[component].to_dict("records")
            ]
        )

    # Colon Filters for Fields
    def cfilt(self, kw: dict):
        for key in kw.copy().keys():
            if ":" in key:
                kw[key.replace(":", "__")] = kw.pop(key)
        return kw
    
   
    """
    def add(self, *gobjs: GObject):
        '''Add a new object to the grid. Must instantiate correctly.'''
        for gobj in gobjs:
            gset = self[gobj.__class__]
            gset.loc[len(gset)] = dict(zip(gobj.fields, astuple(gobj)))
    """


    
