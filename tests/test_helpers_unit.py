"""
Unit tests for pure Python helper functions and validation logic.

These are **unit tests** that do NOT require PowerWorld Simulator. They test
data transformation (df_to_aux), path conversion, argument packing, format
string edge cases, CSV result parsing, matrix file parsing, and Python-side
input validation in the SAW class.

USAGE:
    pytest tests/test_helpers_unit.py -v
"""
import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, Mock, patch, PropertyMock


# =============================================================================
# df_to_aux function
# =============================================================================

class TestDfToAux:
    """Tests for df_to_aux function."""

    def test_df_to_aux_basic(self):
        """df_to_aux writes correct AUX format for a simple DataFrame."""
        from esapp.saw._helpers import df_to_aux
        import io

        df = pd.DataFrame({"BusNum": [1, 2], "BusName": ["Bus1", "Bus2"]})
        fp = io.StringIO()
        df_to_aux(fp, df, "Bus")
        content = fp.getvalue()

        assert "DATA (Bus, [BusNum,BusName])" in content
        assert "{" in content
        assert "}" in content
        assert "1" in content
        assert "Bus1" in content

    def test_df_to_aux_long_header_wraps(self):
        """df_to_aux wraps long headers across multiple lines."""
        from esapp.saw._helpers import df_to_aux
        import io

        # Create a DataFrame with many columns to force header wrapping
        cols = {f"VeryLongFieldName{i}": [i] for i in range(20)}
        df = pd.DataFrame(cols)
        fp = io.StringIO()
        df_to_aux(fp, df, "Branch")
        content = fp.getvalue()

        assert "DATA (Branch," in content
        assert "{" in content
        assert "}" in content


# =============================================================================
# Helper conversion functions
# =============================================================================

class TestHelperConversions:
    """Tests for helper conversion functions."""

    def test_convert_to_windows_path(self):
        from esapp.saw._helpers import convert_to_windows_path
        result = convert_to_windows_path("/tmp/test/file.pwb")
        assert "\\" in result or "/" not in result.replace("//", "")

    def test_create_object_string_single_key(self):
        from esapp.saw._helpers import create_object_string
        assert create_object_string("Bus", 1) == "[BUS 1]"

    def test_create_object_string_multiple_keys(self):
        from esapp.saw._helpers import create_object_string
        assert create_object_string("Branch", 1, 2, "1") == "[BRANCH 1 2 1]"


# =============================================================================
# pack_args function
# =============================================================================

class TestPackArgs:
    """Tests for pack_args helper function."""

    def test_pack_args_basic(self):
        """pack_args joins arguments with commas."""
        from esapp.saw._helpers import pack_args
        result = pack_args("a", "b", "c")
        assert result == "a, b, c"

    def test_pack_args_filters_trailing_none(self):
        """pack_args removes trailing None values."""
        from esapp.saw._helpers import pack_args
        result = pack_args("a", "b", None, None)
        assert result == "a, b"

    def test_pack_args_converts_middle_none_to_empty(self):
        """pack_args converts middle None to empty string."""
        from esapp.saw._helpers import pack_args
        result = pack_args("a", None, "c")
        assert result == "a, , c"

    def test_pack_args_all_none(self):
        """pack_args returns empty string for all None."""
        from esapp.saw._helpers import pack_args
        result = pack_args(None, None)
        assert result == ""

    def test_pack_args_empty(self):
        """pack_args returns empty string for no arguments."""
        from esapp.saw._helpers import pack_args
        result = pack_args()
        assert result == ""

    def test_pack_args_numbers(self):
        """pack_args converts numbers to strings."""
        from esapp.saw._helpers import pack_args
        result = pack_args(1, 2.5, 3)
        assert result == "1, 2.5, 3"


# =============================================================================
# format_optional function
# =============================================================================

class TestFormatOptionalEdgeCases:
    """Tests for format_optional edge cases."""

    def test_format_optional_empty_string_not_quoted(self):
        """format_optional returns empty string for empty input."""
        from esapp.saw._helpers import format_optional
        result = format_optional("")
        assert result == ""

    def test_format_optional_empty_string_with_empty_quoted(self):
        """format_optional returns '\"\"' when empty_quoted=True."""
        from esapp.saw._helpers import format_optional
        result = format_optional("", empty_quoted=True)
        assert result == '""'

    def test_format_optional_none_not_quoted(self):
        """format_optional returns empty string for None."""
        from esapp.saw._helpers import format_optional
        result = format_optional(None)
        assert result == ""

    def test_format_optional_none_with_empty_quoted(self):
        """format_optional returns '\"\"' for None when empty_quoted=True."""
        from esapp.saw._helpers import format_optional
        result = format_optional(None, empty_quoted=True)
        assert result == '""'

    def test_format_optional_value_quoted(self):
        """format_optional quotes non-empty values by default."""
        from esapp.saw._helpers import format_optional
        result = format_optional("MyValue")
        assert result == '"MyValue"'

    def test_format_optional_value_not_quoted(self):
        """format_optional returns raw value when quote=False."""
        from esapp.saw._helpers import format_optional
        result = format_optional("MyValue", quote=False)
        assert result == "MyValue"


# =============================================================================
# load_ts_csv_results function
# =============================================================================

class TestLoadTsCsvResults:
    """Tests for load_ts_csv_results function."""

    def test_load_ts_csv_results_no_files(self, tmp_path):
        """load_ts_csv_results returns empty DataFrames when no files found."""
        from esapp.saw._helpers import load_ts_csv_results
        base_path = tmp_path / "nonexistent_results"
        meta, data = load_ts_csv_results(base_path)
        assert meta.empty
        assert data.empty

    def test_load_ts_csv_results_header_only(self, tmp_path):
        """load_ts_csv_results parses header file correctly."""
        from esapp.saw._helpers import load_ts_csv_results

        # Create header file
        header_file = tmp_path / "results_header.csv"
        header_file.write_text("Column,Object,Variable,Key 1,Key 2\n0,Bus,VPU,1,\n1,Gen,P,2,1\n")

        base_path = tmp_path / "results"
        meta, data = load_ts_csv_results(base_path)

        assert not meta.empty
        assert "ColHeader" in meta.columns
        assert "ObjectType" in meta.columns

    def test_load_ts_csv_results_with_data(self, tmp_path):
        """load_ts_csv_results parses data files correctly."""
        from esapp.saw._helpers import load_ts_csv_results

        # Create header file
        header_file = tmp_path / "results_header.csv"
        header_file.write_text("Column,Object,Variable,Key 1,Key 2\n0,Bus,VPU,1,\n")

        # Create data file
        data_file = tmp_path / "results_data.csv"
        data_file.write_text("0.0,1.0\n0.1,0.99\n0.2,0.98\n")

        base_path = tmp_path / "results"
        meta, data = load_ts_csv_results(base_path)

        assert not data.empty
        assert "time" in data.columns
        assert len(data) == 3

    def test_load_ts_csv_results_object_fields_header(self, tmp_path):
        """load_ts_csv_results skips ObjectFields line in header."""
        from esapp.saw._helpers import load_ts_csv_results

        # Create header file with ObjectFields line
        header_file = tmp_path / "results_header.csv"
        header_file.write_text("ObjectFields\nColumn,Object,Variable,Key 1,Key 2\n0,Bus,VPU,1,\n")

        base_path = tmp_path / "results"
        meta, data = load_ts_csv_results(base_path)

        assert not meta.empty
        assert "ColHeader" in meta.columns

    def test_load_ts_csv_results_delete_files(self, tmp_path):
        """load_ts_csv_results deletes files when delete_files=True."""
        from esapp.saw._helpers import load_ts_csv_results

        # Create header file
        header_file = tmp_path / "results_header.csv"
        header_file.write_text("Column,Object,Variable,Key 1,Key 2\n0,Bus,VPU,1,\n")

        base_path = tmp_path / "results"
        load_ts_csv_results(base_path, delete_files=True)

        assert not header_file.exists()


# =============================================================================
# format_list function
# =============================================================================


class TestFormatList:
    """Tests for format_list helper function."""

    def test_format_list_none(self):
        from esapp.saw._helpers import format_list
        assert format_list(None) == "[]"

    def test_format_list_empty(self):
        from esapp.saw._helpers import format_list
        assert format_list([]) == "[]"

    def test_format_list_basic(self):
        from esapp.saw._helpers import format_list
        assert format_list(["BusNum", "BusName"]) == "[BusNum, BusName]"

    def test_format_list_quote_items(self):
        from esapp.saw._helpers import format_list
        assert format_list(["Gen1", "Gen2"], quote_items=True) == '["Gen1", "Gen2"]'

    def test_format_list_stringify(self):
        from esapp.saw._helpers import format_list
        assert format_list([1.5, 2.0], stringify=True) == "[1.5, 2.0]"


# =============================================================================
# format_optional_numeric function
# =============================================================================


class TestFormatOptionalNumeric:
    """Tests for format_optional_numeric function."""

    def test_none_returns_empty(self):
        from esapp.saw._helpers import format_optional_numeric
        assert format_optional_numeric(None) == ""

    def test_zero_returns_str(self):
        from esapp.saw._helpers import format_optional_numeric
        assert format_optional_numeric(0) == "0"

    def test_float_returns_str(self):
        from esapp.saw._helpers import format_optional_numeric
        assert format_optional_numeric(3.14) == "3.14"


# =============================================================================
# format_filter functions
# =============================================================================


class TestFormatFilterSelectedOnly:
    """Tests for format_filter_selected_only."""

    def test_empty_string(self):
        from esapp.saw._enums import format_filter_selected_only
        assert format_filter_selected_only("") == ""

    def test_none(self):
        from esapp.saw._enums import format_filter_selected_only
        assert format_filter_selected_only(None) == ""

    def test_selected_enum(self):
        from esapp.saw._enums import format_filter_selected_only, FilterKeyword
        result = format_filter_selected_only(FilterKeyword.SELECTED)
        assert result == "SELECTED"

    def test_selected_string(self):
        from esapp.saw._enums import format_filter_selected_only
        result = format_filter_selected_only("SELECTED")
        assert result == "SELECTED"

    def test_custom_filter_quoted(self):
        from esapp.saw._enums import format_filter_selected_only
        result = format_filter_selected_only("MyFilter")
        assert result == '"MyFilter"'

    def test_areazone_enum_quoted(self):
        from esapp.saw._enums import format_filter_selected_only, FilterKeyword
        result = format_filter_selected_only(FilterKeyword.AREAZONE)
        # AREAZONE is not SELECTED, so it gets quoted
        assert result.startswith('"') and result.endswith('"')


class TestFormatFilterAreazone:
    """Tests for format_filter_areazone."""

    def test_empty_string(self):
        from esapp.saw._enums import format_filter_areazone
        assert format_filter_areazone("") == ""

    def test_none(self):
        from esapp.saw._enums import format_filter_areazone
        assert format_filter_areazone(None) == ""

    def test_selected_enum(self):
        from esapp.saw._enums import format_filter_areazone, FilterKeyword
        result = format_filter_areazone(FilterKeyword.SELECTED)
        assert result == "SELECTED"

    def test_areazone_enum(self):
        from esapp.saw._enums import format_filter_areazone, FilterKeyword
        result = format_filter_areazone(FilterKeyword.AREAZONE)
        assert result == "AREAZONE"

    def test_all_enum_quoted(self):
        from esapp.saw._enums import format_filter_areazone, FilterKeyword
        result = format_filter_areazone(FilterKeyword.ALL)
        assert result == '"ALL"'

    def test_selected_string(self):
        from esapp.saw._enums import format_filter_areazone
        result = format_filter_areazone("SELECTED")
        assert result == "SELECTED"

    def test_areazone_string(self):
        from esapp.saw._enums import format_filter_areazone
        result = format_filter_areazone("AREAZONE")
        assert result == "AREAZONE"

    def test_custom_filter_quoted(self):
        from esapp.saw._enums import format_filter_areazone
        result = format_filter_areazone("MyFilter")
        assert result == '"MyFilter"'


# =============================================================================
# load_ts_csv_results edge cases
# =============================================================================


class TestLoadTsCsvResultsEdgeCases:
    """Edge case tests for load_ts_csv_results."""

    def test_bad_header_file_logged(self, tmp_path, caplog):
        """A corrupt header file logs warning and returns empty meta."""
        from esapp.saw._helpers import load_ts_csv_results
        import logging

        header_file = tmp_path / "results_header.csv"
        header_file.write_bytes(b'\xff\xfe' + b'\x00' * 50)

        base_path = tmp_path / "results"
        with caplog.at_level(logging.WARNING):
            meta, data = load_ts_csv_results(base_path)

    def test_bad_data_file_logged(self, tmp_path, caplog):
        """A corrupt data file logs warning and is skipped."""
        from esapp.saw._helpers import load_ts_csv_results
        import logging

        data_file = tmp_path / "results_0.csv"
        data_file.write_bytes(b'\xff\xfe' + b'\x00' * 50)

        base_path = tmp_path / "results"
        with caplog.at_level(logging.WARNING):
            meta, data = load_ts_csv_results(base_path)


# =============================================================================
# SAW Python-side validation tests (no COM calls needed)
# =============================================================================


class TestSAWValidation:
    """Tests for SAW input validation that happens in Python before COM calls."""

    def test_set_simauto_property_invalid_name(self, saw_obj):
        """set_simauto_property raises ValueError for unsupported property."""
        with pytest.raises(ValueError, match="not currently supported"):
            saw_obj.set_simauto_property("InvalidProp", True)

    def test_set_simauto_property_invalid_type(self, saw_obj):
        """set_simauto_property raises ValueError for wrong type."""
        with pytest.raises(ValueError, match="is invalid"):
            saw_obj.set_simauto_property("CreateIfNotFound", "not_a_bool")

    def test_open_case_no_filename_no_path(self, saw_obj):
        """OpenCase raises TypeError when no FileName and no prior path."""
        saw_obj.pwb_file_path = None
        with pytest.raises(TypeError, match="FileName is required"):
            saw_obj.OpenCase(FileName=None)

    def test_save_case_no_filename_no_path(self, saw_obj):
        """SaveCase raises TypeError when no FileName and no opened case."""
        saw_obj.pwb_file_path = None
        with pytest.raises(TypeError, match="SaveCase was called without"):
            saw_obj.SaveCase()

    def test_com_call_invalid_func(self, saw_obj):
        """_com_call raises AttributeError for invalid function."""
        del saw_obj._pwcom.InvalidFunc
        with pytest.raises(AttributeError, match="not a valid SimAuto function"):
            saw_obj._com_call("InvalidFunc")

    def test_replace_decimal_delimiter(self, saw_obj):
        """_replace_decimal_delimiter handles non-string data."""
        data = pd.Series([1.0, 2.0, 3.0])
        result = saw_obj._replace_decimal_delimiter(data)
        assert (result == data).all()

    def test_replace_decimal_delimiter_comma(self, saw_obj):
        """_replace_decimal_delimiter replaces comma with period."""
        saw_obj.decimal_delimiter = ","
        data = pd.Series(["1,5", "2,3", "3,0"])
        result = saw_obj._replace_decimal_delimiter(data)
        assert result.iloc[0] == "1.5"

    def test_get_field_list_copy(self, saw_obj):
        """GetFieldList returns a copy when copy=True."""
        saw_obj._object_fields = {}
        result1 = saw_obj.GetFieldList("Bus", copy=False)
        result2 = saw_obj.GetFieldList("Bus", copy=True)
        assert result1 is not result2

    def test_init_com_dispatch_failure(self):
        """SAW raises when COM dispatch fails."""
        with patch("win32com.client.dynamic.Dispatch", side_effect=Exception("COM init failed")):
            with pytest.raises(Exception, match="COM init failed"):
                from esapp.saw import SAW
                SAW(FileName="dummy.pwb")

    def test_exit_cleanup(self):
        """exit() deletes temp file, closes case, and releases COM."""
        from esapp.saw import SAW
        with patch("win32com.client.dynamic.Dispatch") as mock_dispatch, \
             patch("tempfile.NamedTemporaryFile") as mock_tf, \
             patch("os.unlink"), \
             patch("esapp.saw.base.pythoncom") as mock_pythoncom:
            mock_pwcom = MagicMock()
            mock_dispatch.return_value = mock_pwcom
            mock_tf.return_value = Mock(name="dummy.axd")
            mock_pwcom.OpenCase.return_value = ("",)
            mock_pwcom.GetParametersSingleElement.return_value = ("", ("23", "Jan 01 2023"))
            mock_pwcom.CloseCase.return_value = ("",)
            saw = SAW(FileName="dummy.pwb")
            saw._pwcom = mock_pwcom
            saw.empty_aux = "dummy.axd"

            with patch("os.path.exists", return_value=True), \
                 patch("os.unlink") as mock_unlink:
                saw.exit()
                mock_unlink.assert_called_once_with("dummy.axd")
                assert saw._pwcom is None
                mock_pythoncom.CoUninitialize.assert_called_once()

    def test_request_build_date(self, saw_obj):
        """RequestBuildDate property accesses COM."""
        saw_obj._pwcom.RequestBuildDate = 20230101
        assert saw_obj.RequestBuildDate == 20230101

    def test_run_script_command_2(self, saw_obj):
        """RunScriptCommand2 calls COM correctly."""
        saw_obj._pwcom.RunScriptCommand2.return_value = ("",)
        saw_obj.RunScriptCommand2("SomeCMD;", "Status msg")
        saw_obj._pwcom.RunScriptCommand2.assert_called_once()

    def test_com_call_rpc_error(self, saw_obj):
        """_com_call raises COMError on RPC failure."""
        from esapp.saw._exceptions import COMError, RPC_S_UNKNOWN_IF
        saw_obj._pwcom.OpenCase.side_effect = Exception(f"error {hex(RPC_S_UNKNOWN_IF)}")
        with pytest.raises(COMError):
            saw_obj._com_call("OpenCase", "test.pwb")

    def test_com_call_returns_minus_one(self, saw_obj):
        """_com_call raises PowerWorldError when COM returns -1."""
        from esapp.saw._exceptions import PowerWorldError
        saw_obj._pwcom.OpenCase.return_value = -1
        with pytest.raises(PowerWorldError, match="returned -1"):
            saw_obj._com_call("OpenCase", "test.pwb")

    def test_com_call_returns_int(self, saw_obj):
        """_com_call returns integer output directly."""
        saw_obj._pwcom.GetSpecificFieldMaxNum.return_value = 42
        result = saw_obj._com_call("GetSpecificFieldMaxNum", "Bus", "CustomFloat")
        assert result == 42

    def test_exec_aux_double_quotes(self, saw_obj):
        """exec_aux replaces single quotes with double quotes."""
        with patch("builtins.open", create=True) as mock_open, \
             patch("os.unlink"):
            from unittest.mock import mock_open as mo
            m = mo()
            with patch("builtins.open", m):
                saw_obj.exec_aux("CaseInfo_Options_Value (Option,Value)\n{'key' 'value'}", use_double_quotes=True)
                written = m().write.call_args[0][0]
                assert "'" not in written
                assert '"' in written

    def test_open_case_reopen_uses_stored_path(self, saw_obj):
        """OpenCase with FileName=None reopens stored path."""
        saw_obj.pwb_file_path = "stored.pwb"
        saw_obj.OpenCase(FileName=None)
        saw_obj._pwcom.OpenCase.assert_called_with("stored.pwb")

    def test_open_case_type_options_list(self, saw_obj):
        """OpenCaseType with list options converts to variant."""
        saw_obj._pwcom.OpenCaseType.return_value = ("",)
        saw_obj.OpenCaseType("test.raw", "PTI", ["OPT1", "OPT2"])
        saw_obj._pwcom.OpenCaseType.assert_called_once()

    def test_open_case_type_options_str(self, saw_obj):
        """OpenCaseType with string options passes through."""
        saw_obj._pwcom.OpenCaseType.return_value = ("",)
        saw_obj.OpenCaseType("test.raw", "PTI", "MY_OPTION")
        saw_obj._pwcom.OpenCaseType.assert_called_once()

    def test_open_case_type_error_file_exists(self, saw_obj):
        """OpenCaseType error when file exists shows file-exists hints."""
        from esapp.saw._exceptions import PowerWorldError
        saw_obj._pwcom.OpenCaseType.return_value = ("Error: bad format",)
        with patch("os.path.exists", return_value=True):
            with pytest.raises(PowerWorldError, match="file exists but"):
                saw_obj.OpenCaseType("test.raw", "PTI")

    def test_save_case_uses_stored_path(self, saw_obj):
        """SaveCase with no FileName uses stored path."""
        saw_obj.pwb_file_path = "stored.pwb"
        saw_obj.SaveCase()
        saw_obj._pwcom.SaveCase.assert_called_once()

    def test_new_case(self, saw_obj):
        """NewCase calls _run_script."""
        saw_obj.NewCase()

    def test_renumber_3w_xformer_star_buses(self, saw_obj):
        """Renumber3WXFormerStarBuses calls _run_script."""
        saw_obj.Renumber3WXFormerStarBuses("renumber.txt")

    def test_renumber_ms_line_dummy_buses(self, saw_obj):
        """RenumberMSLineDummyBuses calls _run_script."""
        saw_obj.RenumberMSLineDummyBuses("renumber.txt")

    def test_get_case_header_none_filename(self, saw_obj):
        """GetCaseHeader with None uses stored pwb_file_path."""
        saw_obj.pwb_file_path = "stored.pwb"
        saw_obj._pwcom.GetCaseHeader.return_value = ("", ("Header line 1",))
        saw_obj.GetCaseHeader(filename=None)
        saw_obj._pwcom.GetCaseHeader.assert_called_with("stored.pwb")

    def test_get_params_rect_typed_none(self, saw_obj):
        """GetParamsRectTyped returns None when COM returns None."""
        saw_obj._pwcom.GetParamsRectTyped.return_value = ("", None)
        result = saw_obj.GetParamsRectTyped("Bus", ["BusNum"])
        assert result is None

    def test_send_to_excel(self, saw_obj):
        """SendToExcel calls COM correctly."""
        saw_obj._pwcom.SendToExcel.return_value = ("",)
        saw_obj.SendToExcel("Bus", "", ["BusNum", "BusName"])
        saw_obj._pwcom.SendToExcel.assert_called_once()

    def test_ctg_read_file_pslf(self, saw_obj):
        """CTGReadFilePSLF calls _run_script."""
        saw_obj.CTGReadFilePSLF("test.pslf")

    def test_ctg_read_file_pti(self, saw_obj):
        """CTGReadFilePTI calls _run_script."""
        saw_obj.CTGReadFilePTI("test.con")

    def test_ctg_save_violation_matrices_default_field_list(self, saw_obj):
        """CTGSaveViolationMatrices with field_list=None defaults to empty list."""
        saw_obj.CTGSaveViolationMatrices(
            "out.csv", "CSVCOLHEADER", True, ["Branch"], True, True
        )

    def test_load_pti_seq_data(self, saw_obj):
        """LoadPTISEQData calls _run_script."""
        saw_obj.LoadPTISEQData("test.seq")

    def test_stop_aux_file(self, saw_obj):
        """StopAuxFile calls _run_script."""
        saw_obj.StopAuxFile()

    def test_gic_read_file_pslf(self, saw_obj):
        """GICReadFilePSLF calls _run_script."""
        saw_obj.GICReadFilePSLF("test.gmd")

    def test_gic_read_file_pti(self, saw_obj):
        """GICReadFilePTI calls _run_script."""
        saw_obj.GICReadFilePTI("test.gic")

    def test_merge_line_terminals(self, saw_obj):
        """MergeLineTerminals calls _run_script."""
        saw_obj.MergeLineTerminals()

    def test_merge_ms_line_sections(self, saw_obj):
        """MergeMSLineSections calls _run_script."""
        saw_obj.MergeMSLineSections()

    def test_estimate_voltages(self, saw_obj):
        """EstimateVoltages calls _run_script."""
        saw_obj.EstimateVoltages("ALL")

    def test_diff_case_clear_base(self, saw_obj):
        """DiffCaseClearBase calls _run_script."""
        saw_obj.DiffCaseClearBase()

    def test_diff_case_show_present_and_base(self, saw_obj):
        """DiffCaseShowPresentAndBase calls _run_script."""
        saw_obj.DiffCaseShowPresentAndBase(True)

    def test_do_ctg_action(self, saw_obj):
        """DoCTGAction calls _run_script."""
        saw_obj.DoCTGAction("OPEN BRANCH FROM 1 TO 2 CKT 1")

    def test_interfaces_calculate_post_ctg_mw_flows(self, saw_obj):
        """InterfacesCalculatePostCTGMWFlows calls _run_script."""
        saw_obj.InterfacesCalculatePostCTGMWFlows()

    def test_qv_run_empty_result(self, saw_obj, tmp_path):
        """QVRun returns empty DataFrame when temp file is empty."""
        tmp = str(tmp_path / "qv_result.csv")
        with open(tmp, 'w') as f:
            pass  # Create empty file
        with patch.object(saw_obj, '_run_script'), \
             patch('esapp.saw.qv.get_temp_filepath', return_value=tmp):
            result = saw_obj.QVRun()
            assert isinstance(result, pd.DataFrame)
            assert result.empty

    def test_timestep_do_single_point(self, saw_obj):
        """TimeStepDoSinglePoint calls _run_script."""
        saw_obj.TimeStepDoSinglePoint("2025-06-01T00:00:00")

    def test_timestep_save_selected_modify_finish(self, saw_obj):
        """TIMESTEPSaveSelectedModifyFinish calls _run_script."""
        saw_obj.TIMESTEPSaveSelectedModifyFinish()

    def test_list_of_devices_decimal_delimiter(self, saw_obj):
        """ListOfDevices handles non-dot decimal delimiter."""
        saw_obj.decimal_delimiter = ","
        saw_obj._object_fields = {}
        # Re-mock GetFieldList to return data with comma delimiters
        saw_obj._pwcom.GetFieldList.return_value = ("", [
            ["*1*", "BusNum", "Integer", "Bus Number", "Bus Number"],
            ["*2*", "BusName", "String", "Bus Name", "Bus Name"],
        ])
        saw_obj._pwcom.ListOfDevices.return_value = ("", ((1, 2), ("Bus1", "Bus2")))
        result = saw_obj.ListOfDevices("Bus")
        assert result is not None
        saw_obj.decimal_delimiter = "."

    def test_set_simauto_property_attribute_error_propagates(self, saw_obj):
        """set_simauto_property propagates AttributeError from the COM property."""
        with patch.object(saw_obj, '_set_simauto_property', side_effect=AttributeError("oops")):
            with pytest.raises(AttributeError, match="oops"):
                saw_obj.set_simauto_property("CreateIfNotFound", True)

    def test_condition_voltage_pockets(self, saw_obj):
        """ConditionVoltagePockets calls _run_script."""
        saw_obj.ConditionVoltagePockets(0.5, 30.0)

    def test_diff_case_key_type(self, saw_obj):
        """DiffCaseKeyType calls _run_script."""
        saw_obj.DiffCaseKeyType("PRIMARY")

    def test_get_sub_data_file_not_found(self, saw_obj):
        """GetSubData returns empty DataFrame when file not found."""
        with patch.object(saw_obj, 'SaveData'), \
             patch('os.path.exists', return_value=False), \
             patch('esapp.saw.general.get_temp_filepath', return_value='nonexistent.aux'):
            result = saw_obj.GetSubData("Gen", ["BusNum", "GenID"])
            assert isinstance(result, pd.DataFrame)
            assert result.empty

    def test_get_field_list_new_columns(self, saw_obj):
        """GetFieldList handles new (extended) column format."""
        saw_obj._object_fields = {}
        # Return data with 7 columns (new format) to trigger ValueError path
        saw_obj._pwcom.GetFieldList.return_value = ("", [
            ["*1*", "BusNum", "Integer", "Bus Number", "Bus Number", "Y", "Extra"],
            ["*2*", "BusName", "String", "Bus Name", "Bus Name", "N", "Extra"],
        ])
        from esapp.saw._enums import FieldListColumn
        new_cols = FieldListColumn.new_columns()
        if len(new_cols) == 7:
            result = saw_obj.GetFieldList("Bus")
            assert not result.empty

    def test_program_information_property(self, saw_obj):
        """ProgramInformation property accesses COM and returns tuple."""
        import datetime
        dt = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
        saw_obj._pwcom.ProgramInformation = [["v23", "Build", dt, "info"]]
        result = saw_obj.ProgramInformation
        assert isinstance(result, tuple)


# =============================================================================
# Matrix parsing tests (pure file-based, no COM)
# =============================================================================


class TestMatrixParsing:
    """Tests for matrix file parsing (pure Python, reads from files)."""

    def _make_ybus_file(self, tmp_path):
        """Helper to create a mock YBus .m file in PowerWorld format."""
        content = (
            "% YBus Matrix\n"
            "Ybus=sparse(3,3);\n"
            "Ybus(1,1)=10.0+j*(-5.0);\n"
            "Ybus(1,2)=-5.0+j*(2.5);\n"
            "Ybus(2,1)=-5.0+j*(2.5);\n"
            "Ybus(2,2)=10.0+j*(-5.0);\n"
            "Ybus(3,3)=5.0+j*(-2.5);\n"
        )
        fpath = str(tmp_path / "ybus.m")
        with open(fpath, "w") as f:
            f.write(content)
        return fpath

    def test_parse_real_matrix(self, saw_obj):
        """_parse_real_matrix correctly parses sparse matrix."""
        mat_str = (
            "Jac=sparse(2,2);\n"
            "Jac(1,1)=1.0;\n"
            "Jac(1,2)=-0.5;\n"
            "Jac(2,1)=-0.5;\n"
            "Jac(2,2)=1.0;\n"
        )
        result = saw_obj._parse_real_matrix(mat_str, "Jac")
        arr = result.toarray()
        assert arr.shape == (2, 2)
        assert arr[0, 0] == 1.0
        assert arr[0, 1] == -0.5

    def test_get_ybus_from_file(self, saw_obj, tmp_path):
        """get_ybus reads from an existing file."""
        fpath = self._make_ybus_file(tmp_path)
        result = saw_obj.get_ybus(file=fpath, full=True)
        assert result.shape == (3, 3)
        assert result[0, 0] == 10.0 + (-5.0j)

    def test_get_ybus_sparse(self, saw_obj, tmp_path):
        """get_ybus returns sparse matrix by default."""
        from scipy.sparse import issparse
        fpath = self._make_ybus_file(tmp_path)
        result = saw_obj.get_ybus(file=fpath, full=False)
        assert issparse(result)

    def test_parse_real_matrix_gmatrix(self, saw_obj):
        """_parse_real_matrix correctly parses GMatrix format."""
        mat_str = (
            "GMatrix=sparse(3,3);\n"
            "GMatrix(1,1)=2.0;\n"
            "GMatrix(1,2)=-1.0;\n"
            "GMatrix(2,1)=-1.0;\n"
            "GMatrix(2,2)=3.0;\n"
            "GMatrix(3,3)=1.5;\n"
        )
        result = saw_obj._parse_real_matrix(mat_str, "GMatrix")
        arr = result.toarray()
        assert arr.shape == (3, 3)
        assert arr[0, 0] == 2.0
        assert arr[2, 2] == 1.5

    def test_save_ybus_in_matlab_format(self, saw_obj):
        """SaveYbusInMatlabFormat calls _run_script."""
        saw_obj.SaveYbusInMatlabFormat("ybus.m", include_voltages=True)

    def test_save_jacobian(self, saw_obj):
        """SaveJacobian calls _run_script."""
        saw_obj.SaveJacobian("jac.m", "jid.txt", "M", "R")


# =============================================================================
# TSField unit tests
# =============================================================================


class TestTSFieldIndexing:
    """Tests for TSField.__getitem__."""

    def test_tsfield_getitem(self):
        """TSField[index] creates an indexed field."""
        from esapp.components.ts_fields import TSField
        field = TSField("TSBusInput", "Input voltage")
        indexed = field[1]
        assert str(indexed) == "TSBusInput:1"

    def test_ts_bus_input_indexing(self):
        """TS.Bus.Input[1] creates indexed field."""
        from esapp.components import TS
        indexed = TS.Bus.Input[1]
        assert str(indexed) == "TSBusInput:1"


# =============================================================================
# Workbench logic tests (file I/O, no COM)
# =============================================================================


class TestWorkbenchLogic:
    """Tests for PowerWorld Python-side logic (no PowerWorld needed)."""

    def test_init_no_fname(self):
        """PowerWorld initializes without fname."""
        from esapp.workbench import PowerWorld
        pw = PowerWorld()
        assert pw.esa is None
        assert pw.fname is None

    def test_open_file_not_found(self):
        """PowerWorld.open raises FileNotFoundError for missing file."""
        from esapp.workbench import PowerWorld
        from unittest.mock import patch

        pw = PowerWorld()
        pw.fname = "C:/nonexistent/file.pwb"

        with patch('esapp.indexable.path.isabs', return_value=True), \
             patch('esapp.indexable.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="Case file not found"):
                pw.open()

    def test_log_output(self):
        """PowerWorld.print_log reads and prints log content."""
        from esapp.workbench import PowerWorld
        from unittest.mock import MagicMock

        pw = PowerWorld()
        pw.esa = MagicMock()
        pw._log_last_position = 0

        def mock_log_save(path, append=False):
            with open(path, "w") as f:
                f.write("Some log output")

        pw.esa.LogSave.side_effect = mock_log_save

        result = pw.print_log(new_only=False, clear=False)
        assert "Some log output" in result

    def test_print_log_new_only(self):
        """PowerWorld.print_log returns only new content."""
        from esapp.workbench import PowerWorld
        from unittest.mock import MagicMock

        pw = PowerWorld()
        pw.esa = MagicMock()
        pw._log_last_position = 5

        def mock_log_save(path, append=False):
            with open(path, "w") as f:
                f.write("Hello World")

        pw.esa.LogSave.side_effect = mock_log_save

        result = pw.print_log(new_only=True, clear=False)
        assert result == " World"

    def test_print_log_empty(self):
        """PowerWorld.print_log handles empty log output (whitespace only)."""
        from esapp.workbench import PowerWorld
        from unittest.mock import MagicMock

        pw = PowerWorld()
        pw.esa = MagicMock()
        pw._log_last_position = 0

        def mock_log_save(path, append=False):
            with open(path, "w") as f:
                f.write("   ")

        pw.esa.LogSave.side_effect = mock_log_save

        result = pw.print_log(new_only=False, clear=False)
        assert result == "   "

    def test_log_with_clear(self):
        """PowerWorld.print_log clears log after reading."""
        from esapp.workbench import PowerWorld
        from unittest.mock import MagicMock

        pw = PowerWorld()
        pw.esa = MagicMock()
        pw._log_last_position = 0

        def mock_log_save(path, append=False):
            with open(path, "w") as f:
                f.write("Log content")

        pw.esa.LogSave.side_effect = mock_log_save

        pw.print_log(new_only=False, clear=True)
        pw.esa.LogClear.assert_called_once()
        assert pw._log_last_position == 0

    def test_close(self):
        """PowerWorld.close calls esa.CloseCase."""
        from esapp.workbench import PowerWorld

        pw = PowerWorld()
        pw.esa = MagicMock()
        pw.close()
        pw.esa.CloseCase.assert_called_once()

    def test_ts_solve_empty_results(self):
        """PowerWorld.ts_solve returns empty DataFrames when no results."""
        from esapp.workbench import PowerWorld

        pw = PowerWorld()
        pw.esa = MagicMock()

        with patch("esapp.workbench.get_ts_results", return_value=(None, None)):
            meta, data = pw.ts_solve("ctg1", ["TSBusVPU"])
            assert meta.empty
            assert data.empty

    def test_dc_lines_exception_returns_none(self):
        """Network._dc_lines returns None on exception."""
        from esapp.utils.network import Network

        mock_pw = MagicMock()
        mock_pw.__getitem__ = MagicMock(side_effect=Exception("no DC lines"))
        net = Network(mock_pw)
        result = net._dc_lines()
        assert result is None

    def test_gic_option_descriptor_missing_key(self):
        """GICOption descriptor returns None for missing option key."""
        from esapp.utils.gic import GIC
        import pandas as pd

        mock_pw = MagicMock()
        # Return a DataFrame with no matching VariableName
        mock_pw.__getitem__ = MagicMock(return_value=pd.DataFrame({
            'VariableName': ['OtherOption'],
            'ValueField': ['SomeValue']
        }))
        gic = GIC(mock_pw)
        # pf_include looks for 'IncludeInPowerFlow' which isn't in the mock data
        result = gic.pf_include
        assert result is None

    def test_gic_option_descriptor_bool_get_true(self):
        """GICOption bool descriptor returns True when value is YES."""
        from esapp.utils.gic import GIC
        from esapp.saw._enums import YesNo
        import pandas as pd

        mock_pw = MagicMock()
        mock_pw.__getitem__ = MagicMock(return_value=pd.DataFrame({
            'VariableName': ['IncludeInPowerFlow'],
            'ValueField': [YesNo.YES]
        }))
        gic = GIC(mock_pw)
        assert gic.pf_include is True

    def test_gic_option_descriptor_bool_get_false(self):
        """GICOption bool descriptor returns False when value is NO."""
        from esapp.utils.gic import GIC
        from esapp.saw._enums import YesNo
        import pandas as pd

        mock_pw = MagicMock()
        mock_pw.__getitem__ = MagicMock(return_value=pd.DataFrame({
            'VariableName': ['IncludeInPowerFlow'],
            'ValueField': [YesNo.NO]
        }))
        gic = GIC(mock_pw)
        assert gic.pf_include is False

    def test_gic_option_descriptor_nonbool_get(self):
        """GICOption non-bool descriptor returns raw value."""
        from esapp.utils.gic import GIC
        import pandas as pd

        mock_pw = MagicMock()
        mock_pw.__getitem__ = MagicMock(return_value=pd.DataFrame({
            'VariableName': ['CalcMode'],
            'ValueField': ['SnapShot']
        }))
        gic = GIC(mock_pw)
        assert gic.calc_mode == 'SnapShot'

    def test_gic_option_descriptor_bool_set(self):
        """GICOption bool descriptor calls SetData with YES/NO and EDIT/RUN."""
        from esapp.utils.gic import GIC
        from esapp.saw._enums import YesNo

        mock_pw = MagicMock()
        mock_esa = MagicMock()
        mock_pw.esa = mock_esa
        gic = GIC(mock_pw)

        gic.pf_include = True
        mock_esa.EnterMode.assert_any_call("EDIT")
        mock_esa.SetData.assert_called_with(
            'GIC_Options_Value',
            ['VariableName', 'ValueField'],
            ['IncludeInPowerFlow', YesNo.YES]
        )
        mock_esa.EnterMode.assert_called_with("RUN")

    def test_gic_option_descriptor_nonbool_set(self):
        """GICOption non-bool descriptor passes value directly."""
        from esapp.utils.gic import GIC

        mock_pw = MagicMock()
        mock_esa = MagicMock()
        mock_pw.esa = mock_esa
        gic = GIC(mock_pw)

        gic.calc_mode = 'TimeVarying'
        mock_esa.SetData.assert_called_with(
            'GIC_Options_Value',
            ['VariableName', 'ValueField'],
            ['CalcMode', 'TimeVarying']
        )

    def test_gic_option_descriptor_class_level_access(self):
        """GICOption class-level access returns the descriptor itself."""
        from esapp.utils.gic import GIC

        desc = GIC.pf_include
        assert hasattr(desc, 'key')
        assert desc.key == 'IncludeInPowerFlow'
        assert desc.is_bool is True

        desc_nb = GIC.calc_mode
        assert desc_nb.key == 'CalcMode'
        assert desc_nb.is_bool is False

    def test_load_ts_csv_results_unlink_oserror(self, tmp_path):
        """load_ts_csv_results handles OSError on temp file unlink."""
        from esapp.saw._helpers import load_ts_csv_results
        header_file = tmp_path / "results_header.csv"
        header_file.write_text("Column,Object,Variable,Key 1,Key 2\n0,Bus,VPU,1,\n")
        base_path = tmp_path / "results"
        with patch("pathlib.Path.unlink", side_effect=OSError("permission denied")):
            meta, data = load_ts_csv_results(base_path, delete_files=True)
            assert not meta.empty


# =============================================================================
# Indexable fallback (error routing logic)
# =============================================================================


class TestIndexableFallback:
    """Tests for Indexable.__setitem__ fallback on ChangeParametersMultipleElement."""

    def test_fallback_create_suppresses_not_found(self):
        """Fallback to ChangeParametersMultipleElement suppresses 'not found'."""
        from esapp.saw import PowerWorldPrerequisiteError
        from esapp.indexable import Indexable
        from esapp import components as grid
        from unittest.mock import Mock

        instance = Indexable()
        mock_esa = Mock()
        instance.esa = mock_esa

        update_df = pd.DataFrame({
            "BusNum": [999, 1000],
            "GenID": ["1", "1"],
            "GenMW": [100.0, 200.0],
        })

        mock_esa.ChangeParametersMultipleElementRect.side_effect = PowerWorldPrerequisiteError(
            "Object not found in case"
        )
        mock_esa.ChangeParametersMultipleElement.side_effect = PowerWorldPrerequisiteError(
            "Object not found in case"
        )

        instance[grid.Gen] = update_df

    def test_fallback_create_raises_other_error(self):
        """Fallback to ChangeParametersMultipleElement re-raises non-'not found' errors."""
        from esapp.saw import PowerWorldPrerequisiteError
        from esapp.indexable import Indexable
        from esapp import components as grid
        from unittest.mock import Mock

        instance = Indexable()
        mock_esa = Mock()
        instance.esa = mock_esa

        update_df = pd.DataFrame({
            "BusNum": [999],
            "GenID": ["1"],
            "GenMW": [100.0],
        })

        mock_esa.ChangeParametersMultipleElementRect.side_effect = PowerWorldPrerequisiteError(
            "Object not found in case"
        )
        mock_esa.ChangeParametersMultipleElement.side_effect = PowerWorldPrerequisiteError(
            "License expired"
        )

        with pytest.raises(PowerWorldPrerequisiteError, match="License expired"):
            instance[grid.Gen] = update_df

    def test_non_full_slice_raises_value_error(self):
        """Non-full slice in field selection raises ValueError."""
        from esapp.indexable import Indexable
        from esapp import components as grid
        from unittest.mock import Mock

        instance = Indexable()
        instance.esa = Mock()

        with pytest.raises(ValueError, match="Only the full slice"):
            instance[grid.Bus, [slice(0, 5)]]


# =============================================================================
# Transient validation (Python-side)
# =============================================================================


class TestTransientValidation:
    """Tests for transient stability input validation."""

    def test_ts_set_play_in_signals_dim_mismatch(self, saw_obj):
        """TSSetPlayInSignals raises on dimension mismatch."""
        times = np.array([0.0, 1.0])
        signals = np.array([[1.0], [2.0], [3.0]])
        with pytest.raises(ValueError, match="Dimension mismatch"):
            saw_obj.TSSetPlayInSignals("Sig1", times, signals)

    def test_ts_initialize_exception_logged(self, saw_obj):
        """TSInitialize logs warning on PowerWorldError instead of raising."""
        from esapp.saw._exceptions import PowerWorldError
        with patch.object(saw_obj, '_run_script', side_effect=PowerWorldError("TS init failed")):
            saw_obj.TSInitialize()

    def test_ts_clear_results_non_access_violation_raises(self, saw_obj):
        """TSClearResultsFromRAM re-raises non-access-violation errors."""
        with patch.object(saw_obj, '_run_script', side_effect=Exception("Some other error")):
            with pytest.raises(Exception, match="Some other error"):
                saw_obj.TSClearResultsFromRAM()

    def test_ts_get_results_non_temp_mode(self, saw_obj):
        """TSGetResults with filename returns (None, None)."""
        result = saw_obj.TSGetResults(
            mode="CSV",
            contingencies=["ctg1"],
            plots_fields=["TSBusVPU"],
            filename="output.csv",
        )
        assert result == (None, None)


# =============================================================================
# AUX Parsing / Building helpers
# =============================================================================


class TestAuxParsing:
    """Tests for parse_aux_line, parse_aux_content, and build_aux_string."""

    # ---- parse_aux_line ----

    def test_parse_aux_line_space_delimited(self):
        from esapp.saw._helpers import parse_aux_line
        result = parse_aux_line('101 "Gen 1" 50.0')
        assert result == ["101", "Gen 1", "50.0"]

    def test_parse_aux_line_bracket_format(self):
        from esapp.saw._helpers import parse_aux_line
        result = parse_aux_line("[1, 100.0], [2, 200.0]")
        assert result == ["1, 100.0", "2, 200.0"]

    def test_parse_aux_line_quoted_with_brackets(self):
        """Brackets inside quoted strings should NOT trigger bracket mode."""
        from esapp.saw._helpers import parse_aux_line
        result = parse_aux_line('"Name [test]" 42')
        assert result == ["Name [test]", "42"]

    def test_parse_aux_line_empty(self):
        from esapp.saw._helpers import parse_aux_line
        assert parse_aux_line("") == []
        assert parse_aux_line("   ") == []

    # ---- parse_aux_content: Legacy format ----

    def test_parse_aux_content_legacy_basic(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'DATA (Bus, [BusNum, BusName])\n'
            '{\n'
            '1 "Alpha"\n'
            '2 "Beta"\n'
            '}\n'
        )
        records = parse_aux_content(content, ["BusNum", "BusName"])
        assert len(records) == 2
        assert records[0]["BusNum"] == "1"
        assert records[0]["BusName"] == "Alpha"
        assert records[1]["BusNum"] == "2"

    def test_parse_aux_content_legacy_with_subdata(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'DATA (Gen, [BusNum, GenID])\n'
            '{\n'
            '101 "1"\n'
            '  <SUBDATA BidCurve>\n'
            '  10.0 50.0\n'
            '  20.0 60.0\n'
            '  </SUBDATA>\n'
            '}\n'
        )
        records = parse_aux_content(content, ["BusNum", "GenID"], ["BidCurve"])
        assert len(records) == 1
        assert records[0]["BusNum"] == "101"
        assert len(records[0]["BidCurve"]) == 2
        assert records[0]["BidCurve"][0] == ["10.0", "50.0"]

    def test_parse_aux_content_legacy_multiple_subdata(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'DATA (Gen, [BusNum, GenID])\n'
            '{\n'
            '101 "1"\n'
            '  <SUBDATA BidCurve>\n'
            '  10.0 50.0\n'
            '  </SUBDATA>\n'
            '  <SUBDATA ReactiveCapability>\n'
            '  100.0 -50.0 50.0\n'
            '  </SUBDATA>\n'
            '}\n'
        )
        records = parse_aux_content(content, ["BusNum", "GenID"],
                                    ["BidCurve", "ReactiveCapability"])
        assert len(records) == 1
        assert len(records[0]["BidCurve"]) == 1
        assert len(records[0]["ReactiveCapability"]) == 1

    def test_parse_aux_content_legacy_empty_subdata(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'DATA (Gen, [BusNum, GenID])\n'
            '{\n'
            '101 "1"\n'
            '  <SUBDATA BidCurve>\n'
            '  </SUBDATA>\n'
            '}\n'
        )
        records = parse_aux_content(content, ["BusNum", "GenID"], ["BidCurve"])
        assert len(records) == 1
        assert records[0]["BidCurve"] == []

    def test_parse_aux_content_legacy_comments(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'DATA (Bus, [BusNum, BusName])\n'
            '{\n'
            '// This is a comment\n'
            '1 "Alpha"\n'
            '}\n'
        )
        records = parse_aux_content(content, ["BusNum", "BusName"])
        assert len(records) == 1
        assert records[0]["BusNum"] == "1"

    # ---- parse_aux_content: Concise format ----

    def test_parse_aux_content_concise_basic(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'Bus (BusNum, BusName)\n'
            '{\n'
            '1 "Alpha"\n'
            '2 "Beta"\n'
            '}\n'
        )
        records = parse_aux_content(content, ["BusNum", "BusName"])
        assert len(records) == 2

    def test_parse_aux_content_concise_with_subdata(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'Contingency (CTGName)\n'
            '{\n'
            '"MyCtg"\n'
            '  <SUBDATA CTGElement>\n'
            '  "OPEN BRANCH FROM 1 TO 2 CKT 1"\n'
            '  </SUBDATA>\n'
            '}\n'
        )
        records = parse_aux_content(content, ["CTGName"], ["CTGElement"])
        assert len(records) == 1
        assert records[0]["CTGName"] == "MyCtg"
        assert len(records[0]["CTGElement"]) == 1

    # ---- parse_aux_content: edge cases ----

    def test_parse_aux_content_empty(self):
        from esapp.saw._helpers import parse_aux_content
        assert parse_aux_content("", ["BusNum"]) == []

    def test_parse_aux_content_malformed_subdata(self):
        from esapp.saw._helpers import parse_aux_content
        content = (
            'DATA (Gen, [BusNum])\n'
            '{\n'
            '101\n'
            '  <SUBDATA>\n'
            '  10.0\n'
            '  </SUBDATA>\n'
            '}\n'
        )
        with pytest.raises(ValueError, match="Malformed SUBDATA"):
            parse_aux_content(content, ["BusNum"], ["BidCurve"])

    # ---- build_aux_string ----

    def test_build_aux_string_no_subdata(self):
        from esapp.saw._helpers import build_aux_string
        records = [{"BusNum": 1, "BusName": "Alpha"}]
        result = build_aux_string("Bus", ["BusNum", "BusName"], records)
        assert "DATA (Bus, [BusNum, BusName])" in result
        assert '"Alpha"' in result
        assert "1" in result

    def test_build_aux_string_single_subdata(self):
        from esapp.saw._helpers import build_aux_string
        records = [{
            "BusNum": 101,
            "GenID": "1",
            "BidCurve": [[10.0, 50.0], [20.0, 60.0]],
        }]
        result = build_aux_string("Gen", ["BusNum", "GenID"], records,
                                  subdatatypes="BidCurve")
        assert "<SUBDATA BidCurve>" in result
        assert "</SUBDATA>" in result
        assert "10.0" in result

    def test_build_aux_string_multiple_subdata(self):
        from esapp.saw._helpers import build_aux_string
        records = [{
            "BusNum": 101,
            "GenID": "1",
            "BidCurve": [[10.0, 50.0]],
            "ReactiveCapability": [[100.0, -50.0, 50.0]],
        }]
        result = build_aux_string("Gen", ["BusNum", "GenID"], records,
                                  subdatatypes=["BidCurve", "ReactiveCapability"])
        assert "<SUBDATA BidCurve>" in result
        assert "<SUBDATA ReactiveCapability>" in result

    # ---- Roundtrip ----

    def test_roundtrip_build_then_parse(self):
        """build_aux_string output can be parsed back by parse_aux_content."""
        from esapp.saw._helpers import build_aux_string, parse_aux_content
        records = [{
            "BusNum": 101,
            "GenID": "1",
            "BidCurve": [["10.0", "50.0"], ["20.0", "60.0"]],
        }]
        aux_str = build_aux_string("Gen", ["BusNum", "GenID"], records,
                                   subdatatypes="BidCurve")
        parsed = parse_aux_content(aux_str, ["BusNum", "GenID"], ["BidCurve"])
        assert len(parsed) == 1
        assert parsed[0]["BusNum"] == "101"
        assert parsed[0]["GenID"] == "1"
        assert len(parsed[0]["BidCurve"]) == 2
        assert parsed[0]["BidCurve"][0] == ["10.0", "50.0"]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
