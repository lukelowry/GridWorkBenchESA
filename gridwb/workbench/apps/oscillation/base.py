from scipy.sparse import lil_matrix
from cmath import rect

from ...grid.common import ybus_with_loads, double_cmplx_ybus
from ...grid.components import Gen, Bus, Load

class BaseOscMatrix:

    def __init__(self, Y, gens: list[Gen], oscmodels, buses: list[Bus], loads: list[Load]):

        # [[G, -B], [B, G]] Format
        YC = double_cmplx_ybus(ybus_with_loads(Y, buses, loads))

        # Osc Mastrix - Start with Y Bus in upper left
        self.master = lil_matrix(YC.copy().real, dtype=complex)

        # Indexing Variables
        self.nbuses = len(buses)
        self.nmodels = len(oscmodels)

        # Each Bus Position in Y-Bus
        # TODO Do a sort before because I don't think its gaurenteed order
        self.busPosY = {b.BusNum: i for i, b in enumerate(buses)}

        # Track the diagonal positions of the elments that are differential
        self.diag_diff_locs = []

        # Models that are with a Closed Generator
        # Any passed models are assumed active
        for oscmodel in oscmodels:
            self.add_model(oscmodel)

    def add_model(self, oscmodel):
        '''Inserts Gen Matricies to an Oscillation Matrix'''

        # Index of Insertion in Master
        busidx = self.busPosY[oscmodel.busnum]


        # Extract Differential and 2 Algebraic Matricies
        intern = oscmodel.internal_mat()
        kcl = oscmodel.kcl_mat()
        kvl = oscmodel.kvl_mat()

        # Shape Markers
        N = oscmodel.shape[0]
        end = self.master.shape[0]

        # Add Differential Diagonal locations
        locs = [end + i for i in oscmodel.diag_diff_indicies]
        self.diag_diff_locs += locs

        # Insert Zero Rows and Cols so data can be inserted
        self.master.resize((end+N, end+N))

        # Insert Algebraic
        self.master[busidx, end:end+N]  = kcl[0]
        self.master[busidx+self.nbuses, end:end+N]  = kcl[1]

        # Insert Algebraic
        self.master[end:end+N, busidx]  = kvl[0]
        self.master[end:end+N, busidx+self.nbuses]  = kvl[1]

        # Insert Differential
        self.master[end:end+N, end:end+N] = intern

    def csr(self):
        '''Return Base Oscillation Matrix in CSR Format'''
        return self.master.tocsr()
    
    def transpose(self):
        '''Transpose the Base Osc Matrix'''
        self.master = self.master.transpose()