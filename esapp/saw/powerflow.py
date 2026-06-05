from typing import List, Union
import pandas as pd

from ._exceptions import PowerWorldError
from ._enums import YesNo, SolverMethod, FilterKeyword, KeyFieldType, FilterType, format_filter


class PowerflowMixin:

    def SolvePowerFlow(self, SolMethod: Union[SolverMethod, str] = SolverMethod.RECTNEWT) -> None:
        """Performs a single power flow solution.

        If the DC method is selected, the case is switched to DC power flow mode.
        If one of the other AC methods is selected, the case is switched to AC power
        flow mode. It may be difficult to solve a case with an AC power flow method
        once the case has been switched to DC power flow mode.

        Parameters
        ----------
        SolMethod : Union[SolverMethod, str], optional
            The solution method to use for the power flow calculation:

            - ``RECTNEWT``: Rectangular Newton-Raphson (default)
            - ``POLARNEWT``: Polar Newton-Raphson
            - ``GAUSSSEIDEL``: Gauss-Seidel
            - ``FASTDEC``: Fast Decoupled
            - ``ROBUST``: Attempts the robust solution process
            - ``DC``: DC power flow (switches case to DC mode)

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails or the power flow does not converge.
        """
        method = SolMethod.value if isinstance(SolMethod, SolverMethod) else SolMethod.upper()
        return self._run_script("SolvePowerFlow", method)

    def ClearPowerFlowSolutionAidValues(self):
        """Clears internal power flow solution aid values.

        PowerWorld Simulator maintains several internal flags that track which
        branches are closed or opened, as well as information to help estimate
        the generation change needed after making changes to load or generation.
        This information relates to angle smoothing and generator MW estimation
        features of the power flow solution.

        Typically, this information aids in getting successful power flow solutions.
        However, in some circumstances you may be using an AUX file to edit
        information you know is good and would not want PowerWorld to modify
        the initial bus voltage and angle nor the generator MW outputs before
        a solution is attempted. Call this command to clear all internally stored
        information so PowerWorld does not perform these pre-processing steps.
        """
        self._run_script("ClearPowerFlowSolutionAidValues")

    def ResetToFlatStart(self):
        """Resets all bus voltages to 1.0 per unit and angles to 0.

        This is a wrapper for the ``ResetToFlatStart`` script command.
        """
        self._run_script("ResetToFlatStart")

    def SetMVATolerance(self, tol: float = 0.1) -> None:
        """Sets the MVA Tolerance for Newton-Raphson convergence.

        Parameters
        ----------
        tol : float, optional
            The MVA tolerance value. Defaults to 0.1.
        """
        self.ChangeParametersSingleElement("Sim_Solution_Options", ["ConvergenceTol:2"], [str(tol)])

    def SetDoOneIteration(self, enable: bool = True) -> None:
        """Sets the 'Do One Iteration' power flow option.

        Parameters
        ----------
        enable : bool, optional
            If True, power flow will only perform one iteration. Defaults to True.
        """
        value = YesNo.from_bool(enable)
        self.ChangeParametersSingleElement("Sim_Solution_Options", ["DoOneIteration"], [value])

    def SetInnerLoopCheckMVars(self, enable: bool = True) -> None:
        """Sets the 'Check Mvar Limits Immediately' power flow option.

        Parameters
        ----------
        enable : bool, optional
            If True, the inner loop of the power flow will check Mvar limits
            before proceeding to the outer loop. Defaults to True.
        """
        value = YesNo.from_bool(enable)
        self.ChangeParametersSingleElement("Sim_Solution_Options", ["ChkVars"], [value])

    def GetMinPUVoltage(self) -> float:
        """Gets the minimum per-unit voltage magnitude in the case.

        Returns
        -------
        float
            The minimum p.u. voltage.
        """
        s = self.GetParametersSingleElement("PWCaseInformation", ["BusPUVolt:1"], [""])
        return float(s.iloc[0])

    def UpdateIslandsAndBusStatus(self):
        """Updates islands and bus status without requiring a power flow solution.

        Changes to branch and generator status impact islands and whether or not
        buses are connected. Islands and bus status are always updated at the
        beginning of a power flow solution if necessary, but this command makes
        it convenient to update this information without requiring a power flow
        solution.
        """
        return self._run_script("UpdateIslandsAndBusStatus")

    def ZeroOutMismatches(self, object_type: str = "BUSSHUNT"):
        """Forces mismatches to zero by changing bus shunts or loads.

        Bus shunts or loads are changed at each bus that has a mismatch greater
        than the MVA convergence tolerance so that the mismatch at that bus is
        forced to zero.

        Parameters
        ----------
        object_type : str, optional
            How to adjust the mismatch:

            - ``BUSSHUNT``: Adjust Bus Shunt fields at each bus (default)
            - ``LOAD``: Add a new load at each bus with mismatch (ID starting with Q1)
        """
        return self._run_script("ZeroOutMismatches", object_type)

    def ConditionVoltagePockets(self, voltage_threshold: float, angle_threshold: float, filter_name: FilterType = FilterKeyword.ALL):
        """Finds pockets of buses with bad initial voltage estimates and conditions them.

        Identifies pockets of buses bounded by branches that meet the condition that
        the absolute value of the voltage difference across the branch is greater than
        ``voltage_threshold`` or the absolute value of the angle difference is greater
        than ``angle_threshold``. The tool then estimates better voltages for buses
        in each pocket using known good values outside the pocket.

        Parameters
        ----------
        voltage_threshold : float
            Per-unit voltage difference (absolute value) threshold for identifying
            branches that bound voltage pockets.
        angle_threshold : float
            Angle difference in degrees (absolute value) threshold for identifying
            branches that bound voltage pockets.
        filter_name : str, optional
            Filter specifying which branches to check. Defaults to "ALL".
        """
        filt = format_filter(filter_name)
        return self._run_script("ConditionVoltagePockets", voltage_threshold, angle_threshold, filt)

    def EstimateVoltages(self, filter_name: str):
        """Estimates voltages and angles at buses meeting the filter.

        Parameters
        ----------
        filter_name : str
            Filter specifying which buses should have their voltages estimated.
        """
        filt = format_filter(filter_name)
        return self._run_script("EstimateVoltages", filt)

    def GenForceLDC_RCC(self, filter_name: str = ""):
        """Forces generators onto line drop / reactive current compensation.

        Parameters
        ----------
        filter_name : str, optional
            Filter specifying which generators to force. Defaults to all generators.
        """
        return self._run_script("GenForceLDC_RCC", f'"{filter_name}"')

    def SaveGenLimitStatusAction(self, filename: str):
        """Saves Mvar information about generators to a text file.

        Parameters
        ----------
        filename : str
            Path to the output text file.
        """
        return self._run_script("SaveGenLimitStatusAction", f'"{filename}"')

    def DiffCaseClearBase(self):
        """Clears the base case for the difference case comparison abilities of Simulator."""
        return self._run_script("DiffCaseClearBase")

    def DiffCaseSetAsBase(self):
        """Sets the present case as the base case for difference case comparison."""
        return self._run_script("DiffCaseSetAsBase")

    def DiffCaseKeyType(self, key_type: Union[KeyFieldType, str]):
        """Changes the key type used when comparing fields in difference case mode.

        Parameters
        ----------
        key_type : str
            Key type to use: ``PRIMARY``, ``SECONDARY``, or ``LABEL``.
        """
        return self._run_script("DiffCaseKeyType", key_type)

    def DiffCaseShowPresentAndBase(self, show: bool):
        """Toggles 'Show Present|Base in Difference and Change Mode'."""
        yn = YesNo.from_bool(show)
        return self._run_script("DiffCaseShowPresentAndBase", yn)

    def DiffCaseMode(self, mode: str):
        """Changes the mode for difference case comparison.

        Parameters
        ----------
        mode : str
            Display mode: ``PRESENT``, ``BASE``, ``DIFFERENCE``, or ``CHANGE``.
        """
        return self._run_script("DiffCaseMode", mode)

    def DiffCaseRefresh(self):
        """Refreshes the linking between the base case and the present case.

        Call this before saving data that identifies objects as being added or
        removed, especially if any topological differences have been made that
        affect the comparison.
        """
        return self._run_script("DiffCaseRefresh")

    def DiffCaseWriteCompleteModel(self, filename: str, append: bool = False, save_added: bool = True, save_removed: bool = True, save_both: bool = True, key_fields: Union[KeyFieldType, str] = KeyFieldType.PRIMARY, export_format: str = "", use_area_zone: bool = False, use_data_maintainer: bool = False, assume_base_meet: bool = True, include_clear_pf_aids: bool = True, delete_branches_flip: bool = False):
        """Creates an auxiliary file with difference case comparison information.

        Creates an auxiliary file containing information about objects that have been
        added or removed when comparing the present case to the base case. Fields
        that have changed for objects that exist in both cases can also be written.
        This auxiliary file can then be used to apply these same changes to other cases.

        Parameters
        ----------
        filename : str
            Name of the auxiliary file to create.
        append : bool, optional
            If True, append to existing file. Defaults to False.
        save_added : bool, optional
            If True, save added objects to the file. Defaults to True.
        save_removed : bool, optional
            If True, save removed objects to the file. Defaults to True.
        save_both : bool, optional
            If True, save changed fields for objects in both cases. Defaults to True.
        key_fields : str, optional
            Key field identifiers to use: ``PRIMARY`` or ``SECONDARY``. Defaults to "PRIMARY".
        export_format : str, optional
            Name of Auxiliary File Export Format Description to use. Defaults to "".
        use_area_zone : bool, optional
            If True, use Area/Zone/Owner filter for including objects. Defaults to False.
        use_data_maintainer : bool, optional
            If True, use Data Maintainer filter. Defaults to False.
        assume_base_meet : bool, optional
            If True, assume base case areas/zones/owners meet filters. Defaults to True.
        include_clear_pf_aids : bool, optional
            If True, include ClearPowerFlowSolutionAidValues command. Defaults to True.
        delete_branches_flip : bool, optional
            If True, treat branches with flipped bus order as removed and added. Defaults to False.
        """
        app = YesNo.from_bool(append)
        sa = YesNo.from_bool(save_added)
        sr = YesNo.from_bool(save_removed)
        sb = YesNo.from_bool(save_both)
        uaz = YesNo.from_bool(use_area_zone)
        udm = YesNo.from_bool(use_data_maintainer)
        abm = YesNo.from_bool(assume_base_meet)
        icp = YesNo.from_bool(include_clear_pf_aids)
        dbf = YesNo.from_bool(delete_branches_flip)

        return self._run_script("DiffCaseWriteCompleteModel", f'"{filename}"', app, sa, sr, sb, key_fields, f'"{export_format}"', uaz, udm, abm, icp, dbf)

    def DiffCaseWriteBothEPC(self, filename: str, ge_file_type: str = "GE19", use_area_zone: bool = False, base_area_zone_meet: bool = True, append: bool = False, export_format: str = "", use_data_maintainer: bool = False):
        """Saves elements that exist in both base and present cases in GE EPC format.

        Parameters
        ----------
        filename : str
            Name of the EPC file to create.
        ge_file_type : str, optional
            GE EPC file version (e.g., "GE18", "GE19", "PTI33"). Defaults to "GE19".
        use_area_zone : bool, optional
            If True, use Area/Zone/Owner filter. Defaults to False.
        base_area_zone_meet : bool, optional
            If True, assume base case meets filters. Defaults to True.
        append : bool, optional
            If True, append to existing file. Defaults to False.
        export_format : str, optional
            Export format name. Defaults to "".
        use_data_maintainer : bool, optional
            If True, use Data Maintainer filter. Defaults to False.
        """
        uaz = YesNo.from_bool(use_area_zone)
        baz = YesNo.from_bool(base_area_zone_meet)
        app = YesNo.from_bool(append)
        udm = YesNo.from_bool(use_data_maintainer)
        return self._run_script("DiffCaseWriteBothEPC", f'"{filename}"', ge_file_type, uaz, baz, app, f'"{export_format}"', udm)

    def DiffCaseWriteNewEPC(self, filename: str, ge_file_type: str = "GE19", use_area_zone: bool = False, base_area_zone_meet: bool = True, append: bool = False, use_data_maintainer: bool = False):
        """Saves elements that are new (added) in GE EPC format.

        Parameters
        ----------
        filename : str
            Name of the EPC file to create.
        ge_file_type : str, optional
            GE EPC file version (e.g., "GE18", "GE19", "PTI33"). Defaults to "GE19".
        use_area_zone : bool, optional
            If True, use Area/Zone/Owner filter. Defaults to False.
        base_area_zone_meet : bool, optional
            If True, assume base case meets filters. Defaults to True.
        append : bool, optional
            If True, append to existing file. Defaults to False.
        use_data_maintainer : bool, optional
            If True, use Data Maintainer filter. Defaults to False.
        """
        uaz = YesNo.from_bool(use_area_zone)
        baz = YesNo.from_bool(base_area_zone_meet)
        app = YesNo.from_bool(append)
        udm = YesNo.from_bool(use_data_maintainer)
        return self._run_script("DiffCaseWriteNewEPC", f'"{filename}"', ge_file_type, uaz, baz, app, udm)

    def DiffCaseWriteRemovedEPC(self, filename: str, ge_file_type: str = "GE19", use_area_zone: bool = False, base_area_zone_meet: bool = True, append: bool = False, use_data_maintainer: bool = False):
        """Saves elements that were removed in GE EPC format.

        Parameters
        ----------
        filename : str
            Name of the EPC file to create.
        ge_file_type : str, optional
            GE EPC file version (e.g., "GE18", "GE19", "PTI33"). Defaults to "GE19".
        use_area_zone : bool, optional
            If True, use Area/Zone/Owner filter. Defaults to False.
        base_area_zone_meet : bool, optional
            If True, assume base case meets filters. Defaults to True.
        append : bool, optional
            If True, append to existing file. Defaults to False.
        use_data_maintainer : bool, optional
            If True, use Data Maintainer filter. Defaults to False.
        """
        uaz = YesNo.from_bool(use_area_zone)
        baz = YesNo.from_bool(base_area_zone_meet)
        app = YesNo.from_bool(append)
        udm = YesNo.from_bool(use_data_maintainer)
        return self._run_script("DiffCaseWriteRemovedEPC", f'"{filename}"', ge_file_type, uaz, baz, app, udm)

    def DoCTGAction(self, action: str):
        """Applies a contingency action without the full contingency analysis framework.

        Parameters
        ----------
        action : str
            The contingency action string to execute.
        """
        return self._run_script("DoCTGAction", action)

    def InterfacesCalculatePostCTGMWFlows(self):
        """Updates Interface MW Flow fields on Contingent Interfaces.

        Calculates the post-contingency MW flows for interfaces that have
        contingent elements defined.
        """
        return self._run_script("InterfacesCalculatePostCTGMWFlows")

    def VoltageConditioning(self):
        """Performs voltage conditioning based on the Voltage Conditioning tool options.

        Uses the configured Voltage Conditioning options to improve initial voltage
        estimates throughout the network, which can help power flow convergence.
        """
        return self._run_script("VoltageConditioning")

    def SaveState(self) -> None:
        """Saves the current state of the PowerWorld case.

        This creates an unnamed snapshot of the case that can be restored later
        using `LoadState`.
        """
        return self._com_call("SaveState")

    def LoadState(self) -> None:
        """Loads the last saved state of the PowerWorld case."""
        return self._com_call("LoadState")
