import numpy as np

class gencls:

    def __init__(self, node_num=0, gen_id='1', H=1, Xdp=0.1):
        self.name = "gencls"
        self.states = ("delta", "omega")
        self.node_num = node_num
        self.gen_id = gen_id
        self.H = H
        self.Xdp = Xdp
        self.nx = 2
        self.ny = 5
        self.exciter = None
    
    def initialize(self, v, w, x, y):

        # Initial voltage and current given from power flow solution
        Vterm = v[0] + 1j*v[1]
        Iri = (w[4] + 1j*w[5])*100.0/self.sbase

        # Impedance and admittance
        Z = 1j*self.Xdp
        Y = 1/Z

        # Find delta and Ep from internal voltage
        Vri = Vterm + Iri*Z
        delta = np.angle(Vri)
        Ep = np.abs(Vri)

        # Get voltage and current on machine reference frame
        Vdq = 1j * Ep
        Idq = Iri * (np.sin(delta) + 1j*np.cos(delta))

        # Torque values come from internal voltage and current
        Te = (Vdq * np.conj(Idq)).real
        Tm = Te

        # Norton values based on 
        Inort = (Iri + Vterm * Y) * self.sbase / 100.0
        gr = gi = Y.real * self.sbase / 100.0
        br = bi = Y.imag * self.sbase / 100.0

        # Omega initializes to zero
        omega = 0
        
        # State variables
        x[0] = delta
        x[1] = omega

        # Interface variables
        w[0] = gr
        w[1] = gi
        w[2] = br
        w[3] = bi
        w[4] = Inort.real
        w[5] = Inort.imag

        # Algebraic variables
        y[0] = Idq.real
        y[1] = Idq.imag
        y[2] = Te
        y[3] = Ep
        y[4] = Tm

        
    def calc_interface(self, wread, xread, yread, wwrite, ywrite):
        
        # Interface variables
        gr = wread[0]
        gi = wread[1]
        br = wread[2]
        bi = wread[3]
        Inort = wread[4] + 1j*wread[5]

        # Get algebraic variables
        Idq = yread[0] + 1j*yread[1]
        Te = yread[2]
        Ep = yread[3]
        Tm = yread[4]

        # Get state variables
        delta = xread[0]
        omega = xread[1]

        # 
        Z = 1j*self.Xdp
        Vdq = 1j * Ep
        Inort_dq = Vdq / Z

        # Convert to network reference frame and sbase
        Inort = Inort_dq * (np.sin(delta) - 1j*np.cos(delta)) * self.sbase / 100.0

        # Set nterface variables
        wwrite[0] = gr
        wwrite[1] = gi
        wwrite[2] = br
        wwrite[3] = bi
        wwrite[4] = Inort.real
        wwrite[5] = Inort.imag

        # Other algebraic variables
        ywrite[0] = Idq.real
        ywrite[1] = Idq.imag
        ywrite[2] = Te
        ywrite[3] = Ep
        ywrite[4] = Tm

    def calc_derivative(self, vread, wread, xread, yread, xdot, ywrite):

        # Terminal voltages
        Vterm = vread[0] + 1j*vread[1]

        # Interface variables
        gr = wread[0]
        gi = wread[1]
        br = wread[2]
        bi = wread[3]
        Inort = wread[4] + 1j*wread[5]

        # Get algebraic variables
        Idq = yread[0] + 1j*yread[1]
        Te = yread[2]
        Ep = yread[3]
        Tm = yread[4]

        # Get state variables
        delta = xread[0]
        omega = xread[1]

        Z = 1j*self.Xdp
        Vdq = 1j * Ep
        Inort_dq = Vdq / Z
        Te = (Vterm*((Ep*np.exp(1j*delta)-Vterm)/Z).conjugate()).real

        delta_dot = omega
        omega_dot = 1/(2.0*self.H) * (Tm - Te)

        xdot[0] = delta_dot
        xdot[1] = omega_dot
        
        # Other algebraic variables
        ywrite[0] = Idq.real
        ywrite[1] = Idq.imag
        ywrite[2] = Te
        ywrite[3] = Ep
        ywrite[4] = Tm