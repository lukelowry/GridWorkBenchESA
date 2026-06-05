"""
Integration tests for the BusCat class (esapp.utils.buscat).

These are **integration tests** that require a live connection to PowerWorld
Simulator via the SimAuto COM interface. They test BusCat classification
against a real solved power flow case.

REQUIREMENTS:
    - PowerWorld Simulator installed with SimAuto COM registered
    - A valid PowerWorld case file path set in ``tests/config_test.py``
      (variable ``SAW_TEST_CASE``) or via the ``SAW_TEST_CASE`` env variable

USAGE:
    pytest tests/test_integration_buscat.py -v
"""
import pytest
import pandas as pd

from esapp.utils.buscat import BusCat
from esapp.components import Bus
from esapp.workbench import PowerWorld

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_case,
]


@pytest.fixture(scope="module")
def pw(saw_session):
    """PowerWorld instance connected to the session SAW."""
    pw = PowerWorld()
    pw.esa = saw_session
    return pw


@pytest.fixture(scope="module")
def bc(pw):
    """BusCat instance after solving power flow and refreshing."""
    pw.pflow()
    return pw.buscat.refresh()


class TestBusCat:

    @pytest.mark.order(7000)
    def test_refresh_returns_self(self, pw):
        result = pw.buscat.refresh()
        assert result is pw.buscat

    @pytest.mark.order(7010)
    def test_df_has_expected_columns(self, bc):
        expected = {"VSet", "LimLow", "LimHigh",
                    "Type", "Ctrl", "Role", "Lim", "SVC", "Eff", "Reg"}
        assert expected.issubset(set(bc.df.columns))

    @pytest.mark.order(7020)
    def test_df_row_count_matches_buses(self, bc, pw):
        n_bus = len(pw[Bus])
        assert len(bc.df) == n_bus

    @pytest.mark.order(7100)
    def test_type_partition_covers_all_buses(self, bc):
        """slack + pv(all) + pq = all buses."""
        all_idx = sorted(
            bc.slack_idx() + bc.pv_idx(active_only=False) + bc.pq_idx()
        )
        expected = sorted(bc.df.index.tolist())
        assert all_idx == expected

    @pytest.mark.order(7110)
    def test_equation_partition(self, bc):
        """has_q_eqn + no_q_eqn = all buses (disjoint)."""
        q = set(bc.has_q_eqn_idx())
        no_q = set(bc.no_q_eqn_idx())
        all_buses = set(bc.df.index.tolist())
        assert q | no_q == all_buses
        assert q & no_q == set()

    @pytest.mark.order(7120)
    def test_has_p_eqn_excludes_slack(self, bc):
        p = set(bc.has_p_eqn_idx())
        slack = set(bc.slack_idx())
        assert p & slack == set()
        assert p | slack == set(bc.df.index.tolist())

    @pytest.mark.order(7130)
    def test_has_v_eqn_matches_eff_pv_and_slack(self, bc):
        v = set(bc.has_v_eqn_idx())
        pv_slack = set(bc.eff_pv_idx() + bc.slack_idx())
        assert v == pv_slack

    @pytest.mark.order(7200)
    def test_at_least_one_slack(self, bc):
        assert len(bc.slack_idx()) >= 1

    @pytest.mark.order(7210)
    def test_v_setpoints_length(self, bc):
        assert len(bc.v_setpoints()) == len(bc.has_v_eqn_idx())

    @pytest.mark.order(7220)
    def test_v_setpoints_non_negative(self, bc):
        """Voltage setpoints should be non-negative (per-unit)."""
        v = bc.v_setpoints()
        if len(v) > 0:
            assert (v >= 0).all()

    @pytest.mark.order(7300)
    def test_effective_type_partition(self, bc):
        """eff_slack + eff_pv + eff_pq = all buses."""
        all_idx = sorted(
            bc.slack_idx() + bc.eff_pv_idx() + bc.eff_pq_idx()
        )
        expected = sorted(bc.df.index.tolist())
        assert all_idx == expected

    @pytest.mark.order(7400)
    def test_regulating_subset_of_pv_and_slack(self, bc):
        """Regulating buses must be PV or Slack type."""
        reg = set(bc.regulating_idx())
        pv_slack = set(
            bc.pv_idx(active_only=False) + bc.slack_idx()
        )
        assert reg.issubset(pv_slack)

    @pytest.mark.order(7500)
    def test_constrained_have_lim_flag(self, bc):
        """Every constrained bus should have Lim=True in the DataFrame."""
        for idx in bc.constrained_idx():
            assert bc.df.loc[idx, "Lim"] == True

    @pytest.mark.order(7600)
    def test_pv_dataframe_accessor(self, bc):
        pv_df = bc.pv()
        assert isinstance(pv_df, pd.DataFrame)
        if len(pv_df) > 0:
            assert (pv_df["Type"] == "PV").all()
            assert (pv_df["Reg"]).all()

    @pytest.mark.order(7610)
    def test_remote_masters_have_primary_role(self, bc):
        rm = bc.remote_masters()
        if len(rm) > 0:
            assert (rm["Role"] == "PRIMARY").all()

    @pytest.mark.order(7700)
    def test_svc_idx(self, bc):
        """svc_idx returns a list and all flagged buses have SVC=True."""
        svc = bc.svc_idx()
        assert isinstance(svc, list)
        for idx in svc:
            assert bc.df.loc[idx, "SVC"] == True

    @pytest.mark.order(7710)
    def test_primary_idx(self, bc):
        """primary_idx returns only PRIMARY role buses."""
        for idx in bc.primary_idx():
            assert bc.df.loc[idx, "Role"] == "PRIMARY"

    @pytest.mark.order(7720)
    def test_secondary_idx(self, bc):
        """secondary_idx returns only SECONDARY role buses."""
        for idx in bc.secondary_idx():
            assert bc.df.loc[idx, "Role"] == "SECONDARY"

    @pytest.mark.order(7730)
    def test_target_idx(self, bc):
        """target_idx returns only TARGET role buses."""
        for idx in bc.target_idx():
            assert bc.df.loc[idx, "Role"] == "TARGET"

    @pytest.mark.order(7740)
    def test_local_only_idx(self, bc):
        """local_only buses are regulating with no remote/droop role."""
        for idx in bc.local_only_idx():
            assert bc.df.loc[idx, "Role"] == ""
            assert bc.df.loc[idx, "Reg"] == True

    @pytest.mark.order(7750)
    def test_constrained_dataframe(self, bc):
        """constrained() DataFrame accessor matches constrained_idx()."""
        c_df = bc.constrained()
        assert isinstance(c_df, pd.DataFrame)
        assert sorted(c_df.index.tolist()) == sorted(bc.constrained_idx())
