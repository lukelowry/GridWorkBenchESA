
from scipy.sparse import csr_matrix
from ctypes import POINTER, c_int, c_double
from numpy import int32, float64
from numpy import iscomplexobj, empty
from numpy.ctypeslib import as_array as c_to_np

from .dll import KLUDLL

from ..workbench.utils.decorators import timing

class KLU:
    '''Structural Sparse LU Decomposition for Real and Complex Systems'''

    sym = None
    common = None

    def __init__(self, A: csr_matrix, cmplx: bool = False) -> None:
        '''Input a Scipy CSR matrix to perfrom LU
        Cmplx form -> Ap and Ai to remain same. Ax must be 2*n where (2i, 2i+1) is an index cmplx number'''

        # dim(A) -> Assumed Square
        self.n = A.shape[0]

        # Determine if Complex
        self.isCmplx = cmplx

        # Convert to C-Compatible Arrays for DLL Use
        self.Ap = self.idx_to_c(A.indptr)
        self.Ai = self.idx_to_c(A.indices)
        self.Ax = A.data    #self.vals_to_c(Acsr.data)
        # TODO the above only works with my special format, make works for generic matrix
        
        # DLL object to interface with dll
        self.klu = KLUDLL(cmplx)

        # Pre-Do Common Matrix
        self.common = self.klu.common()

        # Pre-Factor Symbolic Matrix
        self.sym = self.klu.symbolic(self.n, self.Ap, self.Ai, self.common)

    
    def idx_to_c(self, v):
        '''Convert an index-array to C-Compatible Array for DLL Use'''
        return v.astype(int32).ctypes.data_as(POINTER(c_int))

    def vals_to_c(self, v):
        '''Convert array Values to C-Compatible Array for DLL Use'''
        return v.astype(float64).ctypes.data_as(POINTER(c_double))

    def solve(self, b_dense):
        '''KLU Solve with integrated symbolic and numeric phase.
        B Vector in Shape Nx(VecCount)
        
        Re-solve with different non-zero values for the A Matrix.
        The Sparsity structure of A must not change.

        For a concurrent solve (i.e. Many b vectors) b should have the form
        NxM where N is the rows (N=dim of Matrix) and M is the vector count
        '''

        # Number of Concurrent Solves
        nvecs = b_dense.shape[1]

        # Flatten and C-Compatible
        b = self.vals_to_c(b_dense.flatten('F')) # TODO this may cause some compute time, do this beforehand?

        # Numeric LU Decomp
        num = self.klu.numeric(self.Ap, self.Ai, self.Ax, self.sym, self.common)

        # Solve Linear System
        self.klu.solve(self.sym, num, self.common, b, self.n, nvecs) # Last Argument is number of RHS vectos -> can solve many at once!

        # Free Only Numeric
        self.klu.free_numeric()

        # Return np array of result
        if self.isCmplx:
            return c_to_np(b, shape=(nvecs, self.n*2))
        else:
            return c_to_np(b, shape=(nvecs, self.n))
