from abc import ABC
from numpy import diff
import numpy as np
import scipy.sparse as sp
from typing import Any

# Constants
MU0 = 1.256637e-6

# Matrix Helper Functions
def normlap(L, retD=False):
    '''Given a square Laplacian matrix, this function will return the normalized
    Laplacian. If retD is True, the diagonal square root scaling matrix will be returned
    aswell
    Example Return:
    
    Y, D, Di = normlap(Y, True)

    Y = normLap(Y)
    
    '''

    # Get Diagonal and Invert for convenience
    Yd = np.sqrt(L.diagonal())
    Di = sp.diags(1/Yd)

    # Return Normalized Laplacian with or without scaled diag
    if retD:
        D = sp.diags(Yd)
        return Di@L@Di, D, Di
    else:
        return Di@L@Di


def hermitify(A):
    '''Given a (numpy) complex valued symmetric matrix (but not hermitian)
    this function will return the hermitian version of the matrix.'''

    if isinstance(A, np.ndarray):
        return (np.triu(A).conjugate() + np.tril(A))/2
    else:
        return (np.triu(A.A).conjugate() + np.tril(A.A))/2


class Operator(ABC):
    '''Abstract Mathematical Operator Object'''

    def __init__(self) -> None:
        pass
    

class DifferentialOperator(Operator):
    '''Only Supports 2D Fortan Style Ordering'''

    def __init__(self, shape, order='F') -> None:
        self.shape = shape
        self.nx, self.ny = shape
        self.nElement = self.nx*self.ny

        self.D = [-1, 1] 

    def newop(self):
        return np.zeros((self.nElement, self.nElement)), np.zeros((self.nElement, self.nElement))
    
    def aslil(self, Dx, Dy):
        return sp.lil_matrix(Dx), sp.lil_matrix(Dy)

    def flatidx(self, x, y):
        return y*self.nx + x
    
    def flattoloc(self, idx):
        return idx%self.nx, idx//self.nx
    
    def up(self, idx):
        return idx + self.nx
        
    def down(self, idx):
        return idx - self.nx
    
    def right(self, idx):
        return idx + 1
    
    def left(self, idx):
        return idx - 1
    
    def elementiter(self):
        '''Iterate through each tensor element to get index and position'''

        for yi in np.arange(self.ny):
            for xi in np.arange(self.nx):
                yield xi, yi, self.flatidx(xi, yi)
        
    def central_diffs(self) -> None:
        '''Produces central difference gradient operators for a vector field in Fortran ordering'''

        Dx, Dy = self.newop()

        for xi, yi, idx in self.elementiter():

            if xi==0 or xi==self.nx-1: continue
            if yi==0 or yi==self.ny-1: continue

            # Selectors
            dx = [ self.left(idx) , self.right(idx) ]
            dy = [ self.down(idx) , self.up(idx)    ]

            Dx[idx , dx] += self.D
            Dy[idx , dy] += self.D

        return self.aslil(Dx/2, Dy/2)


    def forward_diffs(self) -> None:
        '''Produces forward difference gradient operators for a vector field in Fortran ordering'''

        Dx, Dy = self.newop()

        for xi, yi, idx in self.elementiter():

            # Selectors
            dx = [idx , self.right(idx)]
            dy = [idx , self.up(idx)]

            # Add Y Differential to Tile
            if xi < self.nx-1:
                Dx[idx , dx] += self.D

            # Add to Adjacent Tiles
            if yi < self.ny-1:
                Dy[idx , dy] += self.D

        return self.aslil(Dx, Dy)
    
    def backward_diffs(self) -> None:
        '''Produces backward difference gradient operators for a vector field in Fortran ordering'''

        Dx, Dy = self.newop()

        for xi, yi, idx in self.elementiter():

            # Selectors
            dx = [idx, self.left(idx)]
            dy = [idx, self.down(idx)]

            if xi != 0:
                Dx[idx , dx] += self.D

            if yi != 0:
                Dy[idx , dy] += self.D

        return self.aslil(Dx, Dy)
    
    def partial(self):
        ''' Return centered partial operators for a 2D vector field tensor'''

        Dxf, Dyf = self.forward_diffs()
        Dxb, Dyb = self.backward_diffs()

        return Dxb - Dxf, Dyb - Dyf
    
    def divergence(self):
        '''Central Difference Based Finite Divergence'''

        Dx, Dy = self.partial()
        return sp.hstack([Dx, Dy])
    
    def curl(self):
        '''Central Difference Based Finite Curl'''
    
        Dx, Dy = self.partial()
        return sp.hstack([Dy, -Dx])
    
    def laplacian(self):
        '''Central Difference Based Finite Divergence'''

        Dxf, Dyf = self.forward_diffs()
        return Dxf.T@Dxf + Dyf.T@Dyf
    
    def J(self):
        '''  Complex Unit Equivilent and/or hodge star, Assume 2D Array is flattened'''

        n = self.nElement
        I = sp.eye(n)
        return sp.bmat([
            [None, -I  ],
            [I   , None]
        ])
    
    def ext_der(self):
        '''Calculate exterior derivative of linear function/operator'''
        # Used outside class up top
        pass

    
    #def ext_der(incidince):
        #return np.sum(incidince.A,axis=0, keepdims=True).T


class MeshSelector:

    def __init__(self, dop: DifferentialOperator) -> None:


        self.SELECTOR = np.full(dop.nElement, False)

        nsel = lambda n: (self.SELECTOR.copy() for i in range(n))

        # Sides Including Corners
        self.LEFT, self.RIGHT, self.UP, self.DOWN = nsel(4)

        # Primary Indexing
        for xi, yi, idx in dop.elementiter(): 
            self.LEFT[idx] =  (xi==0)
            self.RIGHT[idx] =  (xi==dop.nx-1)
            self.UP[idx] =  (yi==dop.ny-1)
            self.DOWN[idx] =  (yi==0)

            # CENTRAL2[idx] = ~((xi==1) or (yi==1) or (xi==dop.nx-2) or (yi==dop.ny-2))

        # Secondary Indexing
        self.ALLCRNR = (self.LEFT|self.RIGHT)&(self.UP|self.DOWN)
        self.BOUND = self.LEFT|self.RIGHT|self.UP|self.DOWN
        self.CENTRAL = ~self.BOUND 


        # TODO Generic versions of above


class Chebyshev:
    '''A functional class that helps in the synthesis and evaluation of Chebyshev polynomials'''

    def __init__(self, a=-1, b=1) -> None:
        self.a = a 
        self.b = b 

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        '''Returns a function that evaluates n-th order Chebyshev polynomial in specified domain'''
        n = args[0]

        mid = (self.b+self.a)/2
        scale = (self.b-self.a)/2

        def func(t):
            return np.cos(n*np.arccos((t-mid)/scale))
        
        return func
