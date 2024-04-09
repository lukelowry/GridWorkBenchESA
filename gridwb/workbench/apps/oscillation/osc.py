from numpy import array, where, empty, float64, pi, zeros
from ctypes import POINTER, c_double
from scipy.sparse import lil_matrix

from .base import BaseOscMatrix

class OscMatrix:

    def __init__(self, base: BaseOscMatrix) -> None:
        '''Given a reference base (csr) (python complex) oscillation matrix
        where s=0+0j, This object will allow you to generate an osc matrix
        for any given 's' incredibly efficiently.'''

        # Shift Tracking
        self.prevshft = 0

        # For utility
        self.nbuses = base.nbuses

        '''Pre-calculate Inidices that we will modify in CSR format'''

        # Diag index of target elements
        targets_diag = base.diag_diff_locs

        # Convert to CSR
        base_ref = base.csr()

        # Change 'to-be' changed elements sparsity by jsut setting to zero - Must be done after converting to CSR
        base_ref[targets_diag, targets_diag] += 0
        
        # Extract Ap, Ai, Ax
        self.indptr = base_ref.indptr # Pointers to col-index list for Row
        self.indices = base_ref.indices # Column Indicies of NZ base matrix
        Ax = base_ref.data # Get data to compute double_complex

        # Record Shape
        self.shape = base_ref.shape

        # Row Equivilent of Ai
        row_idxs = array([i for i in range(len(self.indptr)-1) for n in range(self.indptr[i+1]-self.indptr[i])])

        # 'Actual' 'real valued' indicies of complex osc_matrix NxN that will be modified
        # to get the 'complex valued' for the double_cmplx version, we jsut add one to the col index for each target
        targets_sparse_loc = []

        # Find Index of Target in Sparse Data
        for t in targets_diag:

            r = where((self.indices==t) & (row_idxs==t))[0]

            # If Found
            if r.size > 0:
                targets_sparse_loc.append(r[0])

        # Seperate Real and Complex into Two Lists
        self.real_sparse_target_locs = [int(2*t) for t in targets_sparse_loc]
        self.cmplx_sparse_target_locs = [int(2*t+1) for t in targets_sparse_loc]

        '''END Pre-calculate Inidices'''

        # Double_complex  Sparse Data
        self.data = empty(Ax.shape[0]*2)
        self.data[::2] = Ax.real
        self.data[1::2] = Ax.imag

        # Store as C-Type for quick Access in KLU
        self.data = self.data.astype(float64).ctypes.data_as(POINTER(c_double))

    def at(self, alpha=0, freq=0):
        '''To prevent un needed coppies, old change values are removed 
        the new ones are added to enhance speed'''

        # s-Plane value
        wm = 2 * pi * freq
        s = alpha + 1j*wm

        # Shift relative to previous shift
        a_modify = alpha-self.prevshft.real
        w_modify = wm-self.prevshft.imag

        # Shift s-plan val at target indicies
        for t in self.real_sparse_target_locs:
            self.data[t] -= a_modify
        
        for t in self.cmplx_sparse_target_locs:
            self.data[t] -= w_modify
            
        # Save shift that was applied in this call so that it can be reversed later
        self.prevshft = s

        return self

class OscInjGroup:
    '''Convenience Class to assist in Injected Oscillation Currents'''

    def __init__(self, om: OscMatrix) -> None:
        self.om = om
        self._vec = self._null_inj()
        self.nbuses = om.nbuses

    def __str__(self) -> str:
        return str(self.injs)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def _null_inj(self):
        return zeros((2*self.om.shape[0],1), dtype=float64)
    
    def inject(self, bus, realosc=0+0j, imagosc=0+0j):
        '''Adds Oscillation Current to a bus with a Real and Imag Phasor'''
        self._vec[2*bus]   = realosc.real
        self._vec[2*bus+1]   = realosc.imag
        self._vec[2*(bus+self.nbuses)] = imagosc.real
        self._vec[2*(bus+self.nbuses) + 1] = imagosc.imag
    
    @property
    def vec(self):
        return self._vec