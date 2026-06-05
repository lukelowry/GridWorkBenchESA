from typing import List, Optional, Tuple, Union
from contextlib import contextmanager
import logging

import numpy as np
import pandas as pd
from pandas import DataFrame, concat

from .utils.gic import GIC
from .utils.network import Network
from .utils.buscat import BusCat
from .utils.dynamics import get_ts_results, process_ts_results
from .indexable import Indexable
from .components import Bus, Branch, Gen, Load, Shunt, Area, Zone, Sim_Solution_Options
from .saw._helpers import create_object_string
from .saw._enums import JacobianForm, SolverMethod, LinearMethod, PowerWorldMode, BranchDeviceType
from ._descriptors import SolverOption

import tempfile
import os

class PowerWorld(Indexable):
    """
    Main entry point for interacting with the PowerWorld grid model.
    """
    def __init__(self, fname: Optional[str] = None):
        """
        Initialize the PowerWorld interface.

        Parameters
        ----------
        fname : str, optional
            Path to the PowerWorld case file (.pwb).
        """
        # Embedded application modules (back-reference to self)
        self.network = Network(self)
        self.gic     = GIC(self)
        self.buscat  = BusCat(self)

        if fname:
            self.fname = fname
            self.open()
        else:
            self.esa = None
            self.fname = None

    # --- Solver Options (descriptors) ---

    #: Solve only one Newton iteration per call.
    do_one_iteration       = SolverOption('DoOneIteration')
    #: Disable optimal multiplier acceleration.
    disable_opt_mult       = SolverOption('DisableOptMult')
    #: Start from flat voltage profile (1.0 pu, 0 deg).
    flat_start             = SolverOption('FlatStart')
    #: Maximum Newton-Raphson iterations (int).
    max_iterations         = SolverOption('MaxItr', is_bool=False)
    #: Maximum voltage-constrained loop iterations (int).
    max_vcl_iterations     = SolverOption('MaxItr:1', is_bool=False)
    #: Power flow convergence tolerance (float).
    convergence_tol        = SolverOption('ConvergenceTol', is_bool=False)
    #: Minimum voltage for constant-current loads (float, pu).
    min_volt_i_load        = SolverOption('MinVoltILoad', is_bool=False)
    #: Minimum voltage for constant-impedance loads (float, pu).
    min_volt_s_load        = SolverOption('MinVoltSLoad', is_bool=False)

    #: Check switched shunt/contingency controls in inner loop.
    inner_ss_check         = SolverOption('SSContPFInnerLoop')
    #: Disable generator MVR limit checking.
    disable_gen_mvr_check  = SolverOption('DisableGenMVRCheck')
    #: Check generator VAR limits in inner loop.
    inner_check_gen_vars   = SolverOption('ChkVars')
    #: Back off generator VAR limits in inner loop.
    inner_backoff_gen_vars = SolverOption('ChkVars:1')
    #: Check transformer tap adjustments.
    check_taps             = SolverOption('ChkTaps')
    #: Check switched shunt adjustments.
    check_shunts           = SolverOption('ChkShunts')
    #: Check phase shifter adjustments.
    check_phase_shifters   = SolverOption('ChkPhaseShifters')
    #: Prevent control oscillations.
    prevent_oscillations   = SolverOption('PreventOscillations')

    #: Disable automatic angle rotation to slack bus.
    disable_angle_rotation = SolverOption('DisableAngleRotation')
    #: Allow multiple island solutions.
    allow_mult_islands     = SolverOption('AllowMultIslands')
    #: Evaluate solution quality per island.
    eval_solution_island   = SolverOption('EvalSolutionIsland')
    #: Enforce generator MW output limits.
    enforce_gen_mw_limits  = SolverOption('EnforceGenMWLimits')

    #: Enable DC power flow approximation mode.
    dc_mode                = SolverOption('DCPFMode')

    # --- Bus Voltage & Analysis ---

    def voltage(
        self,
        complex: bool = True,
        pu: bool = True,
    ) -> Union[pd.Series, Tuple[pd.Series, pd.Series]]:
        """
        Retrieve bus voltages.

        Parameters
        ----------
        complex : bool, default True
            If True, return complex voltage. Else (magnitude, angle_rad).
        pu : bool, default True
            If True, per-unit. Else kV.

        Returns
        -------
        pd.Series or tuple of pd.Series
            If ``complex=True``, a complex-valued Series V = |V| * exp(j*theta).
            If ``complex=False``, a tuple ``(magnitude, angle_rad)``.
        """
        fields = ["BusPUVolt", "BusAngle"] if pu else ["BusKVVolt", "BusAngle"]
        df = self[Bus, fields]
        mag = df[fields[0]]
        ang = df['BusAngle'] * np.pi / 180.0
        if complex:
            return mag * np.exp(1j * ang)
        return mag, ang

    def set_voltages(self, V: np.ndarray) -> None:
        """
        Set bus voltages from a complex vector.

        Parameters
        ----------
        V : np.ndarray
            Complex voltage vector (per-unit).
        """
        V_df = np.vstack([np.abs(V), np.angle(V, deg=True)]).T
        self[Bus, ["BusPUVolt", "BusAngle"]] = V_df

    def violations(self, v_min: float = 0.9, v_max: float = 1.1) -> DataFrame:
        """
        Return bus voltage violations.

        Parameters
        ----------
        v_min : float, default 0.9
            Low voltage threshold (pu).
        v_max : float, default 1.1
            High voltage threshold (pu).

        Returns
        -------
        DataFrame
            Columns 'Low' and 'High' with violating bus voltages.
        """
        v = self.voltage(complex=False, pu=True)[0]
        low = v[v < v_min]
        high = v[v > v_max]
        return DataFrame({'Low': low, 'High': high})

    def mismatch(self, asComplex: bool = False):
        """
        Return bus power mismatches.

        Parameters
        ----------
        asComplex : bool, default False
            If True, return P + jQ as complex Series.

        Returns
        -------
        tuple of pd.Series or pd.Series
            (P, Q) mismatches or complex S = P + jQ.
        """
        df = self[Bus, ["BusMismatchP", "BusMismatchQ"]]
        P = df['BusMismatchP']
        Q = df['BusMismatchQ']
        if asComplex:
            return P + 1j * Q
        return P, Q

    def netinj(self, asComplex: bool = False):
        """
        Sum of all generator, load, bus shunt, and switched shunt P and Q.

        Parameters
        ----------
        asComplex : bool, default False
            If True, return P + jQ as complex array.

        Returns
        -------
        tuple of np.ndarray or np.ndarray
            (P, Q) or complex S = P + jQ.
        """
        df = self[Bus, ['BusNetMW', 'BusNetMVR']]
        P = df['BusNetMW'].to_numpy()
        Q = df['BusNetMVR'].to_numpy()
        if asComplex:
            return P + 1j * Q
        return P, Q

    # --- Matrix Retrieval ---

    def ybus(self, dense: bool = False):
        """
        Return the Y-Bus matrix.

        Parameters
        ----------
        dense : bool, default False
            If True, return dense array. Else sparse CSR.

        Returns
        -------
        np.ndarray or scipy.sparse.csr_matrix
            The system admittance matrix (n_bus x n_bus).
        """
        return self.esa.get_ybus(dense)

    def jacobian(self, dense: bool = False, form: Union[JacobianForm, str] = JacobianForm.RECTANGULAR, ids: bool = False):
        """
        Get the power flow Jacobian matrix.

        Parameters
        ----------
        dense : bool, default False
            If True, return dense array. Else sparse CSR.
        form : str, default 'R'
            Coordinate form: 'R' (rectangular), 'P' (polar), 'DC' (B').
        ids : bool, default False
            If True, return ``(matrix, row_ids)`` with row/column labels.

        Returns
        -------
        np.ndarray or scipy.sparse.csr_matrix
            The power flow Jacobian matrix (when ``ids=False``).
        tuple
            ``(matrix, row_ids)`` when ``ids=True``.
        """
        if ids:
            return self.esa.get_jacobian_with_ids(dense, form=form)
        return self.esa.get_jacobian(dense, form=form)

    # --- Network Delegation ---

    def busmap(self) -> pd.Series:
        """
        Create mapping from bus numbers to matrix indices.

        Delegates to ``network.busmap()``.

        Returns
        -------
        pd.Series
            Series indexed by BusNum with positional index values.
        """
        return self.network.busmap()

    def buscoords(self, astuple: bool = True):
        """
        Retrieve bus latitude and longitude from substation data.

        Delegates to ``network.buscoords()``.

        Parameters
        ----------
        astuple : bool, default True
            If True, return ``(Longitude, Latitude)`` as a tuple of Series.
            If False, return a merged DataFrame.

        Returns
        -------
        tuple of pd.Series or DataFrame
            Bus geographic coordinates.
        """
        return self.network.buscoords(astuple)

    def pflow(self, getvolts: bool = True, method: Union[SolverMethod, str] = SolverMethod.POLARNEWT) -> Optional[Union[pd.Series, Tuple[pd.Series, pd.Series]]]:
        """
        Solve Power Flow.

        Parameters
        ----------
        getvolts : bool, optional
            Return voltages after solving. Defaults to True.
        method : str, optional
            Solution method. Defaults to "POLARNEWT".

        Returns
        -------
        pd.Series, tuple of pd.Series, or None
            Complex voltage Series if ``getvolts=True`` (default), or
            None if ``getvolts=False``.
        """
        self.esa.SolvePowerFlow(method)
        if getvolts:
            return self.voltage()

    def ts_solve(self, ctgs: Union[str, List[str]], fields: List[str]) -> Tuple[DataFrame, DataFrame]:
        """
        Run transient stability simulation for the specified contingencies.

        Handles auto-correction, initialization, solving each contingency,
        result retrieval, processing, and concatenation.

        Parameters
        ----------
        ctgs : Union[str, List[str]]
            A single contingency name or a list of names.
        fields : List[str]
            Retrieval field strings (e.g., from TSWatch.prepare).

        Returns
        -------
        Tuple[DataFrame, DataFrame]
            (Metadata, Time-Series Data).
        """
        logger = logging.getLogger(__name__)
        ctgs_list = [ctgs] if isinstance(ctgs, str) else list(ctgs)

        if not fields:
            logger.warning("No fields provided. Simulation will run but no results will be retrieved.")

        self.esa.TSAutoCorrect()
        self.esa.TSInitialize()

        all_meta_frames = []
        all_data_frames = {}

        for ctg in ctgs_list:
            logger.info(f"Solving contingency: {ctg}")
            self.esa.TSSolve(ctg)
            meta, df = get_ts_results(self.esa, ctg, fields)

            if meta is None or df is None or df.empty:
                logger.warning(f"No results returned for contingency: {ctg}")
                continue

            meta, df = process_ts_results(meta, df, ctg)
            if not df.empty:
                all_data_frames[ctg] = df
                all_meta_frames.append(meta)

        if not all_meta_frames:
            return DataFrame(), DataFrame()

        final_meta = concat(all_meta_frames, axis=0, ignore_index=True).set_index('ColHeader')
        final_data = concat(all_data_frames.values(), axis=1, keys=all_data_frames.keys()).sort_index(axis=1)

        return final_meta, final_data

    def flatstart(self) -> None:
        """Resets the case to a flat start (1.0 pu voltage, 0.0 angle)."""
        self.esa.ResetToFlatStart()

    def save(self, filename: Optional[str] = None) -> None:
        """
        Save the case to disk.

        Parameters
        ----------
        filename : str, optional
            Output file path. If None, overwrites the currently open case.
        """
        self.esa.SaveCase(filename)

    def log(self, message: str) -> None:
        """
        Add a message to the PowerWorld message log.

        Parameters
        ----------
        message : str
            The message text to append.
        """
        self.esa.LogAdd(message)

    def print_log(self, clear: bool = False, new_only: bool = False):
        """
        Prints the PowerWorld Message Log to the console.

        Parameters
        ----------
        clear : bool, optional
            If True, clears the log after printing. Defaults to False.
        new_only : bool, optional
            If True, only prints new entries. Defaults to False.

        Returns
        -------
        str
            The log contents.
        """
        if not hasattr(self, "_log_last_position"):
            self._log_last_position = 0

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            self.esa.LogSave(tmp_path, append=False)
            with open(tmp_path, "r") as f:
                content = f.read()
        finally:
            os.unlink(tmp_path)

        if new_only:
            output = content[self._log_last_position:]
        else:
            output = content

        self._log_last_position = len(content)

        if output.strip():
            print(output)

        if clear:
            self.esa.LogClear()
            self._log_last_position = 0

        return output

    def close(self) -> None:
        """Closes the current case."""
        self.esa.CloseCase()

    def edit_mode(self) -> None:
        """Enter PowerWorld into EDIT mode."""
        self.esa.EnterMode(PowerWorldMode.EDIT)

    def run_mode(self) -> None:
        """Enter PowerWorld into RUN mode."""
        self.esa.EnterMode(PowerWorldMode.RUN)

    # --- Data Retrieval ---

    def gens(self) -> DataFrame:
        """
        Retrieve generator outputs and status.

        Returns
        -------
        DataFrame
            Columns: ``GenMW``, ``GenMVR``, ``GenStatus``, plus key fields.
        """
        return self[Gen, ["GenMW", "GenMVR", "GenStatus"]]

    def loads(self) -> DataFrame:
        """
        Retrieve load demands and status.

        Returns
        -------
        DataFrame
            Columns: ``LoadMW``, ``LoadMVR``, ``LoadStatus``, plus key fields.
        """
        return self[Load, ["LoadMW", "LoadMVR", "LoadStatus"]]

    def shunts(self) -> DataFrame:
        """
        Retrieve switched shunt outputs and status.

        Returns
        -------
        DataFrame
            Columns: ``ShuntMW``, ``ShuntMVR``, ``ShuntStatus``, plus key fields.
        """
        return self[Shunt, ["ShuntMW", "ShuntMVR", "ShuntStatus"]]

    def lines(self) -> DataFrame:
        """
        Retrieve all transmission lines (excluding transformers).

        Returns
        -------
        DataFrame
            All branch fields for branches with ``BranchDeviceType == "Line"``.
        """
        branches = self[Branch, :]
        return branches[branches["BranchDeviceType"] == BranchDeviceType.LINE]

    def transformers(self) -> DataFrame:
        """
        Retrieve all transformers (excluding lines).

        Returns
        -------
        DataFrame
            All branch fields for branches with ``BranchDeviceType == "Transformer"``.
        """
        branches = self[Branch, :]
        return branches[branches["BranchDeviceType"] == BranchDeviceType.TRANSFORMER]

    def areas(self) -> DataFrame:
        """
        Retrieve all area objects with all available fields.

        Returns
        -------
        DataFrame
            All defined fields for Area objects.
        """
        return self[Area, :]

    def zones(self) -> DataFrame:
        """
        Retrieve all zone objects with all available fields.

        Returns
        -------
        DataFrame
            All defined fields for Zone objects.
        """
        return self[Zone, :]

    # --- Convenience Features ---

    @contextmanager
    def snapshot(self):
        """Context manager that saves and restores case state.

        Usage::

            with pw.snapshot():
                pw[Gen, "GenMW"] = modified_gen
                pw.pflow()
                v = pw.voltage()
            # state restored here
        """
        self.esa.SaveState()
        try:
            yield
        finally:
            self.esa.LoadState()

    def flows(self) -> DataFrame:
        """Retrieve branch power flows and loading.

        Returns
        -------
        DataFrame
            Columns: ``LineMW``, ``LineMVR``, ``LineMVA``, ``LinePercent``,
            plus branch key fields.
        """
        return self[Branch, ["LineMW", "LineMVR", "LineMVA", "LinePercent"]]

    def overloads(self, threshold: float = 100.0) -> DataFrame:
        """Return branches exceeding a loading threshold.

        Parameters
        ----------
        threshold : float, default 100.0
            Percent loading threshold.

        Returns
        -------
        DataFrame
            Subset of ``flows()`` where ``LinePercent > threshold``.
        """
        df = self.flows()
        return df[df["LinePercent"] > threshold]

    def ptdf(self, seller: int, buyer: int, method: Union[LinearMethod, str] = LinearMethod.DC) -> DataFrame:
        """Calculate Power Transfer Distribution Factors.

        Parameters
        ----------
        seller : int
            Seller bus number.
        buyer : int
            Buyer bus number.
        method : str, default "DC"
            Linear method: "DC", "DCPS", or "AC".

        Returns
        -------
        DataFrame
            Branch PTDF values (``LinePTDF`` column) plus key fields.
        """
        seller_str = create_object_string("Bus", seller)
        buyer_str = create_object_string("Bus", buyer)
        self.esa.CalculatePTDF(seller_str, buyer_str, method)
        return self[Branch, ["LinePTDF"]]

    def lodf(self, branch: tuple, method: Union[LinearMethod, str] = LinearMethod.DC) -> DataFrame:
        """Calculate Line Outage Distribution Factors.

        Parameters
        ----------
        branch : tuple
            Branch key as ``(from_bus, to_bus, circuit)``.
        method : str, default "DC"
            Linear method: "DC" or "DCPS".

        Returns
        -------
        DataFrame
            Branch LODF values (``LineLODF`` column) plus key fields.
        """
        branch_str = create_object_string("Branch", *branch)
        self.esa.CalculateLODF(branch_str, method)
        return self[Branch, ["LineLODF"]]

    # --- Quick Properties ---

    @property
    def n_bus(self) -> int:
        """Number of buses in the case."""
        return len(self[Bus])

    @property
    def n_branch(self) -> int:
        """Number of branches in the case."""
        return len(self[Branch])

    @property
    def n_gen(self) -> int:
        """Number of generators in the case."""
        return len(self[Gen])

    @property
    def sbase(self) -> float:
        """System MVA base."""
        return float(self[Sim_Solution_Options, "SBase"]["SBase"].iloc[0])

    def summary(self) -> dict:
        """Quick overview of the current case state.

        Returns
        -------
        dict
            Keys: ``n_bus``, ``n_branch``, ``n_gen``, ``n_load``,
            ``total_gen_mw``, ``total_load_mw``, ``v_min``, ``v_max``,
            ``sbase``.
        """
        g = self.gens()
        l = self.loads()
        v_mag = self.voltage(complex=False, pu=True)[0]
        return {
            'n_bus': self.n_bus,
            'n_branch': self.n_branch,
            'n_gen': len(g),
            'n_load': len(l),
            'total_gen_mw': g['GenMW'].sum(),
            'total_load_mw': l['LoadMW'].sum(),
            'v_min': v_mag.min(),
            'v_max': v_mag.max(),
            'sbase': self.sbase,
        }
