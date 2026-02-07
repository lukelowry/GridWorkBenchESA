"""General script commands and data interaction functions."""
from typing import List, Union
import os, re
import pandas as pd

from ._enums import (
    YesNo, format_filter, format_filter_areazone,
    PowerWorldMode, FileFormat,
)
from ._helpers import (format_list, get_temp_filepath,
                       parse_aux_content, build_aux_string)


class GeneralMixin:
    """Mixin for General Program Actions and Data Interaction."""

    def CopyFile(self, old_filename: str, new_filename: str):
        """Copies a file from `old_filename` to `new_filename`.

        Parameters
        ----------
        old_filename : str
            The path to the source file.
        new_filename : str
            The path to the destination file.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found, permission issues).
        """
        return self._run_script("CopyFile", f'"{old_filename}"', f'"{new_filename}"')

    def DeleteFile(self, filename: str):
        """Deletes a specified file.

        Parameters
        ----------
        filename : str
            The path to the file to delete.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found, permission issues).
        """
        return self._run_script("DeleteFile", f'"{filename}"')

    def RenameFile(self, old_filename: str, new_filename: str):
        """Renames a file from `old_filename` to `new_filename`.

        Parameters
        ----------
        old_filename : str
            The current path of the file.
        new_filename : str
            The new path/name for the file.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found, new name already exists).
        """
        return self._run_script("RenameFile", f'"{old_filename}"', f'"{new_filename}"')

    def WriteTextToFile(self, filename: str, text: str):
        """Writes a given text string to a file.

        Parameters
        ----------
        filename : str
            The path to the file where the text will be written.
        text : str
            The text string to write.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., permission issues).
        """
        escaped_text = text.replace('"', '""')
        return self._run_script("WriteTextToFile", f'"{filename}"', f'"{escaped_text}"')

    def LogAdd(self, text: str) -> None:
        """Adds a message to the PowerWorld Simulator Message Log.

        Parameters
        ----------
        text : str
            The message string to add to the log.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("LogAdd", f'"{text}"')

    def LogClear(self) -> None:
        """Clears all messages from the PowerWorld Simulator Message Log.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("LogClear")

    def LogShow(self, show: bool = True):
        """Shows or hides the PowerWorld Simulator Message Log window.

        Parameters
        ----------
        show : bool, optional
            If True, shows the Message Log window. If False, hides it. Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        yn = YesNo.from_bool(show)
        return self._run_script("LogShow", yn)

    def LogSave(self, filename: str, append: bool = False):
        """Saves the contents of the PowerWorld Simulator Message Log to a file.

        Parameters
        ----------
        filename : str
            The path to the file where the log will be saved.
        append : bool, optional
            If True, appends to the file if it exists. If False, overwrites the file.
            Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., permission issues).
        """
        app = YesNo.from_bool(append)
        return self._run_script("LogSave", f'"{filename}"', app)

    def SetCurrentDirectory(self, directory: str, create_if_not_found: bool = False):
        """Sets the current working directory for PowerWorld Simulator.

        This directory is used for resolving relative file paths in subsequent commands.

        Parameters
        ----------
        directory : str
            The path to the directory to set as current.
        create_if_not_found : bool, optional
            If True, creates the directory if it does not exist. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., invalid path, permission issues).
        """
        c = YesNo.from_bool(create_if_not_found)
        return self._run_script("SetCurrentDirectory", f'"{directory}"', c)

    def EnterMode(self, mode: Union[PowerWorldMode, str]) -> None:
        """Enters PowerWorld Simulator into a specific operating mode.

        Parameters
        ----------
        mode : Union[PowerWorldMode, str]
            The mode to enter. Must be PowerWorldMode.RUN, PowerWorldMode.EDIT,
            or the equivalent strings "RUN" / "EDIT".

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If `mode` is not "RUN" or "EDIT".
        PowerWorldError
            If the SimAuto call fails.
        """
        m = mode.value if isinstance(mode, PowerWorldMode) else mode.upper()
        if m not in [PowerWorldMode.RUN.value, PowerWorldMode.EDIT.value]:
            raise ValueError("Mode must be either 'RUN' or 'EDIT'.")
        return self._run_script("EnterMode", m)

    def StoreState(self, statename: str) -> None:
        """Stores the current state of the PowerWorld case under a given name.

        This creates a named snapshot of the case that can be restored later.

        Parameters
        ----------
        statename : str
            The name to assign to the stored state.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("StoreState", f'"{statename}"')

    def RestoreState(self, statename: str, state_type: str = "USER") -> None:
        """Restores a previously saved state by its name.

        Parameters
        ----------
        statename : str
            The name of the state to restore.
        state_type : str, optional
            The type of state to restore. Defaults to "USER".

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., state not found).
        """
        return self._run_script("RestoreState", state_type, f'"{statename}"')

    def DeleteState(self, statename: str, state_type: str = "USER") -> None:
        """Deletes a previously saved state by its name.

        Parameters
        ----------
        statename : str
            The name of the state to delete.
        state_type : str, optional
            The type of state to delete. Defaults to "USER".

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., state not found).
        """
        return self._run_script("DeleteState", state_type, f'"{statename}"')

    def LoadAux(self, filename: str, create_if_not_found: bool = False):
        """Loads an auxiliary (.aux) file into PowerWorld Simulator.

        Parameters
        ----------
        filename : str
            The path to the auxiliary file.
        create_if_not_found : bool, optional
            If True, attempts to create objects defined in the aux file if they don't exist.
            Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found, syntax error in aux file).
        """
        c = YesNo.from_bool(create_if_not_found)
        return self._run_script("LoadAux", f'"{filename}"', c)

    def ImportData(self, filename: str, filetype: Union[FileFormat, str] = FileFormat.CSV, header_line: int = 1, create_if_not_found: bool = False):
        """Imports data from a file in various formats into PowerWorld Simulator.

        Parameters
        ----------
        filename : str
            The path to the data file.
        filetype : str
            The format of the file (e.g., "CSV", "TXT", "PTI").
        header_line : int, optional
            The line number where the header (column names) is located. Defaults to 1.
        create_if_not_found : bool, optional
            If True, attempts to create objects if they don't exist. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        c = YesNo.from_bool(create_if_not_found)
        return self._run_script("ImportData", f'"{filename}"', filetype, header_line, c)

    def LoadCSV(self, filename: str, create_if_not_found: bool = False):
        """Loads a CSV file, typically one formatted similarly to output from `SendToExcel`.

        Parameters
        ----------
        filename : str
            The path to the CSV file.
        create_if_not_found : bool, optional
            If True, attempts to create objects if they don't exist. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        c = YesNo.from_bool(create_if_not_found)
        return self._run_script("LoadCSV", f'"{filename}"', c)

    def LoadScript(self, filename: str, script_name: str = ""):
        """Loads and runs a script from an auxiliary file.

        Parameters
        ----------
        filename : str
            The path to the auxiliary file containing the script.
        script_name : str, optional
            The name of the script within the file to execute. If empty, the first
            script in the file is run. Defaults to "".

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("LoadScript", f'"{filename}"', f'"{script_name}"')

    def SaveData(
        self,
        filename: str,
        filetype: str,
        objecttype: str,
        fieldlist: List[str],
        subdatalist: List[str] = None,
        filter_name: str = "",
        sortfieldlist: List[str] = None,
        transpose: bool = False,
        append: bool = True,
    ):
        """Saves data for specified objects and fields to a file using the `SaveData` script command.

        Parameters
        ----------
        filename : str
            The path to the output file.
        filetype : str
            The format of the output file (e.g., "CSV", "AUX", "TXT").
        objecttype : str
            The PowerWorld object type (e.g., "Bus", "Gen").
        fieldlist : List[str]
            A list of internal field names to save.
        subdatalist : List[str], optional
            A list of sub-data fields to save (e.g., for time series data). Defaults to None.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string (all).
        sortfieldlist : List[str], optional
            A list of fields to sort the output by. Defaults to None.
        transpose : bool, optional
            If True, transposes the output data (rows become columns, columns become rows).
            Defaults to False.
        append : bool, optional
            If True, appends data to the file if it exists. If False, overwrites.
            Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        fields = format_list(fieldlist)
        subs = format_list(subdatalist)
        sorts = format_list(sortfieldlist)

        filt = format_filter_areazone(filter_name)

        trans = YesNo.from_bool(transpose)
        app = YesNo.from_bool(append)

        return self._run_script("SaveData", f'"{filename}"', filetype, objecttype, fields, subs, filt, sorts, trans, app)

    def SaveDataWithExtra(self, filename: str, filetype: str, objecttype: str, fieldlist: List[str], subdatalist: List[str] = None, filter_name: str = "", sortfieldlist: List[str] = None, header_list: List[str] = None, header_value_list: List[str] = None, transpose: bool = False, append: bool = True):
        """Saves data with extra user-specified header fields and values.

        This method extends `SaveData` by allowing custom header information
        to be added to the output file, useful for metadata or tracking.

        Parameters
        ----------
        filename : str
            The path to the output file.
        filetype : str
            The format of the output file (e.g., "CSV", "AUX", "TXT").
        objecttype : str
            The PowerWorld object type (e.g., "Bus", "Gen").
        fieldlist : List[str]
            A list of internal field names to save.
        subdatalist : List[str], optional
            A list of sub-data fields to save. Defaults to None.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string.
        sortfieldlist : List[str], optional
            A list of fields to sort the output by. Defaults to None.
        header_list : List[str], optional
            A list of custom header names to add to the file. Defaults to None.
        header_value_list : List[str], optional
            A list of values corresponding to `header_list`. Defaults to None.
        transpose : bool, optional
            If True, transposes the output data. Defaults to False.
        append : bool, optional
            If True, appends data to the file. Defaults to True.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        fields = format_list(fieldlist)
        subs = format_list(subdatalist)
        sorts = format_list(sortfieldlist)
        headers = format_list(header_list, quote_items=True)
        values = format_list(header_value_list, quote_items=True)

        filt = format_filter_areazone(filter_name)
        trans = YesNo.from_bool(transpose)
        app = YesNo.from_bool(append)

        return self._run_script("SaveDataWithExtra", f'"{filename}"', filetype, objecttype, fields, subs, filt, sorts, headers, values, trans, app)

    def SetData(self, objecttype: str, fieldlist: List[str], valuelist: List[str], filter_name: str = ""):
        """Sets data for specified objects and fields.

        This is a generic method for modifying object parameters.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type (e.g., "Bus", "Gen").
        fieldlist : List[str]
            A list of internal field names to set.
        valuelist : List[str]
            A list of values corresponding to `fieldlist`.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string (all).

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        fields = format_list(fieldlist)
        values = format_list(valuelist, stringify=True)
        filt = format_filter(filter_name)
        return self._run_script("SetData", objecttype, fields, values, filt)

    def CreateData(self, objecttype: str, fieldlist: List[str], valuelist: List[str]):
        """Creates a new object of a specified type with initial field values.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type to create (e.g., "Bus", "Gen").
        fieldlist : List[str]
            A list of internal field names for the new object. This must include
            all primary key fields.
        valuelist : List[str]
            A list of values corresponding to `fieldlist` for the new object.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., object already exists, invalid parameters).
        """
        fields = format_list(fieldlist)
        values = format_list(valuelist, stringify=True)
        return self._run_script("CreateData", objecttype, fields, values)

    def GetSubData(self, objecttype: str, fieldlist: List[str], subdatalist: List[str] = None, filter_name: str = "") -> pd.DataFrame:
        """Retrieves object data including nested SubData sections as a DataFrame.

        SubData sections contain structured data like cost curves, reactive capability,
        or contingency elements that aren't available through standard CSV exports.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type (e.g., "Gen", "Load", "Contingency").
        fieldlist : List[str]
            A list of standard field names to retrieve.
        subdatalist : List[str], optional
            SubData section names to include (e.g., ["BidCurve", "ReactiveCapability"]).
            Defaults to None (no SubData).
        filter_name : str, optional
            A PowerWorld filter name to apply. Defaults to "" (all objects).

        Returns
        -------
        pd.DataFrame
            DataFrame where standard fields are scalar columns and SubData fields
            contain lists of lists (each inner list is one row from the SubData section).

        Examples
        --------
        >>> df = saw.GetSubData("Gen", ["BusNum", "GenID"], ["BidCurve"])
        >>> for _, row in df.iterrows():
        ...     print(f"Gen {row['BusNum']}: {len(row['BidCurve'])} bid points")
        """
        subdatalist = subdatalist or []
        tmp_path = get_temp_filepath(".aux")

        try:
            self.SaveData(tmp_path, "AUX", objecttype, fieldlist, subdatalist, filter_name, append=False)

            if not os.path.exists(tmp_path):
                return pd.DataFrame(columns=fieldlist + subdatalist)
            with open(tmp_path, 'r') as f:
                content = f.read()

            records = parse_aux_content(content, fieldlist, subdatalist)
            if not records:
                return pd.DataFrame(columns=fieldlist + subdatalist)
            return pd.DataFrame(records)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def SetSubData(self, objecttype: str, fieldlist: List[str],
                   records: List[dict],
                   subdatatype: Union[str, List[str], None] = None) -> None:
        """Write object data with optional SubData sections to PowerWorld via AUX.

        This is the write counterpart to ``GetSubData``. It constructs an AUX
        DATA block and processes it, creating or updating objects including
        their nested SubData sections.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type (e.g., "TSContingency", "Gen", "Contingency").
        fieldlist : List[str]
            Field names for the parent object's scalar columns.
        records : List[dict]
            Each dict must have keys matching ``fieldlist`` for scalar values.
            If ``subdatatype`` is specified, the dict may also contain a key
            matching each subdata type whose value is a list of lists (each
            inner list is one row of subdata values).
        subdatatype : str, List[str], or None
            Name(s) of the SubData section(s) (e.g., "CTGElement",
            "BidCurve", or ["BidCurve", "ReactiveCapability"]).
            If None, no subdata is written.

        Examples
        --------
        >>> saw.SetSubData(
        ...     "TSContingency",
        ...     ["TSCTGName", "StartTime", "EndTime", "CTGSkip"],
        ...     [{
        ...         "TSCTGName": "Fault1",
        ...         "StartTime": 0.0,
        ...         "EndTime": 10.0,
        ...         "CTGSkip": "NO",
        ...         "TSContingencyElement": [
        ...             ["FAULT BUS 1", 1.0],
        ...             ["CLEAR FAULT 1", 1.083],
        ...         ]
        ...     }],
        ...     subdatatype="TSContingencyElement"
        ... )
        """
        aux = build_aux_string(objecttype, fieldlist, records, subdatatype)
        self.exec_aux(aux)

    def SaveObjectFields(self, filename: str, objecttype: str, fieldlist: List[str]):
        """Saves a list of fields available for the specified objecttype to a file.

        Parameters
        ----------
        filename : str
            The path to the output file.
        objecttype : str
            The PowerWorld object type.
        fieldlist : List[str]
            A list of internal field names to save.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        fields = format_list(fieldlist)
        return self._run_script("SaveObjectFields", f'"{filename}"', objecttype, fields)

    def Delete(self, objecttype: str, filter_name: str = ""):
        """Deletes objects of a specified type, optionally filtered.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type to delete.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string (all).

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        filt = format_filter_areazone(filter_name)
        return self._run_script("Delete", objecttype, filt)

    def SelectAll(self, objecttype: str, filter_name: str = ""):
        """Sets the 'Selected' field to YES for objects of a specified type, optionally filtered.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string (all).

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        filt = format_filter_areazone(filter_name)
        return self._run_script("SelectAll", objecttype, filt)

    def UnSelectAll(self, objecttype: str, filter_name: str = ""):
        """Sets the 'Selected' field to NO for objects of a specified type, optionally filtered.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string (all).

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        filt = format_filter_areazone(filter_name)
        return self._run_script("UnSelectAll", objecttype, filt)

    def SendtoExcel(self, objecttype: str, fieldlist: List[str], filter_name: str = "", use_column_headers: bool = True, workbook: str = "", worksheet: str = "", sortfieldlist: List[str] = None, header_list: List[str] = None, header_value_list: List[str] = None, clear_existing: bool = True, row_shift: int = 0, col_shift: int = 0):
        """Sends data for specified objects and fields directly to Microsoft Excel with advanced options.

        This is an extended version of SendToExcel that provides additional control over
        Excel output including workbook/worksheet names, sorting, custom headers, and positioning.
        This method requires Microsoft Excel to be installed on the system.

        Parameters
        ----------
        objecttype : str
            The PowerWorld object type (e.g., "Bus", "Gen").
        fieldlist : List[str]
            A list of internal field names to export.
        filter_name : str, optional
            A PowerWorld filter name to apply to objects. Defaults to an empty string (all).
        use_column_headers : bool, optional
            If True, includes column headers in the Excel output. Defaults to True.
        workbook : str, optional
            The name of the Excel workbook to write to. If empty, a new workbook is created.
            Defaults to "".
        worksheet : str, optional
            The name of the worksheet within the workbook. If empty, a new worksheet is created.
            Defaults to "".
        sortfieldlist : List[str], optional
            A list of fields to sort the output by. Defaults to None.
        header_list : List[str], optional
            A list of custom header names to add to the Excel output. Defaults to None.
        header_value_list : List[str], optional
            A list of values corresponding to `header_list`. Defaults to None.
        clear_existing : bool, optional
            If True, clears existing data in the target worksheet before writing.
            Defaults to True.
        row_shift : int, optional
            Number of rows to shift the output down from the top-left corner. Defaults to 0.
        col_shift : int, optional
            Number of columns to shift the output right from the top-left corner. Defaults to 0.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., Excel not installed, invalid parameters).

        See Also
        --------
        SendToExcel : Basic version with fewer parameters for simple exports.
        """
        fields = format_list(fieldlist)
        filt = format_filter_areazone(filter_name)
        uch = YesNo.from_bool(use_column_headers)
        sorts = format_list(sortfieldlist)
        headers = format_list(header_list, quote_items=True)
        values = format_list(header_value_list, quote_items=True)
        ce = YesNo.from_bool(clear_existing)

        return self._run_script("SendtoExcel", objecttype, fields, filt, uch, f'"{workbook}"', f'"{worksheet}"', sorts, headers, values, ce, row_shift, col_shift)

    def LogAddDateTime(
        self,
        label: str,
        include_date: bool = True,
        include_time: bool = True,
        include_milliseconds: bool = False
    ):
        """Adds the current date and time to the PowerWorld Simulator Message Log.

        Use this action to add a timestamped entry to the message log for tracking
        when certain operations occur during script execution.

        Parameters
        ----------
        label : str
            A string which will appear at the start of the line containing the date/time.
        include_date : bool, optional
            If True, includes the date in the log entry. Defaults to True.
        include_time : bool, optional
            If True, includes the time in the log entry. Defaults to True.
        include_milliseconds : bool, optional
            If True, includes milliseconds in the time. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        id = YesNo.from_bool(include_date)
        it = YesNo.from_bool(include_time)
        im = YesNo.from_bool(include_milliseconds)
        return self._run_script("LogAddDateTime", f'"{label}"', id, it, im)

    def LoadAuxDirectory(
        self,
        file_directory: str,
        filter_string: str = "",
        create_if_not_found: bool = False
    ):
        """Loads multiple auxiliary files from a specified directory.

        The auxiliary files will be loaded in alphabetical order by name. This is
        useful for batch loading configuration files or data updates.

        Parameters
        ----------
        file_directory : str
            The directory where the auxiliary files are located.
        filter_string : str, optional
            A filter string using Windows wildcard patterns (e.g., ``*.aux``).
            If not specified, all files in the directory are loaded. Defaults to "".
        create_if_not_found : bool, optional
            If True, objects that cannot be found will be created while reading
            DATA sections from the files. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., directory not found).
        """
        c = YesNo.from_bool(create_if_not_found)
        if filter_string:
            return self._run_script("LoadAuxDirectory", f'"{file_directory}"', f'"{filter_string}"', c)
        else:
            return self._run_script("LoadAuxDirectory", f'"{file_directory}"', "", c)

    def LoadData(self, filename: str, data_name: str, create_if_not_found: bool = False):
        """Loads a named DATA section from another auxiliary file.

        This opens the auxiliary file denoted by filename but only reads the
        specific data section specified, ignoring other sections.

        Parameters
        ----------
        filename : str
            The filename of the auxiliary file being loaded.
        data_name : str
            The specific data section name from the auxiliary file that should be loaded.
        create_if_not_found : bool, optional
            If True, objects that cannot be found will be created. Defaults to False.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file or data section not found).
        """
        c = YesNo.from_bool(create_if_not_found)
        return self._run_script("LoadData", f'"{filename}"', data_name, c)

    def StopAuxFile(self):
        """Treats the remainder of the file after this command as a comment.

        This includes any script commands inside the present SCRIPT block,
        as well as all remaining SCRIPT or DATA blocks. Useful for temporarily
        disabling portions of an auxiliary file.

        Note: This command is primarily useful when executing auxiliary files
        directly, not when using SimAuto programmatically.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._run_script("StopAuxFile")
