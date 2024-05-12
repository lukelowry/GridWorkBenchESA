

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.axes import Axes
import geopandas as gpd
import shapely.vectorized

from numpy import ceil, sqrt, array, linspace, meshgrid, where, nan, pi, vstack, log
from cmath import polar

from scipy.stats import gaussian_kde
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from os.path import dirname, abspath, sep

def formatPlot(ax: Axes, plotarea='gainsboro', spineColor='black', xlabel='Damping (%)', ylabel="Frequency Hz",title='Eigen Values / Modes', xlim=None, ylim=None):
    ax.set_facecolor(plotarea)
    ax.grid(zorder=0)
    ax.tick_params(color=spineColor, labelcolor=spineColor)
    for spine in ax.spines.values():
        spine.set_edgecolor(spineColor)

    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    ax.vlines([0], ax.get_ylim()[0],ax.get_ylim()[1], zorder=1, colors='r')
    ax.hlines([0], ax.get_xlim()[0],ax.get_xlim()[1], zorder=1, colors='r')
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

def plot_eigs(evals, plotFunc=None, figsize=(18,9)):
    '''
    plotFunc is a function that should return true or false
    indicating if that eigenvalue should be plotted
    '''
    hz = lambda e: e.imag/2/pi
    damping = lambda e: 0 if e==0 else -100*e.real/polar(e)[0]

    if plotFunc is None:
        eigvals = [e for e in evals]
    else:
        eigvals = [e for e in evals if plotFunc(e)]

    alpha = [e.real for e in eigvals]
    damp = [damping(e) for e in eigvals]
    freq = [hz(o) for o in eigvals]

    # Colorings
    xy = vstack([freq,alpha])
    density = log(gaussian_kde(xy)(xy))

    # Plotting
    fig, ax = plt.subplots(1,2, figsize=figsize, facecolor='linen')
    ax[0].scatter(alpha, freq, c =  density, zorder=2)
    ax[1].scatter(damp, freq, c =  density, zorder=2)
    formatPlot(ax[0], xlabel='Alpha Decay')
    formatPlot(ax[1], xlabel='Damping (%)')

    return ax

def scatter_map(values, long, lat, shape='Texas', ax=None, title='Texas Contour', interp=300, cmap='rocket', norm=None, highlight=None, hlMarker='go', radians=False, method='nearest'):
    '''Plot Spatial data with a country or state border
    
    '
    cmap:
        Good Cmaps: Rocket, Twilight

    interpolator:
        - 'linear' or 'nearest'

    shape:
        - 'Texas'
        - 'US'
    '''

    cmap = plt.colormaps[cmap] 

    #Base Figure
    if ax is None:
        fig, ax = plt.subplots()

    # Plot Text
    ax.set_title(title)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel('Latitude')

    # Data used to Interpolate
    x = array(long)
    y = array(lat)
    z = array(values)

    # Post-Interpolation Input Values to Plot
    cartcoord = list(zip(x, y))
    X = linspace(min(x), max(x), interp)
    Y = linspace(min(y), max(y), interp)
    X, Y = meshgrid(X, Y)

    # Interpolation Function
    if method=='linear':
        interp = LinearNDInterpolator(cartcoord, z)
    elif method=='nearest':
        interp = NearestNDInterpolator(cartcoord, z)
    Z0 = interp(X, Y)

    # Use Bound if Givven
    if type(norm) is tuple:
        norm = Normalize(vmin=norm[0], vmax=norm[1])
    elif radians:
        norm = Normalize(vmin=-pi, vmax=pi)

    # Texas Border Over Data - And Mask
    if shape is not None:

        # Load
        _DIRNAME = dirname(abspath(__file__))
        shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'Shape.shp'
        shapeobj = gpd.read_file(shapepath)

        # Mask
        mask = shapely.vectorized.contains(shapeobj.dissolve().geometry.item(), X, Y)

        # Plot Heatmap with Mask
        im = ax.pcolormesh(X, Y, where(mask, Z0, nan), cmap=cmap, norm=norm)

        # Plot
        shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')

    else:
        im = ax.pcolormesh(X, Y, Z0, cmap=cmap, norm=norm)

    cb = plt.gcf().colorbar(im, ax=ax)

    # Color Bar
    if radians:
        cb.set_ticks(ticks=[-pi,-pi/2,0,pi/2,pi], labels=[r'$-\pi$',r'$-\pi/2$',r'$0$',r'$\pi/2$',r'$\pi$'])
        

    # Highlight a Specific Point
    if highlight is not None:
        ax.plot(x[highlight], y[highlight],hlMarker) 