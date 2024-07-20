

class GridObjDNE(Exception):
    '''Describes a data query failure'''
    pass

class FieldDataException(Exception):
    pass

class AuxParseException(Exception):
    pass

class ContainerDeletedException(Exception):
    pass

'''Observable Exceptions'''

class PowerFlowException(Exception):
    '''Raised When Power Flow Error Occurs'''
    pass

class BifurcationException(PowerFlowException):
    '''Raised when bifurcation is suscpected'''
    pass 

class DivergenceException(PowerFlowException): # TODO in use?
    pass 

class GeneratorLimitException(PowerFlowException):
    '''Raised when a generator has exceed a limit'''
    pass 

''' GIC Exceptions '''

class GICException(Exception):
    pass 

