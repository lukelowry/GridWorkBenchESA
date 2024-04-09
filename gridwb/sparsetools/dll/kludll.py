from os import path, add_dll_directory
from ctypes import CDLL, POINTER, c_double, c_int
from .structs import KLUCommon, KLUNumeric, KLUSymbolic

'''
DLL Notes: When Compining DLL, Static Links /MD Multithreaded or else it will have many dependencies and can't run
'''

class KLUDLL:
    '''Object Representing the SuiteSparse DLL'''

    #dll_name = r'SparseDLL.dll'
    real_dll_name = r'KLU_Real.dll'
    cmplx_dll_name = r'KLU_Complex.dll'

    def __init__(self, cmplx=False) -> None:

        # Add to directory incase it can't find
        _DIRNAME = path.dirname(path.abspath(__file__))
        add_dll_directory(_DIRNAME)

        # DLL choice
        dll_name = self.cmplx_dll_name if cmplx else self.real_dll_name

        # Open DLL
        dll = CDLL( _DIRNAME + path.sep + dll_name)

        # Define Function Arguments
        dll.lu_symbolic.argtypes = c_int, POINTER(c_int), POINTER(c_int), POINTER(KLUCommon),
        dll.lu_numeric.argtypes = POINTER(c_int), POINTER(c_int), POINTER(c_double), POINTER(KLUSymbolic), POINTER(KLUCommon),
        dll.lu_solve.argtypes = POINTER(KLUSymbolic), POINTER(KLUNumeric), POINTER(KLUCommon), POINTER(c_double), c_int, c_int,
        dll.lu_free_symbolic.argtypes = POINTER(KLUSymbolic), POINTER(KLUCommon),
        dll.lu_free_numeric.argtypes = POINTER(KLUNumeric), POINTER(KLUCommon),
        dll.lu_free_common.argtypes = POINTER(KLUCommon),

        # Define Function Return
        dll.lu_common.restype = POINTER(KLUCommon)
        dll.lu_symbolic.restype = POINTER(KLUSymbolic)
        dll.lu_numeric.restype = POINTER(KLUNumeric)
        dll.lu_solve.restype = c_int

        # Bind DLL to object
        self.dll = dll

        # Track memory allocation to free later
        self.com_to_free: list[tuple] = []
        self.sym_to_free: list[tuple] = []
        self.num_to_free: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        '''When the DLL is used with a context manager,
        it will take car of all memory managment'''

        # Free Memory
        self.free_all()

    def free_symbolic(self):
        '''Free any Existing Symbolic Matricies Created'''

        for sym, common in self.sym_to_free:
            self.dll.lu_free_symbolic(sym, common)
        
        self.sym_to_free.clear()

    def free_numeric(self):
        '''Free any Existing Numeric Matricies Created'''
        
        for num, common in self.num_to_free:
            self.dll.lu_free_numeric(num, common)

        self.num_to_free.clear()

    def free_common(self):
        '''Free any Existing Common Matricies Created'''
        
        for common in self.com_to_free:
            self.dll.lu_free_common(common)

        self.com_to_free.clear()

    def free_all(self):
        '''Free all pointers that this instance oversees'''

        self.free_symbolic()
        self.free_numeric()
        self.free_common()
    
    def common(self):
        '''Return pointer to a default Common matrix.'''

        # Aquire Default Common
        common = self.dll.lu_common()

        # Free at end of context
        self.com_to_free.append(common)

        return common
    
    def symbolic(self, n, ap, ai, common):
        '''Return the symbolic factorization matrix pointer'''

        # Aquire Symbolic LU
        sym = self.dll.lu_symbolic(n, ap, ai, common)

        # Free at end of context
        self.sym_to_free.append((sym, common))

        return sym
    
    def numeric(self, ap, ai, ax, sym, common):
        '''Return the numeric factorization matrix pointer'''

        # Aquire Numeric LU
        num = self.dll.lu_numeric(ap, ai, ax, sym, common)

        # Free at end of context
        self.num_to_free.append((num, common))

        return num
    
    def solve(self, sym, num, common, b, ldim, nrhs):
        '''Solves Sparse LU and returns result in b pointer
        Solves in form xA=b
        Where x = 1xN A = NxN b = 1xN'''
        
        self.dll.lu_solve(sym, num, common, b, ldim, nrhs)