from scipy.sparse import csr_matrix
from ctypes import POINTER, c_int, c_double
from numpy import int32, float64
from numpy.ctypeslib import as_array as c_to_np

from .dll import SparseDLL

class KLU:
    '''Structural Sparse LU Decomposition'''

    sym = None
    common = None

    def __init__(self, A: csr_matrix) -> None:
        '''Input a Scipy CSR matrix to perfrom LU'''

        # Transpose, Assuming user wants form Ax = b, DLL is xA = b
        #csr = csr.transpose() ?
        self.n = A.shape[0]

        # Convert to C-Compatible Arrays for DLL Use
        self.Ap, self.Ai, self.Ax = self.csr_to_c(A)

        # DLL object to interface with dll
        self.klu = SparseDLL()

        # Pre-Factor Symbolic Matrix
        self.prefactor()

    def csr_to_c(self, Acsr: csr_matrix):
        '''Convert a Numpy CSR Array to a CType Passable array Set'''

        # Convert to C-Compatible Arrays for DLL Use
        Ap = self.idx_to_c(Acsr.indptr)
        Ai = self.idx_to_c(Acsr.indices)
        Ax = self.vals_to_c(Acsr.data)

        return (Ap, Ai, Ax)
    
    def idx_to_c(self, v):
        '''Convert an index-array to C-Compatible Array for DLL Use'''
        return v.astype(int32).ctypes.data_as(POINTER(c_int))

    def vals_to_c(self, v):
        '''Convert array Values to C-Compatible Array for DLL Use'''
        return v.astype(float64).ctypes.data_as(POINTER(c_double))

    def prefactor(self):
        '''Perform a Symbolic LU, which will be remebered and used
        if the resolve() function is used'''

        # Common Matrix
        self.common = self.klu.common()

        # Symbolic Matrix - Compute if not Givven
        self.sym = self.klu.symbolic(self.n, self.Ap, self.Ai, self.common)

    def resolve(self, A, b_dense):
        '''Re-solve with different non-zero values for A
        The Sparsity structure of A must not change.'''

        # C-Compatible
        Ap, Ai, Ax = self.csr_to_c(A)
        b = self.vals_to_c(b_dense)

        # Numeric LU Matrix
        num = self.klu.numeric(Ap, Ai, Ax, self.sym, self.common)

        # Solve Linear System
        self.klu.solve(self.sym, num, self.common, b, self.n, 1)

        # Free Only Numeric
        self.klu.free_numeric()

        # Return np array of result
        return c_to_np(b, shape=(1, self.n))


    def solve(self, b_dense):
        '''KLU Solve with integrated symbolic and numeric phase'''
        
        # Convert to C-Compatible Array for DLL Use
        b = b_dense.astype(float64).ctypes.data_as(POINTER(c_double))

        # Numeric LU Matrix
        num = self.klu.numeric(self.Ap, self.Ai, self.Ax, self.sym, self.common)

        # Solve Linear System
        self.klu.solve(self.sym, num, self.common, b, self.n, 2)

        # Free Only Numeric
        self.klu.free_numeric()

        # Return np array of result
        return c_to_np(b, shape=(1, self.n))
    
