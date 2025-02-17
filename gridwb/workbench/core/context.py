
from numpy import unique
from .powerworld import PowerWorldIO

class Context:
    '''A Context Object that is passed between applications or instances that carry the live data of GWB'''

    def __init__(self, fname: str) -> None:
        '''Context of a workbench session. Holds IO Connection and Common Data Maintainer'''
        
        self.io = PowerWorldIO(fname) 
        self.io.open()

    def getIO(self) -> PowerWorldIO:
        '''Return IO Instance'''
        return self.io
    
