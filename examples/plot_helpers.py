"""
Shared plotting helpers for ESAplus example notebooks.

These functions encapsulate common visualization patterns so that
notebook cells remain focused on core esapp operations. Import from
a hidden cell near the top of each notebook::

    import sys; sys.path.insert(0, '..')
    from plot_helpers import plot_voltage_profile, plot_sensitivity_map, ...

Figure sizes are optimized for PDF documentation rendering via nbsphinx
with a LaTeX text width of 6.5 inches. All figures fit within page width
without scaling, so font sizes render at their true point size.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


def format_plot(ax, title='', xlabel='', ylabel='', grid=True, **_ignored):
    """Minimal axis labeling (replaces the removed map.py styling engine)."""
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if grid:
        ax.grid(alpha=0.3, linewidth=0.5)

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


def plot_sensitivity_map(lines, values, title='Sensitivity Map',
                         clabel='Factor', cmap='RdBu_r', symmetric=True,
                         figsize=(_W2, 2.8), ax=None, fig=None):
    """Geographic network map with lines colored by sensitivity values.

    Parameters
    ----------
    lines : DataFrame
        Branch data with 'Longitude', 'Longitude:1', 'Latitude', 'Latitude:1'.
    values : array-like
        One value per branch (PTDF, LODF, etc.). Length must match ``lines``.
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


def plot_sensitivity_dual(lines, vals_a, vals_b,
                          titles=('PTDF', 'LODF'),
                          clabels=('PTDF', 'LODF'),
                          cmaps=('RdBu_r', 'RdBu_r'),
                          symmetric=(True, True),
                          figsize=(_W2, 2.8)):
    """Side-by-side geographic sensitivity maps (2-panel)."""
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    plot_sensitivity_map(lines, vals_a, title=titles[0],
                         clabel=clabels[0], cmap=cmaps[0],
                         symmetric=symmetric[0], ax=axes[0], fig=fig)
    plot_sensitivity_map(lines, vals_b, title=titles[1],
                         clabel=clabels[1], cmap=cmaps[1],
                         symmetric=symmetric[1], ax=axes[1], fig=fig)
    plt.tight_layout()
    plt.show()


def plot_sensitivity_triple(lines, vals_list,
                            titles=('A', 'B', 'C'),
                            clabels=('', '', ''),
                            cmaps=('RdBu_r', 'RdBu_r', 'RdBu_r'),
                            symmetric=(True, True, True),
                            figsize=(_WFULL, 2.5)):
    """Three-panel geographic sensitivity maps."""
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    for ax, vals, t, cl, cm, sym in zip(axes, vals_list, titles,
                                         clabels, cmaps, symmetric):
        plot_sensitivity_map(lines, vals, title=t,
                             clabel=cl, cmap=cm, symmetric=sym,
                             ax=ax, fig=fig)
    plt.tight_layout()
    plt.show()


def plot_flow_map(lines, loading,
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


# ---------------------------------------------------------------------------
# GIC matrix / sensitivity
# ---------------------------------------------------------------------------


# Keep backward compatibility alias
plot_gic_bar_hist = plot_gic_distribution


# ---------------------------------------------------------------------------
# Geographic / E-field
# ---------------------------------------------------------------------------


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


