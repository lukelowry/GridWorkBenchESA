
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from .generic import Plot
from pandas.api.types import is_numeric_dtype


"""
Input: (meta, data)

:meta - DF of attributes of each time series
:data - DF of time series (each column is time series)

"""
class TimeSeries(Plot):

    # Time Series is only one with custom animate
    def animate(self, frameKey):
        
        # Interactive Animation Settings (Jupyer or IPython)
        plt.rcParams["animation.html"] = "jshtml"
        plt.rcParams["figure.dpi"] = 100
        plt.ioff()

        # ax: Axes
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
                v = "{:.2f}".format(frameVal)
            except:
                v = frameVal
            fig.suptitle(f"{frameKey}: {v}")

            # Plot
            return self.plot(ax)

        # Make Animation
        anim = FuncAnimation(fig, frames, frameCount, interval=1000)

        return anim

    def plot(self, ax = None):

        # Plot Text
        self.title = "Transient Simulations"
        self.xlabel = "Time (s)"
        self.ylabel = self.meta['Metric'].values[0]

        ax = super().plot(ax)

        norm = Normalize(
            vmin=self.meta[self.colorkey].min(),
            vmax=self.meta[self.colorkey].max()
        )

        c=[self.cmap(norm(v)) for v in self.meta[self.colorkey]]
        self.df.plot(legend=False, color=c,ax=ax)
        

        

        # Standard Formats
        return ax