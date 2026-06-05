"""PV (Power-Voltage) Analysis specific functions."""


from typing import Union

from esapp.saw._enums import YesNo, KeyFieldType


class PVMixin:
    """Mixin for PV analysis functions."""

    def PVClear(self):
        """
        Clear all results of the PV (Power-Voltage) study.

        This removes all computed results from a previous PV analysis,
        allowing a fresh study to be performed.

        This is a wrapper for the ``PVClear`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("PVClear")

    def PVRun(self, source: str, sink: str):
        """
        Start a PV (Power-Voltage) analysis.

        PV analysis incrementally transfers power from a source to a sink
        to determine the system's voltage stability limits. The analysis
        increases the transfer until voltage collapse occurs or limits are
        reached.

        This is a wrapper for the ``PVRun`` script command.

        Parameters
        ----------
        source : str
            The source of power for the PV study. Must be an injection group
            specified as '[INJECTIONGROUP "name"]' or '[INJECTIONGROUP "label"]'.
        sink : str
            The sink of power for the PV study. Must be an injection group
            specified as '[INJECTIONGROUP "name"]' or '[INJECTIONGROUP "label"]'.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("PVRun", source, sink)

    def PVDataWriteOptionsAndResults(self, filename: str, append: bool = True, key_field: Union[KeyFieldType, str] = KeyFieldType.PRIMARY):
        """
        Write all PV analysis information to an auxiliary file.

        Saves the same information as ``PVWriteResultsAndOptions`` but uses
        the concise format for DATA section headers and variable names. Data
        is written using DATA sections instead of SUBDATA sections.

        This is a wrapper for the ``PVDataWriteOptionsAndResults`` script command.

        Parameters
        ----------
        filename : str
            Name of the auxiliary file to save.
        append : bool, optional
            If True, appends results to existing file. If False, overwrites
            the file. Defaults to True.
        key_field : str, optional
            Identifier to use for data. Valid values are "PRIMARY" (bus numbers
            and primary key fields), "SECONDARY" (bus name and nominal kV),
            or "LABEL" (device labels). Defaults to "PRIMARY".

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        app = YesNo.from_bool(append)
        return self._run_script("PVDataWriteOptionsAndResults", f'"{filename}"', app, key_field)

    def PVDestroy(self):
        """
        Destroy the PV study and release resources.

        This removes all results and prevents any restoration of the
        initial state that is stored with the PV study. Use this when
        you are finished with a PV analysis and want to free memory.

        This is a wrapper for the ``PVDestroy`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("PVDestroy")

    def PVQVTrackSingleBusPerSuperBus(self):
        """
        Reduce monitored buses to one per super bus.

        If the topology processing add-on is installed, this examines each
        monitored value for each bus, determines if that bus is part of a
        super bus, and selects monitored buses so that only the pnode is
        monitored. This reduces computational overhead for PV/QV studies.

        This is a wrapper for the ``PVQVTrackSingleBusPerSuperBus`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("PVQVTrackSingleBusPerSuperBus")

    def PVSetSourceAndSink(self, source: str, sink: str):
        """
        Specify the source and sink elements for the PV study.

        Sets up the injection groups that define where power will be
        incrementally injected (source) and withdrawn (sink) during
        the PV analysis.

        This is a wrapper for the ``PVSetSourceAndSink`` script command.

        Parameters
        ----------
        source : str
            The source of power for the PV study. Must be an injection group
            specified as '[INJECTIONGROUP "name"]' or '[INJECTIONGROUP "label"]'.
        sink : str
            The sink of power for the PV study. Must be an injection group
            specified as '[INJECTIONGROUP "name"]' or '[INJECTIONGROUP "label"]'.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("PVSetSourceAndSink", source, sink)

    def PVStartOver(self):
        """
        Start over the PV study from the initial state.

        This clears the activity log, clears results, restores the initial
        state, sets the current state as the new initial state, and
        initializes the step size. Use this to reset a PV study without
        destroying it completely.

        This is a wrapper for the ``PVStartOver`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("PVStartOver")

    def PVWriteInadequateVoltages(self, filename: str, append: bool = True, inadequate_type: str = "LOW"):
        """
        Save PV inadequate voltages to a CSV file.

        Exports buses with voltage violations identified during the PV study
        to a CSV file. This helps identify which buses are most vulnerable
        to voltage collapse.

        This is a wrapper for the ``PVWriteInadequateVoltages`` script command.

        Parameters
        ----------
        filename : str
            Name of the CSV file to save.
        append : bool, optional
            If True, appends data to existing file. If False, overwrites
            the file. Defaults to True.
        inadequate_type : str, optional
            Type of inadequate voltages to save. Valid values are "LOW"
            (undervoltage), "HIGH" (overvoltage), or "BOTH". Defaults to "LOW".

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        app = YesNo.from_bool(append)
        return self._run_script("PVWriteInadequateVoltages", f'"{filename}"', app, inadequate_type)

    def PVWriteResultsAndOptions(self, filename: str, append: bool = True):
        """
        Write all PV analysis information to an auxiliary file.

        Exports complete PV analysis data including Contingency Definitions,
        Remedial Action Definitions, Solution Options, PV Options, PV results,
        ATC Extra Monitors, and any Model Criteria used by the Contingency
        and Remedial Action Definitions.

        Dependencies for the PV setup are also included, such as Injection
        Groups used as seller/buyer and Interfaces used for interface ramping.

        This is a wrapper for the ``PVWriteResultsAndOptions`` script command.

        Parameters
        ----------
        filename : str
            Name of the auxiliary file to save.
        append : bool, optional
            If True, appends data to existing file. If False, overwrites
            the file. Defaults to True.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        app = YesNo.from_bool(append)
        return self._run_script("PVWriteResultsAndOptions", f'"{filename}"', app)

    def RefineModel(self, object_type: str, filter_name: str, action: str, tolerance: float):
        """
        Refine the system model to fix modeling idiosyncrasies.

        This command helps prepare a model for voltage stability analysis
        by addressing common modeling issues that may cause numerical
        problems or unrealistic results.

        This is a wrapper for the ``RefineModel`` script command.

        Parameters
        ----------
        object_type : str
            The type of object to refine (e.g., "BUS", "GEN", "LOAD").
        filter_name : str
            Filter name to apply. Empty string means all objects of the type.
        action : str
            Action to perform on the filtered objects.
        tolerance : float
            Tolerance value for the refinement action.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        filt = f'"{filter_name}"' if filter_name else ""
        return self._run_script("RefineModel", object_type, filt, action, tolerance)
