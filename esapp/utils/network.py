"""
Network Matrix Utilities
========================

Provides network topology analysis including incidence matrices,
graph Laplacians with various weighting schemes, and branch parameter
calculations for power system analysis.

Classes
-------
Network
    Network matrix construction and branch weight calculations.
BranchType
    Enumeration of supported branch weight types for Laplacian construction.

Example
-------
Basic network matrix operations::

    >>> from esapp import PowerWorld
    >>> pw = PowerWorld("case.pwb")
    >>> A = pw.network.incidence()  # Incidence matrix
    >>> L = pw.network.laplacian(BranchType.LENGTH)  # Length-weighted Laplacian

See Also
--------
esapp.utils.gic : GIC analysis with network topology.
esapp.saw.matrices : Matrix retrieval from PowerWorld.
"""

from __future__ import annotations

from enum import Enum

import numpy as np
from pandas import DataFrame, Series, concat
from scipy.sparse import diags, coo_matrix, csc_matrix

from ..components import Branch, Bus, DCTransmissionLine, Substation

__all__ = ['Network', 'BranchType']


class BranchType(Enum):
    """
    Branch weighting schemes for Laplacian construction.

    Attributes
    ----------
    LENGTH : int
        Weight by inverse squared physical length (km^-2).
    RES_DIST : int
        Weight by inverse impedance magnitude (resistance distance).
    DELAY : int
        Weight by inverse squared propagation delay (s^-2).
    """
    LENGTH = 1
    RES_DIST = 2
    DELAY = 3


class Network:
    """
    Network matrix construction and analysis.

    Builds sparse network matrices (incidence, Laplacian) and computes
    branch electrical parameters. AC branches and HVDC transmission lines
    are always included when present in the case.

    This class is accessed via ``PowerWorld.network`` and delegates all
    data access to its parent PowerWorld instance.

    Notes
    -----
    Matrix dimensions follow PowerWorld bus ordering. Use busmap()
    to translate between bus numbers and matrix indices.
    """

    def __init__(self, pw=None):
        self._pw = pw
        self._A = None

    def _dc_lines(self) -> DataFrame | None:
        """Return DC transmission line data, or None if unavailable."""
        try:
            df = self._pw[DCTransmissionLine]
            return df if df is not None and len(df) > 0 else None
        except Exception:
            return None

    def busmap(self) -> Series:
        """
        Create mapping from bus numbers to matrix indices.

        Returns
        -------
        pd.Series
            Series indexed by BusNum with positional values.
        """
        buses = self._pw[Bus]
        return Series(buses.index, buses["BusNum"])

    def incidence(self, remake: bool = True) -> csc_matrix:
        """
        Construct the sparse arc-incidence matrix.

        Each row represents a branch with +1 at the to-bus and -1 at the
        from-bus. HVDC lines are appended after AC branches when present.

        Parameters
        ----------
        remake : bool, default True
            If True, recomputes even if cached.

        Returns
        -------
        scipy.sparse.csc_matrix
            Sparse incidence matrix (branches x buses).
        """
        if self._A is not None and not remake:
            return self._A

        fields = ["BusNum", "BusNum:1"]
        branches = self._pw[Branch][fields]

        dc = self._dc_lines()
        if dc is not None:
            branches = concat([branches, dc[fields]], ignore_index=True)

        bmap = self.busmap()
        fr = branches["BusNum"].map(bmap).to_numpy()
        to = branches["BusNum:1"].map(bmap).to_numpy()

        nb, nbus = len(branches), len(bmap)
        idx = np.arange(nb)
        self._A = coo_matrix(
            (np.concatenate([-np.ones(nb), np.ones(nb)]),
             (np.concatenate([idx, idx]), np.concatenate([fr, to]))),
            shape=(nb, nbus),
        ).tocsc()

        return self._A

    def laplacian(
        self,
        weights: BranchType | np.ndarray,
        longer_xfmr_lens: bool = True,
        len_thresh: float = 0.01,
    ) -> csc_matrix:
        """
        Construct weighted graph Laplacian: L = A.T @ W @ A.

        Parameters
        ----------
        weights : BranchType or np.ndarray
            Weighting scheme or custom weight vector.
        longer_xfmr_lens : bool, default True
            Use impedance-based pseudo-lengths for transformers.
        len_thresh : float, default 0.01
            Threshold (km) below which branches are treated as transformers.

        Returns
        -------
        scipy.sparse.csc_matrix
            Sparse weighted Laplacian matrix (buses x buses).
        """
        if isinstance(weights, BranchType):
            if weights is BranchType.LENGTH:
                W = 1 / self.lengths(longer_xfmr_lens, len_thresh) ** 2
            elif weights is BranchType.RES_DIST:
                W = 1 / self.zmag()
            else:
                W = 1 / self.delay() ** 2
        else:
            W = weights

        A = self.incidence()
        return (A.T @ diags(W) @ A).tocsc()

    def lengths(
        self,
        longer_xfmr_lens: bool = False,
        length_thresh_km: float = 0.01,
    ) -> Series:
        """
        Get branch lengths in kilometers.

        Parameters
        ----------
        longer_xfmr_lens : bool, default False
            Calculate pseudo-lengths for transformers based on
            their impedance relative to average line impedance per km.
        length_thresh_km : float, default 0.01
            Branches shorter than this are treated as transformers.

        Returns
        -------
        pd.Series
            Branch lengths in kilometers.
        """
        fields = ["LineLengthByParameters", "LineLengthByParameters:2",
                  "LineR:2", "LineX:2"]
        data = self._pw[Branch, fields][fields]

        # Prefer user-specified length over calculated
        user = data["LineLengthByParameters"]
        data.loc[user > 0, "LineLengthByParameters:2"] = user[user > 0]
        ell = data["LineLengthByParameters:2"]

        dc = self._dc_lines()
        if dc is not None:
            dc_ell = self._pw[DCTransmissionLine, "LineLengthByParameters"]["LineLengthByParameters"]
            ell = concat([ell, dc_ell], ignore_index=True)

        if longer_xfmr_lens:
            is_line = ell > length_thresh_km
            z = np.abs(data["LineR:2"] + 1j * data["LineX:2"])
            z_per_km = (z[is_line] / ell[is_line]).mean()
            ell.loc[~is_line] = (z[~is_line] / z_per_km).to_numpy()
        else:
            ell.loc[ell == 0] = 0.01

        return ell

    def zmag(self) -> Series:
        """
        Get branch impedance magnitudes ``|Z|``.

        Returns
        -------
        pd.Series
            Impedance magnitude for each branch.
        """
        return 1 / np.abs(self.ybranch())

    def ybranch(self, asZ: bool = False) -> Series:
        """
        Get branch admittance (or impedance) in complex form.

        Parameters
        ----------
        asZ : bool, default False
            If True, return impedance Z = R + jX.

        Returns
        -------
        pd.Series
            Complex admittance Y = 1/(R + jX) or impedance Z.
        """
        branches = self._pw[Branch, ["LineR:2", "LineX:2"]]
        Z = branches["LineR:2"] + 1j * branches["LineX:2"]

        dc = self._dc_lines()
        if dc is not None:
            Z = concat([Z, Series(np.full(len(dc), 0.001 + 0j))], ignore_index=True)

        return Z if asZ else 1 / Z

    def yshunt(self) -> Series:
        """
        Get branch shunt admittance in complex form.

        Returns
        -------
        pd.Series
            Complex shunt admittance Y = G + jB.
        """
        branches = self._pw[Branch, ["LineG", "LineC"]]
        return branches["LineG"] + 1j * branches["LineC"]

    def gamma(self) -> Series:
        """
        Compute propagation constants for each branch.

        Returns
        -------
        pd.Series
            Complex propagation constant gamma = sqrt(Z * Y).
        """
        ell = self.lengths()
        Z = self.ybranch(asZ=True).copy()
        Y = self.yshunt().copy()

        Z[Z == 0] = 0.000446 + 0.002878j
        Y[Y == 0] = 0.000463j

        return np.sqrt((Y / ell) * (Z / ell))

    def delay(self, min_delay: float = 10e-4) -> np.ndarray:
        r"""
        Compute effective propagation delay for network branches.

        Parameters
        ----------
        min_delay : float, default 10e-4
            Minimum delay value to prevent numerical overflow when
            computing 1/delay^2 in the Laplacian.

        Returns
        -------
        np.ndarray
            Effective propagation parameter beta for each branch.

        Notes
        -----
        - Branch inductance: omega * L_ij = Im(Z^br_ij)
        - Effective capacitance: C_ij = (C_i + C_j) / 2
        - Propagation delay: omega * tau_ij = Im(sqrt(Z_ij * Y_ij)) = beta_ij
        """
        Z = self.ybranch(asZ=True)

        Ybus = self._pw.esa.get_ybus()
        AVG = np.abs(self.incidence()) / 2
        Y = AVG @ Ybus @ np.ones(Ybus.shape[0])

        return np.maximum(np.imag(np.sqrt(Z * Y)), min_delay)

    def buscoords(self, astuple: bool = True):
        """
        Retrieve bus latitude and longitude from substation data.

        Parameters
        ----------
        astuple : bool, default True
            If True, return (Longitude, Latitude) Series tuple.
            If False, return merged DataFrame.

        Returns
        -------
        tuple of pd.Series or pd.DataFrame
        """
        A = self._pw[Bus, "SubNum"]
        S = self._pw[Substation, ["SubNum", "Longitude", "Latitude"]]
        LL = A.merge(S, on="SubNum")
        if astuple:
            return LL["Longitude"], LL["Latitude"]
        return LL
