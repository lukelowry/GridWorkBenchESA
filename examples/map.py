"""
Geographic visualization utilities for power system analysis.

Provides plotting functions for transmission lines, tesselation grids,
vector fields, and geographic boundaries using matplotlib and geopandas.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
from numpy.typing import NDArray

from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.colors import Normalize, ListedColormap, rgb_to_hsv, hsv_to_rgb
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pandas import DataFrame

__all__ = [
    'format_plot',
    'darker_hsv_colormap',
    'border',
    'plot_lines',
    'plot_mesh',
    'plot_tiles',
    'plot_vecfield',
]

_SHAPES_DIR = Path(__file__).resolve().parent / 'shapes'


def format_plot(
    ax: Axes,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    grid: bool = True,
    plotarea: str = 'white',
    spine_color: str = 'black',
    xticksep: float | None = None,
    yticksep: float | None = None,
    titlesize: float = 12,
    labelsize: float = 10,
    ticksize: float = 9,
    spine_width: float = 0.8,
) -> None:
    """
    Apply journal-standard formatting to a matplotlib axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to format.
    title : str, optional
        Plot title.
    xlabel, ylabel : str, optional
        Axis labels.
    xlim, ylim : tuple of float, optional
        Axis limits as (min, max).
    grid : bool, default True
        Whether to show grid lines.
    plotarea : str, default 'white'
        Background face color.
    spine_color : str, default 'black'
        Color for axis spines and ticks.
    xticksep, yticksep : float, optional
        Tick separation for x and y axes.
    titlesize : float, default 12
        Font size for the title.
    labelsize : float, default 10
        Font size for axis labels.
    ticksize : float, default 9
        Font size for tick labels.
    spine_width : float, default 0.8
        Line width for axis spines.
    """
    ax.set_facecolor(plotarea)

    if grid:
        ax.grid(True, color='#cccccc', linewidth=0.5, linestyle='-')
        ax.set_axisbelow(True)
    else:
        ax.grid(False)

    ax.tick_params(
        axis='both', color=spine_color, labelcolor=spine_color,
        labelsize=ticksize,
    )
    for spine in ax.spines.values():
        spine.set_edgecolor(spine_color)
        spine.set_linewidth(spine_width)

    if xlim:
        ax.set_xlim(xlim)
        if xticksep:
            ax.set_xticks(np.arange(*xlim, xticksep))
    if ylim:
        ax.set_ylim(ylim)
        if yticksep:
            ax.set_yticks(np.arange(*ylim, yticksep))

    if title is not None:
        ax.set_title(title, fontsize=titlesize)
    if xlabel is not None:
        ax.set_xlabel(xlabel, fontsize=labelsize)
    if ylabel is not None:
        ax.set_ylabel(ylabel, fontsize=labelsize)


def darker_hsv_colormap(scale_factor: float = 0.5) -> ListedColormap:
    """
    Create a darker version of the HSV colormap.

    Parameters
    ----------
    scale_factor : float, default 0.5
        Factor to scale the value (brightness). 1 means no change,
        0 means complete darkness.

    Returns
    -------
    matplotlib.colors.ListedColormap
        A darker version of the HSV colormap.
    """
    hsv_cmap = plt.cm.hsv(np.linspace(0, 1, 256))[:, :3]
    hsv_colors = rgb_to_hsv(hsv_cmap)

    hsv_colors[:, 2] *= scale_factor
    hsv_colors[:, 2] = np.clip(hsv_colors[:, 2], 0, 1)

    darker_rgb = hsv_to_rgb(hsv_colors)
    return ListedColormap(darker_rgb)


def border(ax: Axes, shape: str = 'Texas') -> None:
    """
    Plot a geographic boundary on a matplotlib axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to plot on.
    shape : str, default 'Texas'
        Name of the shape directory under ``examples/shapes/``.
    """
    shapepath = _SHAPES_DIR / shape / 'Shape.shp'
    shapeobj = gpd.read_file(shapepath)
    shapeobj.plot(ax=ax, edgecolor='black', facecolor='none')


def plot_lines(
    ax: Axes,
    lines: DataFrame,
    ms: float = 50,
    lw: float = 1,
    color: str = 'k',
) -> None:
    """
    Draw transmission lines geographically using a single LineCollection.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to plot on.
    lines : pandas.DataFrame
        DataFrame with 'Longitude', 'Longitude:1', 'Latitude', 'Latitude:1'.
    ms : float, default 50
        Marker size for bus endpoints.
    lw : float, default 1
        Line width for transmission lines.
    color : str, default 'k'
        Color for lines and endpoint markers.
    """
    cX = lines[['Longitude', 'Longitude:1']].to_numpy()
    cY = lines[['Latitude', 'Latitude:1']].to_numpy()

    segments = np.stack([
        np.column_stack([cX[:, 0], cY[:, 0]]),
        np.column_stack([cX[:, 1], cY[:, 1]]),
    ], axis=1)

    ax.add_collection(
        LineCollection(segments, colors=color, linewidths=lw, zorder=4)
    )
    ax.scatter(cX.ravel(), cY.ravel(), c=color, s=ms, zorder=2)
    ax.autoscale_view()


def plot_mesh(
    ax: Axes,
    gt,
    include_lines: bool = True,
    color: str = 'grey',
    tcolor: str = 'red',
    talpha: float = 0.3,
) -> None:
    """
    Plot a GIC tool tesselation grid.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to plot on.
    gt : object
        GIC tool object with ``tile_info``, ``tile_ids``, and ``lines``.
    include_lines : bool, default True
        Whether to overlay transmission lines.
    color : str, default 'grey'
        Grid line color.
    tcolor : str, default 'red'
        Tile face color.
    talpha : float, default 0.3
        Tile transparency.
    """
    if include_lines:
        plot_lines(ax, gt.lines, ms=2)

    X, Y, W = gt.tile_info

    segs = [[(x, Y.min()), (x, Y.max())] for x in X]
    segs += [[(X.min(), y), (X.max(), y)] for y in Y]
    ax.add_collection(
        LineCollection(segs, colors=color, linewidths=0.5, zorder=1)
    )

    tile_ids = gt.tile_ids
    refpnt = np.array([[X.min(), Y.min()]]).T
    tiles_unique = np.unique(tile_ids[:, ~np.isnan(tile_ids[0])], axis=1)
    tile_pos = tiles_unique * W + refpnt

    patches = [Rectangle((t[0], t[1]), W, W) for t in tile_pos.T]
    pc = PatchCollection(patches, facecolor=tcolor, alpha=talpha,
                         edgecolor='none')
    ax.add_collection(pc)
    ax.autoscale_view()


def plot_tiles(
    ax: Axes,
    gt,
    colors: NDArray | None = None,
    alpha: float = 0.3,
) -> None:
    """
    Plot colored tiles on a tesselation grid.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to plot on.
    gt : object
        GIC tool object with ``tile_info``.
    colors : np.ndarray, optional
        2D array of tile colors. If None, uses red.
    alpha : float, default 0.3
        Tile transparency.
    """
    X, Y, W = gt.tile_info

    patches = []
    facecolors = []
    for i in range(len(X) - 1):
        for j in range(len(Y) - 1):
            patches.append(Rectangle((X[i] * W, Y[j] * W), W, W))
            facecolors.append(colors[j, i] if colors is not None else 'red')

    pc = PatchCollection(patches, alpha=alpha, edgecolor='none')
    pc.set_facecolor(facecolors)
    ax.add_collection(pc)
    ax.autoscale_view()


def plot_vecfield(
    ax: Axes,
    X: NDArray,
    Y: NDArray,
    U: NDArray,
    V: NDArray,
    cmap: ListedColormap | None = None,
    pivot: str = 'mid',
    scale: float = 70,
    width: float = 0.001,
) -> ScalarMappable:
    """
    Plot a vector field colored by angle.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to plot on.
    X, Y : np.ndarray
        Coordinates of vector origins.
    U, V : np.ndarray
        Vector components.
    cmap : matplotlib colormap, optional
        Colormap for angle encoding. Defaults to a darker HSV.
    pivot : str, default 'mid'
        Quiver pivot point.
    scale : float, default 70
        Quiver arrow scaling.
    width : float, default 0.001
        Quiver arrow width.

    Returns
    -------
    matplotlib.cm.ScalarMappable
        Mappable for creating colorbars.
    """
    if cmap is None:
        cmap = darker_hsv_colormap(0.8)

    norm = Normalize(vmin=-np.pi, vmax=np.pi)
    colors = np.arctan2(U, V)
    colors[np.isnan(colors)] = 0

    ax.quiver(X, Y, U, V, colors, norm=norm, pivot=pivot, scale=scale,
              width=width, cmap=cmap)

    return ScalarMappable(norm, cmap)
