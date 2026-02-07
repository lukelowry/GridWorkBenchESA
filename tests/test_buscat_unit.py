"""
Unit tests for parse_buscat string parsing logic.

These are **unit tests** that do NOT require PowerWorld Simulator.
They test the pure-Python BusCat string parser against all known
BusCat string variants returned by PowerWorld.

USAGE:
    pytest tests/test_buscat_unit.py -v
"""
import pytest
from esapp.utils.buscat import parse_buscat


# =============================================================================
# parse_buscat — exhaustive BusCat string test matrix
# =============================================================================


class TestParseBuscat:
    """Test parse_buscat against all known BusCat strings."""

    # --- Slack ---

    def test_slack(self):
        r = parse_buscat("Slack")
        assert r["Type"] == "SLACK"
        assert r["Ctrl"] == "NONE"
        assert r["Role"] == ""
        assert r["Lim"] is False
        assert r["SVC"] is False
        assert r["Eff"] == "SLACK"
        assert r["Reg"] is True

    # --- PQ variants ---

    def test_pq_plain(self):
        r = parse_buscat("PQ")
        assert r["Type"] == "PQ"
        assert r["Ctrl"] == "NONE"
        assert r["Role"] == ""
        assert r["Lim"] is False
        assert r["SVC"] is False
        assert r["Eff"] == "PQ"
        assert r["Reg"] is False

    def test_pq_gens_at_var_limit(self):
        r = parse_buscat("PQ (Gens at Var Limit)")
        assert r["Type"] == "PQ"
        assert r["Lim"] is True
        assert r["SVC"] is False
        assert r["Eff"] == "PQ"

    def test_pq_remotely_regulated(self):
        r = parse_buscat("PQ (Remotely Regulated)")
        assert r["Type"] == "PQ"
        assert r["Ctrl"] == "REMOTE"
        assert r["Role"] == "TARGET"
        assert r["Lim"] is False

    def test_pq_remote_reg_secondary(self):
        r = parse_buscat("PQ (Remote Reg Secondary)")
        assert r["Type"] == "PQ"
        assert r["Ctrl"] == "REMOTE"
        assert r["Role"] == "SECONDARY"

    def test_pq_svc_at_limit(self):
        r = parse_buscat("PQ (SVC at Limit)")
        assert r["Lim"] is True
        assert r["SVC"] is True

    def test_pq_continuous_shunts_at_var_limit(self):
        r = parse_buscat("PQ (Continuous Shunts at Var Limit)")
        assert r["Lim"] is True
        assert r["SVC"] is True

    def test_pq_remotely_regulated_at_var_limit(self):
        r = parse_buscat("PQ (Remotely Regulated at Var Limit)")
        assert r["Ctrl"] == "REMOTE"
        assert r["Role"] == "TARGET"
        assert r["Lim"] is True

    def test_pq_line_drop_comp(self):
        r = parse_buscat("PQ (Line Drop Comp)")
        assert r["Ctrl"] == "LDC"
        assert r["Role"] == ""
        assert r["SVC"] is False

    def test_pq_svc_line_drop_comp(self):
        r = parse_buscat("PQ (SVC Line Drop Comp)")
        assert r["Ctrl"] == "LDC"
        assert r["SVC"] is True

    def test_pq_voltage_droop_reg_bus(self):
        r = parse_buscat("PQ (Voltage Droop Reg Bus)")
        assert "REMOTE" in r["Ctrl"]
        assert "DROOP" in r["Ctrl"]
        assert r["Role"] == "TARGET"

    def test_pq_voltage_droop_remote_bus(self):
        r = parse_buscat("PQ (Voltage Droop Remote Bus)")
        assert "REMOTE" in r["Ctrl"]
        assert "DROOP" in r["Ctrl"]
        assert r["Role"] == "SECONDARY"

    def test_pq_voltage_droop_reg_bus_at_var_limit(self):
        r = parse_buscat("PQ (Voltage Droop Reg Bus at Var Limit)")
        assert "REMOTE" in r["Ctrl"]
        assert "DROOP" in r["Ctrl"]
        assert r["Role"] == "TARGET"
        assert r["Lim"] is True

    def test_pq_voltage_droop_remote_bus_at_var_limit(self):
        r = parse_buscat("PQ (Voltage Droop Remote Bus at Var Limit)")
        assert "REMOTE" in r["Ctrl"]
        assert "DROOP" in r["Ctrl"]
        assert r["Role"] == "SECONDARY"
        assert r["Lim"] is True

    # --- PV variants ---

    def test_pv_plain(self):
        r = parse_buscat("PV")
        assert r["Type"] == "PV"
        assert r["Ctrl"] == "NONE"
        assert r["Role"] == ""
        assert r["Lim"] is False
        assert r["SVC"] is False
        assert r["Eff"] == "PV"
        assert r["Reg"] is True

    def test_pv_remote_reg_primary(self):
        r = parse_buscat("PV (Remote Reg Primary)")
        assert r["Type"] == "PV"
        assert r["Ctrl"] == "REMOTE"
        assert r["Role"] == "PRIMARY"

    def test_pv_svc(self):
        r = parse_buscat("PV (SVC)")
        assert r["Type"] == "PV"
        assert r["SVC"] is True
        assert r["Reg"] is True

    def test_pv_local_remote_reg_primary(self):
        r = parse_buscat("PV (Local/Remote Reg Primary)")
        assert r["Type"] == "PV"
        assert r["Ctrl"] == "REMOTE"
        assert r["Role"] == "PRIMARY"

    def test_pvtol(self):
        r = parse_buscat("PVTol")
        assert r["Type"] == "PV"
        assert r["Ctrl"] == "TOL"
        assert r["Role"] == ""
        assert r["Eff"] == "PV"

    def test_pvtol_remote_reg_primary(self):
        r = parse_buscat("PVTol (Remote Reg Primary)")
        assert r["Type"] == "PV"
        assert "REMOTE" in r["Ctrl"]
        assert "TOL" in r["Ctrl"]
        assert r["Role"] == "PRIMARY"

    def test_pvtol_local_remote_reg_primary(self):
        r = parse_buscat("PVTol (Local/Remote Reg Primary)")
        assert r["Type"] == "PV"
        assert "REMOTE" in r["Ctrl"]
        assert "TOL" in r["Ctrl"]
        assert r["Role"] == "PRIMARY"

    # --- Effective type and regulation ---

    def test_pq_at_limit_stays_pq(self):
        """PQ buses at limit are still effectively PQ."""
        r = parse_buscat("PQ (Gens at Var Limit)")
        assert r["Eff"] == "PQ"

    def test_pq_never_regulates(self):
        """PQ buses never regulate voltage."""
        r = parse_buscat("PQ")
        assert r["Reg"] is False

    def test_slack_always_regulates(self):
        r = parse_buscat("Slack")
        assert r["Reg"] is True
