import numpy as np

class genrou:

    def __init__(self, node_num=0, gen_id='1', H=3, D=0, Ra=0, Xd=2.1, X1=0.5, Xdp=0.2, Xqp=0.5, 
            Xdpp=0.18, Xl=0.15, Tdop=7, Tqop=0.75, Tdopp=0.04, Tqopp=0.05, S1=0, S12=0, Rcomp=0, 
            Xcomp=0):
        self.name = "genrou"
        self.states = ("delta", "omega", "Eqp", "phidp", "phiqp", "Edp")
        self.node_num = node_num
        self.gen_id = gen_id
        self.H      =        H
        self.D      =        D
        self.Ra     =        Ra
        self.Xd     =        Xd
        self.X1     =        X1
        self.Xdp    =        Xdp
        self.Xqp    =        Xqp
        self.Xdpp   =        Xdpp
        self.Xl     =        Xl
        self.Tdop   =        Tdop
        self.Tqop   =        Tqop
        self.Tdopp  =        Tdopp
        self.Tqopp  =        Tqopp
        self.S1     =        S1
        self.S12    =        S12
        self.Rcomp  =        Rcomp
        self.Xcomp  =        Xcomp
        self.nx = 6
        self.ny = 8
        self.exciter = None
        self.governor = None
    
    def initialize(self, v, w, x, y):

        pass
        
    def calc_interface(self, wread, xread, yread, wwrite, ywrite):
        
        pass

    def calc_derivative(self, vread, wread, xread, yread, xdot, ywrite):

        pass