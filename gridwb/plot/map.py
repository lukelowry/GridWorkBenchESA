
from os.path import dirname, abspath, sep
import geopandas as gpd


def border(shape='Texas', ax=None):
    '''Plot Spatial data with a country or state border'''
            
    # Load
    _DIRNAME = dirname(abspath(__file__))
    shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'Shape.shp'
    shapeobj = gpd.read_file(shapepath)

    # Mask
    #mask = shapely.vectorized.contains(shapeobj.dissolve().geometry.item(), X, Y)
    #im = ax.pcolormesh(X, Y, where(mask, Z0, nan), cmap=cmap, norm=norm)

    # Plot
    shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')