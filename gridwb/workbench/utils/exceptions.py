# Exceptions: Used for various WB functions
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 8/18/22 Initial version
#
class GridObjDNE(Exception):
    pass

class FieldDataException(Exception):
    pass

class AuxParseException(Exception):
    pass

class ContainerDeletedException(Exception):
    pass

'''Observable Exceptions'''

class PowerFlowException(Exception):
    pass

class BifurcationException(PowerFlowException):
    pass 

class DivergenceException(PowerFlowException):
    pass 

class GeneratorLimitException(PowerFlowException):
    pass 

''' GIC Exceptions '''

class GICException(Exception):
    pass 

