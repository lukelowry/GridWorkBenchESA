# TODO I want to de-merge this from ESA.
# TODO implement tools to make synthetic grids (or just add components efficiently)
# Orrrr maybe don't, I remeber the reason I integrated it in the first place
# It allows for a way better dessign pattern - or atleast that was the idea

# Imports
import numpy as np
from pandas import DataFrame, Series
from scipy.sparse import lil_matrix

from .grid.components import *
from .apps import Dynamics, Statics, GIC
from .grid.common import arc_incidence, InjectionVector
from .core import *

class GridWorkBench:
    def __init__(self, fname=None, set=GridSet.Light):

        self.context = Context(fname, set)
        self.io = self.context.getIO()
        self.dm = self.context.getDataMaintainer()

        # Applications
        #self.dyn = Dynamics(self.context)
        self.statics = Statics(self.context)
        self.gic = GIC(self.context)

    def __getitem__(self, arg):
        '''Local Indexing of retrieval'''
        return self.dm.get_df(arg)
    
    def ext(self,**args):
        '''External Data Retrieval'''
        # Same as above but get from PW
        pass

    '''
    Disabled Feature as Instance Creation is not Stable
    def __call__(self, arg):
        return self.dm.get_inst(arg)
    '''

    # TODO function that prints out number and type of datasets
    def summary(self):
        pass

    def commit(self, gclass=None):
        '''Send ALL local data to remote model.
        Not recommended.'''
        if gclass is None:
            self.io.upload(self.all)
        else:
            self.io.upload(self.all[gclass])

    def save(self):
        '''Save Open the Power World File'''
        self.io.save()

    def sudos(self):
        '''DANGEROUS. Uploads all local data to power world and saves the file.'''
        self.commit()
        self.save()

    # TODO Remove - New Indexing method is superior
    def change(self, gtype, data: DataFrame):
        '''
        Inteded for a Quick data update to external model.

        Parameters: 
        gtype: Object Type (GWB Class)
        data: DF of fields with keys and (preferably only) fields to be updated.
        '''
        self.io.upload({
            gtype: data
        })

    def pflow(self, getvolts=True) -> DataFrame | None:
        '''Solve Power Flow in external system.
        By default bus voltages will be returned.'''

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
        
    
    def incidence(self):
        '''
        Returns a SparseIncidence Matrix of the branch network of the grid.
        
        Dimensions: (Number of Branches)x(Number of Buses)
        '''

        branches = self.io[Branch,['BusNum', 'BusNum:1']]
        nbranches = len(branches)

        # Column Positions 
        bmap = self.busmap()
        fromBus = branches['BusNum'].map(bmap).to_numpy()
        toBus = branches['BusNum:1'].map(bmap).to_numpy()

        # Sparse Arc-Incidence Matrix
        A = lil_matrix((nbranches,len(bmap)))
        A[np.arange(nbranches), fromBus] = -1
        A[np.arange(nbranches), toBus] = 1

        return A
    
    def ybranch(self):
        '''Return Admittance of Lines in Complex Form'''

        branches = self.all[Branch]
        R = branches['LineR:2']
        X = branches['LineX:2']
        Z = R + 1j*X 
        Y = 1/Z

        return Y
    
    def ybus(self):
        '''Returns the full y-bus as a dense Numpy Matrix'''
        return self.io.esa.get_ybus(True)
