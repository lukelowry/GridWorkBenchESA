"""
Transient Stability Simulation Example
=======================================

High-level interface for running transient stability simulations in
PowerWorld Simulator. Enables contingency definition, simulation
execution, and result retrieval through a fluent API.

Example
-------
    >>> from esapp import PowerWorld
    >>> from esapp.utils import ContingencyBuilder, SimAction, TSWatch
    >>> from dynamics import Dynamics  # with examples/ on sys.path
    >>> pw = PowerWorld("case.pwb")
    >>> dyn = Dynamics(pw)
    >>> dyn.watch(Gen, [TS.Gen.P, TS.Gen.W, TS.Gen.Delta])
    >>> dyn.bus_fault("Fault1", "101", fault_time=1.0, duration=0.1)
    >>> meta, results = dyn.solve("Fault1")
"""

import logging
import os
import re
from typing import List, Tuple, Dict, Union, Optional, Type

from pandas import DataFrame

from esapp.components import GObject, TS, TSContingency, TSContingencyElement
from esapp.utils.contingency import ContingencyBuilder, SimAction
from esapp.utils.dynamics import TSWatch
from esapp.saw._helpers import get_temp_filepath

logger = logging.getLogger(__name__)

__all__ = ['Dynamics']


class Dynamics:
    """
    Transient stability simulation manager.

    Parameters
    ----------
    pw : PowerWorld
        An initialized PowerWorld instance.

    Attributes
    ----------
    runtime : float
        Default simulation duration in seconds (default: 5.0).

    Example
    -------
    >>> dyn = Dynamics(pw)
    >>> dyn.runtime = 10.0
    >>> dyn.watch(Gen, [TS.Gen.P, TS.Gen.W])
    >>> dyn.bus_fault("Fault1", "101", fault_time=1.0, duration=0.1)
    >>> meta, data = dyn.solve("Fault1")
    """

    def __init__(self, pw) -> None:
        self.pw = pw
        self.runtime: float = 5.0
        self._pending_ctgs: Dict[str, ContingencyBuilder] = {}
        self._tswatch = TSWatch()

    def watch(self, gtype: Type[GObject], fields: list) -> 'Dynamics':
        """
        Register fields to record during simulation for a specific object type.

        Parameters
        ----------
        gtype : Type[GObject]
            The GObject type to watch (e.g., Gen, Bus, Branch).
        fields : list
            List of TS field constants or field name strings.

        Returns
        -------
        Dynamics
            Self for method chaining.
        """
        self._tswatch.watch(gtype, fields)
        return self

    def contingency(self, name: str) -> ContingencyBuilder:
        """
        Start building a new contingency.

        Parameters
        ----------
        name : str
            Unique name for the contingency.

        Returns
        -------
        ContingencyBuilder
            A builder instance for defining contingency events.
        """
        builder = ContingencyBuilder(name, self.runtime)
        self._pending_ctgs[name] = builder
        return builder

    def upload_contingency(self, name: str) -> None:
        """
        Compile and upload a pending contingency to the simulation engine.

        Parameters
        ----------
        name : str
            Name of the contingency to upload (must exist in pending list).

        Raises
        ------
        ValueError
            If the contingency name is not found in the pending list.
        """
        if name not in self._pending_ctgs:
            raise ValueError(f"Contingency '{name}' not found in pending list.")

        builder = self._pending_ctgs.pop(name)
        builder.runtime = self.runtime

        ctg_df, ele_df = builder.to_dataframes()

        self.pw[TSContingency] = ctg_df

        if not ele_df.empty:
            self.pw[TSContingencyElement] = ele_df

        logger.info(f"Uploaded contingency: {name} with {len(ele_df)} events.")

    def solve(self, ctgs: Union[str, List[str]]) -> Tuple[DataFrame, DataFrame]:
        """
        Run the simulation for the specified contingencies.

        Parameters
        ----------
        ctgs : Union[str, List[str]]
            A single contingency name or a list of names.

        Returns
        -------
        Tuple[DataFrame, DataFrame]
            (Metadata, Time-Series Data).
        """
        ctgs_to_solve = [ctgs] if isinstance(ctgs, str) else list(ctgs)

        for ctg in ctgs_to_solve:
            if ctg in self._pending_ctgs:
                self.upload_contingency(ctg)

        retrieval_fields = self._tswatch.prepare(self.pw)

        return self.pw.ts_solve(ctgs_to_solve, retrieval_fields)
