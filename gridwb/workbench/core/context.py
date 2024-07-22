
from numpy import unique
from .powerworld import PowerWorldIO
from .sets import GridSet
from .datamaintainer import GridDataMaintainer

class Context:
    '''A Context Object that is passed between applications or instances that carry the live data of GWB'''

    def __init__(self, fname: str, set: GridSet) -> None:
        '''Context of a workbench session. Holds IO Connection and Common Data Maintainer'''
        
        self.io = PowerWorldIO(fname) 
        self.io.open()

        # Create Data Maintainer Instance
        self.dm = self.io.download(set)

    def getIO(self) -> PowerWorldIO:
        '''Return IO Instance'''
        return self.io
    
    def getDataMaintainer(self) -> GridDataMaintainer:
        '''Return Data Maintainer'''
        return self.dm
