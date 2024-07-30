
from functools import partial
from os.path import dirname, abspath, sep
import geopandas as gpd
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .generic import darker_hsv_colormap, formatPlot

import numpy as np



def border(ax, shape='Texas'):
    '''Plot Shape data (Country, State, Etc.) on a Matplotlib Axis'''
            
    # Load
    _DIRNAME = dirname(abspath(__file__))
    shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'Shape.shp'
    shapeobj = gpd.read_file(shapepath)
#
    # Plot
    shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')


def plot_lines(ax, lines, ms=50):
    '''Draw Transmission Line Geographically 
    -lines: GWB DataFrame of Line Data
    -coordsX -> nx2 array of x-coords for TO and FROM repsectively
    -coordsY -> nx2 array of y-coords for TO and FROM repsectively
    '''

    cX = lines[['Longitude', 'Longitude:1']].to_numpy()
    cY = lines[['Latitude', 'Latitude:1']].to_numpy()
    
    for i in range(cX.shape[0]):
        ax.plot(cX[i], cY[i], zorder=4, c='k')
        ax.scatter(cX[i], cY[i], c='k', zorder=2, s=ms)


def plot_tiles(ax, gt, include_lines=True, color='grey'):
    '''Plot a GIC Tool Tesselation Grid. Hx and Hy should be calculated with gt.tesselations before calling.'''

    
    if include_lines:
        plot_lines(ax, gt.lines, ms=2)

    X, Y, W = gt.tile_info

    # Plot Horizontal and Vertical Grid Lines
    for x in X: ax.plot([x, x], [Y.min(), Y.max()], c=color, zorder=1)
    for y in Y: ax.plot([X.min(), X.max()], [y, y], c=color, zorder=1)

    # Plot Intersections
    #inter = np.unique(allpnts[:,~np.isnan(allpnts[0])],axis=1)
    #ax.scatter(inter[0], inter[1])

    # Plot Used Tiles
    tile_ids = gt.tile_ids
    refpnt = np.array([[X.min(), Y.min()]]).T
    tiles_unique = np.unique(tile_ids[:,~np.isnan(tile_ids[0])],axis=1)
    tile_pos = tiles_unique*W + refpnt
    for tile in tile_pos.T:
        ax.add_patch(Rectangle((tile[0],tile[1]), W, W, facecolor='red', alpha=0.3))

    plt.axis('scaled')
    formatPlot(ax, xlabel='Longitude ($^\circ$E)', ylabel='Latitude ($^\circ$N)', title='Geographic Line Plot', plotarea='white', grid=False)
 

def plot_compass(ax: Axes, cmap=None, center=(-81.75, 33.2), radius=0.4, card_fs=16, band_width=0.1, band_thick=2, comp_thick=100, dir_perc=0.6):
    '''Plot a compass element on the passed Axes. 
    Inteded for use as a color legend for vector field plots.
    :param ax: Matplotlib Axes object to draw compass onto.
    :type Axes: 
    :param cmap: Matplotlib Colormap of wheel. Ideally Cyclical.
    '''

    # Custom Ideal Cmap
    if cmap is None:
        cmap = darker_hsv_colormap(0.8)

    # Smoothness
    n_points = 400

    theta = np.linspace(-np.pi,np.pi, n_points)
    shift = np.pi/2
    xr = radius*np.cos(-theta+shift)
    yr = radius*np.sin(-theta+shift)
    norm = Normalize(vmin=-np.pi, vmax=np.pi)

    # Fill White circle
    circle = plt.Circle(center, radius, color='w')
    ax.add_patch(circle)

    # Colors in Band
    ax.scatter(center[0] + xr, center[1] + yr, c=cmap(norm(theta)), s=comp_thick)

    # Black Band
    ax.scatter(center[0] + (1+band_width)*xr , center[1] + (1+band_width)*yr, c='k', s=band_thick)
    ax.scatter(center[0] + (1-band_width)*xr , center[1] + (1-band_width)*yr, c='k', s=band_thick)

    # Cardinal Directions
    dir_rad = radius*dir_perc
    text = partial(ax.text, horizontalalignment='center', verticalalignment='center', fontsize=card_fs, fontfamily='monospace')
    text(center[0]  , center[1] + dir_rad ,  'N')
    text(center[0]  , center[1] - dir_rad , 'S')
    text(center[0] + dir_rad  , center[1] , 'E')
    text(center[0] - dir_rad  , center[1] , 'W')

def plot_vecfield(ax: Axes, X, Y, U, V, cmap=None, pivot='mid', scale=70, width=0.001, title=''):
    '''Plot a vectorfield. A scalar mappable is returned for use in a colorbar or other mpl object.'''

    # Custom Ideal Cmap
    if cmap is None:
        cmap = darker_hsv_colormap(0.8)
    
    # Coloring via Angle
    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    colors = np.arctan2(U, V)
    colors[np.isnan(colors)] = 0

    # Plot Arrows
    ax.quiver(X, Y, U, V, colors, norm=norm,pivot=pivot, scale=scale, width=width, cmap=cmap)#, headwidth=2, headlength=3, headaxislength=3)

    # Format
    formatPlot(ax, xlabel='Longitude ($^\circ$E)', ylabel='Latitude ($^\circ$N)', title=title, plotarea='white', grid=False)
    plt.axis('scaled')

    return ScalarMappable(norm, cmap)