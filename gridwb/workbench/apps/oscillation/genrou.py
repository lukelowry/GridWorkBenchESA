
from abc import ABC, abstractmethod, abstractproperty
from cmath import polar, rect
from numpy import array, arccos, pi

from ...grid.components import Gen, MachineModel_GENROE

class OscModel(ABC):

    @abstractmethod
    def kcl_mat(self):
        pass
    
    @abstractmethod
    def kvl_mat(self):
        pass
    
    @abstractmethod
    def internal_mat(self):
        pass

    @abstractproperty
    def shape(self):
        pass

    @abstractproperty
    def diag_diff_indicies(self):
        pass

class OscModelGenrou(OscModel):

    # 2 Algebraic Vars 6 Differential Vars
    shape = (8,8)

    # Differential Diagonals Range from 2-6
    diag_diff_indicies = list(range(2,8))

    def __init__(self, gr: MachineModel_GENROE, gen:Gen, vterm:complex) -> None:

        '''Creates 3 matricies for Genrou Model:
        - Algebraic Vertical
        - Algebraic Horizontal
        - Differential Diagonal
        '''

        # Store
        self.gr = gr
        self.gen = gen
        self.busnum = gen.BusNum
        
        # Values that are Transient-Dependent
        delta  = rect(1,gen.TSGenDelta*pi/180) # unit complex
        deltaC = delta.conjugate()
        VT = vterm

        # IDQ calc
        pa = (polar(VT)[1] - arccos(gen.PowerFactor)) # phase angle v & i
        it = rect(gen.TSGenIPU, pa) # terminal current
        Idq = 1j*it*delta.conjugate() # dq current
        Id = Idq.real
        Iq = Idq.imag

        # Calculated - Psippd not given in data
        Psippq = gen.TSGenMachineState__5
        Psippd = self.psippd()
        Psipp = Psippd + 1j*Psippq

        # Static Values - 'State Independent'
        ws  = 2*pi*60 # TODO Get actual but should be 60 Hz
        D   = gr.TSD
        H   = gr.TSH
        Zs  = gr.TSRa + gr.TSXd__2 * 1j
        Tpd = gr.TSTdo
        Tpq = gr.TSTqo
        Tppd= gr.TSTdo__1
        Tppq= gr.TSTqo__1
        Xd  = gr.TSXd 
        Xq  = gr.TSXq
        Xpd = gr.TSXd__1
        Xpq = gr.TSXq__1
        Xppd= gr.TSXd__2 
        Xppq= gr.TSXd__2 # X''d = X''q Genrou
        Xl  = gr.TSXl
        
        # Calculated Values for Clarity
        X1 = (Xd-Xpd)*(Xpd-Xppd)/(Xpd-Xl)**2
        X2 = (Xd-Xpd)*(Xpd-Xppd)/(Xpd-Xl) - (Xd-Xpd)
        X3 = (Xq-Xpq)*(Xpq-Xppq)/(Xpq-Xl)**2
        X4 = (Xq-Xpq)*(Xpq-Xppq)/(Xpq-Xl) - (Xq-Xpq)

        X5 = (Xppd-Xl)/(Xpd-Xl)
        X6 = (Xpd-Xppd)/(Xpd-Xl)
        X7 = (Xpq-Xppq)/(Xpq-Xl)
        X8 = (Xppq-Xl)/(Xpq-Xl)

        # Model Matrix (Does not include delta shifting or injection equation)
        mat = array([
            [Zs                        , 1j*Zs          , VT*deltaC      , -1j*Psipp , 0                     , -X7                , -X8           , 0        ],
            [-1j*Zs                    , Zs             , -1j*VT*deltaC  , -Psipp    , -X6                   , 0                  , 0             , -X5      ],      
            [0                         , 0              , 0              , ws        , 0                     , 0                  , 0             , 0        ], 
            [-Psippq                   , Psippd         , 0              , D         , X6*Iq                 , X7*Id              , X8*Id         , X5*Iq    ],
            [-(Xpd-Xl)                 , 0              , 0              , 0         , -1                    , 0                  , 0             , 1        ],
            [0                         , (Xpq-Xl)       , 0              , 0         , 0                     , -1                 , 1             , 0        ],
            [0                         , -X4            , 0              , 0         , 0                     , X3                 , -1-X3         , 0        ],
            [X2                        , 0              , 0              , 0         , X1                    , 0                  , 0             , -1-X1    ],
        ])

        # Coefficients of State Variables, Divide so we can do (A - sI) in computation
        mat[2] /= 1
        mat[3] /= -2*H # The only negative
        mat[4] /= Tppd
        mat[5] /= Tppq
        mat[6] /= Tpq
        mat[7] /= Tpd

        # Differential - Take Real Part, constructed with Complex to avoid sin/cos
        self.internal = mat.real

        # Algebraic Matrix Upper - Take Real!
        self.inj     = array([[1j*delta , -delta   , -Idq*delta  , 0, 0, 0, 0, 0],
                        [delta    ,  1j*delta, 1j*Idq*delta, 0, 0, 0, 0, 0]]).real
        
        # Algebraic Matrix Left - Take Real!
        self.volts   = array([[1j*deltaC, deltaC   ,0, 0, 0, 0, 0 ,0],
                        [-deltaC  , 1j*deltaC,0, 0, 0, 0, 0 ,0]]).real
    
    def kcl_mat(self):

        return self.inj
    
    def kvl_mat(self):

        return self.volts
    
    def internal_mat(self):

        return self.internal

    def psippd(self):
        '''Calculate D-Axis Value of Psipp'''

        Xpd = self.gr.TSXd__1
        Xppd= self.gr.TSXd__2 
        Xl  = self.gr.TSXl
        X5 = (Xppd-Xl)/(Xpd-Xl)
        X6 = (Xpd-Xppd)/(Xpd-Xl)
        
        Psidp = self.gen.TSGenMachineState__4
        Eqp = self.gen.TSGenMachineState__3

        return Psidp*X6+Eqp*X5