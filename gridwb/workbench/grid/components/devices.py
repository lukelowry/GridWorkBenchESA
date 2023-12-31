from .structures import TieredObject




# Generic Device
class Device(TieredObject):
    text = "Device"

# Generator Object
class Gen(Device):
    text = "Gen"

    MW = "GenMW"
    Voltage = ""

    
    
# Load Object
class Load(Device):
    text = "Load"

# Shunt Object
class Shunt(Device):
    text = "Shunt"