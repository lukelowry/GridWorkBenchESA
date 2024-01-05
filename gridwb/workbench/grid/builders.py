

from ..io.model import IModelIO
from .parts import GridObject, GridType
from pandas import DataFrame

# Builds Objects
class ObjectBuilder:

    # Initialize Production List
    def __init__(self) -> None:

        self._objlist: list[GridObject] = []

        # Track Key fields for obj type
        self._key_library = {gt: set() for gt in GridType}

    # Begin Building a new object
    def new(self, otype: GridType) -> None:

        self._obj = GridObject(otype)
        self._objlist.append(self._obj)
        
    # Set Attibute for Object
    def attr(self, name: str, value, iskey=False) -> None:

        # TODO idk why but pandas wont convert to numeric so doing it here
        try: value = float(value)
        except: pass
        
        setattr(self._obj, name, value)

        # Indicate Attr as Key
        if iskey:
            self._obj._keys.update({name: value})

    # Return list of compelted objects
    def collect(self) -> list[GridObject]:
        return self._objlist
    
    def tie(self):

        # For Each Object
        for obj in self._objlist:

            # Find objects that reference 'obj'
            for candidate in self._objlist:

                if candidate is obj:
                    continue

                # Check by keys
                for key, value in obj._keys.items():

                    # Skip if No Match
                    if not hasattr(candidate, key) or not getattr(candidate, key)==value:
                        break

                # Match Direct Association  
                else:
                    obj._associatedObjs.append(candidate)
                    candidate._associatedObjs.append(obj)
    
# Class to Generate Objects for Grid
class ObjectFactory:

    @staticmethod
    def makeFrom(io: IModelIO) -> list[GridObject]:
        
        # Data nd Builder
        raw = io.download()
        builder = ObjectBuilder()
        
        # For Each Object
        for id in raw['ObjectID'].unique():

            # Extract Data and Type
            objData: DataFrame = raw[raw['ObjectID']==id]
            objType: GridType  = objData['ObjectType'].iloc[0]

            # Start Object Synthesis
            builder.new(objType)

            # Set Attributes
            for idx in objData.index:
                fieldInfo = objData.loc[idx]
                name      = fieldInfo['Field']
                value     = fieldInfo['Value']
                isKey     = fieldInfo['IsKey']
                builder.attr(name, value, isKey)

        # Match objects (e.g. Identify Sub Data)
        builder.tie()

        # Return all built objects
        return builder.collect()





    