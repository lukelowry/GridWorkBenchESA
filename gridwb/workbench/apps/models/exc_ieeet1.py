import numpy as np

class exc_ieeet1:

    def __init__(self, node_num=0, gen_id='1', Tr=0, Ka=50, Ta=.04, Vrmax=1, Vrmin=-1, Ke=-.06,
            Te=0.6, Kf=.09, Tf=1.46, Switch=0, E1=2.8, SE1=0.04, E2=3.73, SE2=.33, Spdmlt=0):
        self.name = "exc_ieeet1"
        self.states = ("vts", "vr", "efdp", "vfx")
        self.node_num = node_num
        self.gen_id = gen_id
        self.Tr         =      Tr      
        self.Ka         =      Ka      
        self.Ta         =      Ta      
        self.Vrmax      =      Vrmax   
        self.Vrmin      =      Vrmin   
        self.Ke         =      Ke      
        self.Te         =      Te      
        self.Kf         =      Kf      
        self.Tf         =      Tf      
        self.Switch     =      Switch  
        self.E1         =      E1      
        self.SE1        =      SE1     
        self.E2         =      E2      
        self.SE2        =      SE2     
        self.Spdmlt     =      Spdmlt  
        self.nx = 4
        self.ny = 4
    
    def initialize(self, v, w, x, y):

        pass
        
    def calc_interface(self, wread, xread, yread, wwrite, ywrite):
        
        pass

    def calc_derivative(self, vread, wread, xread, yread, xdot, ywrite):

        pass