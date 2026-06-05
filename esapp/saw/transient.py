from pathlib import Path
from typing import List, Tuple, Union, Optional

import numpy as np
import pandas as pd
from ._enums import YesNo, TSGetResultsMode, KeyFieldType, FilterKeyword, FileFormat
from ._exceptions import PowerWorldError
from ._helpers import format_list, get_temp_filepath, load_ts_csv_results, pack_args

class TransientMixin:

    def TSTransferStateToPowerFlow(self, calculate_mismatch: bool = False):
        """Transfers the transient stability state to the power flow.

        After running a transient stability simulation, this allows the
        state of the system at the final time step to be loaded into the
        power flow solver for steady-state analysis.

        Parameters
        ----------
        calculate_mismatch : bool, optional
            If True, calculates power mismatch when transferring transient state
            to the power flow case. Defaults to False (no mismatch calculation).
        """
        cm = YesNo.from_bool(calculate_mismatch)
        self._run_script("TSTransferStateToPowerFlow", cm)

    def TSInitialize(self):
        """Initializes the transient stability simulation parameters.

        This command must be called before solving a transient stability
        run. It prepares the simulation engine with the model data.

        This is a wrapper for the ``TSInitialize`` script command.
        """
        try:
            self._run_script("TSInitialize")
        except PowerWorldError:
            self.log.warning("Failed to Initialize TS Values")

    def TSResultStorageSetAll(self, object="ALL", value=True):
        """Sets the 'Store results in RAM' flag for all objects of a given type.

        This is a wrapper for the ``TSResultStorageSetAll`` script command.

        Parameters
        ----------
        object : str, optional
            The PowerWorld object type (e.g., "GEN", "BUS", "BRANCH").
            Defaults to "ALL".
        value : bool, optional
            If True, results for this object type will be stored.
            If False, they will not. Defaults to True.
        """
        yn = YesNo.from_bool(value)
        self._run_script("TSResultStorageSetAll", object, yn)

    def TSSolve(
        self,
        ctgname: str,
        start_time: float = None,
        stop_time: float = None,
        step_size: float = None,
        step_in_cycles: bool = False,
    ):
        """Solves a single transient stability contingency.

        This is a wrapper for the ``TSSolve`` script command.

        Parameters
        ----------
        ctgname : str
            The name of the contingency to solve.
        start_time : float, optional
            Start time in seconds. Overrides the contingency's property.
        stop_time : float, optional
            Stop time in seconds. Overrides the contingency's property.
        step_size : float, optional
            Step size (in seconds unless step_in_cycles is True).
            Overrides the contingency's property.
        step_in_cycles : bool, optional
            If True, step_size is interpreted as cycles rather than seconds.
            Defaults to False.
        """
        if start_time is not None or stop_time is not None or step_size is not None:
            parts = []
            parts.append(str(start_time) if start_time is not None else "")
            parts.append(str(stop_time) if stop_time is not None else "")
            parts.append(str(step_size) if step_size is not None else "")
            sic = YesNo.from_bool(step_in_cycles)
            parts.append(str(sic))
            self.RunScriptCommand(f'TSSolve("{ctgname}", [{", ".join(parts)}])')
        else:
            self._run_script("TSSolve", f'"{ctgname}"')

    def TSSolveAll(self):
        """Solves all defined transient contingencies that are not set to skip.

        Distributed computing is not enabled by default.
        """
        self._run_script("TSSolveAll")

    def TSStoreResponse(self, object_type: str = "ALL", value: bool = True):
        """Convenience wrapper to toggle transient stability result storage.

        This is a high-level wrapper around ``TSResultStorageSetAll``.

        Parameters
        ----------
        object_type : str, optional
            The PowerWorld object type (e.g., "GEN", "BUS", "BRANCH").
            Defaults to "ALL".
        value : bool, optional
            If True, results will be stored. If False, they will not.
            Defaults to True.
        """
        self.TSResultStorageSetAll(object=object_type, value=value)

    def TSClearResultsFromRAM(
        self,
        ctg_name: str = "ALL",
        clear_summary: bool = True,
        clear_events: bool = True,
        clear_statistics: bool = True,
        clear_time_values: bool = True,
        clear_solution_details: bool = True,
    ):
        """Clears all transient stability results from RAM.

        This is useful for managing memory when running many simulations.

        This is a wrapper for the ``TSClearResultsFromRAM`` script command.
        """
        if ctg_name.upper() not in [FilterKeyword.ALL.value, FilterKeyword.SELECTED.value] and not ctg_name.startswith('"'):
            ctg_name = f'"{ctg_name}"'

        c_sum = YesNo.from_bool(clear_summary)
        c_evt = YesNo.from_bool(clear_events)
        c_stat = YesNo.from_bool(clear_statistics)
        c_time = YesNo.from_bool(clear_time_values)
        c_sol = YesNo.from_bool(clear_solution_details)
        try:
            self._run_script("TSClearResultsFromRAM", ctg_name, c_sum, c_evt, c_stat, c_time, c_sol)
        except Exception as e:
            if "access violation" in str(e).lower():
                self.log.warning("TSClearResultsFromRAM: PW access violation (no results in RAM to clear)")
            else:
                raise

    def TSClearPlayInSignals(self) -> None:
        """Deletes all defined PlayIn signals.

        This is a wrapper for the ``DELETE(PLAYINSIGNAL)`` script command.
        """
        self._run_script("DELETE", "PLAYINSIGNAL")

    def TSSetPlayInSignals(self, name: str, times: np.ndarray, signals: np.ndarray) -> None:
        """Sets PlayIn signals using an AUX file command.

        This method constructs and executes an AUX data block to define
        transient stability play-in signals.

        :param name: Name of the PlayIn Signal configuration.
        :param times: 1D NumPy array of time points.
        :param signals: 2D NumPy array of signal values (rows=time, cols=signals).
        """
        if times.ndim != 1 or signals.ndim != 2 or times.shape[0] != signals.shape[0]:
            raise ValueError("Dimension mismatch in times and signals arrays.")

        # Format Data Header
        header_fields = ["TSName", "TSTime"]
        if signals.shape[1] > 0:
            header_fields.append("TSSignal")
            for i in range(2, signals.shape[1] + 1):
                header_fields.append(f"TSSignal:{i}")

        header = f"DATA (PLAYINSIGNAL, [{', '.join(header_fields)}]){{\n"

        # Format each time record
        body = []
        for t, row in zip(times, signals):
            row_str = "\t".join([f"{d:.6f}" for d in row])
            body.append(f'"{name}"\t{t:.6f}\t{row_str}')

        cmd = header + "\n".join(body) + "\n}\n"

        # Execute
        self.exec_aux(cmd)

    def TSClearResultsFromRAMAndDisableStorage(self) -> None:
        """Disables result storage in RAM and clears any existing results.

        This is a convenience method that calls ``TSResultStorageSetAll(value=False)``
        followed by ``TSClearResultsFromRAM()``.
        """
        self.TSResultStorageSetAll(value=False)
        self.TSClearResultsFromRAM()

    def TSAutoCorrect(self):
        """Runs auto correction of parameters for transient stability.

        Attempts to automatically fix common model parameter issues.
        """
        return self._run_script("TSAutoCorrect")

    def TSClearAllModels(self):
        """Clears all transient stability models from the case."""
        return self._run_script("TSClearAllModels")

    def TSValidate(self):
        """Validates transient stability models and input values.

        Useful for examining model errors and warnings when preparing a case
        for analysis. Validation is done automatically when running transient
        analysis, so this command does not need to be run manually prior to
        analysis.
        """
        return self._run_script("TSValidate")

    def TSWriteOptions(
        self,
        filename: str,
        save_dynamic_model: bool = True,
        save_stability_options: bool = True,
        save_stability_events: bool = True,
        save_results_events: bool = True,
        save_plot_definitions: bool = True,
        save_transient_limit_monitors: bool = True,
        save_result_analyzer_time_window: bool = True,
        key_field: Union[KeyFieldType, str] = KeyFieldType.PRIMARY,
    ):
        """Save transient stability option settings to an auxiliary file."""
        opts = [
            YesNo.from_bool(save_dynamic_model),
            YesNo.from_bool(save_stability_options),
            YesNo.from_bool(save_stability_events),
            YesNo.from_bool(save_results_events),
            YesNo.from_bool(save_plot_definitions),
            YesNo.from_bool(save_transient_limit_monitors),
            YesNo.from_bool(save_result_analyzer_time_window),
        ]
        opt_str = format_list(opts)
        return self._run_script("TSWriteOptions", f'"{filename}"', opt_str, key_field)

    def TSLoadPTI(self, filename: str):
        """Loads transient stability data in the PTI DYR format.

        Parameters
        ----------
        filename : str
            Path to the PTI DYR file to load.
        """
        return self._run_script("TSLoadPTI", f'"{filename}"')

    def TSLoadGE(self, filename: str):
        """Loads transient stability data stored in the GE DYD format.

        Parameters
        ----------
        filename : str
            Path to the GE DYD file to load.
        """
        return self._run_script("TSLoadGE", f'"{filename}"')

    def TSLoadBPA(self, filename: str):
        """Loads transient stability data stored in the BPA format.

        Parameters
        ----------
        filename : str
            Path to the BPA file to load.
        """
        return self._run_script("TSLoadBPA", f'"{filename}"')

    def TSAutoInsertDistRelay(
        self, reach: float, add_from: bool, add_to: bool, transfer_trip: bool, shape: int, filter_name: str
    ):
        """Inserts DistRelay models on the lines meeting the specified filter."""
        af = YesNo.from_bool(add_from)
        at = YesNo.from_bool(add_to)
        tt = YesNo.from_bool(transfer_trip)
        self._run_script("TSAutoInsertDistRelay", reach, af, at, tt, shape, f'"{filter_name}"')

    def TSAutoInsertZPOTT(self, reach: float, filter_name: str):
        """Inserts ZPOTT models on the lines meeting the specified filter."""
        self._run_script("TSAutoInsertZPOTT", reach, f'"{filter_name}"')

    def TSAutoSavePlots(
        self,
        plot_names: List[str],
        ctg_names: List[str],
        image_type: str = "JPG",
        width: int = 800,
        height: int = 600,
        font_scalar: float = 1.0,
        include_case_name: bool = False,
        include_category: bool = False,
    ):
        """Create and save images of the plots."""
        plots = format_list(plot_names, quote_items=True)
        ctgs = format_list(ctg_names, quote_items=True)
        icn = YesNo.from_bool(include_case_name)
        icat = YesNo.from_bool(include_category)
        self._run_script("TSAutoSavePlots", plots, ctgs, image_type, width, height, font_scalar, icn, icat)

    def TSCalculateCriticalClearTime(self, element_or_filter: str):
        """Calculate critical clearing time for faults."""
        self._run_script("TSCalculateCriticalClearTime", element_or_filter)

    def TSCalculateSMIBEigenValues(self):
        """Calculate single machine infinite bus eigenvalues."""
        self._run_script("TSCalculateSMIBEigenValues")

    def TSClearModelsforObjects(self, object_type: str, filter_name: str = ""):
        """Deletes all transient stability models associated with the objects that meet the filter."""
        self._run_script("TSClearModelsforObjects", object_type, f'"{filter_name}"')

    def TSDisableMachineModelNonZeroDerivative(self, threshold: float = 0.001):
        """Disable machine models with non-zero state derivatives."""
        self._run_script("TSDisableMachineModelNonZeroDerivative", threshold)

    def TSGetVCurveData(self, filename: str, filter_name: str):
        """Generates V-curve data for synchronous generators."""
        self._run_script("TSGetVCurveData", f'"{filename}"', f'"{filter_name}"')

    def TSGetResults(
            self,
            mode: Union[TSGetResultsMode, str],
            contingencies: List[str],
            plots_fields: List[str],
            filename: Optional[str] = None,
            start_time: float = None,
            end_time: float = None,
        ) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
            """Retrieves transient stability results.

            If `filename` is None, creates a temporary file, reads the results
            into DataFrames, deletes the temporary files, and returns (meta,
            data).
            """
            # 1. Determine File Path
            is_temp_mode = filename is None
            file_path = Path(get_temp_filepath(".csv")) if is_temp_mode else Path(filename)

            # PowerWorld requires forward slashes
            pw_path_str = str(file_path).replace("\\", "/")

            # 2. Format Script Arguments
            ctgs_str = format_list(contingencies, quote_items=True)
            pfs_str = format_list(plots_fields, quote_items=True)

            # 3. Execute PowerWorld Command
            self._run_script("TSGetResults", f'"{pw_path_str}"', mode, ctgs_str, pfs_str, start_time, end_time)

            if not is_temp_mode:
                return None, None

            # 4. Retrieval and Cleanup
            return load_ts_csv_results(file_path, delete_files=True)

    def TSJoinActiveCTGs(
        self, time_delay: float, delete_existing: bool, join_with_self: bool, filename: str = "", first_ctg: str = "Both"
    ):
        """Joins two lists of TSContingency objects."""
        de = YesNo.from_bool(delete_existing)
        jws = YesNo.from_bool(join_with_self)
        self._run_script("TSJoinActiveCTGs", time_delay, de, jws, f'"{filename}"', first_ctg)

    def TSLoadRDB(self, filename: str, model_type: str, filter_name: str = ""):
        """Loads a SEL RDB file."""
        self._run_script("TSLoadRDB", f'"{filename}"', model_type, f'"{filter_name}"')

    def TSLoadRelayCSV(self, filename: str, model_type: str, filter_name: str = ""):
        """Loads relay data from CSV."""
        self._run_script("TSLoadRelayCSV", f'"{filename}"', model_type, f'"{filter_name}"')

    def TSPlotSeriesAdd(
        self,
        plot_name: str,
        sub_plot_num: int,
        axis_group_num: int,
        object_type: str,
        field_name: str,
        filter_name: str = "",
        attributes: str = "",
    ):
        """Adds one or multiple plot series to a new or existing plot definition."""
        self._run_script("TSPlotSeriesAdd", f'"{plot_name}"', sub_plot_num, axis_group_num, object_type, field_name, f'"{filter_name}"', f'"{attributes}"')

    def TSRunResultAnalyzer(self, ctg_name: str = ""):
        """Run the Transient Result Analyzer."""
        self._run_script("TSRunResultAnalyzer", f'"{ctg_name}"')

    def TSRunUntilSpecifiedTime(
        self,
        ctg_name: str,
        stop_time: float = None,
        step_size: float = 0.25,
        steps_in_cycles: bool = True,
        reset_start_time: bool = False,
        steps_to_do: int = 0,
    ):
        """Allows manual control of the transient stability run."""
        # Construct the options list for the second argument
        opt_list = [
            stop_time,
            step_size,
            YesNo.from_bool(steps_in_cycles),
            YesNo.from_bool(reset_start_time)
        ]
        if steps_to_do > 0:
            opt_list.append(steps_to_do)

        # Use pack_args to build the inner bracket content
        opt_content = pack_args(*opt_list)
        opt_str = f"[{opt_content}]"

        self._run_script("TSRunUntilSpecifiedTime", f'"{ctg_name}"', opt_str)

    def TSSaveBPA(self, filename: str, diff_case_modified_only: bool = False):
        """Saves transient stability data in the BPA IPF format.

        Parameters
        ----------
        filename : str
            Path for the output file.
        diff_case_modified_only : bool, optional
            If True, only saves models modified from base case. Defaults to False.
        """
        dc = YesNo.from_bool(diff_case_modified_only)
        self._run_script("TSSaveBPA", f'"{filename}"', dc)

    def TSSaveGE(self, filename: str, diff_case_modified_only: bool = False):
        """Saves transient stability data in the GE DYD format.

        Parameters
        ----------
        filename : str
            Path for the output file.
        diff_case_modified_only : bool, optional
            If True, only saves models modified from base case. Defaults to False.
        """
        dc = YesNo.from_bool(diff_case_modified_only)
        self._run_script("TSSaveGE", f'"{filename}"', dc)

    def TSSavePTI(self, filename: str, diff_case_modified_only: bool = False):
        """Saves transient stability data in the PTI DYR format.

        Parameters
        ----------
        filename : str
            Path for the output file.
        diff_case_modified_only : bool, optional
            If True, only saves models modified from base case. Defaults to False.
        """
        dc = YesNo.from_bool(diff_case_modified_only)
        self._run_script("TSSavePTI", f'"{filename}"', dc)

    def TSSaveTwoBusEquivalent(self, filename: str, bus_identifier: str):
        """Save the two bus equivalent model of a specified bus to a PWB file."""
        self._run_script("TSSaveTwoBusEquivalent", f'"{filename}"', bus_identifier)

    def TSWriteModels(self, filename: str, diff_case_modified_only: bool = False):
        """Saves transient stability dynamic model records to an auxiliary file.

        Parameters
        ----------
        filename : str
            Name and path for the output file. Typically with ``.aux`` extension.
        diff_case_modified_only : bool, optional
            If True, only saves models that are new or have had a parameter modified
            compared to the difference case tool base case. Defaults to False.
        """
        dc = YesNo.from_bool(diff_case_modified_only)
        self._run_script("TSWriteModels", f'"{filename}"', dc)

    def TSSetSelectedForTransientReferences(
        self, set_what: str, set_how: str, object_types: List[str], model_types: List[str]
    ):
        """Set the Custom Integer field or Selected field for objects referenced in a transient stability model."""
        objs = format_list(object_types)
        models = format_list(model_types)
        self._run_script("TSSetSelectedForTransientReferences", set_what, set_how, objs, models)

    def TSSaveDynamicModels(
        self, filename: str, file_type: Union[FileFormat, str] = "AUX", object_type: str = "", filter_name: str = "", append: bool = False
    ):
        """Save dynamics models for specified object types to file."""
        app = YesNo.from_bool(append)
        self._run_script("TSSaveDynamicModels", f'"{filename}"', file_type, object_type, f'"{filter_name}"', app)
