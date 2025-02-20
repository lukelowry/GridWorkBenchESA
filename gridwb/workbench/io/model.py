from abc import ABC, abstractmethod

class IModelIO(ABC):
    '''Standard Interface for Model Interaction'''

    def __init__(self, fname: str = None):
        self.fname = fname

    """
    Open Connection to Remote Model
    """

    @abstractmethod
    def open(self):
        pass

