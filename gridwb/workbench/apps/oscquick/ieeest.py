
from abc import ABC, abstractmethod, abstractproperty
from cmath import polar, rect
from numpy import array, arccos, pi, sqrt

from gridwb.workbench.apps.oscquick.genrou import OscModelQ

from ...grid.components import Gen, Stabilizer_IEEEST


class OscModelIEEESTQ(OscModelQ):

    # 2 Algebraic Vars 6 Differential Vars
    shape = (8,8)

    # Differential Diagonals Range from 2-6
    diag_diff_indicies = list(range(2,8))

    def __init__(self, stab: Stabilizer_IEEEST, gen:Gen, vterm:complex) -> None:

        '''Creates 3 matricies for Genrou Model:
        - Algebraic Vertical
        - Algebraic Horizontal
        - Differential Diagonal
        '''

        # Store
        self.stab = stab
        self.gen = gen
        self.busnum = gen.BusNum

        # Gains
        Ks = stab.TSKs

        # Notch Filter
        A1 = stab.TSA__1
        A2 = stab.TSA__2
        A3 = stab.TSA__3
        A4 = stab.TSA__4
        A5 = stab.TSA__5
        A6 = stab.TSA__6

        # Time Constant
        T1 = stab.TST__1
        T2 = stab.TST__2
        T3 = stab.TST__3
        T4 = stab.TST__4
        T5 = stab.TST__5
        T6 = stab.TST__6

        # Computed Values TODO validate scenario where AX = 0 might be wrong
        R1n = 0 if A2==0 else (A1-sqrt(A1**2-4*A2))/(2*A2) 
        R1p = 0 if A2==0 else (A1+sqrt(A1**2-4*A2))/(2*A2)
        R3n = 0 if A4==0 else (A3-sqrt(A3**2-4*A4))/(2*A4)
        R3p = 0 if A4==0 else (A3+sqrt(A3**2-4*A4))/(2*A4)
        R5n = 0 if A6==0 else (A5-sqrt(A5**2-4*A6))/(2*A6)
        R5p = 0 if A6==0 else (A5+sqrt(A5**2-4*A6))/(2*A6)

        if A2==0 and A4!=0 and A6!=0: 

            # Model Matrix
            mat = array([
                [T5*Ks , -1  , 0   , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0], # A w
                [0     , 1   , -1  , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0], # Asx
                [0     , 0   , 1   , -1 , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0], # A1
                [0     , 0   , 0   , 1  , -1  , 0  , 0  , 0  , 0  , 0  , 0  , 0], # A2
                [0     , 0   , 0   , 0  , R5n , -1 , 0  , 0  , 0  , 0  , 0  , 0], # a3
                [0     , 0   , 0   , 0  , 0   , R5p, 0  , 0  , 0  , 0  , 0  , -1],# a4
                [0     , 0   , 0   , 0  , 0   , 0  , 1  , 0  , 0  , 0  , 0  , -1],# a5
                [0     , 0   , 0   , 0  , 0   , 0  , -1 , 1  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , -1 , 1  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , -1 , R3n, 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , 0  , -1 , R3p, 0],
            ])

        elif A2!=0 and A4==0 and A6!=0: 

            # Model Matrix
            mat = array([
                [T5*Ks , -1  , 0   , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0],
                [0     , 1   , -1  , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0],      
                [0     , 0   , 1   , -1 , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0],    
                [0     , 0   , 0   , 1  , -1  , 0  , 0  , 0  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , R5n , -1 , 0  , 0  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , R5p, 0  , 0  , 0  , 0  , 0  , -1],   
                [0     , 0   , 0   , 0  , 0   , 0  , 1  , 0  , 0  , 0  , 0  , -1],   
                [0     , 0   , 0   , 0  , 0   , 0  , -1 , 1  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , -1 , 1  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , -1 , R1n, 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , 0  , -1 , R1p, 0], 
            ])

        else:

            # Model Matrix
            mat = array([
                [T5*Ks , -1  , 0   , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0],
                [0     , 1   , -1  , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0],      
                [0     , 0   , 1   , -1 , 0   , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0],    
                [0     , 0   , 0   , 1  , -1  , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , R5n , -1 , 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , R5p, 0  , 0  , 0  , 0  , 0  , 0  , 0  , -1],   
                [0     , 0   , 0   , 0  , 0   , 0  , 1  , 0  , 0  , 0  , 0  , 0  , 0  , -1],   
                [0     , 0   , 0   , 0  , 0   , 0  , -1 , 1  , 0  , 0  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , -1 , 1  , 0  , 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , -1 , R1n, 0  , 0  , 0  , 0],   
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , 0  , -1 , R1p, 0  , 0  , 0], 
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , 0  , 0  , -1 , R3n, 0  , 0], 
                [0     , 0   , 0   , 0  , 0   , 0  , 0  , 0  , 0  , 0  , 0  , -1 , R3p, 0], 
            ])

        # Coefficients of State Variables, Divide so we can do (A - sI) in computation
        #mat[2] /= 1
        #mat[3] /= -2*H # The only negative
        #mat[4] /= Tppd
        #mat[5] /= Tppq
        #mat[6] /= Tpq
        #mat[7] /= Tpd

        # Differential - Take Real Part, constructed with Complex to avoid sin/cos
        self.internal = mat.real
    
    def kcl_mat(self):

        return self.inj
    
    def kvl_mat(self):

        return self.volts
    
    def internal_mat(self):

        return self.internal
    
    def pA(self):

        # Notch Filter
        A1 = self.stab.TSA__1
        A2 = self.stab.TSA__2
        A3 = self.stab.TSA__3
        A4 = self.stab.TSA__4
        A5 = self.stab.TSA__5
        A6 = self.stab.TSA__6

        print(A1)
        print(A2)
        print(A3)
        print(A4)
        print(A5)
        print(A6)
