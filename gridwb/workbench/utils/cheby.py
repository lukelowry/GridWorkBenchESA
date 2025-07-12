
from numpy import diff, pi
import numpy as np
from scipy.sparse import csr_array
from typing import Callable, Tuple, Any
from scipy.fft import dct



def T(order: int, x):
    '''
    Description:
        Explicity Chebyshev of the First kind
    Parameters:
        p: order
        x: domain to evaluate
    '''
    return np.cos(order*np.arccos(x))


class Recurrence:
    '''
    Iterable object that performs chebyshev recurrance
    '''

    def __init__(self, u0, u1, P, R):
        '''
        Do P times:
            u(p+1) = R@u(p) - u(p-1)
        Parameters:
            u0: 0-th order cheby of function
            u1: 1-st order cheby of function
            P : Order of the approximation
            R : Recurrance operator (Assumed to include 2 scalar of the relation)
        '''
        self.u0, self.u1 = u0, u1
        self.P = P
        self.R = R


    def __iter__(self):

        u = self.u0 
        up = self.u1

        for k in range(self.P):

            yield u

            upp, up = up, u
            u = self.R@up - upp




class Chebyshev:
    """
    Class for synthesis and evaluation of Chebyshev polynomials
    over an arbitrary interval [a, b].
    """

    def __init__(self, domain: Tuple[float, float] = (-1, 1)) -> None:
        self.a, self.b = domain
        self.mid = (self.a + self.b) / 2
        self.scale = (self.b - self.a) / 2

    def __call__(self, k: int) -> Callable[[np.ndarray], np.ndarray]:
        """
        Returns the k-th Chebyshev polynomial of the first kind,
        scaled to the domain [a, b].
        """
        def T_k(x: np.ndarray) -> np.ndarray:
            x_scaled = (x - self.mid) / self.scale
            return np.cos(k * np.arccos(np.clip(x_scaled, -1, 1)))
        return T_k

    @property
    def domain(self) -> Tuple[float, float]:
        return self.a, self.b
    
    def coeff(self, f: Callable[[np.ndarray], np.ndarray], K: int = 7, N: int = 100) -> np.ndarray:
        """
        Fast Chebyshev coefficients using DCT-I (Clenshaw Curtis).
        """
        theta = np.pi * np.arange(N) / (N - 1)
        x_cheb = np.cos(theta)
        x_mapped = self.mid + self.scale * x_cheb

        # Sampe the function to be approximated
        fx = f(x_mapped)

        # Use DCT-I (type 1), which is mathematically equivalent to Clenshaw–Curtis
        c = dct(fx, type=1) / (N - 1)
        c[0] *= 0.5
        c[-1] *= 0.5

        return c[:K]

