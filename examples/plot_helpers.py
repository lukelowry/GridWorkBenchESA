"""
Shared plotting helpers for ESAplus example notebooks.

These functions encapsulate common visualization patterns so that
notebook cells remain focused on core esapp operations. Import from
a hidden cell near the top of each notebook::

    import sys; sys.path.insert(0, '..')
    from plot_helpers import plot_barh_top, plot_direction_sensitivity, ...

Figure sizes are optimized for PDF documentation rendering via nbsphinx
with a LaTeX text width of 6.5 inches. All figures fit within page width
without scaling, so font sizes render at their true point size.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

# Import plotting utilities from the sibling map module. Notebooks add
# the examples/ directory to sys.path, so the sibling import is primary;
# the package-style import covers running from the repository root.
try:
    from map import format_plot, border, plot_lines, plot_vecfield, darker_hsv_colormap
except ImportError:
    from examples.map import format_plot, border, plot_lines, plot_vecfield, darker_hsv_colormap

# ---------------------------------------------------------------------------
# Standard figure dimensions (inches) for 6.5" LaTeX text width
# ---------------------------------------------------------------------------
_W1 = 4.5          # single panel width
_H1 = 3.2          # single panel height
_W2 = 6.5          # two-panel row width
_H2 = 2.8          # two-panel row height
_W3 = 6.5          # three-panel row width
_H3 = 2.5          # three-panel row height
_WFULL = 6.5       # full page width

# Font sizes for multi-panel (3+) plots to avoid title crowding
_FS3 = dict(titlesize=10, labelsize=9, ticksize=8)
_FS2 = dict(titlesize=11, labelsize=9, ticksize=8)

# ---------------------------------------------------------------------------
# Professional color palette
# ---------------------------------------------------------------------------
_C1 = '#4C72B0'     # primary blue
_C2 = '#DD8452'     # secondary orange
_C3 = '#55A868'     # tertiary green
_C4 = '#C44E52'     # accent red
_C5 = '#8172B3'     # purple
_C6 = '#CCB974'     # yellow
_C7 = '#64B5CD'     # cyan
_CG = '#8C8C8C'     # gray
_LIMIT = '#C44E52'  # limit/warning lines


# ---------------------------------------------------------------------------
# Generic chart helpers
# ---------------------------------------------------------------------------

def plot_barh_top(values, labels=None, n=20, title='', xlabel='', ylabel='',
                  color=None, figsize=(_WFULL, 3.5), ax=None):
    """Horizontal bar chart of the top-*n* items sorted descending."""
    if color is None:
        color = _C1
    top = values[:n] if len(values) <= n else values.sort_values(ascending=False).head(n)
    if labels is None:
        labels = [f'{i+1}' for i in range(len(top))]
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    ax.barh(range(len(top)), top.values if hasattr(top, 'values') else top,
            color=color)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(labels[:len(top)])
    ax.invert_yaxis()
    format_plot(ax, title=title, xlabel=xlabel, ylabel=ylabel, plotarea='white')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_dual_bar(values_a, values_b, label_a='A', label_b='B',
                  xlabel='Index', ylabel='Value', title='',
                  figsize=(_W2, _H2), ax=None):
    """Grouped bar chart comparing two datasets side-by-side."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    x = range(len(values_a))
    width = 0.35
    ax.bar([i - width / 2 for i in x], values_a, width,
           label=label_a, color=_C1, alpha=0.85)
    ax.bar([i + width / 2 for i in x], values_b, width,
           label=label_b, color=_C2, alpha=0.85)
    format_plot(ax, title=title, xlabel=xlabel, ylabel=ylabel, plotarea='white')
    ax.legend(fontsize=8)
    if show:
        plt.tight_layout()
        plt.show()
    return ax


# ---------------------------------------------------------------------------
# PTDF / LODF / sensitivity
# ---------------------------------------------------------------------------


def plot_sensitivity_map(lines, values, shape=None, title='Sensitivity Map',
                         clabel='Factor', cmap='RdBu_r', symmetric=True,
                         figsize=(_W2, 2.8), ax=None, fig=None):
    """Geographic network map with lines colored by sensitivity values.

    Parameters
    ----------
    lines : DataFrame
        Branch data with 'Longitude', 'Longitude:1', 'Latitude', 'Latitude:1'.
    values : array-like
        One value per branch (PTDF, LODF, etc.). Length must match ``lines``.
    shape : str, optional
        Shape name for geographic border overlay (e.g. 'Texas', 'US').
    title : str
        Plot title.
    clabel : str
        Colorbar label.
    cmap : str
        Matplotlib colormap name.
    symmetric : bool
        If True, center the colormap at zero.
    """
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    vals = np.asarray(values, dtype=float)
    valid = np.isfinite(vals)
    vmax = np.abs(vals[valid]).max() if valid.any() else 1.0
    norm = Normalize(vmin=-vmax if symmetric else vals[valid].min(),
                     vmax=vmax)

    cX = lines[['Longitude', 'Longitude:1']].to_numpy()
    cY = lines[['Latitude', 'Latitude:1']].to_numpy()
    segments = np.stack([
        np.column_stack([cX[:, 0], cY[:, 0]]),
        np.column_stack([cX[:, 1], cY[:, 1]]),
    ], axis=1)

    cm = plt.get_cmap(cmap)
    colors = cm(norm(vals))
    widths = 0.5 + 3.0 * np.abs(vals) / vmax if vmax > 0 else np.ones(len(vals))
    widths[~valid] = 0.3

    # Sort by magnitude so largest values draw on top
    order = np.argsort(np.abs(vals))
    lc = LineCollection(segments[order], colors=colors[order],
                        linewidths=widths[order], zorder=4)
    ax.add_collection(lc)

    # Bus endpoints in neutral gray
    ax.scatter(cX.ravel(), cY.ravel(), c=_CG, s=8, zorder=3,
               edgecolors='white', linewidth=0.2)

    if shape is not None:
        border(ax, shape)

    ax.autoscale_view()
    sm = ScalarMappable(cmap=cm, norm=norm)
    sm.set_array([])
    if fig is not None:
        fig.colorbar(sm, ax=ax, label=clabel, shrink=0.8)

    format_plot(ax, title=title,
                xlabel=r'Lon ($^\circ$E)', ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_sensitivity_dual(lines, vals_a, vals_b, shape=None,
                          titles=('PTDF', 'LODF'),
                          clabels=('PTDF', 'LODF'),
                          cmaps=('RdBu_r', 'RdBu_r'),
                          symmetric=(True, True),
                          figsize=(_W2, 2.8)):
    """Side-by-side geographic sensitivity maps (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    plot_sensitivity_map(lines, vals_a, shape=shape, title=titles[0],
                         clabel=clabels[0], cmap=cmaps[0],
                         symmetric=symmetric[0], ax=axes[0], fig=fig)
    plot_sensitivity_map(lines, vals_b, shape=shape, title=titles[1],
                         clabel=clabels[1], cmap=cmaps[1],
                         symmetric=symmetric[1], ax=axes[1], fig=fig)
    plt.tight_layout()
    plt.show()


def plot_sensitivity_triple(lines, vals_list, shape=None,
                            titles=('A', 'B', 'C'),
                            clabels=('', '', ''),
                            cmaps=('RdBu_r', 'RdBu_r', 'RdBu_r'),
                            symmetric=(True, True, True),
                            figsize=(_WFULL, 2.5)):
    """Three-panel geographic sensitivity maps."""
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    for ax, vals, t, cl, cm, sym in zip(axes, vals_list, titles,
                                         clabels, cmaps, symmetric):
        plot_sensitivity_map(lines, vals, shape=shape, title=t,
                             clabel=cl, cmap=cm, symmetric=sym,
                             ax=ax, fig=fig)
    plt.tight_layout()
    plt.show()


def plot_flow_map(lines, loading, shape=None,
                  title='Branch Loading', clabel='Loading (%)',
                  threshold=100.0, highlight_idx=None,
                  figsize=(_W2, 2.8), ax=None, fig=None):
    """Geographic map with lines colored by loading percentage.

    Parameters
    ----------
    lines : DataFrame
        Branch data with geographic endpoints.
    loading : array-like
        Branch loading (%) values.
    threshold : float
        Overload threshold shown as a colorbar marker.
    highlight_idx : int or array-like, optional
        Index(es) into ``lines`` to draw with a thick dashed overlay.
    """
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    vals = np.asarray(loading, dtype=float)
    valid = np.isfinite(vals)
    vmax = max(vals[valid].max(), threshold) if valid.any() else threshold
    norm = Normalize(vmin=0, vmax=vmax)

    cX = lines[['Longitude', 'Longitude:1']].to_numpy()
    cY = lines[['Latitude', 'Latitude:1']].to_numpy()
    segments = np.stack([
        np.column_stack([cX[:, 0], cY[:, 0]]),
        np.column_stack([cX[:, 1], cY[:, 1]]),
    ], axis=1)

    cm = plt.get_cmap('YlOrRd')
    colors = cm(norm(vals))
    widths = 0.8 + 2.5 * vals / vmax
    widths[~valid] = 0.3

    # Sort by loading so heavily loaded lines draw on top
    order = np.argsort(vals)
    lc = LineCollection(segments[order], colors=colors[order],
                        linewidths=widths[order], zorder=4)
    ax.add_collection(lc)

    # Highlight specific branches
    if highlight_idx is not None:
        hi = np.atleast_1d(highlight_idx)
        hi_segs = segments[hi]
        lc_hi = LineCollection(hi_segs, colors='black', linewidths=3.5,
                               linestyles='dashed', zorder=5,
                               label='Outaged')
        ax.add_collection(lc_hi)
        ax.legend(fontsize=7, loc='lower right')

    ax.scatter(cX.ravel(), cY.ravel(), c=_CG, s=6, zorder=3,
               edgecolors='white', linewidth=0.2)

    if shape is not None:
        border(ax, shape)

    ax.autoscale_view()
    sm = ScalarMappable(cmap=cm, norm=norm)
    sm.set_array([])
    if fig is not None:
        fig.colorbar(sm, ax=ax, label=clabel, shrink=0.8)

    format_plot(ax, title=title,
                xlabel=r'Lon ($^\circ$E)', ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_bus_markers(ax, lon, lat, indices, marker='*', color=_C4,
                     size=120, label=None):
    """Add star markers at specific bus locations on an existing axes."""
    ax.scatter(lon[indices], lat[indices], marker=marker, c=color,
               s=size, zorder=10, edgecolors='black', linewidth=0.5,
               label=label)
    if label:
        ax.legend(fontsize=7, loc='lower right')


def plot_snapshot_comparison(base, modified, field='BusPUVolt',
                              figsize=(_W2, _H2)):
    """Before/after voltage scatter + difference histogram (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].scatter(range(len(base)), base, s=12, c=_C1,
                    edgecolors='white', linewidth=0.3, label='Base', alpha=0.7)
    axes[0].scatter(range(len(modified)), modified, s=12, c=_C2,
                    edgecolors='white', linewidth=0.3, label='Modified', alpha=0.7)
    axes[0].axhline(y=0.95, color=_LIMIT, linestyle='--', alpha=0.5)
    axes[0].axhline(y=1.05, color=_LIMIT, linestyle='--', alpha=0.5)
    format_plot(axes[0], title='Voltage Comparison',
                xlabel='Bus Index', ylabel='Voltage (pu)',
                plotarea='white', **_FS2)
    axes[0].legend(fontsize=7)

    diff = modified - base
    axes[1].hist(diff, bins=25, color=_C1, edgecolor='white')
    axes[1].axvline(x=0, color=_CG, linewidth=0.5)
    format_plot(axes[1], title=f'Voltage Change (max={np.abs(diff).max():.4f})',
                xlabel='\u0394V (pu)', ylabel='Count',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_state_chain(states, labels=None, figsize=(_W1, _H1)):
    """Line plot of state-chain voltage trajectories."""
    fig, ax = plt.subplots(figsize=figsize)
    pal = [_C1, _C2, _C3, _C4, _C5]
    for i, v in enumerate(states):
        lbl = labels[i] if labels else f'State {i}'
        ax.plot(range(len(v)), v, 'o-', color=pal[i % len(pal)],
                markersize=3, label=lbl)
    ax.axhline(y=0.95, color=_LIMIT, linestyle='--', alpha=0.5)
    ax.axhline(y=1.05, color=_LIMIT, linestyle='--', alpha=0.5)
    format_plot(ax, title='State Chain Voltages',
                xlabel='Bus Index', ylabel='Voltage (pu)',
                plotarea='white', **_FS2)
    ax.legend(fontsize=7)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Power system specific
# ---------------------------------------------------------------------------

def plot_voltage_profile(vmag, vang=None, figsize=(_W2, _H2)):
    """Scatter of bus voltage magnitudes + angle stem plot (always 2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].scatter(range(len(vmag)), vmag, c=_C1, s=18, edgecolors='white',
                    linewidth=0.4)
    axes[0].axhline(y=0.95, color=_LIMIT, linestyle='--', alpha=0.7, label='0.95 pu')
    axes[0].axhline(y=1.05, color=_LIMIT, linestyle='--', alpha=0.7, label='1.05 pu')
    axes[0].axhline(y=1.0, color=_CG, linestyle='-', alpha=0.3)
    format_plot(axes[0], title='Voltage Magnitude',
                xlabel='Bus Index', ylabel='Voltage (pu)',
                plotarea='white', **_FS2)
    axes[0].legend(fontsize=7)

    if vang is not None:
        axes[1].stem(range(len(vang)), vang, linefmt=_C1, markerfmt='o', basefmt=' ')
        format_plot(axes[1], title='Voltage Angles',
                    xlabel='Bus Index', ylabel='Angle (deg)',
                    plotarea='white', **_FS2)
    else:
        axes[1].hist(vmag, bins=20, color=_C1, edgecolor='white')
        format_plot(axes[1], title='Voltage Distribution',
                    xlabel='Voltage (pu)', ylabel='Count',
                    plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_contingency_results(violations, figsize=(_W2, _H2)):
    """Bar chart of violations per contingency + histogram (2-panel)."""
    if len(violations) == 0 or 'Contingency' not in violations.columns:
        return
    ctg_counts = violations['Contingency'].value_counts().head(15)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].barh(range(len(ctg_counts)), ctg_counts.values, color=_C1)
    axes[0].set_yticks(range(len(ctg_counts)))
    axes[0].set_yticklabels(ctg_counts.index, fontsize=7)
    axes[0].invert_yaxis()
    format_plot(axes[0], title='Top Contingencies',
                xlabel='Number of Violations', plotarea='white', **_FS2)

    axes[1].hist(violations.groupby('Contingency').size(), bins=20,
                 color=_C1, edgecolor='white')
    format_plot(axes[1], title='Violation Distribution',
                xlabel='Violations per Contingency', ylabel='Count',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_pv_curve(mw_points, v_points, ax=None, figsize=(_W1, _H1)):
    """PV curve with nose point marker."""
    if not mw_points:
        return
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    ax.plot(mw_points, v_points, 'o-', color=_C1, markersize=3)

    nose_idx = np.argmax(mw_points)
    ax.plot(mw_points[nose_idx], v_points[nose_idx], '*', color=_C4,
            markersize=12, label=f'Nose: {mw_points[nose_idx]:.0f} MW')

    ax.axhline(y=0.95, color=_LIMIT, linestyle='--', alpha=0.5, label='0.95 pu')
    format_plot(ax, title='PV Curve',
                xlabel='Transfer (MW)', ylabel='Voltage (pu)',
                plotarea='white', **_FS2)
    ax.legend(fontsize=7)
    if show:
        plt.tight_layout()
        plt.show()
    return ax


# ---------------------------------------------------------------------------
# Sparse matrix / spectral
# ---------------------------------------------------------------------------

def plot_spy_matrices(matrices, titles, figsize=None, markersize=3, colors=None):
    """Side-by-side spy() plots for one or more sparse matrices."""
    n = max(len(matrices), 2)
    if figsize is None:
        figsize = (min(_WFULL, 3.2 * n), _H2)
    if colors is None:
        colors = [_C1, _C2, _C3, _C5, _C6, _C7][:len(matrices)]
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]
    fs = _FS3 if n >= 3 else _FS2
    for ax, M, t, c in zip(axes, matrices, titles, colors):
        ax.spy(M, markersize=markersize, color=c)
        format_plot(ax, title=t, plotarea='white', grid=False, **fs)
    for j in range(len(matrices), n):
        axes[j].set_visible(False)
    plt.tight_layout()
    plt.show()


def plot_ybus_analysis(Y, figsize=(_W2, _H2)):
    """Y-Bus sparsity pattern + eigenvalue spectrum (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].spy(Y, markersize=3, color=_C1)
    format_plot(axes[0], title=f'Y-Bus Sparsity\n{Y.shape}, nnz={Y.nnz}',
                plotarea='white', grid=False, **_FS2)

    eig_Y = np.linalg.eigvals(Y.toarray())
    axes[1].scatter(eig_Y.real, eig_Y.imag, s=15, c=_C1, edgecolors='white',
                    linewidth=0.4)
    axes[1].axhline(y=0, color=_CG, linewidth=0.5)
    axes[1].axvline(x=0, color=_CG, linewidth=0.5)
    format_plot(axes[1], title='Eigenvalue Spectrum',
                xlabel='Real', ylabel='Imaginary',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_incidence_and_degree(A, figsize=(_W2, _H2)):
    """Incidence matrix spy + bus degree bar chart (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].spy(A, markersize=2, color=_C1)
    format_plot(axes[0], title=f'Incidence Matrix\n{A.shape}',
                xlabel='Bus index', ylabel='Branch index',
                plotarea='white', grid=False, **_FS2)

    degrees = np.abs(A).T @ np.ones(A.shape[0])
    axes[1].bar(range(len(degrees)), degrees, color=_C1)
    format_plot(axes[1], title='Bus Degree Distribution',
                xlabel='Bus index', ylabel='Degree',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_incidence_and_laplacian(A, figsize=(_W2, _H2)):
    """Incidence matrix spy + |A^T A| image (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].spy(A, markersize=2, color=_C1)
    format_plot(axes[0], title=f'Incidence Matrix\n{A.shape}',
                xlabel='Bus index', ylabel='Branch index',
                plotarea='white', grid=False, **_FS2)

    L_unw = (A.T @ A).toarray()
    axes[1].imshow(np.abs(L_unw), cmap='Blues', aspect='auto')
    format_plot(axes[1], title='|A\u1d40A| (Unweighted Laplacian)',
                xlabel='Bus index', ylabel='Bus index',
                plotarea='white', grid=False, **_FS2)

    plt.axis('equal')
    plt.tight_layout()
    plt.show()


def plot_eigenspectrum(eigenvalue_sets, titles, figsize=None):
    """Stem plots of eigenvalue arrays (always >= 2 panels)."""
    n = max(len(eigenvalue_sets), 2)
    if figsize is None:
        figsize = (min(_WFULL, 3.2 * n), _H2)
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]
    fs = _FS3 if n >= 3 else _FS2
    for ax, vals, t in zip(axes, eigenvalue_sets, titles):
        ax.stem(vals, basefmt=' ')
        format_plot(ax, title=t, xlabel='Index', ylabel='Eigenvalue',
                    plotarea='white', **fs)
    for j in range(len(eigenvalue_sets), n):
        axes[j].set_visible(False)
    plt.tight_layout()
    plt.show()


def plot_fiedler(fiedler, figsize=(_W2, _H2)):
    """Fiedler vector bar chart colored by sign + partition histogram (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    colors = [_C1 if v >= 0 else _C2 for v in fiedler]
    axes[0].bar(range(len(fiedler)), fiedler, color=colors)
    axes[0].axhline(y=0, color='black', linewidth=0.5)
    format_plot(axes[0], title='Fiedler Vector (Network Partition)',
                xlabel='Bus index', ylabel='Fiedler component',
                plotarea='white', **_FS2)

    axes[1].hist(fiedler, bins=15, color=_C1, edgecolor='white')
    axes[1].axvline(x=0, color='black', linewidth=0.5)
    n_pos = sum(1 for v in fiedler if v >= 0)
    n_neg = len(fiedler) - n_pos
    axes[1].set_title(f'Partition: {n_pos} vs {n_neg} buses', fontsize=11)
    format_plot(axes[1], xlabel='Component value', ylabel='Count',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_histograms(datasets, titles, xlabels, colors=None, bins=25, figsize=None):
    """Side-by-side histograms (always >= 2 panels)."""
    n = max(len(datasets), 2)
    if figsize is None:
        figsize = (min(_WFULL, 3.2 * n), _H2)
    if colors is None:
        colors = [_C1, _C2, _C3, _C6][:len(datasets)]
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]
    fs = _FS3 if n >= 3 else _FS2
    for ax, data, t, xl, c in zip(axes, datasets, titles, xlabels, colors):
        ax.hist(data, bins=bins, color=c, edgecolor='white')
        format_plot(ax, title=t, xlabel=xl, ylabel='Count',
                    plotarea='white', **fs)
    for j in range(len(datasets), n):
        axes[j].set_visible(False)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Direction sensitivity (GIC)
# ---------------------------------------------------------------------------

def plot_direction_sensitivity(directions, max_gics, title='Max GIC vs Direction',
                               figsize=(_W2, 2.8)):
    """Line plot + polar plot of GIC vs. storm direction (2-panel)."""
    fig = plt.figure(figsize=figsize)

    ax1 = fig.add_subplot(121)
    ax1.plot(directions, max_gics, 'o-', color=_C1, markersize=3)
    format_plot(ax1, title=title,
                xlabel='Direction (deg from N)',
                ylabel='Max |GIC| (A)', plotarea='white', **_FS2)

    ax2 = fig.add_subplot(122, projection='polar')
    theta = np.radians(directions)
    ax2.plot(theta, max_gics, 'o-', color=_C2, markersize=3)
    ax2.set_title('Polar Response', pad=15, fontsize=10)

    plt.tight_layout()
    plt.show()

    worst = directions[np.argmax(max_gics)]
    print(f"Worst-case direction: {worst} degrees")
    print(f"Worst-case max GIC: {max_gics.max():.2f} Amps")


def plot_direction_profiles(directions, gic_profiles, labels, figsize=(_W2, 2.8)):
    """Multi-transformer direction sensitivity: line + polar (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    pal = [_C1, _C2, _C3, _C4, _C5]
    for j, lbl in enumerate(labels):
        axes[0].plot(directions, gic_profiles[:, j], label=lbl,
                     color=pal[j % len(pal)])
    format_plot(axes[0], title='Transformer GIC vs Direction',
                xlabel='Direction (deg from N)', ylabel='|GIC| (A)',
                plotarea='white', **_FS2)
    axes[0].legend(fontsize=7)

    ax_polar = fig.add_axes(axes[1].get_position(), projection='polar')
    axes[1].set_visible(False)
    theta = np.radians(directions)
    for j, lbl in enumerate(labels):
        ax_polar.plot(theta, gic_profiles[:, j], label=lbl,
                      color=pal[j % len(pal)])
    ax_polar.set_title('Polar Response', pad=15, fontsize=10)
    ax_polar.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=7)

    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# GIC matrix / sensitivity
# ---------------------------------------------------------------------------

def plot_gic_distribution(gic_abs, n=15, figsize=(_W2, _H2)):
    """Histogram + top-N bar chart for GIC magnitudes (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    axes[0].hist(gic_abs, bins=20, color=_C1, edgecolor='white')
    format_plot(axes[0], title='GIC Distribution',
                xlabel='|GIC| (A)', ylabel='Count',
                plotarea='white', **_FS2)

    top = gic_abs.sort_values(ascending=False).head(n)
    axes[1].barh(range(len(top)), top.values, color=_C1)
    axes[1].set_yticks(range(len(top)))
    axes[1].set_yticklabels([f'XF {i + 1}' for i in range(len(top))], fontsize=7)
    axes[1].invert_yaxis()
    format_plot(axes[1], title=f'Top {n} Transformer GICs',
                xlabel='|GIC| (A)', ylabel='Transformer',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


# Keep backward compatibility alias
plot_gic_bar_hist = plot_gic_distribution


def plot_gmatrix_comparison(G_model, G_pw, figsize=(_W3, _H3)):
    """Compare model G-matrix vs PowerWorld G-matrix with difference (3-panel)."""
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    im0 = axes[0].imshow(np.abs(G_model), cmap='Blues', aspect='auto')
    fig.colorbar(im0, ax=axes[0], shrink=0.7)
    format_plot(axes[0], title='|G| Model', plotarea='white',
                grid=False, **_FS3)

    im1 = axes[1].imshow(np.abs(G_pw), cmap='Blues', aspect='auto')
    fig.colorbar(im1, ax=axes[1], shrink=0.7)
    format_plot(axes[1], title='|G| PowerWorld', plotarea='white',
                grid=False, **_FS3)

    if G_model.shape == G_pw.shape:
        diff = np.abs(G_model - G_pw)
        im2 = axes[2].imshow(diff, cmap='Reds', aspect='auto')
        fig.colorbar(im2, ax=axes[2], shrink=0.7)
        format_plot(axes[2], title=f'|Diff| max={diff.max():.2e}',
                    plotarea='white', grid=False, **_FS3)
    else:
        axes[2].text(0.5, 0.5, 'Shape mismatch',
                     ha='center', va='center', transform=axes[2].transAxes,
                     fontsize=9)
        format_plot(axes[2], title='Difference', plotarea='white',
                    grid=False, **_FS3)

    plt.tight_layout()
    plt.show()


def plot_jacobian_sensitivity(J_dense, figsize=(_W2, _H2)):
    """dI/dE Jacobian heatmap + row-wise sensitivity bar chart (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    im0 = axes[0].imshow(np.abs(J_dense), cmap='Blues', aspect='auto')
    fig.colorbar(im0, ax=axes[0], shrink=0.7)
    format_plot(axes[0], title='|dI/dE| Jacobian',
                xlabel='Branch index', ylabel='Transformer index',
                plotarea='white', grid=False, **_FS2)

    row_sens = np.sum(np.abs(J_dense), axis=1)
    axes[1].barh(range(len(row_sens)), row_sens, color=_C1)
    axes[1].invert_yaxis()
    format_plot(axes[1], title='Transformer E-Field Sensitivity',
                xlabel='Total sensitivity', ylabel='Transformer index',
                plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()


def plot_branch_impact(col_sens, top_n=5, figsize=(_W2, _H2)):
    """Branch impact bar chart + top-N detail (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    top_branches = np.argsort(col_sens)[::-1][:top_n]
    colors = [_C2 if i in top_branches else _C1 for i in range(len(col_sens))]
    axes[0].bar(range(len(col_sens)), col_sens, color=colors, width=1.0)
    format_plot(axes[0], title='Branch Impact on GIC',
                xlabel='Branch index', ylabel='Aggregate |dI/dE|',
                plotarea='white', **_FS2)

    axes[1].barh(range(top_n), col_sens[top_branches], color=_C2)
    axes[1].set_yticks(range(top_n))
    axes[1].set_yticklabels([f'Branch {b}' for b in top_branches], fontsize=7)
    axes[1].invert_yaxis()
    format_plot(axes[1], title=f'Top {top_n} Branches',
                xlabel='|dI/dE|', plotarea='white', **_FS2)

    plt.tight_layout()
    plt.show()

    print(f"\nTop {top_n} most influential branches: {top_branches}")


# ---------------------------------------------------------------------------
# Geographic / E-field
# ---------------------------------------------------------------------------

def plot_geo_grid_buses(LON, LAT, lon, lat, shape, xlim, ylim,
                        figsize=(_W2, 2.8), ax=None, fig=None):
    """Grid points + bus locations on a geographic border."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(LON.ravel(), LAT.ravel(), s=1, c=_C7, alpha=0.5,
               label='Grid points')
    ax.scatter(lon, lat, s=12, c=_C4, zorder=5, label='Bus locations')
    border(ax, shape)
    ax.set_xlim(xlim[0] - 0.1, xlim[1] + 0.1)
    ax.set_ylim(ylim[0] - 0.1, ylim[1] + 0.1)
    format_plot(ax, title='Grid & Bus Locations',
                xlabel=r'Lon ($^\circ$E)', ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.legend(fontsize=7, loc='lower right')
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_efield_comparison(LON, LAT, fields, shape, figsize=None):
    """Side-by-side magnitude heatmaps for E-field patterns (>= 2-panel).

    Parameters
    ----------
    fields : list of (name, Ex, Ey) tuples
    """
    n = max(len(fields), 2)
    if figsize is None:
        figsize = (_WFULL, _H3)
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]
    fs = _FS3 if n >= 3 else _FS2
    for ax, (name, Ex, Ey) in zip(axes, fields):
        magnitude = np.sqrt(Ex ** 2 + Ey ** 2)
        im = ax.pcolormesh(LON, LAT, magnitude, cmap='hot_r', shading='auto')
        border(ax, shape)
        ax.set_xlim(LON.min(), LON.max())
        ax.set_ylim(LAT.min(), LAT.max())
        fig.colorbar(im, ax=ax, label='|E| (V/km)', shrink=0.7)
        format_plot(ax, title=f'{name} |E|',
                    xlabel=r'Lon ($^\circ$E)',
                    ylabel=r'Lat ($^\circ$N)',
                    plotarea='white', grid=False, **fs)
        ax.set_aspect('equal')
    for j in range(len(fields), n):
        axes[j].set_visible(False)
    plt.tight_layout()
    plt.show()


def plot_efield_vectors(LON, LAT, Ex, Ey, shape, step=3,
                        figsize=(_W2, 2.8), ax=None, fig=None):
    """Heatmap of E-field magnitude + vector field overlay."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    magnitude = np.sqrt(Ex ** 2 + Ey ** 2)
    im = ax.pcolormesh(LON, LAT, magnitude, cmap='YlOrRd', shading='auto', alpha=0.6)
    border(ax, shape)
    ax.set_xlim(LON.min(), LON.max())
    ax.set_ylim(LAT.min(), LAT.max())

    sm = plot_vecfield(ax, LON[::step, ::step], LAT[::step, ::step],
                       Ex[::step, ::step], Ey[::step, ::step],
                       scale=40, width=0.003)
    if fig is not None:
        fig.colorbar(im, ax=ax, label='|E| (V/km)', shrink=0.7)
    format_plot(ax, title='E-Field Vectors',
                xlabel=r'Lon ($^\circ$E)',
                ylabel=r'Lat ($^\circ$N)', grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_network_efield(LON, LAT, magnitude, lines, lon, lat, Ex, Ey,
                        shape, step=4, figsize=(_W2, 2.8), ax=None, fig=None):
    """Full network overlay: heatmap + lines + buses + E-field vectors."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    im = ax.pcolormesh(LON, LAT, magnitude, cmap='YlOrRd', shading='auto', alpha=0.4)
    border(ax, shape)
    plot_lines(ax, lines, ms=4, lw=0.6)
    ax.scatter(lon, lat, s=12, c='navy', zorder=6, label='Buses',
               edgecolors='white', linewidth=0.4)
    ax.quiver(LON[::step, ::step], LAT[::step, ::step],
              Ex[::step, ::step], Ey[::step, ::step],
              color='darkred', alpha=0.7, scale=30, width=0.002, zorder=7)
    ax.set_xlim(LON.min(), LON.max())
    ax.set_ylim(LAT.min(), LAT.max())

    if fig is not None:
        fig.colorbar(im, ax=ax, label='|E| (V/km)', shrink=0.7)
    format_plot(ax, title='Network + E-Field',
                xlabel=r'Lon ($^\circ$E)',
                ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.legend(loc='lower right', fontsize=7)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_gic_geo_map(lines, xf_geo, gic_mag, shape, xlim, ylim,
                     figsize=(_W2, 2.8), ax=None, fig=None):
    """GIC magnitudes on a geographic map with transmission network."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    border(ax, shape)
    plot_lines(ax, lines, ms=3, lw=0.4)

    sizes = 10 + 120 * gic_mag / gic_mag.max()
    sc = ax.scatter(xf_geo['Longitude'], xf_geo['Latitude'],
                    s=sizes, c=gic_mag, cmap='Reds', zorder=8,
                    edgecolors='black', linewidth=0.4)
    if fig is not None:
        fig.colorbar(sc, ax=ax, label='|GIC| (A)', shrink=0.7)

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    format_plot(ax, title='Transformer GIC Map',
                xlabel=r'Lon ($^\circ$E)',
                ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_b3d_roundtrip(LON, LAT, ex_orig, ex_loaded, shape, ny, nx,
                       figsize=(_W2, _H2)):
    """Side-by-side original vs loaded Ex from B3D (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    ex_2d_orig = ex_orig[0].reshape(ny, nx, order='F')
    ex_2d_load = ex_loaded[0].reshape(ny, nx, order='F')

    for ax, data, title in zip(axes,
                               [ex_2d_orig, ex_2d_load],
                               ['Original Ex', 'B3D Round-Trip Ex']):
        im = ax.pcolormesh(LON, LAT, data, cmap='RdBu_r', shading='auto')
        border(ax, shape)
        ax.set_xlim(LON.min(), LON.max())
        ax.set_ylim(LAT.min(), LAT.max())
        fig.colorbar(im, ax=ax, label='Ex (V/km)')
        format_plot(ax, title=title,
                    xlabel=r'Lon ($^\circ$E)',
                    ylabel=r'Lat ($^\circ$N)',
                    plotarea='white', grid=False, **_FS2)
        ax.set_aspect('equal')

    plt.tight_layout()
    plt.show()


def plot_b3d_components(LON, LAT, Ex, Ey, shape, suptitle='',
                        figsize=(_W3, _H3)):
    """Three-panel plot: |E|, Ex, Ey on a geographic background."""
    magnitude = np.sqrt(Ex ** 2 + Ey ** 2)
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    for ax, data, cmap, label, title in zip(
        axes,
        [magnitude, Ex, Ey],
        ['hot_r', 'RdBu_r', 'RdBu_r'],
        ['|E| (V/km)', 'Ex (V/km)', 'Ey (V/km)'],
        ['|E| Magnitude', 'Ex (Eastward)', 'Ey (Northward)'],
    ):
        im = ax.pcolormesh(LON, LAT, data, cmap=cmap, shading='auto')
        border(ax, shape)
        fig.colorbar(im, ax=ax, label=label, shrink=0.7)
        format_plot(ax, title=title,
                    xlabel=r'Lon ($^\circ$E)',
                    ylabel=r'Lat ($^\circ$N)',
                    plotarea='white', grid=False, **_FS3)
        ax.set_aspect('equal')

    if suptitle:
        plt.suptitle(suptitle, fontsize=12)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Dynamics
# ---------------------------------------------------------------------------

def plot_dynamics(meta, df, xlim=None, figsize_width=10, **kwargs):
    """Plot transient stability results grouped by Object and Metric.

    Parameters
    ----------
    meta : DataFrame
        Metadata DataFrame returned by ``Dynamics.solve()``.
    df : DataFrame
        Time-series DataFrame returned by ``Dynamics.solve()``.
    xlim : tuple, optional
        (min, max) for x-axis limits.
    figsize_width : float, default 10
        Figure width in inches.
    kwargs : dict
        Additional arguments passed to ``plt.subplots()``.
    """
    if meta.empty or df.empty:
        return

    grouped = meta.groupby(['Object', 'Metric'])
    n_groups = len(grouped)
    if n_groups == 0:
        return

    if xlim is None:
        xlim = (df.index.min(), df.index.max())

    fig_height = max(n_groups * 3.0, 5)
    fig, axes = plt.subplots(n_groups, 1, sharex=True,
                             figsize=(figsize_width, fig_height),
                             squeeze=False, **kwargs)
    axes_flat = axes.flatten()

    for ax, ((obj, metric), grp) in zip(axes_flat, grouped):
        ctg_list = df.columns.get_level_values(0).unique()
        for ctg in ctg_list:
            ctg_data = df[ctg]
            matching_cols = grp.index.intersection(ctg_data.columns)
            for col in matching_cols:
                id_a = grp.at[col, 'ID-A']
                id_b = grp.at[col, 'ID-B'] if 'ID-B' in grp.columns else None
                id_a_str = str(id_a) if id_a is not None and str(id_a).lower() != 'nan' else ""
                id_b_str = str(id_b) if id_b is not None and str(id_b).lower() != 'nan' else ""
                label_parts = [p for p in [id_a_str, id_b_str] if p]
                lbl = " ".join(label_parts)
                plot_label = f"{ctg} | {lbl}" if lbl else ctg
                ax.plot(ctg_data.index, ctg_data[col], label=plot_label, linewidth=1.5)

        ax.set_ylabel(f"{obj}\n{metric}", fontsize=10, fontweight='bold')
        ax.grid(True, which='major', linestyle='-', linewidth=0.75, alpha=0.7)
        ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.5)
        ax.minorticks_on()
        if xlim:
            ax.set_xlim(xlim)

    axes_flat[-1].set_xlabel("Time (s)", fontsize=10, fontweight='bold')
    plt.tight_layout(pad=2.0)
    plt.show()


def plot_comparative_dynamics(ctg_names, all_results, figsize=None):
    """Stacked subplots of generator power for each contingency (multi-row)."""
    n = len(ctg_names)
    ncols = min(n, 2)
    nrows = (n + ncols - 1) // ncols
    if figsize is None:
        figsize = (_WFULL, 2.6 * nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, sharex=True)
    axes_flat = np.array(axes).ravel() if n > 1 else [axes]
    fs = _FS3 if ncols >= 3 else _FS2
    for ax, name in zip(axes_flat, ctg_names):
        results = all_results[name]
        p_cols = [c for c in results.columns if 'P' in str(c) or 'MW' in str(c)]
        if p_cols:
            results[p_cols].plot(ax=ax, legend=True)
            ax.legend(fontsize=6)
        format_plot(ax, title=f'{name}',
                    xlabel='Time (s)', ylabel='P (MW)',
                    plotarea='white', **fs)
    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Discrete calculus / Grid2D utilities
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Spectral analysis utilities
# ---------------------------------------------------------------------------


def plot_colormap_2d(LON, LAT, theta, scales, figsize=(_WFULL, 4)):
    """1D gradient + 2D angle field at multiple colormap scales."""
    gradient = np.linspace(-np.pi, np.pi, 256).reshape(1, -1)

    fig, axes = plt.subplots(2, len(scales), figsize=figsize)
    fs = _FS3 if len(scales) >= 3 else {}
    for ax, scale in zip(axes[0], scales):
        cmap = darker_hsv_colormap(scale)
        ax.imshow(gradient, aspect='auto', cmap=cmap)
        format_plot(ax, title=f'scale={scale}', plotarea='white',
                    grid=False, **fs)
        ax.set_yticks([])
    for ax, scale in zip(axes[1], scales):
        cmap = darker_hsv_colormap(scale)
        ax.pcolormesh(LON, LAT, theta, cmap=cmap, shading='auto')
        format_plot(ax, title=f'Angle field (scale={scale})',
                    plotarea='white', grid=False, **fs)
        ax.set_aspect('equal')
    plt.suptitle('darker_hsv_colormap at Different Scales', fontsize=12)
    plt.tight_layout()
    plt.show()


def plot_borders(shapes, figsize=(_W2, _H2)):
    """Side-by-side geographic borders."""
    fig, axes = plt.subplots(1, len(shapes), figsize=figsize)
    if len(shapes) == 1:
        axes = [axes]
    fs = _FS3 if len(shapes) >= 3 else {}
    for ax, shape in zip(axes, shapes):
        border(ax, shape)
        format_plot(ax, title=f'{shape} Border',
                    xlabel=r'Longitude ($^\circ$E)',
                    ylabel=r'Latitude ($^\circ$N)',
                    plotarea='white', grid=False, **fs)
        ax.set_aspect('equal')
    plt.tight_layout()
    plt.show()


def plot_network_map(lines, lon, lat, shape, pad=0.5,
                     figsize=(_W2, 2.8), ax=None, fig=None):
    """Transmission network on geographic background."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    border(ax, shape)
    plot_lines(ax, lines, ms=8, lw=0.8)
    ax.set_xlim(lon.min() - pad, lon.max() + pad)
    ax.set_ylim(lat.min() - pad, lat.max() + pad)
    format_plot(ax, title='Transmission Network',
                xlabel=r'Lon ($^\circ$E)',
                ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_bus_voltages_map(lines, lon, lat, vmag, shape, pad=0.5,
                          figsize=(_W2, 2.8), ax=None, fig=None):
    """Bus voltages colored on geographic map with network overlay."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    border(ax, shape)
    plot_lines(ax, lines, ms=3, lw=0.6)

    sc = ax.scatter(lon, lat, s=30, c=vmag, cmap='RdYlGn', vmin=0.95, vmax=1.05,
                    zorder=6, edgecolors='black', linewidth=0.4)
    if fig is not None:
        fig.colorbar(sc, ax=ax, label='V (pu)', shrink=0.7)

    ax.set_xlim(lon.min() - pad, lon.max() + pad)
    ax.set_ylim(lat.min() - pad, lat.max() + pad)
    format_plot(ax, title='Bus Voltages',
                xlabel=r'Lon ($^\circ$E)',
                ylabel=r'Lat ($^\circ$N)',
                plotarea='white', grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_vecfield_map(LON, LAT, Ex, Ey, lines, shape,
                      figsize=(_W2, 2.8), ax=None, fig=None):
    """Vector field over network with geographic border."""
    show = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    border(ax, shape)
    plot_lines(ax, lines, ms=3, lw=0.4)

    sm = plot_vecfield(ax, LON, LAT, Ex, Ey, scale=30, width=0.003)
    if fig is not None:
        fig.colorbar(sm, ax=ax, label='Angle (rad)', shrink=0.7)

    ax.set_xlim(LON.min(), LON.max())
    ax.set_ylim(LAT.min(), LAT.max())
    format_plot(ax, title='Vector Field over Network',
                xlabel=r'Lon ($^\circ$E)',
                ylabel=r'Lat ($^\circ$N)',
                grid=False, **_FS2)
    ax.set_aspect('equal')
    if show:
        plt.tight_layout()
        plt.show()
    return ax


def plot_format_showcase(x_data, figsize=(_W3, _H3)):
    """Showcase of format_plot styling options (3-panel)."""
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    axes[0].plot(x_data, np.sin(x_data), 'o-', markersize=3, color=_C1)
    format_plot(axes[0], title='Default Style', xlabel='x', ylabel='sin(x)',
                **_FS3)

    axes[1].plot(x_data, np.cos(x_data), 'o-', markersize=3, color=_C2)
    format_plot(axes[1], title='Colored Background', xlabel='x', ylabel='cos(x)',
                plotarea='#f0f0f0', **_FS3)

    axes[2].plot(x_data, np.sin(x_data) * np.exp(-x_data / 5), 'o-',
                 markersize=3, color=_C3)
    format_plot(axes[2], title='Custom Ticks', xlabel='x', ylabel='y',
                xlim=(0, 10), ylim=(-1, 1), xticksep=2.5, yticksep=0.5, **_FS3)

    plt.tight_layout()
    plt.show()
