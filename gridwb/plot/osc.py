
from numpy import ceil, sqrt, array, linspace, meshgrid, where, nan, pi
import matplotlib.pyplot as plt
import seaborn as sns

import geopandas as gpd
import shapely.vectorized
from matplotlib.colors import Normalize

from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from os.path import dirname, abspath, sep

def ploteigs(data, figsize=(16,16), cmap='rocket'):

    # Blank Plot
    dim = int(ceil(sqrt(len(data.columns))))
    fig, axs = plt.subplots(dim, dim, figsize=figsize)

    if dim > 1:
        axs = axs.reshape(-1)

    ax_idx=0

    # Plot Each Bus Heatmap
    for bus in data:

        # Get Axis once plot chosen
        if dim > 1:
            ax = axs[ax_idx]
        else:
            ax = axs

        ploteig(data[[bus]], ax=ax, title=f"Bus {bus} S-Plane Modes")

        # Progress Plot
        ax_idx+=1

        # Stop once reached max plots
        if dim == 1 or ax_idx >= len(axs):
            break

def ploteig(data, ax=None, figsize=(8,8), cmap='rocket', title='Bus Modes', cblabel='Log Magnitude'):

    # Blank Plot
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    # Pivoted Data
    dataf = data.unstack(0).droplevel(0, axis=1)

    # Plot Heat Map 
    sns.heatmap(
        dataf, 
        ax=ax, 
        cmap=cmap,
        cbar_kws={'label': cblabel}
    ) 

    # Plot Details
    ax.set_xlabel(r'$\alpha$ - Exp Growth')
    ax.set_ylabel(r'$j\omega$ (Hz)')
    ax.set_title(title)

    # Ticks
    ax.tick_params(axis='x', labelrotation=90)
    ax.tick_params(axis='y', labelrotation=0)

def scatter_map(values, long, lat, shape='Texas', ax=None, title='Texas Contour', interp=300, cmap='rocket', norm=None, highlight=None, hlMarker='go', radians=False, method='nearest'):
    '''Plot Spatial data with a country or state border
    
    mapping:
        Should be a dataframe with BusNum, Value, Longitude, and Latitude as Columns

    cmap:
        Good Cmaps: Rocket, Twilight

    interpolator:
        - 'linear' or 'nearest'
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
    if norm is not None:
        norm = Normalize(vmin=norm[0], vmax=norm[1])
    elif radians:
        norm = Normalize(vmin=-pi, vmax=pi)

    # Texas Border Over Data - And Mask
    if shape is not None:

        # Load
        _DIRNAME = dirname(abspath(__file__))
        shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'State.shp'
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

def plot_spatial(data, mapping, shape='Texas', ax=None, title='Texas Contour', interp=300, cmap='twilight', norm=None, injbus=None):
    '''Plot Spatial data with a country or state border
    
    mapping:
        Should be a dataframe with BusNum, Value, Longitude, and Latitude as Columns

    cmap:
        Good Cmaps: Rocket, Twilight

    '''

    cmap = plt.colormaps[cmap] 

    # Get & Format
    data.columns.names = ['BusNum']
    data = data.stack()
    data.name = 'Value'
    data_loc = data.to_frame().reset_index().merge(mapping) # Add Bus Pos
    data_loc = data_loc.drop(columns=['BusNum']).set_index(['Alpha', "Hz"])

    #Base Figure
    if ax is None:
        fig, ax = plt.subplots()

    # Plot Text
    ax.set_title(title)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel('Latitude')

    # Data used to Interpolate
    x = array(data_loc['Longitude'].to_list())
    y = array(data_loc['Latitude'].to_list())
    z = array(data_loc['Value'].to_list())

    # Post-Interpolation Input Values to Plot
    cartcoord = list(zip(x, y))
    X = linspace(min(x), max(x), interp)
    Y = linspace(min(y), max(y), interp)
    X, Y = meshgrid(X, Y)

    # Interpolation Function
    interp = LinearNDInterpolator(cartcoord, z)
    Z0 = interp(X, Y)

    # Use Bound if Givven
    if norm is not None:
        norm = Normalize(vmin=norm[0], vmax=norm[1])

    # Texas Border Over Data - And Mask
    if shape is not None:

        # Load
        _DIRNAME = dirname(abspath(__file__))

        if shape=='US':
            shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'tl_2023_us_state.shp'
        else:
            shapepath = _DIRNAME + sep + 'shapes' + sep + shape + sep + 'State.shp'
        shapeobj = gpd.read_file(shapepath)

        # Mask
        mask = shapely.vectorized.contains(shapeobj.dissolve().geometry.item(), X, Y)

        # Plot Heatmap with Mask
        im = ax.pcolormesh(X, Y, where(mask, Z0, nan), cmap=cmap, norm=norm)

        # Plot
        shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')

    else:
        im = ax.pcolormesh(X, Y, Z0, cmap=cmap, norm=norm)

    # Color Bar
    plt.gcf().colorbar(im, ax=ax)

    # Point at Bus if Passed
    if injbus is not None:
        rec = mapping.loc[mapping['BusNum']==injbus]
        long = rec.iloc[0]['Longitude']
        lat = rec.iloc[0]['Latitude']
        ax.plot(long, lat,'ro') 