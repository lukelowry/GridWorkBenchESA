from typing import Any
import numpy as np
from functools import partial
import scipy.sparse as sp

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



class WKernel:
    '''
    Example Class use case

    # Create Wavelet Kernel, pass Eigenvalues and Eigenvectors
    wk = WKernel()
    wk.seteig(eigvals, eigvects)

    
    # Plot Scaling Functions
    t = np.linspace(0, 2, 1000)
    fig, ax = plt.subplots()
    for i in range(wk.J): 
        ax.plot(t,wk.g(t, i))

    '''

    def __init__(self, J=4, K=2**4, x1=1/20, x2=2/20, alpha=2, beta=2, lmax=2) -> None:
        self.J = J 
        self.K = K 
        self.x1 = x1 
        self.x2 = x2 
        self.alpha = alpha 
        self.beta = beta 
        self.lmax = lmax 

        # Minimum Eigen Parameter Determined by K
        self.lmin = lmax/K 

        # Maximum Scale
        self.smax = x2/self.lmin 

        # Minimum Scale
        self.smin = x1/lmax

        # Cubic Spline
        self.coeff = self.cspline(x1, x2, alpha, beta)
        self.spline = self.cfunc(self.coeff)

    def __left(self, x):
        return (x/self.x1)**self.alpha
    
    def __right(self, x):
        f = lambda t:  (self.x2/t)**self.beta
        return np.piecewise(
            x, 
            [x==0, x!=0], 
            [0   , f]
        )
    
    def __scale(self, i):
        '''Returns the i-th discrete scale based on the finite
        scale restrictions of the SGWT 
        '''
        return self.smax*(self.smin/self.smax)**(i/(self.J-1))
    
    # I got cubic to work
    def cspline(self, x1, x2, a, b):
        '''Returns coefficients of cubic spline given parameters of left and right functions'''
        A = np.array([
            [3*x1**3  , 2*x1**2,  x1, 0],
            [  x1**3  ,   x1**2,  x1, 1],
            [3*x2**3  , 2*x2**2,  x2, 0],
            [  x2**3  ,   x2**2,  x2, 1],
        ])
        b = np.array([[
            a, 1, -b, 1
        ]]).T

        return np.linalg.inv(A)@b

    def cfunc(self, coeff):
        '''Returns function given cubic coefficients that can be used to evaluate'''
        a, b, c, d = coeff 

        def f(t):
            return a*t**3 + b*t**2 + c*t + d
        
        return f
    
    def g(self, t, s=None):
        '''
        Scaling Function, Cublic Spline Piecewise
        s -> Scale of Function
        '''

        if s is not None:
            ts = t* self.__scale(s)
        else:
            ts = t

        A = ts < self.x1 
        C = ts > self.x2  
        B = ~(A|C)
        return np.piecewise(
            ts,
            [A, B, C],
            [self.__left, self.spline, self.__right]
        )

    def seteig(self, lam: np.ndarray, U: np.ndarray):
        '''Assign the Eigenvalues and Eigenvectors of the
        Laplacian matrix to create wavelet coefficient space.
        Not required to use this object.
        lam -> vector of ordered real eigenvalues
        U -> orthonormal eigenvector matrix
        '''
        self.lam = lam 
        self.U = U

    def wavelet(self, m, s):
        ''' 
        Generate the space (node) and scale (duration) wavelet basis vectors
        m - Index of Node
        s - Scale
        '''
        # Impulse at node # NOTE when normalized, bus scale by D index
        Xm = self.U[[m]].conj().T #* D.A[m,m]

        # Scaling Function
        G = self.g(self.lam, s)

        # The wavelet Vector
        WAV = self.U@sp.diags(G)@Xm

        # Return 1D vector
        return WAV[:,0]
