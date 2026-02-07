"""QV (Reactive Power-Voltage) Analysis specific functions."""
import os
from pathlib import Path

import pandas as pd

from typing import Union

from esapp.saw._enums import YesNo, KeyFieldType
from ._helpers import get_temp_filepath


class QVMixin:
    """Mixin for QV analysis functions."""

    def QVDataWriteOptionsAndResults(self, filename: str, append: bool = True, key_field: Union[KeyFieldType, str] = KeyFieldType.PRIMARY):
        """
        Write all QV analysis information to an auxiliary file.

        Saves the same information as ``QVWriteResultsAndOptions`` but uses
        the concise format for DATA section headers and variable names. Data
        is written using DATA sections instead of SUBDATA sections.

        This is a wrapper for the ``QVDataWriteOptionsAndResults`` script command.

        Parameters
        ----------
        filename : str
            Name of the auxiliary file to save.
        append : bool, optional
            If True, appends results to existing file. If False, overwrites.
            Defaults to True.
        key_field : str, optional
            Identifier to use for data. "PRIMARY" uses bus numbers and primary
            key fields. "SECONDARY" uses bus name and nominal kV. "LABEL" uses
            device labels. Defaults to "PRIMARY".

        Returns
        -------
        str
            The response from the PowerWorld script command.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        app = YesNo.from_bool(append)
        return self._run_script("QVDataWriteOptionsAndResults", f'"{filename}"', app, key_field)

    def QVDeleteAllResults(self):
        """
        Delete all QV results from memory.

        Removes all QV analysis results including QVCurve and
        PWQVResultListContainer object types. Use this to free memory
        after QV analysis is complete.

        This is a wrapper for the ``QVDeleteAllResults`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("QVDeleteAllResults")

    def QVRun(self, filename: str = None, make_base_solvable: bool = True, write_case_after_solve: bool = False) -> pd.DataFrame:
        """
        Run a QV (Reactive Power-Voltage) analysis.

        Performs a QV study for buses whose QVSELECTED field is set to YES.
        QV analysis varies reactive power injection at monitored buses to
        determine voltage stability margins. The analysis produces QV curves
        showing the relationship between reactive power and voltage.

        This is a wrapper for the ``QVRun`` script command.

        Parameters
        ----------
        filename : str, optional
            Path to a CSV file to save results. If None, a temporary file is
            used and results are returned as a DataFrame. Defaults to None.
        make_base_solvable : bool, optional
            If True, attempts to fix the base case if it is not solvable
            before running the QV analysis. Defaults to True.
        write_case_after_solve : bool, optional
            If True, writes the case file after each QV solve point.
            Defaults to False.

        Returns
        -------
        pandas.DataFrame or None
            If `filename` is None, returns a DataFrame containing the QV
            analysis results (voltage vs. reactive power for each bus).
            Otherwise, returns None.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails or the QV analysis does not complete.
        """
        mbs = YesNo.from_bool(make_base_solvable)
        wcas = YesNo.from_bool(write_case_after_solve)
        if filename:
            self._run_script("QVRun", f'"{filename}"', mbs, wcas)
            return None
        else:
            temp_path = get_temp_filepath(".csv")

            try:
                self._run_script("QVRun", f'"{temp_path}"', mbs, wcas)
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    return pd.read_csv(temp_path)
                else:
                    return pd.DataFrame()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def QVSelectSingleBusPerSuperBus(self):
        """
        Reduce monitored QV buses to one per pnode (super bus).

        When using QV analysis on a full topology model, this modifies the
        monitored buses so that only one bus is monitored for each pnode.
        This simplifies analysis and reduces computational load by focusing
        on representative buses.

        This is a wrapper for the ``QVSelectSingleBusPerSuperBus`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("QVSelectSingleBusPerSuperBus")

    def QVWriteCurves(self, filename: str, include_quantities: bool = True, filter_name: str = "", append: bool = False):
        """
        Save QV curve points to a CSV file.

        Exports the QV curve data (voltage vs. reactive power points) for
        each monitored bus to a comma-separated file.

        This is a wrapper for the ``QVWriteCurves`` script command.

        Parameters
        ----------
        filename : str
            Name of the CSV file to save.
        include_quantities : bool, optional
            If True, includes any Quantities to Track along with the QV
            curve points. Defaults to True.
        filter_name : str, optional
            Filter applied to QVCurve objects. Empty string selects all
            curve results. Note: AREAZONE filtering is ignored for QVCurve.
            Defaults to "" (all curves).
        append : bool, optional
            If True, appends data to existing file. If False, overwrites.
            Defaults to False.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        iq = YesNo.from_bool(include_quantities)
        app = YesNo.from_bool(append)
        return self._run_script("QVWriteCurves", f'"{filename}"', iq, f'"{filter_name}"', app)

    def QVWriteResultsAndOptions(self, filename: str, append: bool = True):
        """
        Write all QV analysis information to an auxiliary file.

        Exports complete QV analysis data including Contingency Definitions,
        Remedial Action Definitions, Solution Options, QV Options, QV results,
        and any Model Criteria used by Contingency and Remedial Action
        Definitions.

        Dependencies are saved along with definitions, including: Model
        Conditions, Model Filters, Model Planes, Model Expressions, Model
        Result Overrides, Interfaces, Injection Groups, Calculated Fields,
        and Expressions.

        This is a wrapper for the ``QVWriteResultsAndOptions`` script command.

        Parameters
        ----------
        filename : str
            Name of the auxiliary file to save.
        append : bool, optional
            If True, appends data to existing file. If False, overwrites.
            Defaults to True.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        app = YesNo.from_bool(append)
        return self._run_script("QVWriteResultsAndOptions", f'"{filename}"', app)
