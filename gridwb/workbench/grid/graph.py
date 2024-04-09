
from scipy.sparse import lil_matrix, eye, diags

from .components import Gen, Load, Bus

class WBGraph:


    def __init__(self, lines, buses) -> None:

        # Save Data
        self.lines = lines
        self.buses = buses

        # N is Number of Nodes, M is number of Edges
        self.n = len(buses)
        self.m = len(lines)

        self._init_matrix()


    def _init_matrix(self):

        # Indicies
        busmap = {b.BusNum: i for i,b in enumerate(self.buses)}

        # Arc-Node Incidence Matrix (LxN)
        ADJ = lil_matrix((self.n, self.n), dtype=complex)
        DEG = lil_matrix((self.n, self.n), dtype=complex)

        # For Each Line
        for line in self.lines:

            Y = 1/(line.LineR__2 + 1j*line.LineX__2)

            # Locate Index of To-From Buses
            fromI = busmap[line.BusNum]
            toI = busmap[line.BusNum__1]

            # Arc-Node Adjacency Matrix
            ADJ[fromI, toI] += Y
            ADJ[toI, fromI] += Y

            DEG[fromI, fromI] += Y
            DEG[toI, toI] += Y
        
        self._ADJ = ADJ
        self._DEG = DEG
        


    @property
    def ADJ(self):
        '''
        The Weight Matrix of the Network

        Where W_ij = Weight of Edge between Nodes
        
        dim(ADJ) = (N Nodes)x(N Nodes)
        
        '''

        return self._ADJ
    
    @property
    def DEG(self):
        '''
        Degree Matrix of Network (Diagonal)
        
        dim(DEG) = (N Nodes)x(N Nodes)
        '''

        return self._DEG
    
    @property
    def LAP(self):
        '''Nodal Laplacian Matrix of the Network'''

        return self.DEG - self.ADJ
    
