import numpy as np

class gov_tgov1:

    def __init__(self, node_num=0, gen_id='1', R=.05, T1=0.5, Vmax=1, Vmin=0, T2=2.5, T3=7.5, Dt=0,
            Trate=0):
        self.name = "gov_tgov1"
        self.states = ("pv", "ptx")
        self.node_num = node_num
        self.gen_id = gen_id
        self.R         =      R      
        self.T1         =      T1      
        self.Vmax         =      Vmax      
        self.Vmin      =      Vmin   
        self.T2      =      T2   
        self.T3         =      T3      
        self.Dt         =      Dt      
        self.Trate         =      Trate 
        self.nx = 2
        self.ny = 2
    
    def initialize(self, v, w, x, y):

        pass
        
    def calc_interface(self, wread, xread, yread, wwrite, ywrite):
        
        pass

    def calc_derivative(self, vread, wread, xread, yread, xdot, ywrite):

        pass