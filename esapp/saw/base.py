import datetime
import locale
import logging
import os
import re
from typing import Union

import pythoncom
import win32com

from ._exceptions import (
    COMError,
    PowerWorldError,
    RPC_S_UNKNOWN_IF,
    RPC_S_CALL_FAILED,
)
from ._helpers import (
    convert_list_to_variant,
    get_temp_filepath,
)
# Set up locale
locale.setlocale(locale.LC_ALL, "")

# noinspection PyPep8Naming
class SAWBase(object):
    """Base class for the SimAuto Wrapper, containing core COM functionality."""

    SIMAUTO_PROPERTIES = {
        "CreateIfNotFound": bool,
        "CurrentDir": str,
        "UIVisible": bool,
    }

    def __init__(
        self,
        FileName,
        early_bind=False,
        UIVisible=False,
        CreateIfNotFound: bool = False,
        UseDefinedNamesInVariables: bool = False,
    ) -> None:
        """Initializes the SimAuto Wrapper (SAW) and establishes a COM connection to PowerWorld Simulator.

        Parameters
        ----------
        FileName : str
            Absolute or relative path to the PowerWorld case file (.pwb or .pwx).
        early_bind : bool, optional
            If True, uses `gencache` for faster COM calls (requires admin/write access to site-packages).
            Defaults to False.
        UIVisible : bool, optional
            If True, makes the PowerWorld Simulator application window visible. Defaults to False.
        CreateIfNotFound : bool, optional
            Sets the SimAuto property to create new objects during `ChangeParameters` calls. Defaults to False.
        UseDefinedNamesInVariables : bool, optional
            If True, configures the case to use defined names instead of internal IDs. Defaults to False.

        Raises
        ------
        Exception
            If the SimAuto COM server cannot be initialized (e.g., PowerWorld not installed or license issue).
        """
        self.log = logging.getLogger(self.__class__.__name__)
        locale_db = locale.localeconv()
        self.decimal_delimiter = locale_db["decimal_point"]
        pythoncom.CoInitialize()

        try:
            if early_bind:
                try:
                    self._pwcom = win32com.client.gencache.EnsureDispatch("pwrworld.SimulatorAuto")
                except AttributeError:  # pragma: no cover
                    self._pwcom = win32com.client.dynamic.Dispatch("pwrworld.SimulatorAuto")
            else:
                self._pwcom = win32com.client.dynamic.Dispatch("pwrworld.SimulatorAuto")
        except Exception as e:
            m = (
                "Unable to launch SimAuto. Please confirm that your PowerWorld license includes "
                "the SimAuto add-on, and that SimAuto has been successfully installed."
            )
            self.log.exception(m)
            raise e

        self.pwb_file_path = None
        self.set_simauto_property("CreateIfNotFound", CreateIfNotFound)
        self.set_simauto_property("UIVisible", UIVisible)

        # Initialize temporary file for UI updates
        self.empty_aux = get_temp_filepath(".axd")
        with open(self.empty_aux, "w") as f:
            pass

        self.OpenCase(FileName=FileName)

        version_string, self.build_date = self.get_version_and_builddate()
        self.version = int(re.search(r"\d+", version_string)[0])

        if UseDefinedNamesInVariables:
            self.exec_aux(
                'CaseInfo_Options_Value (Option,Value)\n{"UseDefinedNamesInVariables" "YES"}'
            )

        self._object_fields = {}


    def exit(self):
        """Closes the PowerWorld case, deletes temporary files, and releases the COM object.

        This method should be called when the SimAuto session is no longer needed
        to ensure proper cleanup and resource release.
        """
        if os.path.exists(self.empty_aux):
            os.unlink(self.empty_aux)
        self.CloseCase()
        del self._pwcom
        self._pwcom = None
        pythoncom.CoUninitialize()
        return None

    def set_simauto_property(self, property_name: str, property_value: Union[str, bool]):
        """Sets a property on the underlying SimAuto COM object.

        This method provides a controlled way to set various SimAuto properties,
        including validation of property names and value types.

        Parameters
        ----------
        property_name : str
            The name of the property to set (e.g., 'UIVisible', 'CurrentDir', 'CreateIfNotFound').
        property_value : Union[str, bool]
            The value to assign to the property. The type must match the expected type
            for the specific property.

        Raises
        ------
        ValueError
            If the `property_name` is unsupported, the `property_value` has an incorrect type,
            or if `CurrentDir` is set to an invalid path.
        """
        if property_name not in self.SIMAUTO_PROPERTIES:
            raise ValueError(
                f"The given property_name, {property_name}, is not currently supported. "
                f"Valid properties are: {list(self.SIMAUTO_PROPERTIES.keys())}"
            )

        if not isinstance(property_value, self.SIMAUTO_PROPERTIES[property_name]):
            m = (
                f"The given property_value, {property_value}, is invalid. "
                f"It must be of type {self.SIMAUTO_PROPERTIES[property_name]}."
            )
            raise ValueError(m)

        if property_name == "CurrentDir" and not os.path.isdir(property_value):
            raise ValueError(f"The given path for CurrentDir, {property_value}, is not a valid path!")

        self._set_simauto_property(property_name=property_name, property_value=property_value)

    def _set_simauto_property(self, property_name, property_value):
        """Internal helper to directly set a SimAuto COM property."""
        setattr(self._pwcom, property_name, property_value)

    def ProcessAuxFile(self, FileName):
        """Executes a PowerWorld auxiliary (.aux) file.

        Auxiliary files contain script commands or data definitions that PowerWorld
        can process to modify the case or perform actions.

        Parameters
        ----------
        FileName : str
            Path to the auxiliary (.aux) file.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found, syntax error in aux file).

        """
        return self._com_call("ProcessAuxFile", FileName)

    def _run_script(self, command: str, *args) -> None:
        """Execute a PowerWorld script command with optional arguments.

        This is the standard way for mixin methods to invoke PowerWorld script
        commands. It builds the command string and routes it through
        ``RunScriptCommand``.

        Parameters
        ----------
        command : str
            The script command name (e.g., ``"SolvePowerFlow"``, ``"GICCalculate"``).
        *args
            Arguments to pass to the command. ``None`` values are converted to
            empty strings. Trailing ``None`` values are stripped.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the script command fails.
        """
        # Strip trailing Nones
        arg_list = list(args)
        while arg_list and arg_list[-1] is None:
            arg_list.pop()

        if arg_list:
            arg_str = ", ".join("" if a is None else str(a) for a in arg_list)
            stmt = f"{command}({arg_str});"
        else:
            stmt = f"{command};"

        self.log.debug("RunScript: %s", stmt)
        return self.RunScriptCommand(stmt)

    def RunScriptCommand(self, Statements):
        """Executes one or more PowerWorld script statements.

        Parameters
        ----------
        Statements : str
            A string containing one or more PowerWorld script commands, separated by semicolons.
            See the "SCRIPT Section" in the Auxiliary File Format PDF for command syntax.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If any of the script commands fail.
        """
        return self._com_call("RunScriptCommand", Statements)

    def RunScriptCommand2(self, Statements: str, StatusMessage: str):
        """Executes script statements and provides a status message for the PowerWorld UI.

        This method is similar to `RunScriptCommand` but also allows displaying
        a custom message in the PowerWorld Simulator status bar.

        Parameters
        ----------
        Statements : str
            A string containing one or more PowerWorld script commands.
            See the "SCRIPT Section" in the Auxiliary File Format PDF for command syntax.

        StatusMessage : str
            A message to display in the PowerWorld Simulator status bar while the
            commands are being executed.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If any of the script commands fail.
        """
        return self._com_call("RunScriptCommand2", Statements, StatusMessage)


    @property
    def CreateIfNotFound(self):
        return self._pwcom.CreateIfNotFound

    @property
    def CurrentDir(self) -> str:
        return self._pwcom.CurrentDir

    @property
    def ProcessID(self) -> int:
        return self._pwcom.ProcessID

    @property
    def RequestBuildDate(self) -> int:
        return self._pwcom.RequestBuildDate

    @property
    def UIVisible(self) -> bool:
        return self._pwcom.UIVisible

    @property
    def ProgramInformation(self) -> tuple:
        """Tuple property: Detailed information about the Simulator version and license."""
        result = self._pwcom.ProgramInformation
        result = [list(x) for x in result]
        result[0][2] = datetime.datetime.fromtimestamp(result[0][2].timestamp(), tz=result[0][2].tzinfo)
        return tuple(tuple(x) for x in result)

    def _com_call(self, func: str, *args):
        """Internal helper to execute SimAuto COM methods and handle error codes.

        This method wraps all direct COM calls to PowerWorld Simulator, providing
        consistent error handling and unwrapping of results.

        Parameters
        ----------
        func : str
            The name of the SimAuto method to call (e.g., "OpenCase", "GetParametersMultipleElement").
        *args : Any
            Variable arguments to pass to the SimAuto method. These are typically
            converted to COM-compatible types (e.g., variants) before the call.

        Returns
        -------
        Any
            The data returned by SimAuto, unwrapped from the (Error, Result) tuple.
            Returns None if SimAuto indicates no data or an empty result.

        Raises
        ------
        AttributeError
            If `func` is not a valid SimAuto function.
        COMError
            If a COM-specific error occurs during the call.
        PowerWorldError
            If SimAuto returns an error message (e.g., invalid parameters, operation failed).
        """
        # repr() of variant payloads is expensive (renders the full data),
        # so skip building the message entirely unless DEBUG is enabled.
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug("COM call: %s(%s)", func, ", ".join(repr(a) for a in args))
        try:
            f = getattr(self._pwcom, func)
        except AttributeError:
            raise AttributeError(f"The given function, {func}, is not a valid SimAuto function.") from None

        try:
            output = f(*args)
        except Exception as e:
            # Handle specific RPC server unavailable/unknown interface errors
            msg = str(e)
            if hex(RPC_S_UNKNOWN_IF) in msg or hex(RPC_S_CALL_FAILED) in msg:
                m = f"SimAuto server crashed or is unresponsive during call to {func} with {args}. (RPC Error)"
                self.log.critical(m)
            m = f"An error occurred when trying to call {func} with {args}"
            self.log.exception(m)
            raise COMError(m) from e

        if output == ("",):
            return None

        try:
            if output is None or output[0] == "":
                pass
            elif not isinstance(output[0], str):
                pass
            elif "No data" not in output[0]:
                raise PowerWorldError.from_message(output[0])
        except TypeError as e:
            if "is not subscriptable" in e.args[0]:
                if output == -1:
                    m = (
                        f"PowerWorld simply returned -1 after calling '{func}' with '{args}'. "
                        "Unfortunately, that's all we can help you with. Perhaps the arguments are "
                        "invalid or in the wrong order - double-check the documentation."
                    )
                    raise PowerWorldError(m) from e
                elif isinstance(output, int):
                    return output
            raise e

        return output[1] if len(output) == 2 else output[1:]

    def _replace_decimal_delimiter(self, data):
        """Internal helper to replace locale-specific decimal delimiters with '.' in a Series.

        Parameters
        ----------
        data : pandas.Series
            The Series whose string elements might contain locale-specific decimal delimiters.

        Returns
        -------
        pandas.Series
            A new Series with decimal delimiters replaced, or the original Series
            if it does not contain string data.
        """
        try:
            return data.str.replace(self.decimal_delimiter, ".")
        except AttributeError:
            return data

    def exec_aux(self, aux: str, use_double_quotes: bool = False):
        """Executes an auxiliary command string directly.

        This method writes the provided `aux` string to a temporary .aux file
        and then processes it using `ProcessAuxFile`.

        Parameters
        ----------
        aux : str
            The auxiliary command string to execute.
        use_double_quotes : bool, optional
            If True, single quotes in `aux` will be replaced with double quotes. Defaults to False.
        """
        if use_double_quotes:
            aux = aux.replace("'", '"')
        fpath = get_temp_filepath(".aux")
        try:
            with open(fpath, "w") as f:
                f.write(aux)
            self.ProcessAuxFile(fpath)
        finally:
            os.unlink(fpath)

    def update_ui(self) -> None:
        """Triggers a refresh of the PowerWorld Simulator user interface.

        This can be useful after making programmatic changes that might not immediately reflect in the GUI.
        """
        return self.ProcessAuxFile(self.empty_aux)

    def set_logging_level(self, level: Union[int, str]) -> None:
        """Sets the logging level for the SAW instance logger.

        Parameters
        ----------
        level : int or str
            The logging level (e.g., logging.DEBUG, "DEBUG").
        """
        self.log.setLevel(level)
