
import numpy as np
from functools import partial
import scipy.sparse as sp
from numpy import pi

class WaveletCoeff:
    '''Stores Necessary Information about signals wavelet transform'''

    def __init__(self, C, trange, srange) -> None:
        self.C = C 
        self.trange = trange 
        self.srange = srange

def sech(t):
    return 1/np.cosh(t)

class ModWavelet:
    '''
    Description:
        Generalized Wavelet Object, with scaling and generating kernels.
    Parameters:
        Filter-Defining parameters alpha & beta
    '''

    def __init__(self, alpha=1, beta=1) -> None:
        self.alpha = alpha
        self.beta = beta

        # Searching spectra through a+b at scale=1 finds this value
        self.gmax = np.max(self.g(np.linspace(0,alpha+beta,1000)))

    def __call__(self, t):
        # Note when a 'proper' scaling is done
        # The entire function is divided by the square root of scale
        return np.sqrt(2*self.alpha)*np.exp(1j*self.beta*t)*sech(self.alpha*t)
    
    def g(self, xi, s=1):
        '''
        Description:
            Evaluates the Spectrum of Wavelet at given scale S
        Parameters:
            xi: Scalar or Array of spectral values to evaluate g.
            s: Scale at which to evaluate.
        '''
        #a = xi * s * np.sqrt(2 * pi) / (4*self.alpha)
        #b = pi/(2*self.alpha)*(s*xi-self.beta)
        #return a * sech(b)

        A = pi/self.alpha 
        B = self.beta/2/self.alpha 

        return sech(A*s*xi - B) - sech(A*s*xi)*sech(B)
    
    def h(self, xi, lmin):
        '''
        Description:
            Evaluates scaling function, requires 'lmin' which is the smallest spectra.
        '''
        return self.gmax/np.cosh((2*xi/lmin)**2)
    
    def coeff(self, a, b, f, t):
        '''
        Performs inner product to determine a wavelet coefficient
        a -> Time Locality of Wavelet
        b -> Scale of Wavelet
        f -> Function to be transformed
        t -> Domain of function
        '''
        
        wav = self((t-a)/b)
        wav /= np.sqrt(b)

        # Depends on use case if I want to normalize
        # 'edge' wavelets are severly distroted by this
        #wav /= np.linalg.norm(wav)

        return np.dot(np.conjugate(wav), f)
    
    def coeffs(self,t, f, times=None, scales=(0,3), numscales=5):
        '''
        Performs inner product to determine a wavelet coefficients 
        at the specified scales and time localities
        
        t -> Domain of function
        f -> Function to be transformed
        times -> N Locations in Time
        scales -> M Scales of Wavelet

        Returns
        NxM wavelet coefficient matrix
        '''

        # Wavelet Transform
        trange = times.min(), times.max()
        A = times
        B = np.logspace(*scales, numscales, base=2)
        C = np.zeros((A.shape[0],B.shape[0]), dtype=complex)

        for i, a in enumerate(A):
            for j, b in enumerate(B):
                C[i, j] = self.coeff(a, b, f, t)

        return WaveletCoeff(C, trange, scales)
    
class SGWT:
    '''Given a wavelet kernel and GFT basis, this will perform helper functions.'''

    def __init__(self, ker: ModWavelet, U, Lam, scales) -> None:
        self.ker = ker 
        self.U = U
        self.Lam = Lam 
        self.scales = scales 

        self.AbsLam = np.abs(Lam)

        '''DETERMINE SCALING FUNCTION IN SPECTRAL DOMAIN'''

        # Get largest scale wavelet kernel
        gLarge = self.ker.g(self.AbsLam, 2**self.scales[-1])

        # Find curve peak and identify the lambda that does this
        largestIDX = np.argmax(gLarge)
        lmin = self.AbsLam[largestIDX]

        # Scaling function
        self.h = sp.diags(self.ker.h(self.AbsLam, lmin))

        '''CONSTANTS'''
        self.Cg = np.sum(self.ker.g(self.AbsLam)**2/np.abs(Lam))

    def wavelet(self, J=None, n=None):
        '''
        Returns the graph wavelet of given scale and localized at a given node.
        If n=None, then each localization will be returned (column vectors)
        If J=None, then each scale will be returned
        Otherwise the J-th scale is returned
        '''

        # Evaluate g at this scale and diagonalize, then ->
        scaling_func = self.ker.g(self.AbsLam, s=2**self.scales[J])
        g = sp.diags(scaling_func)

        # Calculate Wavelets of this scale for each vertex localization
        if n is None:
            return self.U@g@self.U.T.conj()
        else:
            return self.U@g@self.U.T.conj()[:,n]
        
    def transformation(self):
        '''Effectively same as SGWT.wavelet, except it returns a matrix for all coefficients to be calculated.
        When multipled, all cofficents are determined. The first n rows are for the smallest scale, localized at each node.
        The blocks repeat for each scale.
        '''

        # SCaling Functions in Vertex-Domain, then ->
        return np.vstack([
            self.U@sp.diags(self.ker.g(self.AbsLam, s=2**i)) for i in self.scales
        ])@self.U.T.conj()  # Post-Multiply the GFT conversion!
    
    def psuedoinv(self):
        '''Returns the psuedo inverse of the transformation'''
        T = self.transformation()

        # Adjoint
        Th = T.conj().T

        return np.linalg.inv(Th@T)@Th
    
    def scalingvec(self, n):
        '''Returns the scaling function localized at node n. None returns all'''

        if n is None:
            return self.U@self.h@self.U.T.conj()
        else:
            return self.U@self.h@self.U.T.conj()[:,n]

    