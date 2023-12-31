# Contingencies: classes to hold contingency set definition data
#
# Adam Birchfield, Texas A&M University
# 
# Log:
# 4/28/2022 ABB Initial version, stub for now
#
#from ..containers import Bus
#from ..devices import Branch, Gen, Load
r'''
class ContingencyAction:

    def __init__(self):
        self.command = "NONE"
        self.object = "NONE"
        self.value = 0.0

    def __str__(self) -> str:
        return f"({self.command} {self.object} {self.value})"

class Contingency:

    def __init__(self):
        self.label = ""
        self.actions = []
        self.violations = []
    
    def __str__(self) -> str:
        return f"CTG:{self.label}[" + ", ".join([str(a) for a in self.actions]) + "]"

class ContingencyViolation:

    def __init__(self):
        self.contingency = None
        self.type = "NONE"
        self.obj = None
        self.value = 0.0

    def __str__(self) -> str:
        return f"VIO: {self.type} {self.obj} {self.value} : {self.contingency}"

class ContingencySet:

    def __init__(self):
        self.contingencies = []
        self.base_vios = []
'''