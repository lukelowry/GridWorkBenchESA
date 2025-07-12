
import numpy as np


# MISC
from os.path import dirname, abspath, sep
from matplotlib.pylab import Axes
from numpy import array, linspace, meshgrid, where, nan, pi, vstack, log
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator, CloughTocher2DInterpolator
import geopandas as gpd
import shapely.vectorized

# MPL
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

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


def plotwave(W, ax, L1, L2, method='nearest', zero_scale=False, cmap='seismic', mx = None, mn = None):

    if zero_scale:
        norm = (0, np.max(W))
    else:
        norm = (-np.max(W), np.max(W))
    if mx is not None:
        if mn is None:
            norm = (-mx, mx)
        else:
            norm= (mn, mx)

    scatter_map(W, L1, L2,method=method,cmap=cmap, 
                ax=ax, title=f'', norm=norm, usecbar=False,
                extrap=(0.2, 0.1, 0, 0.1)
    )

    ax.set_xticks([],[])  
    ax.set_yticks([],[]) 
    ax.set_axis_off()

def quickwave(W, ax, L1, L2, method='nearest', cmap='seismic', norm=None):

    if norm is None:
        norm = (np.min(W), np.max(W))

    scatter_map(W, L1, L2,method=method,cmap=cmap, 
                ax=ax, title=f'', norm=norm, usecbar=False,
                extrap=(0.2, 0.1, 0, 0.1)
    )

    ax.set_xticks([],[])  
    ax.set_yticks([],[]) 
    ax.set_axis_off()