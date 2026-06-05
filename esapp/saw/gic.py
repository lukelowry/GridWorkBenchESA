"""Geomagnetically Induced Current (GIC) specific functions."""
from typing import List, Union

from ._enums import YesNo, KeyFieldType


class GICMixin:
    """Mixin for GIC analysis functions."""

    def GICCalculate(self, max_field: float, direction: float, solve_pf: bool = True):
        """Calculates the 'Single Snapshot' GIC solution for a uniform electric field.

        This method computes Geomagnetically Induced Currents (GIC) based on a
        specified electric field magnitude and direction.

        Parameters
        ----------
        max_field : float
            Maximum Electric Field in Volts/km.
        direction : float
            Storm Direction in degrees, from 0 to 360 (0=North, 90=East, 180=South, 270=West).
        solve_pf : bool, optional
            If True, includes the calculated GIC in the power flow solution.
            Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., GIC not enabled, invalid parameters).
        """
        spf = YesNo.from_bool(solve_pf)
        return self._run_script("GICCalculate", max_field, direction, spf)

    def GICClear(self):
        """Clears GIC (Geomagnetically Induced Current) values from the case.

        This is a wrapper for the ``GICClear`` script command.

        Returns
        -------
        None
        """
        return self._run_script("GICClear")

    def GICLoad3DEfield(self, file_type: str, filename: str, setup_on_load: bool = True):
        """Loads GIC data, including time-varying electric fields, from a specified file.

        Parameters
        ----------
        file_type : str
            The type of file to be loaded. Options are CSV, B3D, JSON, and DAT.
        filename : str
            The name (path) of the file to be loaded.
        setup_on_load : bool, optional
            If True, runs the procedure to set up time-varying series after loading the file.
            Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found, invalid format).
        """
        sol = YesNo.from_bool(setup_on_load)
        return self._run_script("GICLoad3DEfield", file_type, f'"{filename}"', sol)

    def GICReadFilePSLF(self, filename: str):
        """Reads GIC supplemental data from a GMD text file format.

        Parameters
        ----------
        filename : str,
            The name (path) of the file to be loaded, typically with a .GMD extension.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICReadFilePSLF", f'"{filename}"')

    def GICReadFilePTI(self, filename: str):
        """Reads GIC supplemental data from a GIC text file format.

        Parameters
        ----------
        filename : str,
            The name (path) of the file to be loaded, typically with a .GIC extension.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICReadFilePTI", f'"{filename}"')

    def GICSaveGMatrix(self, gmatrix_filename: str, gmatrix_id_filename: str):
        """Saves the GMatrix used with the GIC calculations in a file formatted for use with Matlab.

        The G-matrix represents the network's conductance properties relevant to GIC.

        Parameters
        ----------
        gmatrix_filename : str
            The path to the file where the G-matrix will be saved (e.g., a .mat file).
        gmatrix_id_filename : str
            The path to the file where a description of the rows and columns of the
            G-matrix will be saved (e.g., a .txt file).

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICSaveGMatrix", f'"{gmatrix_filename}"', f'"{gmatrix_id_filename}"')

    def GICSetupTimeVaryingSeries(self, start: float = 0.0, end: float = 0.0, delta: float = 0.0):
        """Creates a set of Branch series DC input voltages for time-varying GIC analysis.

        This is done from the Active Event(s) in the "Time-Varying Electric Field Inputs"
        Calculation Mode.

        Parameters
        ----------
        start : float, optional
            Start Time Offset in seconds. Defaults to 0.0.
        end : float, optional
            End Time Offset in seconds. Defaults to 0.0.
        delta : float, optional
            Sampling Rate (time step) in seconds. Defaults to 0.0.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICSetupTimeVaryingSeries", start, end, delta)

    def GICShiftOrStretchInputPoints(
        self,
        lat_shift: float = 0.0,
        lon_shift: float = 0.0,
        mag_scalar: float = 1.0,
        stretch_scalar: float = 1.0,
        update_time_varying_series: bool = False,
    ):
        """Scales, shifts, or stretches the active set of Time Varying Electric Field Inputs.

        This allows for adjusting the geographic and magnitude characteristics of the
        time-varying electric field model.

        Parameters
        ----------
        lat_shift : float, optional
            Latitude Shift in degrees. Defaults to 0.0.
        lon_shift : float, optional
            Longitude Shift in degrees. Defaults to 0.0.
        mag_scalar : float, optional
            E-Field Magnitude scalar multiplier. Defaults to 1.0.
        stretch_scalar : float, optional
            Geographic Stretch scalar multiplier. Defaults to 1.0.
        update_time_varying_series : bool, optional
            If True, updates the time-varying voltage input values after the shift/stretch.
            Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        update = YesNo.from_bool(update_time_varying_series)
        return self._run_script("GICShiftOrStretchInputPoints", lat_shift, lon_shift, mag_scalar, stretch_scalar, update)

    def GICTimeVaryingCalculate(self, the_time: float, solve_pf: bool = True):
        """Calculates GIC values using the 'Time-Varying Series Voltage Inputs' calculation mode.

        This method is used for dynamic GIC analysis where the electric field
        varies over time.

        Parameters
        ----------
        the_time : float
            Current Time Offset from Reference in seconds.
        solve_pf : bool, optional
            If True, includes GIC in the Power Flow and Transient Stability calculations.
            Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        spf = YesNo.from_bool(solve_pf)
        return self._run_script("GICTimeVaryingCalculate", the_time, spf)

    def GICTimeVaryingAddTime(self, new_time: float):
        """Adds a new time point to the time-varying voltage input series.

        Parameters
        ----------
        new_time : float
            The new time in seconds for which to add input values.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICTimeVaryingAddTime", new_time)

    def GICTimeVaryingDeleteAllTimes(self):
        """Deletes all input time-varying voltage input values.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICTimeVaryingDeleteAllTimes")

    def GICTimeVaryingEFieldCalculate(self, the_time: float, solve_pf: bool = True):
        """Calculates GIC Values using the 'Time-Varying Electric Field Inputs' calculation mode.

        Parameters
        ----------
        the_time : float
            Current Time Offset from Reference in seconds.
        solve_pf : bool, optional
            If True, includes GIC in the Power Flow and Transient Stability calculations.
            Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        spf = YesNo.from_bool(solve_pf)
        return self._run_script("GICTimeVaryingEFieldCalculate", the_time, spf)

    def GICTimeVaryingElectricFieldsDeleteAllTimes(self):
        """Clears all time-varying electric field input values.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICTimeVaryingElectricFieldsDeleteAllTimes")

    def GICWriteFilePSLF(self, filename: str, use_filters: bool = False):
        """Writes GIC supplemental data to a GMD text file format (PSLF).

        Parameters
        ----------
        filename : str
            The name (path) of the file to write, typically with a .GMD extension.
        use_filters : bool, optional
            If True, applies Area/Zone filters when writing the data. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        uf = YesNo.from_bool(use_filters)
        return self._run_script("GICWriteFilePSLF", f'"{filename}"', uf)

    def GICWriteFilePTI(self, filename: str, use_filters: bool = False, version: int = 4):
        """Writes GIC supplemental data to a GIC text file format (PTI).

        Parameters
        ----------
        filename : str
            The name (path) of the file to write, typically with a .GIC extension.
        use_filters : bool, optional
            If True, applies Area/Zone filters when writing the data. Defaults to False.
        version : int, optional
            The version number of the GIC file format to use. Defaults to 4.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        uf = YesNo.from_bool(use_filters)
        return self._run_script("GICWriteFilePTI", f'"{filename}"', uf, version)

    def GICWriteOptions(self, filename: str, key_field: Union[KeyFieldType, str] = KeyFieldType.PRIMARY):
        """Writes the current GIC solution options to an auxiliary file.

        Parameters
        ----------
        filename : str
            The name (path) of the auxiliary file to write the options to.
        key_field : str, optional
            The identifier to use for the data in the auxiliary file
            ("PRIMARY", "SECONDARY", or "LABEL"). Defaults to "PRIMARY".

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("GICWriteOptions", f'"{filename}"', key_field)
