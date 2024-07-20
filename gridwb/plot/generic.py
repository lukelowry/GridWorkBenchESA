'''

Generic plotting tools.

This is from early GWB, will probably remove.

'''

# Class Abstraction
from numpy import arange, linspace, clip, unique
from warnings import filterwarnings
from abc import ABC, abstractmethod

# Plotting
filterwarnings("ignore", module="matplotlib\..*")
from matplotlib.collections import LineCollection
from matplotlib import pyplot as plt
from matplotlib import lines as lines
from matplotlib.axes import Axes
from matplotlib.animation import FuncAnimation
from matplotlib.style import use
from matplotlib.colors import Normalize, hsv_to_rgb, rgb_to_hsv

# Utils
from pandas import DataFrame
from networkx import *

# I Use this all the time
def formatPlot(ax: Axes, 
               title='Chart Tile',
               xlabel='X Axis Label', 
               ylabel="Y Axis Label", 
               xlim=None, 
               ylim=None, 
               grid=True,
               plotarea='linen', 
               spineColor='black'
               ):
    '''Generic Axes Formatter'''

    
    ax.set_facecolor(plotarea)
    ax.grid(grid, zorder=0)
    ax.set_axisbelow(True)

    ax.tick_params(color=spineColor, labelcolor=spineColor)
    for spine in ax.spines.values():
        spine.set_edgecolor(spineColor)

    if xlim:
        ax.set_xlim(xlim)
        ax.set_xticks(arange(*xlim,0.1))
    if ylim:
        ax.set_ylim(ylim)
    
    # Text
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)


def darker_hsv_colormap(scale_factor=0.5):
    """
    Creates a modified version of the HSV colormap that is darker in shade.
    Parameters:
        scale_factor (float): Factor to scale the value (brightness). Should be between 0 and 1.
                             1 means no change, 0 means complete darkness.
    Returns:
        darker_hsv_cmap: A modified colormap that is a darker version of the original HSV colormap.
    """
    # Create the HSV colormap in RGB
    hsv_cmap = plt.cm.hsv(linspace(0, 1, 256))[:, :3]
    hsv_colors = rgb_to_hsv(hsv_cmap)
    
    # Scale the Value component to make it darker
    hsv_colors[:, 2] *= scale_factor
    hsv_colors[:, 2] = clip(hsv_colors[:, 2], 0, 1)

    darker_rgb_colors = hsv_to_rgb(hsv_colors)
    darker_hsv_cmap = plt.cm.colors.ListedColormap(darker_rgb_colors)
    return darker_hsv_cmap

# Old plotting tools geared toward large dynamic datasets. Save for now.

class Plot(ABC):
    def __init__(
        self,
        data: tuple[DataFrame, DataFrame] = (None, None),
        colorkey: str = None,
        framkey: str = None,
        sizekey=None,
        connectObjs=False,
        xkey: str = None,
        ykey: str = None,
        cmap: str = "cool",
        xlim: tuple[float, float] = None,
        ylim: tuple[float, float] = None,
        xlabel: str = "X-Axis",
        ylabel: str = "Y-Axis",
        dark: bool = True,
        **kwargs,
    ) -> None:
        # Access Args
        self.metaMaster = data[0].copy()
        self.dfMaster = data[1].copy()
        self.framekey = framkey
        self.colorkey = colorkey
        self.sizekey = sizekey
        self.connectObjs = connectObjs
        self.xkey = xkey
        self.ykey = ykey
        self.cmap = cmap
        self.xlim = xlim
        self.ylim = ylim
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = "Plot"

        # Color Mapping
        self.cmap = plt.get_cmap(self.cmap)

        # 'Frame' Versions Copys
        self.meta = self.metaMaster
        self.df = self.dfMaster

        # Flat Index
        self.dataMaster = self.metaMaster.merge(
            self.dfMaster.T, left_index=True, right_index=True
        )
        self.data = self.dataMaster

        # Units (if more than 1, delimeted string)
        # self.units = ",".join(self.metaMaster["Metric"].unique())

        # Theme
        textColor = "black"
        if dark:
            use("dark_background")
            textColor = "white"

        # Default Styles
        plt.rc(
            "axes", grid=True, labelsize=10, labelcolor=textColor, titlecolor=textColor
        )
        plt.rc("grid", color="xkcd:charcoal")
        plt.rc("lines", linewidth=1)

    @abstractmethod
    def plot(self, ax: Axes) -> Axes:
        if ax is None:
            fig, ax = plt.subplots()

        # Axis Numeric Limits
        ax.set_xlim(self.xlim, auto=self.xlim is None)
        ax.set_ylim(self.ylim, auto=self.ylim is None)

        # Axis Titles
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)

        # Title - Will Be Overwritten in an Animation
        ax.set_title(self.title)

        return ax

    def animate(self, framekey):
        # Interactive Animation Settings (Jupyer or IPython)
        plt.rcParams["animation.html"] = "jshtml"
        plt.rcParams["figure.dpi"] = 100
        plt.ioff()

        # ax: Axes
        ax: Axes
        fig, ax = plt.subplots()

        frameVals = self.dataMaster[framekey].unique()
        frameCount = len(frameVals)

        def frames(i):
            ax.clear()

            # Get Data for this frame
            frameVal = frameVals[i]
            self.data = self.dataMaster[self.dataMaster[framekey] == frameVals[i]]

            # Frame Value as Title, Round if Num
            try:
                v = "{:.2f}".format(frameVal)
            except:
                v = frameVal
            fig.suptitle(f"{framekey}: {v}")

            # Plot
            return self.plot(ax)

        # Make Animation
        anim = FuncAnimation(fig, frames, frameCount, interval=1000)

        return anim

class Scatter(Plot):
    cb = None

    def plot(self, ax: Axes = None):
        # Plot Text
        self.title = "Transient vs. Power Flow"
        self.xlabel = self.xkey
        self.ylabel = self.ykey

        # Standard Formats
        ax = super().plot(ax)

        if self.colorkey == "ID-A":
            keys = unique(self.data[self.colorkey])
            idmap = {key: id for id, key in enumerate(keys)}
            self.cdata = self.data[self.colorkey].apply(lambda x: idmap[x])
        else:
            self.cdata = self.data[self.colorkey]

        # Quantile Color Range
        low = self.cdata.quantile(0.05)
        high = self.cdata.quantile(0.95)

        # Plot Scatter
        sc = ax.scatter(
            x=self.data[self.xkey],
            y=self.data[self.ykey],
            c=self.cdata,
            s=self.sizekey,
            cmap=self.cmap,
            norm=Normalize(vmin=low, vmax=high),
            zorder=3,
        )

        if self.connectObjs:
            # Lines Connecting Scatter Indicating Objects
            for o, key in self.data.groupby(["Object", "ID-A"]).size().index:
                isObj = self.data["Object"] == o
                isKey = self.data["ID-A"] == key
                objPoints: DataFrame = self.data[isObj & isKey]

                x = objPoints[self.xkey].tolist()
                y = objPoints[self.ykey].tolist()
                segments = []

                i = 0
                for x1, x2, y1, y2 in zip(x, x[1:], y, y[1:]):
                    segments.append([(x1, y1), (x2, y2)])
                    i += 1

                lc = LineCollection(segments, color="grey", linewidths=1, zorder=2)
                ax.add_collection(lc)

        # Color Bar Once
        if self.cb is None:
            self.cb = plt.colorbar(sc)
            self.cb.set_label(self.colorkey)

        return

