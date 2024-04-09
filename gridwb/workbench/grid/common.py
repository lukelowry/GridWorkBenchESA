from numpy import zeros, pi, diagflat, block, eye, all, reciprocal, array
from numpy.linalg import inv
from cmath import rect

from scipy.sparse import lil_matrix 

from .components import Gen, Load, Bus

def ybus_with_loads(Y, buses: list[Bus], loads: list[Load], gens=None):
    '''
    If a list of Generators are passed it will add
    the generation as negative impedence for gens without GENROU models
    '''

    # Copy so don't modify
    Y = Y.copy()

    # Map the bus number to its Y-Bus Index
    # TODO Do a sort by Bus Num to gaurentee order
    busPosY = {b.BusNum: i for i, b in enumerate(buses)}

    #Bus.LoadMW

    # For Per-Unit Conversion
    basemva = 100

    for bus in buses:

        # Location in YBus
        busidx = busPosY[bus.BusNum]

        # Net Load at Bus
        pumw = bus.BusLoadMW/basemva if bus.BusLoadMW > 0 else 0
        pumvar = bus.BusLoadMVR/basemva if bus.BusLoadMVR > 0 or bus.BusLoadMVR < 0 else 0
        puS = pumw + 1j*pumvar

        # V at Bus
        vmag = bus.BusPUVolt

        # Const Impedenace Load/Gen
        constAdmit = puS.conjugate()/vmag**2

        # Add to Ybus
        Y[busidx][busidx] += constAdmit # TODO determine if to use + or -!


    # Add Generators without models as negative load (if closed)
    if gens is not None:
        for gen in gens:

            gen: Gen
            if gen.TSGenMachineName == 'GENROU' and gen.GenStatus=='Closed':
                continue
            else:
                basemva = 100
                # Net Load at Bus
                pumw = gen.GenMW/basemva
                pumvar = gen.GenMVR/basemva
                puS = pumw + 1j*pumvar

                # V at Bus
                vmag =gen.BusPUVolt

                # Const Impedenace Load/Gen
                constAdmit = puS.conjugate()/vmag**2

                # Location in YBus
                busidx = busPosY[gen.BusNum]

                # Negative Admittance
                Y[busidx][busidx] -= constAdmit


    return Y

def double_cmplx_ybus(Y):
    
    # Create New Y-Bus
    l = len(Y)
    YC = zeros((2*l, 2*l), dtype=complex)

    YC[0:l, 0:l] = Y
    YC[l:2*l, 0:l] = -1j*Y
    YC[0:l, l:2*l] = 1j*Y
    YC[l:2*l, l:2*l] = Y

    return YC.real

def rlc_bus(buses, loads, gens):
    '''
    Returns a (R,L,C) Tuple with equivlent RLC load parameters
    '''

    # Indicies
    nbus = len(buses)
    busmap = {b.BusNum: i for i,b in enumerate(buses)}

    # Complex Voltages
    V = array([[rect(b.BusPUVolt, b.BusAngle*pi/180) for b in buses]]).T
    
    # Load R C L
    # (Vertex)

    Rload = zeros((nbus,1))
    Cload = zeros((nbus,1))
    Lload = zeros((nbus,1))

    # Bus R C L
    GenAndLoad = {l.BusNum: 0 for l in loads if l.NetMW!=0 or l.NetMvar!=0}
    basemva = 100

    # Get Load MVA
    for load in loads:
        bnum = load.BusNum
        mw = load.NetMW
        mvr = load.NetMvar
        s = (mw + 1j*mvr) / basemva
        GenAndLoad[bnum] += s # Add

    # Get Gen MVA
    for gen in gens:
        bnum = gen.BusNum
        mw = gen.GenMW
        mvr = gen.GenMVR
        s = (mw + 1j*mvr) / basemva

        if s != 0:
            if bnum not in GenAndLoad:
                GenAndLoad[bnum] = -s
            else:
                GenAndLoad[bnum] -= s # Sub
    
    # Calculate Net RLC
    for bus in GenAndLoad:
        s =  GenAndLoad[bus]/basemva

        id = busmap[bus]
        vmag = abs(V[id,0])

        Z = vmag**2/s.conjugate()
        X = Z.imag

        R = Z.real
        Rload[id] += R

        # Inductive Load [ L=X/w ]
        if X > 0:
            L = X/(2*pi*60)
            Lload[id] += L

        # Capacitive Load [ C = (1/(Xw)) ]
        elif X < 0:
            C = -1/(X*2*pi*60)
            Cload[id] += C
    
    return (Rload, Lload, Cload)

def rlc_line(lines, buses):  
    '''
    Returns LC parameters of lines as well 
    as Assigned Bus Shunt Capacitance and
    and Adjacency Matrix
     (Re, Le, Cbus, A)
    '''

    # Indicies
    nbus = len(buses)
    nlines = len(lines)
    busmap = {b.BusNum: i for i,b in enumerate(buses)}

    # Arc-Node Incidence Matrix (LxN)
    A = zeros((nlines, nbus))

    # Line R & L
    Re = zeros((nlines, 1))
    Le = zeros((nlines, 1))

    # Pi-Model Split C
    # (Vertex)
    Cbus = zeros((nbus,1))

    # Normal Incidence Matrix
    # Le, Re, (part of) Cd
    for i, line in enumerate(lines):

        # Line Values
        R = line.LineR__2
        X = line.LineX__2
        L = X/(2*pi*60)
        B = line.LineC

        # In Reality all lines have shunt suseptance
        # If '0' we approximate as really small value
        if B !=0:
            C = 1/B/(2*pi*60)
        else:
            C = 0.001 # Was 0.0001

        # Add to List of Values
        Re[i] = R
        Le[i] = L

        # Locate Index of To-From Buses
        fromI = busmap[line.BusNum]
        toI = busmap[line.BusNum__1]

        # Arc-Node Adjacency Matrix
        A[i, fromI] = 1
        A[i, toI] = -1

        # Pi Model
        Cbus[fromI] += C/2
        Cbus[toI] += C/2

    return (Re, Le, Cbus, A)

def transient_network_matrix(lines, buses, loads, gens, f_ref=60):
    '''
    Generates the Equivilent RLC network for the state of the grid

    f_ref:
    Frequency of relative operation.
    - If a value is passed, dynamic values of V and I can be
      represented as phasors.
    '''
    
    # Line Values
    R, L, C, A = rlc_line(lines, buses)
    Re = diagflat(R)
    Le = diagflat(L)
    Cbus = diagflat(C)
    
    # Shunt/Bus Values
    R,L,C = rlc_bus(buses, loads, gens) 
    Rload = diagflat(R)
    Lload = diagflat(L)
    Cload = diagflat(C)

    '''
    
    ODE STRUCTURE

    '''

    # Net Bus Capacitance (Generative Cap + Line Pi Cap)
    # Gaurenteed a Non-Zero Value
    Cd = Cbus + Cload
    Cdi = inv(Cd)

    # Net Bus Indictance (Q Load)
    # Remove rows that have no Inductance
    Ld = Lload[~all(Lload == 0, axis=1)]
    Ldi = reciprocal(Ld, where=(Ld!=0))

    # Inverse Net Bus Resistance (MW)
    # Only Reciprical if R exists
    Rdi = reciprocal(Rload, where=(Rload!=0)) 

    # Inverse of Line Inductances
    Lei = inv(Le)

    # Version of Cdi with only nodes that have +Q Load
    Cdiq = Cdi[:,~all(Lload == 0, axis=1)]

    # Filler Matricies TODO sparse instead
    ZRO2 = zeros((Ldi.shape[0],A.shape[0]))
    ZRO3 = zeros((Lei.shape[0],Cdiq.shape[1]))

    '''

    FREQUENCY SHIFT

    '''

    # Shifts ODE to be in a rotating frame
    W1 = - 1j*2*pi*f_ref * eye(Cdi.shape[0], dtype=complex)
    W2 = - 1j*2*pi*f_ref * eye(Ldi.shape[0], dtype=complex) 
    W3 = - 1j*2*pi*f_ref * eye(A.shape[0], dtype=complex)

    '''
    
    RESULTS

    '''

    # Explicit ODE Form 
    # TODO top right negate? top row?
    ode_form = block([[-Cdi@Rdi+W1 , -Cdiq   , -Cdi@A.T  ],
                      [Ldi         , W2      , ZRO2      ],
                      [Lei@A       , ZRO3    , -Lei@Re+W3]])

    return ode_form