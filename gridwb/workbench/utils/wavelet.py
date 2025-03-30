
import numpy as np
from functools import partial
import scipy.sparse as sp
from numpy import pi

from numpy import block, diag, real, imag
from scipy.linalg import schur, pinv
from abc import ABC, abstractmethod

 
def sech(t):
    return 1/np.cosh(t)


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

    def __init__(self, sig=1) -> None:
        self.sig = sig
        self.csig = (1+np.exp(-sig**2)-2*np.exp(-3/4*sig**2))**(-1/2)
        self.ksig = np.exp(-1/2*sig**2)
        self.alpha = 2

    def window(self, t):
        #y = self.csig*np.pi**(-1/4)*np.exp(-t**2/2)*(np.exp(1j*self.sig*t) - self.ksig)
        #y = np.exp(1j*self.sig*t)*(1/np.cosh(2*t))
        y = np.sqrt(2*self.alpha)*np.exp(1j*self.sig*t)*(1/np.cosh(self.alpha*t))
        return y
    
    def fourier(self, w):
        y = self.csig*np.pi**(-1/4)*(np.exp(-(self.sig-w)**2/2) - self.ksig*np.exp(-w**2/2))
        return y.real
    
    def centralw(self):

        f = lambda w: w-self.sig/(1-np.exp(-self.sig*w))
        df = lambda w: 1-self.sig**2*np.exp(-self.sig*w)/(1-np.exp(-self.sig*w))**2

        w0 = self.sig

        for i in range(10):
            w0 -= f(w0)/df(w0)
            print(f(w0), df(w0))
            
        return w0
    
    def transform(self, a, b, f, t):
        '''Performs inner product based on parameters'''
        
        wav = self.window((t-a)/b)
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
            self.U@sp.diags(g) for g in self.g_all
        ])@self.U.T.conj()  # Post-Multiply the GFT conversion!

        self.T = T 

        return T
    
    def inverse(self):
        '''Returns the psuedo inverse of the transformation'''

        if self.T is None:
            self.transformation()

        return pinv(self.T)
    