
from typing import Any
import numpy as np
from functools import partial
import scipy.sparse as sp
from numpy import pi

from numpy import block, diag, real, imag
from scipy.linalg import schur, pinv
from abc import ABC, abstractmethod
from scipy.sparse.linalg import eigsh

from gridwb.workbench.utils.cheby import Chebyshev, Recurrence

 
def sech(t):
    return 1/np.cosh(t)

def eigmax(L):
    '''Finds Largest Eigenvalue (intended for Sparse Laplacians)'''
    return eigsh(L, k=1, which='LA', return_eigenvectors=False)

def takagi(M):
   n = M.shape[0]
   D, P = schur(block([[-real(M),imag(M)],[imag(M),real(M)]]))
   pos = diag(D) > 0
   Sigma = diag(D[pos,pos])
   # Note: The arithmetic below is technically not necessary
   U = P[n:,pos] + 1j*P[:n,pos]
   return U, Sigma.diagonal()

'''
TIME - DOMAIN
'''

class Morlet:
    '''
    A morlet wavelet analyzer.
    '''
    

    def __init__(self, sig=2*pi) -> None:

        # It is convention to use atleast sig > 5 to prevent locality issues
        self.sig = sig

        # Constants of normalization
        self.csig = (1+np.exp(-sig**2)-2*np.exp(-3/4*sig**2))**(-1/2)
        self.ksig = np.exp(-1/2*sig**2)

        # This is just the aggregate scalars of function
        self.alpha = self.csig/pi**(1/4)

    def eval(self, t):
        '''Evaluates at unity scale centered at t=0'''
        y = self.alpha*np.exp(-t**2/2)*(np.exp(1j*self.sig*t) - self.ksig)
        return y
    
    def fourier(self, w):
        y = self.csig*np.pi**(-1/4)*(np.exp(-(self.sig-w)**2/2) - self.ksig*np.exp(-w**2/2))
        return y.real
    
    def transform(self, a, b, f, t):
        '''Performs inner product based on parameters'''
        
        wav = self.eval((t-a)/b)
        wav /= np.sqrt(b)
        #wav /= np.linalg.norm(wav)

        return np.dot(wav, np.conjugate(f))

class WaveletCoeff:
    '''Stores Necessary Information about signals wavelet transform'''

    def __init__(self, C, trange, srange) -> None:
        self.C = C 
        self.trange = trange 
        self.srange = srange

'''
GRAPH - DOMAIN
'''

class AbstractKernel:

    def __init__(self) -> None:
        pass

    @abstractmethod
    def h(self, x):
        '''
        Description:
            The scaling kerenl h(x) evaluating the 'DC-like' spectrum
        Parameters:
            Vector x, the spectrum domain to evaluate.
        Returns:
            Spectral domain scaling kerenel
        '''

    @abstractmethod
    def g(self, x):
        '''
        Description:
            The wavelet generating kerenl g(x) evaluating the un-scaled wavelet
        Parameters:
            Vector x, the spectrum domain to evaluate.
        Returns:
            Spectral domain wavelet kerenel
        '''


class SGWTKernel(AbstractKernel):
    '''
    Description:
        Kernel intended for discrete SGWT
    Parameters:
        Filter-Defining parameters alpha, and spectrum bounds
    '''

    def __init__(self, smin, smax, alpha, nscales) -> None:
        self.smin = smin 
        self.smax = smax
        self.alpha = alpha
        self.nscales = nscales

    def calc_scales(self):
  
        # Log samples between min and max
        return np.logspace(
            np.log2(self.smin), 
            np.log2(self.smax), 
            num=self.nscales, 
            base=2
        )
    
    def g(self, x, scale=1):
        '''
        Description:
            Evaluates the Spectrum of Wavelet at given scale S
        Parameters:
            xi: Scalar or Array of spectral values to evaluate g.
            s: Scale at which to evaluate.
        '''

        xp = x/scale
        f = 2*xp/(xp**2 + 1)
        a = self.alpha 

        return f**a
    
    def h(self, x):
        '''
        Description:
            Evaluates scaling function, requires 'lmin' which is the smallest spectra.
        '''
        # Scale to the minimum desired spectrum
        xp = x/self.smin
        f = 1/(xp**2+1)
        a = self.alpha 

        return f**a
    
class SGWT:
    '''Given a wavelet kernel and GFT basis, this will perform helper functions.'''

    def __init__(self, ker: SGWTKernel, U, xi) -> None:
        self.ker = ker 
        self.U = U.copy()
        self.xi = xi

        # The minimum is a design parameter, maximum is just maximum eigenvalue
        self.scales = ker.calc_scales()

        # Scaling function
        self.h = self.ker.h(xi)

        # GFT domain wavelets - Pre compute
        self.g_all = np.array([
            ker.g(xi, s) for s in self.scales
        ])

        # NOTE When graph is complex-valued must do inverse :( assume hermitian for now
        # Only compute full transformation if called 
        self.Ui = self.U.T.conj()
        self.T = None


    def wavelet(self, vertex=None, scale_idx=None):
        '''
        Returns the graph wavelet of given scale and localized at a given node.
        n is 
        J is the index of the scale (0 is smallest scale)
        '''

        # Get g at this scale
        g = self.g_all[scale_idx]

        # Impulse in GFT domain
        fhat = self.Ui[:,vertex]

        # Filter with wavelet kernel
        psi = fhat*g

        # Filter and change back to vertex domain
        return self.U@psi
    
    def scalingvec(self, vertex):
        '''Returns the scaling function localized at node n. None returns all'''

        # Impulse in GFT domain
        fhat = self.Ui[:,vertex]

        # Filter with wavelet kernel
        S = fhat*self.h

        return self.U@S
        
    def transformation(self):
        '''Effectively same as SGWT.wavelet, except it returns a matrix for all coefficients to be calculated.
        When multipled, all cofficents are determined. The first n rows are for the smallest scale, localized at each node.
        The blocks repeat for each scale.
        '''

        # SCaling Functions in Vertex-Domain, then ->
        T = np.vstack([
            self.U@sp.diags(g) for g in self.g_all # TODO
        ])@self.U.T.conj()  # Post-Multiply the GFT conversion!

        self.T = T 

        return T
    
    def inverse(self):
        '''Returns the psuedo inverse of the transformation'''

        if self.T is None:
            self.transformation()

        return pinv(self.T)
    

'''
FAST CHEBYSHEV
'''

class FastSGWT:

    def __init__(self, L, nscales=10, K=500, pow=2) -> None:

        # Graph Laplacian
        self.L = L

        # Set Power of the wavelet kernel
        self.pow = pow

        # Number of discrete scales
        self.nscales = nscales
        self.scales = self.__makescales(nscales)

        # Determine node count from laplacian
        self.nbus = L.shape[0]

        # Calculate max eigenvalue
        self.emax = eigmax(L)

        # Recurrance Operator
        self.R = self.Rmatrix()

        # Chebyshev object & domain
        self.T = Chebyshev((0, self.emax)) # ((1e-6, self.emax))

        # Order of approximation (chebyshev)
        self.K = K
        self.setK(K)

    def __makescales(self, nscales):
        return np.logspace(2, 5, nscales)
    
    def __kernelcoeff(self, N=None):

        # N is the number of Chebyshev sample/anchor nodes
        if N is None:
            N = self.K

        # Calculates Coefficients for each scaled kerenel 
        # Each col Order (k) and each row spatial scale
        Cs = np.array([self.T.coeff(partial(self.g,s=s), self.K, N) for s in self.scales])

        # NOTE in the summation process, we divide the first-order coefficient by 2.
        # We pre-compute that here so we can standardize in integration
        Cs[:,0] /= 2

        return Cs
    
    def __itercheby(self, up, upp):
        # Recurrence Function
        return self.R@up - upp
    
        
    def __allocatewav(self):
        return np.zeros((self.nscales, self.nbus))

    def g(self, x,s=1):
        return (2*s*x/(1+(s*x)**2))**self.pow

    def Rmatrix(self):

        # Recurrance matrix
        # NOTE R matrix is technically without the 2, 
        # but it is easier to include it here
        I = np.eye(self.nbus)
        a = self.emax/2
        R = 2*(self.L-a*I)/a

        return R
    
    
    def setK(self, K):
        ''' 
        Description:
            Calls functions that should be called if K is changed.
            Example: updates kernel functions  when order of model is changed
        '''
        # Store K
        self.K = K 

        # Update kernel coefficients
        self.Cs = self.__kernelcoeff()

    def __call__(self, *args: Any, **kwds: Any):
        
        # Function to transform
        f = args[0]

        # Seed Vectors
        u0, u1 = f, 0.5*self.R@f

        # Manages Recurrance formula
        recurr = Recurrence(u0, u1, self.K, self.__itercheby)

        # Allocate Wavelet Coeff Storage
        WAVS = self.__allocatewav()

        # Looping Through Cheby Orders
        for i, u in enumerate(recurr): 
            WAVS += self.Cs[:,[i]]*u

        return WAVS
