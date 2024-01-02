
# Class Abstraction
from abc import ABC, abstractmethod

# Plotting
from warnings import filterwarnings

from matplotlib.collections import LineCollection
import numpy as np
filterwarnings( "ignore", module = "matplotlib\..*" )

from matplotlib import pyplot as plt
from matplotlib import lines as lines
from matplotlib.axes        import Axes
from matplotlib.animation   import FuncAnimation
from matplotlib.style       import use
from matplotlib.colors      import Normalize

# Utils
from pandas import DataFrame
from networkx import *

# TODO I think large plot delay is mosly due to df beign passed as arg
# pass a reference like C?

class Plot(ABC):

    def __init__(self, 
                 data: tuple[DataFrame, DataFrame] = (None, None),
                 colorkey: str = None,
                 framkey: str = None,
                 cmap: str = 'cool',
                 xlim: tuple[float, float] = None,
                 ylim: tuple[float, float] = None,
                 xlabel: str = "X-Axis",
                 ylabel: str = "Y-Axis",
                 dark: bool = True,
                 **kwargs) -> None:

        self.metaMaster = data[0] 
        self.dfMaster   = data[1]
        self.df         = data[1]

        self.framekey   = framkey
        self.colorkey   = colorkey
        self.cmap       = cmap
        self.xlim       = xlim
        self.ylim       = ylim
        self.xlabel     = xlabel
        self.ylabel     = ylabel
        self.title = "Plot"

        # Color Mapping
        cmap  = plt.get_cmap(self.cmap)
        cVals = self.metaMaster[self.colorkey]
        match self.colorkey:
            case 'Contingency':
                cValsUnique = cVals.unique().tolist()
                norm = lambda x: cValsUnique.index(x)/len(cValsUnique)
            case _:
                norm = Normalize(vmin=min(cVals), vmax=max(cVals))

        # Add Color to Meta
        self.metaMaster['Color'] = [cmap(norm(v)) for v in cVals]
        self.cmap = cmap
        self.norm = norm

        # 'Frame' Versions - Identical for a plot
        self.meta  = self.metaMaster
        self.df    = self.dfMaster

        # Units (if more than 1, delimeted string)
        self.units = ",".join(self.metaMaster["Metric"].unique())

        # Theme
        textColor = 'black'
        if dark:
            use('dark_background')
            textColor = 'white'

        # Default Styles
        plt.rc('axes', grid=True, labelsize=10, labelcolor=textColor, titlecolor=textColor)
        plt.rc('grid', color='xkcd:charcoal')
        plt.rc('lines', linewidth=1)

    @abstractmethod
    def plot(self, ax: Axes) -> Axes:

        if ax is None:
            fig, ax = plt.subplots()
        
        # Axis Numeric Limits
        ax.set_xlim(self.xlim,auto=self.xlim is None)
        ax.set_ylim(self.ylim,auto=self.ylim is None)

        # Axis Titles
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)

        # Title - Will Be Overwritten in an Animation
        ax.set_title(self.title)

        return ax

    def animate(self, frameKey):

        # Interactive Animation Settings (Jupyer or IPython)
        plt.rcParams["animation.html"] = "jshtml"
        plt.rcParams['figure.dpi'] = 100
        plt.ioff()

        #ax: Axes
        ax: Axes
        fig, ax = plt.subplots()

        m = self.metaMaster
        frameVals = m[frameKey].unique()
        frameCount = len(frameVals)

        def frames(i):

            ax.clear()

            # Get Data for this frame
            frameVal = frameVals[i]
            self.meta = m[m[frameKey] == frameVal]
            self.df = self.dfMaster[self.meta.index]

            # Frame Value as Title, Round if Num
            try:
                v = '{:.2f}'.format(frameVal)
            except:
                v = frameVal
            fig.suptitle(f"{frameKey}: {v}")

            # Plot
            return self.plot(ax)

        #Make Animation
        anim = FuncAnimation(fig, frames, frameCount, interval=1000)

        return anim

class TSPlot(Plot):

    def plot(self, ax: Axes=None):

        ax = super().plot(ax)

        # Plot - Have more control with mpl
        for col in self.df:
            ax.plot(
                self.df[col],
                color=self.meta.loc[col, 'Color']
            )
        
        # Plot Text
        self.title  = "Transient Simulations"
        self.xlabel = "Time (s)"
        self.ylabel = self.units
        
        # Standard Formats
        return ax

class ContingencyImpact(Plot):

    def plot(self, ax: Axes=None):

        # Plot Text
        self.title  = "Contingency Impact"
        self.xlabel = "Pre-CTG "  + self.units
        self.ylabel = "Post-CTG " + self.units
        
        # Standard Formats
        ax = super().plot(ax)

        # Scatter Form
        m = self.meta
        d = self.df.T

         # 'No Change' Line
        line = lines.Line2D([0, 2], [0, 2], color='red')
        ax.add_line(line)


        # Lines Connecting Scatter Indicating Objects
        for o in m['ID-A'].unique():
            objmeta = m[m['ID-A']==o].index
            #print(m[m['ID-A']==o].sort_values(by=[self.colorkey]))
            objPoints = d.loc[objmeta]

            x = objPoints["Reference"].tolist()
            y = objPoints["Value"].tolist()
            colors = m.loc[objmeta, 'Color'].tolist()[1:]
            segments = []

            i = 0
            for x1, x2, y1,y2 in zip(x, x[1:], y, y[1:]):
                segments.append([(x1, y1), (x2, y2)])
                i += 1  

            lc = LineCollection(segments,color=colors, linewidths=2)
            ax.add_collection(lc)

        # Plot Scatter
        '''
        ax.scatter(
            x=d['Reference'],
            y=d['Value'],
            c=self.meta['Color'],
            zorder=3
        )
        '''

        return 



class NetworkPlot(Plot):

    def plot(self, ax):

         #Temp Map graph to Substation Here
        Gx: Graph = relabel_nodes(
            self,
            {bus: self.sub(bus) for bus in self}
        )

        # Remove merged lines (useful in future for 'clusters' or thev eq)
        Gx.remove_edges_from(selfloop_edges(Gx))
        
        # Node Visual Properties
        pos = {n: self.subPos(n) for n in Gx}
        node_colors = {n: 'blue' for n in Gx}
        node_sizes = {n: 40 for n in Gx}

        # Set Indicated Node to Mapped Indication Color
        for bus, color in self._indicateMap.items():
            sub = self.sub(bus)
            node_colors[sub] = color
            node_sizes[sub] = 120
        
        # Draw Nodes, labels, edges
        draw_networkx_nodes(Gx, pos, edgecolors='k', ax=ax,
                            node_color=list(node_colors.values()),
                            node_size=list(node_sizes.values()))
        draw_networkx_edges(Gx, pos, ax=ax)