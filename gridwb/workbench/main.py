# TODO I want to de-merge this from ESA.
# TODO implement tools to make synthetic grids (or just add components efficiently)
# Orrrr maybe don't, I remeber the reason I integrated it in the first place
# It allows for a way better dessign pattern - or atleast that was the idea

# Imports
import numpy as np
from pandas import DataFrame
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
        return self.dm.get_df(arg)

    '''
    Disabled Feature as Instance Creation is not Stable
    def __call__(self, arg):
        return self.dm.get_inst(arg)
    '''

    # TODO function that prints out number and type of datasets
    def summary(self):
        pass

    # TODO move to datawiz
    def joint(self, type1: GObject, type2, key='BusNum'):
        '''Merges Two Component Sets (Used to map data)'''
        return self[type1].merge(self[type2], on=key)

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

    # TODO remove or make this better ffs I don't want to pass the type.
    # Dataframe subclass!
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

    def ybus(self):
        '''Returns the full y-bus as a dense Numpy Matrix'''
        return self.io.esa.get_ybus(True)

    def incidence(self):
        '''Returns the Incidence Matrix (In BusNum Order)'''
        busmap = {b: i for i, b in enumerate(self.all[Bus]['BusNum'])}
        linedata = self.all[Branch][['BusNum', 'BusNum:1']].to_records()
        ft = [(busmap[FB], busmap[TB])for i, FB, TB in linedata]

        return arc_incidence(ft)
    
    def ybranch(self):
        '''Return Admittance of Lines in Complex Form'''

        branches = self.all[Branch]
        R = branches['LineR:2']
        X = branches['LineX:2']
        Z = R + 1j*X 
        Y = 1/Z

        return Y
    