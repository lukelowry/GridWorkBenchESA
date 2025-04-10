
'''

Plots geared toward oscillation metrics. 

From old GWB. Probably remove.

'''

# MISC
from os.path import dirname, abspath, sep
from matplotlib.pylab import Axes
from numpy import array, linspace, meshgrid, where, nan, pi, vstack, log
from numpy import histogram, diff, arange
from scipy.stats import gaussian_kde
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator, CloughTocher2DInterpolator
import geopandas as gpd
import shapely.vectorized
from cmath import polar

# MPL
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

# GWB
from .generic import formatPlot

def freqhist(evals, bins=60, rng=(0,2), tstep=0.1):
    '''Plot the frequency distribution in Hz of a set of Eigen Values'''

    # Formatting
    fig, ax = plt.subplots(figsize=(18,5))
    formatPlot(ax, xlim=rng, xlabel='Frequency (Hz)', ylabel='Count', title='Frequency Occurance Histogram', tstep=tstep)

    # Data
    freqs = evals.imag/2/pi
    freqs = freqs[(freqs < rng[1]) & (freqs>rng[0])]
    hist, bin_edges = histogram(freqs, bins=bins)

    # Plot
    ax.bar(bin_edges[:-1], hist, width=diff(bin_edges), edgecolor='black', align='edge', zorder=4)

def plot_eigs(evals, plotFunc=None, figsize=(18,9)):
    '''
    Plots the complex eigen values in two panes: standard and damped format.
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
    fig, ax = plt.subplots(1,2, figsize=figsize)
    ax[0].scatter(alpha, freq, c =  density, zorder=2)
    ax[1].scatter(damp, freq, c =  density, zorder=2)
    formatPlot(ax[0], xlabel='Exponential Decay', ylabel='Angular Frequnecy', title='Laplace Domain')
    formatPlot(ax[1], xlabel='Damping (%)', ylabel='Angular Frequnecy', title='Damping Domain')

    return ax

def scatter_map(values, long, lat, shape='Texas', ax:Axes=None, title='Texas Contour', usecbar=True, interp=300, cmap='plasma', norm=None, highlight=None, hlMarker='go', radians=False, method='nearest', extrap=(0,0,0,0)):
    '''Plot Spatial data with a country or state border
    
    '
    cmap:
        Good Cmaps: Rocket, Twilight

    interpolator:
        - 'linear' or 'nearest'

    shape:
        - 'Texas'
        - 'US'
    extrap:
        (xleft, xright, ydown, yup) percents to extend
    '''

    cmap = mpl.colormaps[cmap] 

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

    xmin, xmax = min(x), max(x)
    xdist = xmax-xmin
    xmin -= extrap[0]*xdist
    xmax += extrap[1]*xdist

    ymin, ymax = min(y), max(y)
    ydist = ymax-ymin
    ymin -= extrap[2]*ydist
    ymax += extrap[3]*ydist

    X = linspace(xmin, xmax, interp)
    Y = linspace(ymin, ymax, interp)
    X, Y = meshgrid(X, Y)

    # Interpolation Function
    if method=='linear':
        interp = LinearNDInterpolator(cartcoord, z)
    elif method=='nearest':
        interp = NearestNDInterpolator(cartcoord, z)
    elif method=='cl':
        interp = CloughTocher2DInterpolator(cartcoord, z)
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

    if usecbar:
        cb = plt.gcf().colorbar(im, ax=ax)

        # Color Bar
        if radians:
            cb.set_ticks(ticks=[-pi,-pi/2,0,pi/2,pi], labels=[r'$-\pi$',r'$-\pi/2$',r'$0$',r'$\pi/2$',r'$\pi$'])
            

    # Highlight a Specific Point
    if highlight is not None:
        ax.plot(x[highlight], y[highlight],hlMarker) 

