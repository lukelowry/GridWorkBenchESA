"""Data retrieval and modification functions (SimAuto data access layer)."""
from typing import List, Tuple, Union

import numpy as np
import pandas as pd
import pythoncom

from ._enums import FieldListColumn, SpecificFieldListColumn
from ._exceptions import Error
from ._helpers import (
    convert_df_to_variant,
    convert_list_to_variant,
    convert_nested_list_to_variant,
)


class DataMixin:
    """Mixin for data retrieval, modification, enumeration, and export."""

    def ChangeParametersSingleElement(self, ObjectType: str, ParamList: list, Values: list) -> None:
        """Modifies parameters for a single object in PowerWorld.

        This method is used to update specific fields for a single PowerWorld object,
        identified by its primary key values (which must be included in `Values`).

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type (e.g., 'Bus', 'Gen').
        ParamList : List[str]
            A list of internal field names to modify. This list must include the
            primary key fields for the `ObjectType` to identify the target object.
        Values : List[Any]
            A list of values corresponding to the parameters in `ParamList`. The order
            and length must match `ParamList`.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., invalid object type, field name, or value).
        """
        return self._com_call(
            "ChangeParametersSingleElement",
            ObjectType,
            convert_list_to_variant(ParamList),
            convert_list_to_variant(Values),
        )

    def ChangeParametersMultipleElement(self, ObjectType: str, ParamList: list, ValueList: list) -> None:
        """Modifies parameters for multiple objects using a nested list of values.

        This method is suitable for updating a moderate number of objects where
        the data is structured as a list of lists. For very large datasets,
        `ChangeParametersMultipleElementRect` is generally more efficient.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        ParamList : List[str]
            A list of internal field names to modify. This list must include the
            primary key fields for the `ObjectType` to identify the target objects.
        ValueList : List[List[Any]]
            A list of lists, where each inner list contains values for one object.
            The order of values in each inner list must match `ParamList`.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._com_call(
            "ChangeParametersMultipleElement",
            ObjectType,
            convert_list_to_variant(ParamList),
            convert_nested_list_to_variant(ValueList),
        )

    def ChangeParametersMultipleElementRect(self, ObjectType: str, ParamList: list, df: pd.DataFrame) -> None:
        """
        Modifies parameters for multiple objects using a pandas DataFrame (rectangular data structure).

        This is generally the most efficient way to update a large number of objects at once.
        The DataFrame must include the primary key fields for the object type to identify
        which objects to update.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        ParamList : List[str]
            A list of internal field names being updated. These must correspond to the
            column names in the `df`.
        df : pandas.DataFrame
            A DataFrame containing the data to update. The column names of `df` must
            match the `ParamList`, and it must contain primary key columns.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._com_call(
            "ChangeParametersMultipleElementRect",
            ObjectType,
            convert_list_to_variant(ParamList),
            convert_df_to_variant(df),
        )

    def ChangeParametersMultipleElementFlatInput(
        self, ObjectType: str, ParamList: list, NoOfObjects: int, ValueList: list
    ) -> None:
        """Modifies parameters for multiple objects using a flat, 1-D list of values.

        This method is an alternative to `ChangeParametersMultipleElement` for cases
        where the data is already flattened.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        ParamList : List[str]
            A list of internal field names to modify.
        NoOfObjects : int
            The number of objects being updated.
        ValueList : List[Any]
            A flat list of values. Its length must be `NoOfObjects * len(ParamList)`.
            The values are ordered by object, then by parameter within each object.

        Returns
        -------
        None

        Raises
        ------
        Error
            If `ValueList` is not a 1-D array (i.e., it's a list of lists).
        PowerWorldError
            If the SimAuto call fails.
        """
        if isinstance(ValueList[0], list):
            raise Error("The value list has to be a 1-D array")
        return self._com_call(
            "ChangeParametersMultipleElementFlatInput",
            ObjectType,
            convert_list_to_variant(ParamList),
            NoOfObjects,
            convert_list_to_variant(ValueList),
        )

    def GetCaseHeader(self, filename: str = None) -> Tuple[str]:
        """Retrieves the header information from a PowerWorld case file.

        Parameters
        ----------
        filename : str, optional
            Path to the .pwb or .pwx file. If None, the header of the currently
            open case is retrieved.

        Returns
        -------
        tuple
            A tuple of strings, where each string is a line from the case header.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., file not found).
        """
        if filename is None:
            filename = self.pwb_file_path
        return self._com_call("GetCaseHeader", filename)

    def GetFieldList(self, ObjectType: str, copy=False) -> pd.DataFrame:
        """Retrieves the complete list of available fields for a given PowerWorld object type.

        This method queries PowerWorld for all fields associated with an object type
        and caches the result for performance.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type (e.g., 'Bus', 'Gen').
        copy : bool, optional
            If True, returns a deep copy of the cached field list DataFrame.
            Defaults to False.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing columns like 'key_field', 'internal_field_name',
            'field_data_type', 'description', 'display_name', and 'enterable'.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., invalid object type).
        """
        object_type = ObjectType.lower()
        try:
            output = self._object_fields[object_type]
        except KeyError:
            result = self._com_call("GetFieldList", ObjectType)
            result_arr = np.array(result)

            # Standard 5-column format, with the extended 6-column format
            # from newer Simulator versions as the fallback.
            try:
                output = pd.DataFrame(result_arr, columns=FieldListColumn.base_columns())
            except ValueError:
                output = pd.DataFrame(result_arr, columns=FieldListColumn.new_columns())

            output.sort_values(by=[FieldListColumn.INTERNAL_FIELD_NAME.value], inplace=True)
            self._object_fields[object_type] = output

        return output.copy(deep=True) if copy else output

    def GetParametersSingleElement(self, ObjectType: str, ParamList: list, Values: list) -> pd.Series:
        """Retrieves parameters for a single object identified by its primary keys.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type (e.g., 'Bus', 'Gen').
        ParamList : List[str]
            A list of internal field names to retrieve. This list must include the
            primary key fields for the `ObjectType` to identify the target object.
        Values : List[Any]
            A list containing the primary key values for the object, followed by
            empty strings or placeholders for other parameters in `ParamList` if they
            are not part of the key. The length must match `ParamList`.

        Returns
        -------
        pandas.Series
            A pandas Series containing the requested data, indexed by `ParamList`.

        Raises
        ------
        AssertionError
            If the length of `ParamList` and `Values` do not match.
        PowerWorldError
            If the SimAuto call fails.
        """
        assert len(ParamList) == len(Values), "The given ParamList and Values must have the same length."

        output = self._com_call(
            "GetParametersSingleElement",
            ObjectType,
            convert_list_to_variant(ParamList),
            convert_list_to_variant(Values),
        )

        return pd.Series(output, index=ParamList)

    def GetParametersMultipleElement(
        self, ObjectType: str, ParamList: list, FilterName: str = ""
    ) -> Union[pd.DataFrame, None]:
        """Retrieves parameters for multiple objects of a specific type, optionally filtered.

        This method is commonly used to fetch data for all objects of a given type
        or a subset defined by a PowerWorld filter.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type (e.g., 'Bus', 'Gen').
        ParamList : List[str]
            A list of internal field names to retrieve.
        FilterName : str, optional
            Optional name of a PowerWorld filter to restrict the result set.
            Defaults to an empty string, meaning no filter is applied.

        Returns
        -------
        Union[pandas.DataFrame, None]
            A pandas DataFrame where columns correspond to `ParamList`.
            Returns None if no objects are found matching the criteria.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., invalid object type or field names).
        """
        output = self._com_call(
            "GetParametersMultipleElement",
            ObjectType,
            convert_list_to_variant(ParamList),
            FilterName,
        )
        if output is None:
            return output

        return pd.DataFrame(np.array(output).transpose(), columns=ParamList)

    def GetParamsRectTyped(
        self, ObjectType: str, ParamList: list, FilterName: str = ""
    ) -> Union[pd.DataFrame, None]:
        """Retrieves data in a rectangular format with PowerWorld's native variant typing preserved.

        This method is similar to `GetParametersMultipleElement` but attempts to preserve
        the original data types as returned by SimAuto, which can sometimes be more efficient
        or necessary for specific use cases.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        ParamList : List[str]
            A list of internal field names to retrieve.
        FilterName : str, optional
            Optional name of a PowerWorld filter to apply. Defaults to an empty string.

        Returns
        -------
        Union[pandas.DataFrame, None]
            A pandas DataFrame containing the requested data. Returns None if no objects found.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        output = self._com_call(
            "GetParamsRectTyped",
            ObjectType,
            convert_list_to_variant(ParamList),
            FilterName,
            pythoncom.VT_VARIANT,
        )
        if output is None:
            return output

        return pd.DataFrame(output, columns=ParamList)

    def GetParametersMultipleElementFlatOutput(
        self, ObjectType: str, ParamList: list, FilterName: str = ""
    ) -> Union[None, Tuple[str]]:
        """Retrieves data for multiple elements in a flat, 1-D output format.

        The data is returned as a single tuple of strings, where values for each
        object are concatenated. This format can be less convenient for direct
        DataFrame conversion but might be useful for specific parsing needs.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        ParamList : List[str]
            A list of internal field names to retrieve.
        FilterName : str, optional
            Optional name of a PowerWorld filter to apply. Defaults to an empty string.

        Returns
        -------
        Union[None, Tuple[str]]
            A tuple of strings containing the data. Returns None if no data is found.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        result = self._com_call(
            "GetParametersMultipleElementFlatOutput",
            ObjectType,
            convert_list_to_variant(ParamList),
            FilterName,
        )

        if len(result) == 0:
            return None
        else:
            return result

    def GetSpecificFieldList(self, ObjectType: str, FieldList: List[str]) -> pd.DataFrame:
        """Retrieves detailed metadata for a specific subset of fields for a given object type.

        This method provides more detailed information about specific fields,
        including their display names and whether they are enterable.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        FieldList : List[str]
            A list of internal field names to query metadata for.

        Returns
        -------
        pandas.DataFrame
            A DataFrame with columns like 'variablename:location', 'field',
            'column header', 'field description', and 'enterable'.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        base_cols = SpecificFieldListColumn.base_columns()
        new_cols = SpecificFieldListColumn.new_columns()
        sort_col = SpecificFieldListColumn.VARIABLENAME_LOCATION.value

        try:
            df = (
                pd.DataFrame(
                    self._com_call("GetSpecificFieldList", ObjectType, convert_list_to_variant(FieldList)),
                    columns=base_cols,
                )
                .sort_values(by=sort_col)
                .reset_index(drop=True)
            )
        except ValueError:
            df = (
                pd.DataFrame(
                    self._com_call("GetSpecificFieldList", ObjectType, convert_list_to_variant(FieldList)),
                    columns=new_cols,
                )
                .sort_values(by=sort_col)
                .reset_index(drop=True)
            )
        return df

    def GetSpecificFieldMaxNum(self, ObjectType: str, Field: str) -> int:
        """Retrieves the maximum index for a field that supports multiple entries (e.g., CustomFloat).

        Some PowerWorld fields, like 'CustomFloat', can have multiple instances
        (e.g., 'CustomFloat:1', 'CustomFloat:2'). This method returns the highest
        available index for such a field.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type.
        Field : str
            The base field name (e.g., 'CustomFloat').

        Returns
        -------
        int
            The maximum integer index available for the specified field.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._com_call("GetSpecificFieldMaxNum", ObjectType, Field)

    def ListOfDevices(self, ObjType: str, FilterName="") -> Union[None, pd.DataFrame]:
        """Retrieves a list of all objects of a specific type and their primary keys.

        This method is useful for getting an inventory of all objects of a certain type
        in the case, or a filtered subset.

        Parameters
        ----------
        ObjType : str
            The PowerWorld object type (e.g., 'Bus', 'Gen').
        FilterName : str, optional
            Optional name of a PowerWorld filter to apply. Defaults to an empty string.

        Returns
        -------
        Union[None, pandas.DataFrame]
            A pandas DataFrame containing the primary key fields for the objects.
            Returns None if no objects are found.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        # Get key field metadata to know column names
        key_col = FieldListColumn.KEY_FIELD.value
        name_col = FieldListColumn.INTERNAL_FIELD_NAME.value

        field_list = self.GetFieldList(ObjectType=ObjType, copy=False)
        key_field_mask = field_list[key_col].str.match(r"\*[0-9]+[A-Z]*\*").to_numpy()
        key_field_df = field_list.loc[key_field_mask].copy()
        key_field_df[key_col] = key_field_df[key_col].str.replace(r"\*", "", regex=True)
        key_field_df[key_col] = key_field_df[key_col].str.replace("[A-Z]*", "", regex=True)
        key_field_series = key_field_df[key_col]
        if self.decimal_delimiter != ".":
            try:
                key_field_series = key_field_series.str.replace(self.decimal_delimiter, ".")
            except AttributeError:
                pass
        key_field_df["key_field_index"] = pd.to_numeric(key_field_series, errors='coerce').fillna(key_field_df[key_col]) - 1
        key_field_df.sort_values(by="key_field_index", inplace=True)
        column_names = key_field_df[name_col].to_numpy()

        output = self._com_call("ListOfDevices", ObjType, FilterName)

        all_none = all(i is None for i in output)

        if all_none:
            return None

        df = pd.DataFrame(output).transpose()
        df.columns = column_names

        return df

    def ListOfDevicesAsVariantStrings(self, ObjType: str, FilterName="") -> tuple:
        """Retrieves a list of devices where primary keys are returned as variant strings.

        This method returns the primary keys as a tuple of strings, which might be
        useful for direct use in other SimAuto commands that expect string identifiers.

        Parameters
        ----------
        ObjType : str
            The PowerWorld object type.
        FilterName : str, optional
            Optional name of a PowerWorld filter to apply. Defaults to an empty string.

        Returns
        -------
        tuple
            A tuple of strings, where each string represents the primary key(s) of an object.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._com_call("ListOfDevicesAsVariantStrings", ObjType, FilterName)

    def ListOfDevicesFlatOutput(self, ObjType: str, FilterName="") -> tuple:
        """Retrieves a list of devices in a flat, 1-D output format.

        Similar to `ListOfDevicesAsVariantStrings`, but the output format might differ
        slightly depending on the SimAuto version.

        Parameters
        ----------
        ObjType : str
            The PowerWorld object type.
        FilterName : str, optional
            Optional name of a PowerWorld filter to apply. Defaults to an empty string.

        Returns
        -------
        tuple
            A tuple of strings.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails.
        """
        return self._com_call("ListOfDevicesFlatOutput", ObjType, FilterName)

    def SendToExcel(self, ObjectType: str, FilterName: str, FieldList) -> None:
        """Exports data for the specified objects directly to Microsoft Excel.

        This method requires Microsoft Excel to be installed on the system.

        Parameters
        ----------
        ObjectType : str
            The PowerWorld object type (e.g., 'Bus', 'Gen').
        FilterName : str
            Optional PowerWorld filter name to apply.
        FieldList : List[str]
            A list of internal field names to export.

        Returns
        -------
        None

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails (e.g., Excel not installed, invalid parameters).
        """
        return self._com_call("SendToExcel", ObjectType, FilterName, FieldList)
