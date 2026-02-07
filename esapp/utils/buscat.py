"""
Bus Category Classification
============================

Parses PowerWorld's ``BusCat`` field into structured bus types,
control flags, and regulation roles. Provides index-based access
for Jacobian construction and voltage control analysis.

Classes
-------
BusCat
    Parses BusCat strings and provides typed bus index access.

Functions
---------
parse_buscat
    Parse a single BusCat string into a classification dict.

See Also
--------
esapp.saw._enums.BusType : Fundamental bus type enum.
esapp.saw._enums.BusCtrl : Voltage control modifier flags.
esapp.saw._enums.Role : Regulation group role enum.
esapp.utils.network : Network topology matrices.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from pandas import DataFrame

from ..saw._enums import BusType, BusCtrl, Role
from ..components import Bus

__all__ = ['BusCat', 'parse_buscat']


def parse_buscat(cat: str) -> dict:
    """Parse a BusCat string into a bus classification dict.

    Extracts the base type (Slack/PV/PQ), control modifiers,
    regulation role, limit status, and effective type from the
    descriptive string PowerWorld returns in the BusCat field.

    Parameters
    ----------
    cat : str
        Raw BusCat string from PowerWorld, e.g.
        ``"PQ (Remotely Regulated at Var Limit)"``.

    Returns
    -------
    dict
        Keys:

        - **Type** (*str*) -- Base bus type name (``"SLACK"``,
          ``"PV"``, or ``"PQ"``).
        - **Ctrl** (*str*) -- Control flags joined by ``"+"``,
          e.g. ``"REMOTE+DROOP"`` or ``"NONE"``.
        - **Role** (*str*) -- Regulation role name, or ``""``
          if the bus is not part of a regulation group.
        - **Lim** (*bool*) -- True if the bus is at a reactive
          power limit.
        - **SVC** (*bool*) -- True if the bus has SVC or
          continuous shunt control.
        - **Eff** (*str*) -- Effective type after limit
          enforcement (a PV bus at its limit becomes PQ).
        - **Reg** (*bool*) -- True if the bus is actively
          regulating voltage (PV/Slack and not limited).
    """
    s = str(cat).lower()

    # --- Base type ---
    if "slack" in s:          typ = BusType.SLACK
    elif s.startswith("pv"):  typ = BusType.PV
    else:                     typ = BusType.PQ

    # --- Control flags ---
    ctrl = BusCtrl.NONE
    if "remote" in s or "droop" in s:  ctrl |= BusCtrl.REMOTE
    if "droop" in s:                    ctrl |= BusCtrl.DROOP
    if "line drop" in s:                ctrl |= BusCtrl.LDC
    if "tol" in s:                      ctrl |= BusCtrl.TOL

    # --- Regulation role ---
    if "remotely regulated" in s or "droop reg bus" in s:
        role = Role.TARGET
    elif "secondary" in s or "droop remote bus" in s:
        role = Role.SECONDARY
    elif "primary" in s or "local/remote" in s:
        role = Role.PRIMARY
    else:
        role = Role.NONE

    # --- Derived state ---
    limited = "limit" in s
    svc = "svc" in s or "continuous" in s
    eff = BusType.PQ if (limited and typ == BusType.PV) else typ
    active = typ in (BusType.PV, BusType.SLACK) and not limited
    ctrl_str = "+".join(
        f.name for f in BusCtrl if f in ctrl and f.name
    ) or "NONE"

    return {
        "Type": typ.name,
        "Ctrl": ctrl_str,
        "Role": role.name if role != Role.NONE else "",
        "Lim": limited,
        "SVC": svc,
        "Eff": eff.name,
        "Reg": active,
    }


class BusCat:
    """Parsed bus type classifications from a solved power flow case.

    Fetches the ``BusCat`` field from PowerWorld, parses each bus
    into its type, control mode, regulation role, and limit status,
    then provides index-based access for selecting bus subsets.

    Typical usage after solving power flow::

        >>> pw = PowerWorld("case.pwb")
        >>> pw.pflow()
        >>> bc = pw.buscat.refresh()
        >>> pv = bc.pv_idx()
        >>> v_set = bc.v_setpoints()
        >>> q_buses = bc.has_q_eqn_idx()

    The internal DataFrame is available via the :attr:`df` property
    and contains one row per bus with columns: ``VSet``, ``LimLow``,
    ``LimHigh``, ``Type``, ``Ctrl``, ``Role``, ``Lim``, ``SVC``,
    ``Eff``, ``Reg``.

    Attributes
    ----------
    df : DataFrame
        Parsed classification data. Raises ``RuntimeError`` if
        accessed before :meth:`refresh` is called.
    """

    _COL_MAP = {
        "BusRGVoltSet": "VSet",
        "BusVoltLimLow": "LimLow",
        "BusVoltLimHigh": "LimHigh",
    }
    _FIELDS = [
        "BusCat", "BusRGVoltSet", "BusVoltLimLow", "BusVoltLimHigh",
    ]

    def __init__(self, pw=None):
        self._pw = pw
        self._df: Optional[DataFrame] = None

    @property
    def df(self) -> DataFrame:
        """Parsed bus classification DataFrame.

        Raises
        ------
        RuntimeError
            If :meth:`refresh` has not been called yet.
        """
        if self._df is None:
            raise RuntimeError(
                "No data. Call refresh() after solving power flow."
            )
        return self._df

    def refresh(self) -> 'BusCat':
        """Fetch BusCat from PowerWorld and rebuild classifications.

        Must be called after each power flow solve, since bus types
        can change when generators hit reactive limits.

        Returns
        -------
        BusCat
            Self, for method chaining.
        """
        raw = self._pw[Bus, self._FIELDS]
        df = raw.rename(columns=self._COL_MAP)
        parsed = DataFrame(
            [parse_buscat(c) for c in df["BusCat"]],
            index=raw.index,
        )
        self._df = pd.concat([df, parsed], axis=1).drop(columns=["BusCat"])
        return self

    def _idx(self, mask) -> list:
        """Return bus indices where mask is True."""
        return self.df.index[mask].tolist()

    def _mask_v_eqn(self):
        """Boolean mask for buses with a voltage equation."""
        return self.df["Eff"].isin([BusType.PV.name, BusType.SLACK.name])

    def slack_idx(self) -> list:
        """Indices of Slack buses."""
        return self._idx(self.df["Type"] == BusType.SLACK.name)

    def pv_idx(self, active_only: bool = True) -> list:
        """Indices of PV buses.

        Parameters
        ----------
        active_only : bool, default True
            If True, exclude PV buses that have hit a reactive
            limit (they are effectively PQ).
        """
        mask = self.df["Type"] == BusType.PV.name
        return self._idx(mask & self.df["Reg"]) if active_only else self._idx(mask)

    def pq_idx(self) -> list:
        """Indices of PQ buses (originally typed as PQ)."""
        return self._idx(self.df["Type"] == BusType.PQ.name)

    def eff_pv_idx(self) -> list:
        """Indices of buses effectively acting as PV."""
        return self._idx(self.df["Eff"] == BusType.PV.name)

    def eff_pq_idx(self) -> list:
        """Indices of buses effectively acting as PQ (includes limited PV)."""
        return self._idx(self.df["Eff"] == BusType.PQ.name)

    def has_p_eqn_idx(self) -> list:
        """Buses with an active power balance equation (all except Slack)."""
        return self._idx(self.df["Eff"] != BusType.SLACK.name)

    def has_q_eqn_idx(self) -> list:
        """Buses with a reactive power balance equation (effective PQ only)."""
        return self._idx(self.df["Eff"] == BusType.PQ.name)

    def no_q_eqn_idx(self) -> list:
        """Buses without a Q equation (PV and Slack regulate voltage instead)."""
        return self._idx(self.df["Eff"] != BusType.PQ.name)

    def has_v_eqn_idx(self) -> list:
        """Buses with a voltage magnitude equation (effective PV and Slack)."""
        return self._idx(self._mask_v_eqn())

    def v_setpoints(self):
        """Voltage setpoints for buses with a V equation.

        Returns values in the same order as :meth:`has_v_eqn_idx`.

        Returns
        -------
        numpy.ndarray
            Per-unit voltage setpoints.
        """
        return self.df.loc[self._mask_v_eqn(), "VSet"].values

    def constrained_idx(self) -> list:
        """Indices of buses at a reactive power limit."""
        return self._idx(self.df["Lim"])

    def svc_idx(self) -> list:
        """Indices of buses with SVC or continuous shunt control."""
        return self._idx(self.df["SVC"])

    def regulating_idx(self) -> list:
        """Indices of buses actively regulating voltage."""
        return self._idx(self.df["Reg"])

    # --- By regulation role ---

    def primary_idx(self) -> list:
        """Indices of primary regulating buses."""
        return self._idx(self.df["Role"] == Role.PRIMARY.name)

    def secondary_idx(self) -> list:
        """Indices of secondary regulating buses."""
        return self._idx(self.df["Role"] == Role.SECONDARY.name)

    def target_idx(self) -> list:
        """Indices of remotely regulated target buses."""
        return self._idx(self.df["Role"] == Role.TARGET.name)

    def local_only_idx(self) -> list:
        """Indices of regulating buses with local control only (no remote/droop)."""
        return self._idx((self.df["Role"] == "") & self.df["Reg"])

    # --- DataFrame accessors ---

    def pv(self, active_only: bool = True) -> DataFrame:
        """DataFrame of PV bus classifications.

        Parameters
        ----------
        active_only : bool, default True
            If True, only include PV buses still regulating.
        """
        mask = self.df["Type"] == BusType.PV.name
        return self.df[mask & self.df["Reg"]] if active_only else self.df[mask]

    def constrained(self) -> DataFrame:
        """DataFrame of buses at reactive power limits."""
        return self.df[self.df["Lim"]]

    def remote_masters(self) -> DataFrame:
        """DataFrame of primary regulating buses in remote control groups."""
        return self.df[self.df["Role"] == Role.PRIMARY.name]
