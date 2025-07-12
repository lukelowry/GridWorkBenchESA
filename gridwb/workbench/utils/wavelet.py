from typing import Any
import numpy as np
from functools import partial
import scipy.sparse as sp
from numpy import pi
from pywt import cwt

from numpy import block, diag, real, imag
from scipy.linalg import schur, pinv
from abc import ABC, abstractmethod
from scipy.sparse import csc_matrix
from scipy.linalg import pinv

from gridwb.workbench.utils.cheby import Chebyshev, Recurrence



def takagi(M):
   n = M.shape[0]
   D, P = schur(block([[-real(M),imag(M)],[imag(M),real(M)]]))
   pos = diag(D) > 0
   Sigma = diag(D[pos,pos])
   # Note: The arithmetic below is technically not necessary
   U = P[n:,pos] + 1j*P[:n,pos]
   return U, Sigma.diagonal()

def dirac(n, cnt=2000):
    '''
    Description:
        Helper Function to produce a nx1 array
    '''
    d = np.zeros(cnt)
    d[n] = 1
    return d

'''
TIME - DOMAIN
'''

def fcwt(signals, widths, wavelet, dt):
    '''
    Description:
        pywavelet helper function for multi-signals
    Parameters:
        signals: (n-th signal, time-index)
        widths: scales corresponding to frequencies
        wavelet: string name of wavelet to use
        dt: average delta time of samples
    Returns:
        COEFFS: (Frequnecy x nth-signal x time-index)
        freqs: list of frequnecies
    '''

    nfreq = widths.shape[0]
    nsignals, ntime = signals.shape
    COEFFS = np.empty((nfreq, nsignals, ntime), dtype=complex)

    for i, signal in enumerate(signals):
        cwtmatr, freqs = cwt(signal, widths, wavelet, dt)
        COEFFS[:, i] = cwtmatr

    return COEFFS, freqs

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


'''
 Eigen value based SGWT
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
    
class EigenSGWT:
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
        S = (fhat.T*self.h).T

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
Chebyshev based SGWT
'''

class ChebySGWT:

    def __init__(self, L, nscales=10, K=500, pow=2, srng=(2,5)) -> None:

        # Graph Laplacian
        self.L = L

        # Set Power of the wavelet kernel
        self.pow = pow

        # Number of discrete scales
        self.nscales = nscales
        self.scales = self.__makescales(nscales, srng)

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

            
    def __allocatewav(self, f):
        '''
        Determines memory to allocate
        '''
        if f.ndim >= 2:
            nseries = f.shape[1]
            return np.zeros((self.nscales, self.nbus, nseries))

        else:
            return np.zeros((self.nscales, self.nbus))

    def __makescales(self, nscales, srng):
        '''
        Determines scales based on range and count
        '''
        return np.logspace(*srng, nscales)
    
    def __kernelcoeff(self, N=None):
        '''
        Determines Chebyshev expansion of kernel for each scale
        '''

        # N is the number of Chebyshev sample/anchor nodes
        if N is None:
            N = 2*self.K

        # Calculates Coefficients for each scaled kerenel 
        # Each col Order (k) and each row spatial scale
        Cs = np.array([
            self.T.coeff(
                partial(self.g,s=s), 
                self.K, N
            ) 
            for s in self.scales
        ])

        # NOTE in the summation process, we divide the first-order coefficient by 2.
        # We pre-compute that here so we can standardize in integration
        Cs[:,0] /= 2

        return Cs


    def g(self, x,s=1):
        return (2*s*x/(1+(s*x)**2))**self.pow

    def Rmatrix(self):

        # Recurrance matrix
        # NOTE R matrix is technically without the 2, 
        # but it is easier to include it here
        I = np.eye(self.nbus)
        a = self.emax/2
        R = (self.L-a*I)/a

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

        # Manages Recurrance formula  (Pass extra two here, faster than in loop)
        recurr = Recurrence(u0, u1, self.K, 2*self.R)

        # Allocate Wavelet Coeff Storage
        WAVS = self.__allocatewav(f)

        # Looping Through Cheby Orders
        for Cp, u in zip(self.Cs.T, recurr): 

            # For each scale
            for j, c in enumerate(Cp):
                WAVS[j] += c*u

        return WAVS

'''
Vector Fitted based SGWT
'''

class WaveletFitting:
    '''A Helper class that determines the residues and poles of a discrete
    set of frequnecy-domain wavelet kernels'''

    def __init__(self, domain, samples, initial_poles):
        '''
        Parameters:
            domain: (log spaced) sample points of signal
            samples: (on domain) kernel values, each col is different scale
            initial poles: (log spaced) initial pole locations
        '''

        # location, samples of VF, and initial poles
        self.x = domain
        self.G = samples # scale x lambda
        self.Q0 = initial_poles

    def eval_pole_matrix(self, Q, x):
        '''
        Description:
            Evaluates the 'pole matrix' over some domain x given poles Q
        Parameters:
            Q: Poles array (npoles x 1)
            x: domain to evaluate (nsamp x 1)
        Returns:
            Pole Matrix: shape is  (nsamps x npoles)
        '''
        return 1/(x + Q.T)
    
    def calc_residues(self, V, G):
        '''
        Description:
            Solves least square problem for residues for given set of poles
        Parameters:
            V: 'pole matrix' (use eval_pole_matrix)
            G: function being approximated
        Returns:
            Residue Matrix: shape is  (npoles x nscales)
        '''
        # Solve Equation: V@R = G
        return pinv(V)@G
    
    def fit(self):
        '''
        Description:
            Performs VF procedure on signal G.
        Returns:
            R, Q: shape is  (npoles x nscales), (npoles x 1)
        '''
        
        # (samples x poles)
        self.V = self.eval_pole_matrix(self.Q0, self.x)

        # (pole x scale)
        R = self.calc_residues(self.V, self.G)

        # TODO pole relalocation step here and iterative
        Q = self.Q0

        return R, Q
    
class KernelDesign(AbstractKernel):
    ''' 
    Class holding the spectral form of the wavelet function
    '''

    def __init__(
            self, 
            spectrum_range = (1e-7, 1e2),
            scale_range    = (1e-2, 1e5),
            pole_min       = 1e-5,
            nscales        = 10, 
            npoles         = 10, 
            nsamples       = 300,
            order          = 2 
        ):

        # Scales, Domain, and initial poles
        s  = self.logsamp(*scale_range   , nscales )   
        x  = self.logsamp(*spectrum_range, nsamples)  
        Q0 = self.logsamp(pole_min,spectrum_range[1], npoles  )  

        # Sample the function for all scales
        # (Scales x lambda)
        G = self.g(x*s.T, order=order)

        wf = WaveletFitting(
            domain        = x, 
            samples       = G, 
            initial_poles = Q0
        )

        # Fit and return pole and residues of apporimation
        R, Q = wf.fit()

        # Calculate the interval of scales on log scale
        self.ds = np.log(s[1]/s[0])[0]

        # Assign Poles, residues, scales
        self.wf  = wf
        self.__q = Q
        self.__r = R
        self.__s = s
        self.nscales  = nscales 
        self.npoles   = npoles
        self.nsamples = nsamples

        # Useful for debugging
        self.x = x
        self.G = G
        
    def logsamp(self, start, end, N=5):
        '''
        Description:
            Helper sampling function for log scales
        Parameters:
            start: first value
            end: last value
            N: number of log-spaced values between start and end
        Returns:
            Samples array: shape is  (N x 1)
        '''
        return np.geomspace(start, [end],N)
    
    def g(self, x, order=1):
        '''
        Description:
            Default kernel function evaluator
        Parameters:
            x: domain to evaluate (array)
            order: higher order -> narrower bandwidth
        Returns:
            g(x): same shape as x
        '''
        f = 2*x/(1+x**2)
        return f**order
    
    def h(self, x):
        '''
        Description:
            The scaling kerenl h(x) evaluating the 'DC-like' spectrum
        Parameters:
            x: domain to evaluate (array)
        Returns:
           h(x): same shape as x
        '''
        f = 1/(1+x**2)
        return f
    
    def get_approx(self):

        V, R = self.wf.V, self.R

        return V@R

    @property
    def R(self):
        '''Residue Matrix where each column is a scale
        and each row corresponds to a pole '''
        return self.__r

    @property
    def Q(self):
        '''Vector of Poles'''
        return self.__q
    
    @property
    def scales(self):
        '''Vector of Scales'''
        return self.__s
    
    def write(self, fname):
        '''
        Description:
            Writes poles & residue model to npz file format.
            Post-fix .npz not needed, just write desired name.
        Parameters:
            fname: Filename/directory if needed
        Returns:
            None
        '''
        np.savez(f'{fname}.npz', R=self.R, Q=self.Q, S=self.scales)

# NOTE: Fast SGWT w/ SUITESPARSE is written in seperate py file
# due to version incompatibility. You cannot run the below with 
# the version of python that Grid WB uses for scikit-sparse
# from sksparse.cholmod import cholesky, analyze

class FastSGWT:
    '''
    A rational-approximation approach to the SGWT
    '''

    def __init__(self, L: csc_matrix, kern: str):

        # Sparse Laplacian
        self.L = L

        # Load Residues, Poles, Scales
        npzfile = np.load(f'{kern}.npz')
        self.R, self.Q, self.scales = npzfile['R'], npzfile['Q'], npzfile['S']
        npzfile.close()

        # Wavelet Constant (scalar mult)
        ds = np.log(self.scales[1]/self.scales[0])[0]
        self.C = 1/ds

        # Number of scales
        self.nscales = len(self.scales)

        # Pre-Factor (Symbolic)
        # BUG NOTE cannot run sadly
        #self.factor = analyze(L)

    def allocate(self, f):
        return np.zeros((*f.shape, self.nscales))

    def __call__(self, f):
        '''
        Returns:
            W:  Array size (Bus, Time, Scale)
        '''

        
        W = self.allocate(f)
        F = self.factor
        L = self.L

        for q, r in zip(self.Q, self.R):

            F.cholesky_inplace(L, q) 
            W += F(f)[:, :, None]*r   # Almost the entire duration is occupied multiplying here

        return W
    
    def singleton(self, f, n):
        '''
        Returns:
            Coefficients of f localized at n
        '''
        
        F = self.factor
        L = self.L

        # LOCALIZATION VECTOR
        local = np.zeros((L.shape[0], 1))
        local[n] = 1

        # Singleton Matrix
        W = np.zeros((L.shape[0], self.nscales))

        # Compute
        for q, r in zip(self.Q, self.R):

            F.cholesky_inplace(L, q) 
            W += F(local)*r.T  

        return f.T@W 
    
    def inv(self, W):
        # The inverse transformation! (For now, only 1 time point)
        # Input W: Bus x Times x Scales
        
        fact, L = self.factor, self.L
        f = np.zeros((W.shape[0], W.shape[1]))

        for q, r in zip(self.Q, self.R):

            fact.cholesky_inplace(L, q) 
            f += fact(W@r) 

        return f/self.C