# TODO I want to de-merge this from ESA.
# TODO implement tools to make synthetic grids (or just add components efficiently)
# Orrrr maybe don't, I remeber the reason I integrated it in the first place
# It allows for a way better dessign pattern - or atleast that was the idea

# Imports
import numpy as np
from pandas import DataFrame, Series
from scipy.sparse import lil_matrix, diags

from .grid.components import *
from .apps import GIC, Statics
from .grid.common import arc_incidence, InjectionVector
from .core import *

class GridWorkBench:
    def __init__(self, fname=None):

        self.context = Context(fname)
        self.io = self.context.getIO()

        # Temp disable - my IO getter is more reliable
        # NOTE disable statics until it knowns to disable DM
        #self.dm = self.context.getDataMaintainer()

        # Applications
        #self.dyn = Dynamics(self.context)
        self.statics = Statics(self.context)
        self.gic = GIC(self.context)

    def __getitem__(self, arg):
        '''Local Indexing of retrieval'''
        return self.io[arg]

    def save(self):
        '''Save Open the Power World File'''
        self.io.save()

    def pflow(self, getvolts=True) -> DataFrame | None:
        """Solve Power Flow in external system.
        By default bus voltages will be returned.

        :param getvolts: flag to indicate the voltages should be returned after power flow, 
            defaults to True
        :type getvolts: bool, optional
        :return: Dataframe of bus number and voltage if requested
        :rtype: DataFrame or None
        """

        # Solve Power Flow through External Tool
        self.io.pflow()

        # Request Voltages if needed
        if getvolts:
            vpu = self.io.get_quick(Bus, 'BusPUVolt')
            rad = self.io.get_quick(Bus, 'BusAngle')['BusAngle']*np.pi/180

            vpu['BusPUVolt'] *= np.exp(1j*rad)
            vpu.columns = ['Bus Number', 'Voltage']
            return vpu

    def busmap(self):
        '''
        Returns a Pandas Series indexed by BusNum to the positional value of each bus
        in matricies like the Y-Bus, Incidence Matrix, Etc.

        Example usage:
        branches['BusNum'].map(busmap)
        '''
        busNums = self.io[Bus]
        return Series(busNums.index, busNums['BusNum'])
    
    def lines(self):
        '''
        Retrieves and returns all transmission line data. Convenience function.
        '''

        # Get Data
        branches = self.io[Branch, :]

        # Return requested Records
        return branches.loc[branches['BranchDeviceType']=='Line']
    
    def xfmrs(self):
        '''
        Retrieves and returns all transformer data. Convenience function.
        '''

        # Get Data
        branches = self.io[Branch, :]

        # Return requested Records
        return branches.loc[ branches['BranchDeviceType']=='Transformer']
    
    def incidence(self):
        '''
        Returns:
        Sparse Incidence Matrix of the branch network of the grid.

        Dimensions: (Number of Branches)x(Number of Buses)
        '''

        # Retrieve
        branches = self.io[Branch,['BusNum', 'BusNum:1']]

        # Column Positions 
        bmap = self.busmap()
        fromBus = branches['BusNum'].map(bmap).to_numpy()
        toBus = branches['BusNum:1'].map(bmap).to_numpy()

        # Sparse Arc-Incidence Matrix
        nbranches = len(branches)
        A = lil_matrix((nbranches,len(bmap)))
        A[np.arange(nbranches), fromBus] = -1
        A[np.arange(nbranches), toBus] = 1

        return A
    
    def ybranch(self):
        '''Return Admittance of Lines in Complex Form'''

        branches = self[Branch, ['LineR:2', 'LineX:2']]
        R = branches['LineR:2']
        X = branches['LineX:2']
        Z = R + 1j*X 
        Y = 1/Z

        return Y
    
    def ybus(self, dense=False):
        '''Returns the sparse Y-Bus Matrix'''
        return self.io.esa.get_ybus(dense)
    
    def buscoords(self):
        '''Retrive dataframe of bus latitude and longitude coordinates based on substation data'''
        A, S = self.io[Bus, 'SubNum'],  self.io[Substation, ['Longitude', 'Latitude']]
        return A.merge(S, on='SubNum') 
    
    def length_laplacian(self):
        '''
        Returns a distance-based Laplacian that approximates the second spatial derivative.
        Transformer lengths are assumed to be 1 meter.
        '''

        # Get branch elgnths
        ell = self.lengths()

        # Branch Weight (km^-2)
        W = diags(1/ell**2)

        # Line Only Incidence
        A = self.incidence()

        # Laplacian
        return A.T@W@A
    
    def lengths(self):
        '''
        Returns lengths of each branch in kilometers.
        Transformer lengths are assumed to be 1 meter.
        '''

        # This is distance in kilometers
        field = 'LineLengthByParameters:2'
        ell = self.io[Branch,field][field]

        # Assume XFMR 1 meter long
        ell.loc[ell==0] = 0.001

        return ell

    
    def lineprop(self):
        '''Returns approximation of propagation constants for each branch'''

        branches = self.io[Branch,['LineR','LineG', 'LineC', 'LineX']]

        # Length (Set Xfmr to 1 meter)
        ell = self.lengths()

        # Series Parameters
        R = branches['LineR']
        X = branches['LineX']
        Z = R + 1j*X

        # Shunt Parameters
        G = branches['LineG']
        B = branches['LineC']
        Y = G + 1j*B


        # Correct Zero-Values
        Z[Z==0] = 0.000446+ 0.002878j
        Y[Y==0] = 0.000463j

        # By Length
        Y /= ell 
        Z /= ell

        # Propagation Parameter
        return  np.sqrt(Y*Z)
    

    def proplap(self):
        '''
        Returns the propagation laplacian, which is a manifold representation
        of the telgeraphers equations near synchronous frequnecy
        Branch Weights are (1/length^2 - gamma^2)
        '''

        ell = self.lengths()
        GAM = self.lineprop()

        # Branch Weight m^-2
        W = diags(1/ell**2 - GAM**2)/1e6 

        # Line Only Incidence
        A = self.incidence()

        # Laplacian
        return A.T@W@A
    

