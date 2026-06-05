"""Fault analysis specific functions."""


from typing import Union

from esapp.saw._enums import YesNo, FaultType


class FaultMixin:
    """Mixin for fault analysis functions."""

    def RunFault(
        self,
        element: str,
        fault_type: Union[FaultType, str],
        r: float = 0.0,
        x: float = 0.0,
        location: float = None,
    ):
        """Calculates fault currents for a single fault.

        This method simulates a fault at a specified element and calculates
        the resulting currents and voltages.

        Parameters
        ----------
        element : str
            The fault element string (e.g., '[BUS 1]', '[BRANCH 1 2 1]').
        fault_type : str
            The type of fault: "SLG" (Single Line to Ground), "LL" (Line to Line),
            "3PB" (Three Phase Balanced), or "DLG" (Double Line to Ground).
        r : float, optional
            Fault resistance in per unit. Defaults to 0.0.
        x : float, optional
            Fault reactance in per unit. Defaults to 0.0.
        location : float, optional
            Percentage distance (0-100) along the branch for branch faults.
            Required if `element` is a branch. Defaults to None.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., invalid element, fault type, or location).
        """
        # If location is None, it is omitted from the arguments
        if location is not None:
            return self._run_script("Fault", element, location, fault_type, r, x)
        else:
            return self._run_script("Fault", element, fault_type, r, x)

    def FaultClear(self):
        """Clears a single fault that has been calculated with the Fault command."""
        return self._run_script("FaultClear")

    def FaultAutoInsert(self):
        """Inserts multiple fault definitions using the Ctg_AutoInsert_Options object.

        Multiple fault definitions are inserted using the options in the
        Ctg_AutoInsert_Options object that are relevant for fault analysis.
        Faults can only be inserted for transmission lines or buses.
        """
        return self._run_script("FaultAutoInsert")

    def FaultMultiple(self, use_dummy_bus: bool = False):
        """Runs fault analysis on a list of defined faults.

        Parameters
        ----------
        use_dummy_bus : bool, optional
            If True, dummy buses are created and inserted at the specified
            percent location for branch faults, and faults are calculated at
            the dummy buses. If False, the fault is calculated at the branch
            terminal bus closest to the specified location. Defaults to False.
        """
        dummy = YesNo.from_bool(use_dummy_bus)
        return self._run_script("FaultMultiple", dummy)

    def LoadPTISEQData(self, filename: str, version: int = 33):
        """Loads sequence data in the PTI format.

        Parameters
        ----------
        filename : str
            Name of the file containing sequence data (typically ``.seq`` extension).
        version : int, optional
            Integer representing the PTI version of the SEQ file. Defaults to 33.
        """
        return self._run_script("LoadPTISEQData", f'"{filename}"', version)
