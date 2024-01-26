from abc import ABC, abstractmethod

from pandas import DataFrame


# Standard Interface for model interaction
class IModelIO(ABC):
    # Data Structure Template
    Template = DataFrame(columns=["ObjectID", "ObjectType", "Field", "IsKey", "Value"])

    def __init__(self, fname: str = None):
        self.fname = fname

    """
    Open Connection to Remote Model
    """

    @abstractmethod
    def open(self):
        pass

    """
    Download Grid Data
    Return as DataFrame

    --------------- Data ----------------------

    [ObjectType  ][Field ][isKey?][Value]

    [GridType.Bus][BusNum][True  ][45   ]
    [GridType.Bus][MW    ][False ][27   ]
    [GridType.Sub][SubNum][True  ][1    ]

    """

    @abstractmethod
    def download(self) -> DataFrame:
        pass

    """
    Pass DF
    Modify Remote Grid Model

    --------------- Data ----------------------

    [ObjectType  ][Field ][isKey?][Value]

    [GridType.Bus][BusNum][True  ][45   ]
    [GridType.Bus][MW    ][False ][27   ]
    [GridType.Sub][SubNum][True  ][1    ]
    """

    @abstractmethod
    def upload(self, df) -> bool:
        pass
