"""
Integration tests for ATC, OPF, PV/QV, Time Step, Weather, and Scheduled Actions via SAW.

These are **integration tests** that require a live connection to PowerWorld
Simulator via the SimAuto COM interface. They test Available Transfer Capability,
Optimal Power Flow, PV/QV curve analysis, Time Step simulation, Weather models,
and Scheduled Action operations.

REQUIREMENTS:
    - PowerWorld Simulator installed with SimAuto COM registered
    - A valid PowerWorld case file path set in ``tests/config_test.py``
      (variable ``SAW_TEST_CASE``) or via the ``SAW_TEST_CASE`` env variable

RELATED TEST FILES:
    - test_integration_saw_core.py          -- base SAW operations, logging, I/O
    - test_integration_saw_modify.py        -- destructive modify, region, case actions
    - test_integration_saw_powerflow.py     -- power flow, matrices, sensitivity, topology
    - test_integration_saw_contingency.py   -- contingency and fault analysis
    - test_integration_saw_gic.py           -- GIC analysis
    - test_integration_saw_transient.py     -- transient stability
    - test_integration_workbench.py         -- PowerWorld facade and statics
    - test_integration_network.py           -- Network topology

USAGE:
    pytest tests/test_integration_saw_operations.py -v
"""

import os
import pytest
import pandas as pd
import numpy as np

from conftest import ensure_areas

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_case,
]

try:
    from esapp.saw import SAW, PowerWorldError, PowerWorldPrerequisiteError, create_object_string
except ImportError:
    raise


@pytest.fixture(scope="module")
def saw_instance(saw_session):
    """Provides the session-scoped SAW instance to the tests in this module."""
    return saw_session


# =========================================================================
# ATC (Available Transfer Capability)
# =========================================================================

class TestATC:
    """ATC analysis via SAW commands."""

    @pytest.mark.order(3950)
    def test_atc_ensure_two_areas(self, saw_instance):
        """Ensure the case has at least 2 areas for ATC testing."""
        areas = ensure_areas(saw_instance, min_count=2)
        assert areas is not None and len(areas) >= 2, "Failed to create second area"

    @pytest.mark.order(4010)
    def test_atc_determine_for_and_scenarios(self, saw_instance):
        """Test ATCDetermineATCFor, increase transfer, and take me to scenario."""
        areas = ensure_areas(saw_instance, min_count=2)
        seller = create_object_string("Area", areas.iloc[0]["AreaNum"])
        buyer = create_object_string("Area", areas.iloc[1]["AreaNum"])

        gens = saw_instance.GetParametersMultipleElement(
            "Gen", ["BusNum", "GenID", "GenMW", "GenMWMax", "AreaNum"]
        )
        for area_row in areas.itertuples():
            area_num = str(area_row.AreaNum).strip()
            area_gens = gens[gens["AreaNum"].astype(str).str.strip() == area_num]
            if area_gens.empty:
                continue
            for _, g in area_gens.head(3).iterrows():
                mw = float(g["GenMW"]) if g["GenMW"] not in (None, "") else 0
                dispatch_mw = max(mw, 10)
                saw_instance.SetData(
                    "Gen",
                    ["BusNum", "GenID", "GenMW", "GenMWMax", "GenMWMin",
                     "GenAGCAble", "GenParFac", "GenStatus"],
                    [str(g["BusNum"]).strip(), str(g["GenID"]).strip(),
                     str(dispatch_mw), str(dispatch_mw + 500), "0",
                     "YES", "1.0", "Closed"],
                )
        saw_instance.SolvePowerFlow()

        saw_instance.ATCSetAsReference()
        saw_instance.ATCDetermine(seller, buyer)

        saw_instance.ATCDetermineATCFor(0, 0, 0)
        saw_instance.ATCDetermineATCFor(0, 0, 0, apply_transfer=True)
        saw_instance.ATCIncreaseTransferBy(0.0)
        saw_instance.ATCTakeMeToScenario(0, 0, 0)

    @pytest.mark.order(4020)
    def test_atc_determine_and_results(self, saw_instance):
        """Test ATC determination and results retrieval."""
        areas = saw_instance.GetParametersMultipleElement("Area", ["AreaNum"])
        seller = create_object_string("Area", areas.iloc[0]["AreaNum"])
        buyer = create_object_string("Area", areas.iloc[1]["AreaNum"])

        saw_instance.ATCDetermine(seller, buyer)

        saw_instance._object_fields["transferlimiter"] = pd.DataFrame({
            "internal_field_name": ["LimitingContingency", "MaxFlow"],
            "field_data_type": ["String", "Real"],
            "key_field": ["", ""],
            "description": ["", ""],
            "display_name": ["", ""]
        }).sort_values(by="internal_field_name")
        saw_instance.GetATCResults(["MaxFlow", "LimitingContingency"])

    @pytest.mark.order(4025)
    def test_atc_create_contingent_interfaces(self, saw_instance):
        saw_instance.ATCCreateContingentInterfaces()
        with pytest.raises((PowerWorldPrerequisiteError, PowerWorldError)):
            saw_instance.ATCCreateContingentInterfaces(filter_name="NonExistentFilter")

    @pytest.mark.order(4030)
    def test_atc_multiple_directions(self, saw_instance):
        """Test ATC multiple directions."""
        saw_instance.DirectionsAutoInsert("AREA", "AREA")
        saw_instance.ATCDetermineMultipleDirections()

    @pytest.mark.order(4040)
    def test_atc_data_write_options(self, saw_instance, temp_file):
        tmp_aux = temp_file(".aux")
        saw_instance.ATCDataWriteOptionsAndResults(tmp_aux, append=False, key_field="PRIMARY")

    @pytest.mark.order(4042)
    def test_atc_write_results_and_options(self, saw_instance, temp_file):
        tmp_aux = temp_file(".aux")
        saw_instance.ATCWriteResultsAndOptions(tmp_aux, append=False)

    @pytest.mark.order(4043)
    def test_atc_write_scenario_log(self, saw_instance, temp_file):
        tmp_txt = temp_file(".txt")
        saw_instance.ATCWriteScenarioLog(tmp_txt, append=False)

    @pytest.mark.order(4044)
    def test_atc_write_scenario_log_with_filter(self, saw_instance, temp_file):
        tmp_txt = temp_file(".txt")
        saw_instance.ATCWriteScenarioLog(tmp_txt, append=True, filter_name="ALL")

    @pytest.mark.order(4045)
    def test_atc_write_scenario_minmax(self, saw_instance, temp_file):
        tmp_csv = temp_file(".csv")
        saw_instance.ATCWriteScenarioMinMax(tmp_csv, filetype="CSV", operation="MIN")

    @pytest.mark.order(4046)
    def test_atc_write_scenario_minmax_with_fields(self, saw_instance, temp_file):
        tmp_csv = temp_file(".csv")
        saw_instance.ATCWriteScenarioMinMax(
            tmp_csv, filetype="CSV", append=True,
            fieldlist=["TransferLimit", "Contingency"],
            operation="MAX", operation_field="TransferLimit",
            group_scenario="NONE",
        )

    @pytest.mark.order(4047)
    def test_atc_write_to_text(self, saw_instance, temp_file):
        tmp_txt = temp_file(".txt")
        saw_instance.ATCWriteToText(tmp_txt, filetype="TAB")

    @pytest.mark.order(4048)
    def test_atc_write_to_text_csv_fields(self, saw_instance, temp_file):
        tmp_csv = temp_file(".csv")
        saw_instance.ATCWriteToText(tmp_csv, filetype="CSV", fieldlist=["MaxFlow"])

    @pytest.mark.order(4049)
    def test_atc_delete_scenario_change(self, saw_instance):
        saw_instance.ATCDeleteScenarioChangeIndexRange("RL", ["0"])

    @pytest.mark.order(4050)
    def test_atc_get_results_default_fields(self, saw_instance):
        saw_instance._object_fields["transferlimiter"] = pd.DataFrame({
            "internal_field_name": ["LimitingContingency", "MaxFlow", "LimitingElement",
                                    "TransferLimit", "LimitUsed", "PTDF", "OTDF"],
            "field_data_type": ["String", "Real", "String", "Real", "String", "Real", "Real"],
            "key_field": ["", "", "", "", "", "", ""],
            "description": ["", "", "", "", "", "", ""],
            "display_name": ["", "", "", "", "", "", ""]
        }).sort_values(by="internal_field_name")
        saw_instance.GetATCResults()

    @pytest.mark.order(4090)
    def test_atc_reference_and_state(self, saw_instance):
        """Test ATC set reference, restore initial, and delete results."""
        saw_instance.ATCSetAsReference()
        saw_instance.ATCRestoreInitialState()
        saw_instance.ATCDeleteAllResults()


# =========================================================================
# OPF
# =========================================================================

class TestOPF:
    """Tests for OPF solver operations."""

    @pytest.mark.order(60000)
    def test_opf_initialize_primal_lp(self, saw_instance):
        saw_instance.InitializePrimalLP()

    @pytest.mark.order(60100)
    def test_opf_solve_primal_lp(self, saw_instance):
        saw_instance.SolvePrimalLP()

    @pytest.mark.order(60200)
    def test_opf_solve_primal_lp_with_aux(self, saw_instance, temp_file):
        tmp_aux = temp_file(".aux")
        saw_instance.SolvePrimalLP(
            on_success_aux=tmp_aux, create_if_not_found1=True
        )

    @pytest.mark.order(60300)
    def test_opf_solve_single_outer_loop(self, saw_instance):
        saw_instance.SolveSinglePrimalLPOuterLoop()

    @pytest.mark.order(60400)
    def test_opf_solve_full_scopf(self, saw_instance):
        saw_instance.SolveFullSCOPF(bc_method="OPF")

    @pytest.mark.order(60500)
    def test_opf_solve_full_scopf_powerflow(self, saw_instance):
        saw_instance.SolveFullSCOPF(bc_method="POWERFLOW")

    @pytest.mark.order(60600)
    def test_opf_write_results(self, saw_instance, temp_file):
        tmp_aux = temp_file(".aux")
        saw_instance.OPFWriteResultsAndOptions(tmp_aux)
        assert os.path.exists(tmp_aux)


# =========================================================================
# TimeStep
# =========================================================================

class TestTimeStep:
    """Time Step Simulation operations via SAW."""

    @pytest.mark.order(8900)
    def test_timestep_run(self, saw_instance):
        saw_instance.TimeStepDoRun()

    @pytest.mark.order(8910)
    def test_timestep_clear_results(self, saw_instance):
        try:
            saw_instance.TimeStepClearResults()
        except PowerWorldPrerequisiteError:
            pass

    @pytest.mark.order(8920)
    def test_timestep_reset_run(self, saw_instance):
        saw_instance.TimeStepResetRun()

    @pytest.mark.order(9100)
    def test_timestep_save(self, saw_instance, temp_file):
        tmp_pww = temp_file(".pww")
        saw_instance.TimeStepSavePWW(tmp_pww)

    @pytest.mark.order(9110)
    def test_timestep_save_results_csv(self, saw_instance, temp_file):
        tmp_csv = temp_file(".csv")
        try:
            saw_instance.TimeStepSaveResultsByTypeCSV("Gen", tmp_csv)
        except PowerWorldError:
            pass

    @pytest.mark.order(9200)
    def test_timestep_delete(self, saw_instance):
        saw_instance.TimeStepDeleteAll()

    @pytest.mark.order(9210)
    def test_timestep_fields(self, saw_instance):
        saw_instance.TimeStepSaveFieldsSet("Gen", ["GenMW"])
        saw_instance.TimeStepSaveFieldsClear(["Gen"])

    @pytest.mark.order(76200)
    def test_timestep_append_pww(self, saw_instance, temp_file):
        """TimeStepAppendPWW with a file path."""
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepAppendPWW(tmp, solution_type="Single Solution")

    @pytest.mark.order(76300)
    def test_timestep_append_pww_range(self, saw_instance, temp_file):
        """TimeStepAppendPWWRange with time range."""
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepAppendPWWRange(
                tmp, "2025-01-01T00:00:00", "2025-01-02T00:00:00",
            )

    @pytest.mark.order(76400)
    def test_timestep_append_pww_range_latlon(self, saw_instance, temp_file):
        """TimeStepAppendPWWRangeLatLon with geographic filter."""
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepAppendPWWRangeLatLon(
                tmp, "2025-01-01T00:00:00", "2025-01-02T00:00:00",
                30.0, 50.0, -100.0, -80.0,
            )

    @pytest.mark.order(76500)
    def test_timestep_load_b3d(self, saw_instance, temp_file):
        """TimeStepLoadB3D with a file path."""
        tmp = temp_file(".b3d")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepLoadB3D(tmp)

    @pytest.mark.order(76600)
    def test_timestep_load_pww(self, saw_instance, temp_file):
        """TimeStepLoadPWW with a file path."""
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepLoadPWW(tmp, solution_type="Single Solution")

    @pytest.mark.order(76700)
    def test_timestep_load_pww_range(self, saw_instance, temp_file):
        """TimeStepLoadPWWRange with time range."""
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepLoadPWWRange(
                tmp, "2025-01-01T00:00:00", "2025-01-02T00:00:00",
            )

    @pytest.mark.order(76800)
    def test_timestep_load_pww_range_latlon(self, saw_instance, temp_file):
        """TimeStepLoadPWWRangeLatLon with geographic filter."""
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepLoadPWWRangeLatLon(
                tmp, "2025-01-01T00:00:00", "2025-01-02T00:00:00",
                30.0, 50.0, -100.0, -80.0,
            )

    @pytest.mark.order(76900)
    def test_timestep_save_pww_range(self, saw_instance, temp_file):
        """TimeStepSavePWWRange with time range."""
        tmp = temp_file(".pww")
        saw_instance.TimeStepSavePWWRange(
            tmp, "2025-01-01T00:00:00", "2025-01-02T00:00:00",
        )

    @pytest.mark.order(77000)
    def test_timestep_save_selected_modify(self, saw_instance):
        """TIMESTEPSaveSelectedModifyStart/Finish cycle."""
        try:
            saw_instance.TIMESTEPSaveSelectedModifyStart()
            saw_instance.TIMESTEPSaveSelectedModifyFinish()
        except PowerWorldError:
            pass

    @pytest.mark.order(77100)
    def test_timestep_save_input_csv(self, saw_instance, temp_file):
        """TIMESTEPSaveInputCSV writes to file."""
        tmp = temp_file(".csv")
        saw_instance.TIMESTEPSaveInputCSV(tmp, ["BusNum", "BusPUVolt"])

    @pytest.mark.order(77200)
    def test_timestep_load_tsb(self, saw_instance, temp_file):
        """TimeStepLoadTSB with a file path."""
        tmp = temp_file(".tsb")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.TimeStepLoadTSB(tmp)

    @pytest.mark.order(77300)
    def test_timestep_save_tsb(self, saw_instance, temp_file):
        """TimeStepSaveTSB writes to file."""
        tmp = temp_file(".tsb")
        saw_instance.TimeStepSaveTSB(tmp)


# =========================================================================
# PV/QV
# =========================================================================

class TestPVQV:
    """PV and QV curve analysis via SAW."""

    @pytest.mark.order(9300)
    def test_pv_qv_run(self, saw_instance):
        df = saw_instance.QVRun()
        assert df is not None

    @pytest.mark.order(9450)
    def test_pv_export(self, saw_instance, temp_file):
        tmp_aux = temp_file(".aux")
        saw_instance.PVWriteResultsAndOptions(tmp_aux)
        assert os.path.exists(tmp_aux)

    @pytest.mark.order(9600)
    def test_qv_clear(self, saw_instance):
        saw_instance.QVDeleteAllResults()

    @pytest.mark.order(9700)
    def test_qv_export(self, saw_instance, temp_file):
        tmp_aux = temp_file(".aux")
        saw_instance.QVWriteResultsAndOptions(tmp_aux)
        assert os.path.exists(tmp_aux)

    @pytest.mark.order(73000)
    def test_pv_clear(self, saw_instance):
        """PVClear completes without error."""
        saw_instance.PVClear()

    @pytest.mark.order(73100)
    def test_pv_destroy(self, saw_instance):
        """PVDestroy completes without error."""
        saw_instance.PVDestroy()

    @pytest.mark.order(73200)
    def test_pv_set_source_and_sink(self, saw_instance):
        """PVSetSourceAndSink with injection group strings."""
        saw_instance.InjectionGroupCreate("PVTestSrc", "Gen", 1.0, "")
        saw_instance.InjectionGroupCreate("PVTestSink", "Load", 1.0, "")
        saw_instance.PVSetSourceAndSink(
            '[INJECTIONGROUP "PVTestSrc"]',
            '[INJECTIONGROUP "PVTestSink"]',
        )

    @pytest.mark.order(73300)
    def test_pv_start_over(self, saw_instance):
        """PVStartOver completes without error."""
        saw_instance.PVStartOver()

    @pytest.mark.order(73400)
    def test_pv_run(self, saw_instance):
        """PVRun with injection groups."""
        saw_instance.InjectionGroupCreate("PVRunSrc", "Gen", 1.0, "")
        saw_instance.InjectionGroupCreate("PVRunSink", "Load", 1.0, "")
        saw_instance.PVRun(
            '[INJECTIONGROUP "PVRunSrc"]',
            '[INJECTIONGROUP "PVRunSink"]',
        )

    @pytest.mark.order(73500)
    def test_pv_data_write_options(self, saw_instance, temp_file):
        """PVDataWriteOptionsAndResults writes to file."""
        tmp = temp_file(".aux")
        saw_instance.PVDataWriteOptionsAndResults(tmp, append=False, key_field="PRIMARY")

    @pytest.mark.order(73600)
    def test_pv_write_results_and_options(self, saw_instance, temp_file):
        """PVWriteResultsAndOptions writes to file."""
        tmp = temp_file(".aux")
        saw_instance.PVWriteResultsAndOptions(tmp, append=False)

    @pytest.mark.order(73700)
    def test_pv_write_inadequate_voltages(self, saw_instance, temp_file):
        """PVWriteInadequateVoltages writes to file."""
        tmp = temp_file(".csv")
        saw_instance.PVWriteInadequateVoltages(tmp, append=False, inadequate_type="BOTH")

    @pytest.mark.order(73800)
    def test_pv_qv_track_single_bus(self, saw_instance):
        """PVQVTrackSingleBusPerSuperBus completes without error."""
        saw_instance.PVQVTrackSingleBusPerSuperBus()

    @pytest.mark.order(73900)
    def test_refine_model(self, saw_instance):
        """RefineModel completes without error."""
        saw_instance.RefineModel("Area", "", "SHUNTS", 0.0)

    @pytest.mark.order(74000)
    def test_refine_model_with_filter(self, saw_instance):
        """RefineModel with a different action."""
        saw_instance.RefineModel("Zone", "", "OFFAVR", 0.001)

    @pytest.mark.order(74100)
    def test_qv_data_write_options(self, saw_instance, temp_file):
        """QVDataWriteOptionsAndResults writes to file."""
        tmp = temp_file(".aux")
        saw_instance.QVDataWriteOptionsAndResults(tmp, append=False, key_field="PRIMARY")

    @pytest.mark.order(74200)
    def test_qv_run_with_filename(self, saw_instance, temp_file):
        """QVRun with explicit filename returns None."""
        tmp = temp_file(".csv")
        result = saw_instance.QVRun(filename=tmp)
        assert result is None

    @pytest.mark.order(74300)
    def test_qv_select_single_bus(self, saw_instance):
        """QVSelectSingleBusPerSuperBus completes without error."""
        saw_instance.QVSelectSingleBusPerSuperBus()

    @pytest.mark.order(74400)
    def test_qv_write_curves(self, saw_instance, temp_file):
        """QVWriteCurves writes to file."""
        tmp = temp_file(".csv")
        saw_instance.QVWriteCurves(tmp, include_quantities=True, filter_name="", append=False)

    @pytest.mark.order(74500)
    def test_qv_write_results_and_options(self, saw_instance, temp_file):
        """QVWriteResultsAndOptions writes to file."""
        tmp = temp_file(".aux")
        saw_instance.QVWriteResultsAndOptions(tmp, append=False)

    @pytest.mark.order(74600)
    def test_qv_delete_all_results(self, saw_instance):
        """QVDeleteAllResults completes without error."""
        saw_instance.QVDeleteAllResults()


# =========================================================================
# Scheduled Actions
# =========================================================================

class TestScheduledActions:
    """Tests for Scheduled Actions mixin."""

    @pytest.mark.order(50000)
    def test_scheduled_set_reference(self, saw_instance):
        saw_instance.ScheduledActionsSetReference()

    @pytest.mark.order(50100)
    def test_scheduled_apply_at(self, saw_instance):
        """ApplyScheduledActionsAt with various parameter combinations."""
        saw_instance.ApplyScheduledActionsAt("01/01/2025 10:00")
        saw_instance.ApplyScheduledActionsAt(
            "01/01/2025 10:00", end_time="01/01/2025 12:00"
        )
        saw_instance.ApplyScheduledActionsAt(
            "01/01/2025 10:00", filter_name="ALL"
        )
        saw_instance.ApplyScheduledActionsAt(
            "01/01/2025 10:00", revert=True
        )

    @pytest.mark.order(50500)
    def test_scheduled_revert_at(self, saw_instance):
        """RevertScheduledActionsAt with and without filter."""
        saw_instance.RevertScheduledActionsAt("01/01/2025 10:00")
        saw_instance.RevertScheduledActionsAt(
            "01/01/2025 10:00", filter_name="ALL"
        )

    @pytest.mark.order(50700)
    def test_scheduled_identify_breakers(self, saw_instance):
        """IdentifyBreakersForScheduledActions with both boolean values."""
        saw_instance.IdentifyBreakersForScheduledActions(identify_from_normal=True)
        saw_instance.IdentifyBreakersForScheduledActions(identify_from_normal=False)

    @pytest.mark.order(50900)
    def test_scheduled_set_view(self, saw_instance):
        """SetScheduleView with and without options."""
        saw_instance.SetScheduleView("01/01/2025 10:00")
        saw_instance.SetScheduleView(
            "01/01/2025 10:00",
            apply_actions=True,
            use_normal_status=False,
            apply_window=True,
        )

    @pytest.mark.order(51100)
    def test_scheduled_set_window(self, saw_instance):
        """SetScheduleWindow with different resolutions."""
        saw_instance.SetScheduleWindow(
            "01/01/2025 00:00", "02/01/2025 00:00",
            resolution=1.0, resolution_units="HOURS",
        )
        saw_instance.SetScheduleWindow(
            "01/01/2025 00:00",
            "02/01/2025 00:00",
            resolution=0.5,
            resolution_units="HOURS",
        )


# =========================================================================
# Weather
# =========================================================================

class TestWeather:
    """Tests for Weather mixin."""

    @pytest.mark.order(52010)
    def test_weather_limits_gen_update(self, saw_instance):
        """WeatherLimitsGenUpdate with both true and false params."""
        saw_instance.WeatherLimitsGenUpdate(update_max=True, update_min=True)
        saw_instance.WeatherLimitsGenUpdate(update_max=False, update_min=False)

    @pytest.mark.order(52200)
    def test_weather_temperature_limits_branch(self, saw_instance):
        saw_instance.TemperatureLimitsBranchUpdate()

    @pytest.mark.order(52300)
    def test_weather_temperature_limits_branch_custom(self, saw_instance):
        saw_instance.TemperatureLimitsBranchUpdate(
            rating_set_precedence="CTG",
            normal_rating_set="A",
            ctg_rating_set="B",
        )

    @pytest.mark.order(52400)
    def test_weather_pfw_set_inputs(self, saw_instance):
        saw_instance.WeatherPFWModelsSetInputs()

    @pytest.mark.order(52500)
    def test_weather_pfw_set_inputs_and_apply(self, saw_instance):
        """WeatherPFWModelsSetInputsAndApply with and without solve."""
        saw_instance.WeatherPFWModelsSetInputsAndApply(solve_pf=True)
        saw_instance.WeatherPFWModelsSetInputsAndApply(solve_pf=False)

    @pytest.mark.order(52700)
    def test_weather_pfw_restore_design(self, saw_instance):
        saw_instance.WeatherPFWModelsRestoreDesignValues()

    @pytest.mark.order(52800)
    def test_weather_pww_load_datetime(self, saw_instance):
        try:
            saw_instance.WeatherPWWLoadForDateTimeUTC("2025-01-01T10:00:00")
        except PowerWorldPrerequisiteError:
            pass

    @pytest.mark.order(52900)
    def test_weather_pww_set_directory(self, saw_instance, temp_dir):
        """WeatherPWWSetDirectory with and without subdirs."""
        saw_instance.WeatherPWWSetDirectory(str(temp_dir), include_subdirs=True)
        saw_instance.WeatherPWWSetDirectory(str(temp_dir), include_subdirs=False)

    @pytest.mark.order(53100)
    def test_weather_pww_file_all_meas_valid(self, saw_instance, temp_file):
        tmp = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.WeatherPWWFileAllMeasValid(tmp, ["Temperature"])

    @pytest.mark.order(53200)
    def test_weather_pww_file_combine(self, saw_instance, temp_file):
        src1 = temp_file(".pww")
        src2 = temp_file(".pww")
        dst = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.WeatherPWWFileCombine2(src1, src2, dst)

    @pytest.mark.order(53300)
    def test_weather_pww_file_geo_reduce(self, saw_instance, temp_file):
        src = temp_file(".pww")
        dst = temp_file(".pww")
        with pytest.raises((PowerWorldError, PowerWorldPrerequisiteError)):
            saw_instance.WeatherPWWFileGeoReduce(src, dst, 30.0, 50.0, -100.0, -80.0)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
