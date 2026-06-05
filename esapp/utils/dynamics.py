"""
Transient stability simulation utilities.

Provides field-watching, result retrieval, and result processing
for transient stability simulations in PowerWorld Simulator.
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Type, Optional

from pandas import DataFrame

from ..components import GObject
from ..saw._enums import TSGetResultsMode

logger = logging.getLogger(__name__)

__all__ = ['TSWatch', 'process_ts_results', 'get_ts_results']


class TSWatch:
    """
    Manages TS result field registration and environment preparation.

    Example
    -------
    >>> tsw = TSWatch()
    >>> tsw.watch(Gen, [TS.Gen.P, TS.Gen.W])
    >>> fields = tsw.prepare(pw)
    """

    def __init__(self):
        self._watch_fields: Dict[Type[GObject], List[str]] = {}

    def watch(self, gtype: Type[GObject], fields: List[Any]) -> 'TSWatch':
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
        TSWatch
            Self for method chaining.
        """
        field_names = [str(f) for f in fields]
        self._watch_fields[gtype] = field_names
        return self

    def prepare(self, pw) -> List[str]:
        """
        Configure the ESA environment for simulation and build retrieval fields.

        Parameters
        ----------
        pw : PowerWorld
            An initialized PowerWorld instance.

        Returns
        -------
        List[str]
            List of retrieval field strings for TSGetResults.
        """
        fields = []
        for gtype, flds in self._watch_fields.items():
            pw.esa.TSResultStorageSetAll(object=gtype.TYPE(), value=True)

            objs = pw[gtype, ['ObjectID']]

            if objs is not None and not objs.empty:
                valid_ids = objs['ObjectID'].dropna().unique()
                for oid in valid_ids:
                    fields.extend(f"{oid} | {f}" for f in flds)

        return fields

    @property
    def fields(self) -> Dict[Type[GObject], List[str]]:
        """Currently registered watch fields."""
        return self._watch_fields


def get_ts_results(esa, ctg: str, fields: List[str]) -> Tuple[Optional[DataFrame], Optional[DataFrame]]:
    """
    Retrieve results for a single contingency using TSGetResults.

    Parameters
    ----------
    esa : SAW
        The SAW (SimAuto Wrapper) instance.
    ctg : str
        Contingency name.
    fields : List[str]
        List of fields/plots to retrieve.

    Returns
    -------
    Tuple[Optional[DataFrame], Optional[DataFrame]]
        Tuple of (Metadata DataFrame, Data DataFrame), or (None, None).
    """
    result = esa.TSGetResults(TSGetResultsMode.SEPARATE, [ctg], fields)
    if result is None:
        return None, None
    return result


def process_ts_results(meta: DataFrame, df: DataFrame, ctg_name: str) -> Tuple[DataFrame, DataFrame]:
    """
    Clean and format raw transient stability simulation results.

    Parameters
    ----------
    meta : DataFrame
        Metadata DataFrame from TSGetResults.
    df : DataFrame
        Time-series data DataFrame from TSGetResults.
    ctg_name : str
        Name of the contingency (added as a column to metadata).

    Returns
    -------
    Tuple[DataFrame, DataFrame]
        (Processed metadata, Processed time-series data).
    """
    if df is None or df.empty:
        return DataFrame(), DataFrame()

    if "time" in df.columns:
        df = df.set_index("time")

    valid_headers = set(meta['ColHeader']) if 'ColHeader' in meta.columns else set()
    existing_cols = [c for c in df.columns if c in valid_headers]

    if not existing_cols:
        return DataFrame(), DataFrame()

    df_processed = df[existing_cols].astype(np.float32)

    meta = meta.rename(columns={
        'ObjectType': 'Object',
        'PrimaryKey': 'ID-A',
        'SecondaryKey': 'ID-B',
        'VariableName': 'Metric'
    })
    meta["Contingency"] = ctg_name

    return meta, df_processed
