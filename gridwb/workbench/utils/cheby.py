
from numpy import diff, pi
import numpy as np
from typing import Any


class Recurrence:

    def __init__(self, u0, u1, K, relation=None):
        '''K is the order of the model (one iteration per order)'''
        self.u0, self.u1 = u0, u1
        self.K = K
        self.relation = relation


    def __iter__(self):

        upp, up = 0, 0

        for k in range(self.K):
            if   k == 0: u = self.u0
            elif k == 1: u = self.u1
            else:        u = self.relation(up, upp)
        
            yield u
            upp, up = up, u


class Chebyshev:
    '''A functional class that helps in the synthesis and evaluation of Chebyshev polynomials'''

    def __init__(self, domain = (-1, 1)) -> None:
        
        # Parameter Calculations
        a, b = domain
        self.mid   = (a + b)/2
        self.scale = (b - a)/2

        # Store
        self.a, self.b = a, b

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        '''
        Description:
            Generates k-th order Chebyshev polynomial in pre-specified domain
        Parameters:
            k: Polynomial order
        Returns:
            Function that evaluates polynomial
        '''
        k = args[0]

        mid   = self.mid
        scale = self.scale

        def func(t):
            return np.cos(k*np.arccos((t-mid)/scale))
        
        return func
    
    @property
    def domain(self) -> tuple:
        '''
        Description:
            Minimum Maximum value of the Chebyshev domain
        '''
        return self.a, self.b
    
    
    def coeff(self, f, K=7, N=100):
        '''
        Description:
            Given a function f, determines cheby coefficients up to order kmax
        Parameters:
            f: function to be approximated
            K: max order of polynomial
            N: number of samples to use
            A: Max RHS domain [0, A]
        '''

        # Parameterization
        t = np.linspace(0, pi, N) # NOTE I changed to 2pi
        alp = self.b/2
        x = alp*(1 + np.cos(t))

        # Boundary Weights
        ft = f(x)

        # Coefficients
        C = 2/N*np.array([
            np.cos(k*t)@ft for k in range(K)
        ])

        return C

