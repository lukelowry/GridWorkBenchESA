
from os.path import dirname, abspath, sep
import geopandas as gpd


def border(ax, shape='Texas'):
    '''Plot Shape data (Country, State, Etc.) on a Matplotlib Axis'''
            
    # Load
    _DIRNAME = dirname(abspath(__file__))
    shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'Shape.shp'
    shapeobj = gpd.read_file(shapepath)

    # Mask
    #mask = shapely.vectorized.contains(shapeobj.dissolve().geometry.item(), X, Y)
    #im = ax.pcolormesh(X, Y, where(mask, Z0, nan), cmap=cmap, norm=norm)

    # Plot
    shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')