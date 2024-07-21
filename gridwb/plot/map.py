
from os.path import dirname, abspath, sep
import geopandas as gpd


def border(ax, shape='Texas'):
    '''Plot Shape data (Country, State, Etc.) on a Matplotlib Axis'''
            
    # Load
    _DIRNAME = dirname(abspath(__file__))
    shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'Shape.shp'
    shapeobj = gpd.read_file(shapepath)
#
    # Plot
    shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')


def draw_lines(ax, coordsX, coordsY, ms=50):
    '''Draw Transmission Line Geographically 
    -coordsX -> nx2 array of x-coords for TO and FROM repsectively
    -coordsY -> nx2 array of y-coords for TO and FROM repsectively
    '''
    for i in range(coordsX.shape[0]):
        ax.plot(coordsX[i], coordsY[i], zorder=4, c='k')
        ax.scatter(coordsX[i], coordsY[i], c='k', zorder=2, s=ms)