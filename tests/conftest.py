"""
Global fixtures for the ESA++ test suite.

Provides reusable test fixtures for both offline (mocked) and online
(integration) testing of the ESA++ library.
"""
import pytest
import os
import hashlib
import tempfile
import warnings
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

if TYPE_CHECKING:
    from esapp.saw import SAW

try:
    from esapp.saw import SAW
except ImportError:
    SAW = None  # type: ignore


def _get_test_case_path():
    """
    Get the test case path from configuration.

    Priority order:
    1. Environment variable SAW_TEST_CASE
    2. config_test.py file
    3. None (skip online tests)
    """
    env_path = os.environ.get("SAW_TEST_CASE")
    if env_path:
        return env_path

    try:
        import config_test
        if hasattr(config_test, 'SAW_TEST_CASE'):
            return config_test.SAW_TEST_CASE
    except ImportError:
        pass

    return None


def _get_gic_test_cases():
    """
    Get additional GIC test case paths from configuration.

    Returns a list of (path, label) tuples for parametrization.
    Only includes paths that exist on disk.
    """
    try:
        import config_test
        if hasattr(config_test, 'GIC_TEST_CASES'):
            cases = []
            for path in config_test.GIC_TEST_CASES:
                if os.path.exists(path):
                    label = os.path.splitext(os.path.basename(path))[0]
                    cases.append((path, label))
            return cases
    except ImportError:
        pass
    return []


# -------------------------------------------------------------------------
# Integration fixture (live PowerWorld)
# -------------------------------------------------------------------------

@pytest.fixture(scope="session")
def saw_session():
    """
    Session-scoped SAW instance connected to a live PowerWorld case.

    Configuration:
        Set case path in config_test.py or via SAW_TEST_CASE env variable.
    """
    if SAW is None:
        pytest.skip("esapp library not found.")

    case_path = _get_test_case_path()
    if not case_path:
        pytest.skip("SAW test case not configured. Set path in tests/config_test.py or SAW_TEST_CASE env variable.")

    if not os.path.exists(case_path):
        pytest.skip(f"SAW test case file not found: {case_path}")

    print(f"\n[Session Setup] Connecting to PowerWorld with case: {case_path}")
    saw = None
    try:
        saw = SAW(case_path, CreateIfNotFound=True, early_bind=True)
        yield saw
    finally:
        print("\n[Session Teardown] Closing case and exiting PowerWorld...")
        if saw is not None:
            try:
                saw.exit()
            except Exception as e:
                print(f"Warning: Error during SAW cleanup: {e}")


# -------------------------------------------------------------------------
# Case file integrity check
# -------------------------------------------------------------------------

def _file_hash(path):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="session")
def _case_file_hash():
    """Record the on-disk hash of the test case file at session start."""
    case_path = _get_test_case_path()
    if not case_path or not os.path.exists(case_path):
        yield None
        return
    yield _file_hash(case_path)


@pytest.fixture(autouse=True, scope="class")
def _check_case_file_integrity(_case_file_hash):
    """Fail loudly if any test class accidentally saves over the case file."""
    yield
    if _case_file_hash is None:
        return
    case_path = _get_test_case_path()
    if not case_path or not os.path.exists(case_path):
        return
    current_hash = _file_hash(case_path)
    if current_hash != _case_file_hash:
        pytest.fail(
            f"CASE FILE MODIFIED ON DISK! The test case file has been "
            f"altered by a test. This will corrupt results for subsequent "
            f"tests. File: {case_path}"
        )


# -------------------------------------------------------------------------
# GIC multi-case fixture
# -------------------------------------------------------------------------

def pytest_generate_tests(metafunc):
    """Parametrize tests that request the gic_saw fixture."""
    if "gic_saw" in metafunc.fixturenames:
        cases = _get_gic_test_cases()
        if cases:
            metafunc.parametrize(
                "gic_saw",
                [path for path, _ in cases],
                ids=[label for _, label in cases],
                indirect=True,
            )
        else:
            # Fall back to main case
            main = _get_test_case_path()
            if main and os.path.exists(main):
                label = os.path.splitext(os.path.basename(main))[0]
                metafunc.parametrize("gic_saw", [main], ids=[label], indirect=True)


@pytest.fixture
def gic_saw(request, saw_session):
    """
    Reuses the session SAW instance but swaps in a different case file.

    After the test, the original session case is reopened so subsequent
    tests are not affected. This avoids creating a second PowerWorld COM
    connection, which would conflict with the single-instance application.
    """
    case_path = request.param
    original_case = _get_test_case_path()
    label = os.path.splitext(os.path.basename(case_path))[0]

    # Always reload the case from disk to ensure a clean state,
    # even when it's the same as the session case (prior tests may
    # have modified the in-memory state).
    print(f"\n[GIC] Loading case: {label}")
    saw_session.CloseCase()
    saw_session.OpenCase(case_path)
    try:
        yield saw_session
    finally:
        # Restore the original session case if we switched to a different one
        if os.path.normcase(os.path.abspath(case_path)) != os.path.normcase(os.path.abspath(original_case)):
            print(f"\n[GIC] Restoring original case")
            try:
                saw_session.CloseCase()
                saw_session.OpenCase(original_case)
            except Exception:
                pass


# -------------------------------------------------------------------------
# Unit test fixture (mocked COM)
# -------------------------------------------------------------------------

@pytest.fixture(scope="function")
def saw_obj():
    """
    Function-scoped mocked SAW object for offline unit tests.

    Patches COM dispatch calls to prevent actual PowerWorld connection.
    """
    with patch("win32com.client.dynamic.Dispatch") as mock_dispatch, \
         patch("win32com.client.gencache.EnsureDispatch", create=True) as mock_ensure_dispatch, \
         patch("tempfile.NamedTemporaryFile") as mock_tempfile, \
         patch("os.unlink"):

        mock_pwcom = MagicMock()
        mock_dispatch.return_value = mock_pwcom
        mock_ensure_dispatch.return_value = mock_pwcom

        mock_ntf = Mock()
        mock_ntf.name = "dummy_temp.axd"
        mock_tempfile.return_value = mock_ntf

        mock_pwcom.RunScriptCommand.return_value = ("",)
        mock_pwcom.ChangeParametersSingleElement.return_value = ("",)
        mock_pwcom.ProcessAuxFile.return_value = ("",)
        mock_pwcom.SaveCase.return_value = ("",)
        mock_pwcom.CloseCase.return_value = ("",)
        mock_pwcom.GetCaseHeader.return_value = ("",)
        mock_pwcom.ChangeParametersMultipleElementRect.return_value = ("",)
        mock_pwcom.GetParametersMultipleElement.return_value = ("", [[1, 2], ["Bus1", "Bus2"]])
        mock_pwcom.OpenCase.return_value = ("",)
        mock_pwcom.GetParametersSingleElement.return_value = ("", ("23", "Jan 01 2023"))
        field_list_data = [
            ["*1*", "BusNum", "Integer", "Bus Number", "Bus Number"],
            ["*2*", "BusName", "String", "Bus Name", "Bus Name"],
        ]
        mock_pwcom.GetFieldList.return_value = ("", field_list_data)

        saw_instance = SAW(FileName="dummy.pwb")
        saw_instance._pwcom = mock_pwcom

        yield saw_instance


# -------------------------------------------------------------------------
# Utility fixtures
# -------------------------------------------------------------------------

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Temporary directory for test file operations."""
    return tmp_path


@pytest.fixture
def temp_file():
    """Factory for temporary files with automatic cleanup."""
    import tempfile
    files = []

    def _create(suffix):
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tf.close()
        files.append(tf.name)
        return tf.name

    yield _create

    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


# -------------------------------------------------------------------------
# Test configuration
# -------------------------------------------------------------------------

def pytest_configure(config):
    """Add custom markers for test organization."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests requiring PowerWorld")
    config.addinivalue_line("markers", "unit: marks tests with mocked dependencies")
    config.addinivalue_line("markers", "requires_case: marks tests requiring a valid case file")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on file naming."""
    for item in items:
        if "test_integration_" in item.nodeid:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.requires_case)
        elif "test_" in item.nodeid and "test_integration_" not in item.nodeid:
            item.add_marker(pytest.mark.unit)


# -------------------------------------------------------------------------
# Shared test utilities
# -------------------------------------------------------------------------

def get_all_gobject_subclasses():
    """Recursively find all GObject subclasses with a _TYPE attribute."""
    try:
        from esapp import components as grid
    except ImportError:
        return []

    all_subclasses = []
    q = list(grid.GObject.__subclasses__())
    visited = set(q)
    while q:
        cls = q.pop(0)
        if hasattr(cls, '_TYPE'):
            all_subclasses.append(cls)
        for subclass in cls.__subclasses__():
            if subclass not in visited:
                visited.add(subclass)
                q.append(subclass)
    return all_subclasses


def get_sample_gobject_subclasses(require_keys=False, require_multiple_editable=False, require_editable_non_key=False):
    """Return a representative sample of GObject subclasses for faster parametrized tests.

    Parameters
    ----------
    require_keys : bool
        If True, only return classes with at least one key field.
    require_multiple_editable : bool
        If True, only return classes with at least 2 editable non-key fields.
    require_editable_non_key : bool
        If True, only return classes with at least 1 editable non-key field.
    """
    try:
        from esapp import components as grid
        all_classes = get_all_gobject_subclasses()

        if not all_classes:
            import warnings
            warnings.warn("No GObject subclasses found.")
            return []

        # Apply filters if requested
        if require_keys:
            all_classes = [c for c in all_classes if hasattr(c, 'keys') and c.keys()]

        if require_editable_non_key:
            def has_editable_non_key(cls):
                if not hasattr(cls, 'editable') or not hasattr(cls, 'keys'):
                    return False
                editable_non_key = [f for f in cls.editable() if f not in cls.keys()]
                return len(editable_non_key) >= 1
            all_classes = [c for c in all_classes if has_editable_non_key(c)]

        if require_multiple_editable:
            def has_multiple_editable(cls):
                if not hasattr(cls, 'editable') or not hasattr(cls, 'keys'):
                    return False
                editable_non_key = [f for f in cls.editable() if f not in cls.keys()]
                return len(editable_non_key) >= 2
            all_classes = [c for c in all_classes if has_multiple_editable(c)]

        priority_types = ['Bus', 'Gen', 'Load', 'Branch', 'Shunt', 'Area', 'Zone',
                         'Contingency', 'Interface', 'InjectionGroup']

        sample = []
        for type_name in priority_types:
            for cls in all_classes:
                if hasattr(cls, 'TYPE') and cls.TYPE() == type_name:
                    sample.append(cls)
                    break

        import random
        random.seed(42)
        remaining = [c for c in all_classes if c not in sample]
        if remaining and len(sample) < 15:
            sample.extend(random.sample(remaining, min(5, len(remaining))))

        return sample
    except (ImportError, Exception) as e:
        import warnings
        warnings.warn(f"Error getting GObject subclasses: {e}")
        return []


def assert_dataframe_valid(df, expected_columns=None, min_rows=1, name="DataFrame"):
    """Assert a DataFrame is valid and has expected structure."""
    import pandas as pd
    assert df is not None, f"{name} is None"
    assert isinstance(df, pd.DataFrame), f"{name} is not a DataFrame"
    assert len(df) >= min_rows, f"{name} has {len(df)} rows, expected at least {min_rows}"
    if expected_columns:
        for col in expected_columns:
            assert col in df.columns, f"{name} missing column: {col}"


def ensure_areas(saw, min_count=2):
    """Ensure at least *min_count* areas exist with buses, creating if needed.

    If the case has fewer areas than *min_count*, new areas are created
    and buses are reassigned from the largest area so each area has
    network elements (required for ATC, directions, etc.).

    Returns the area DataFrame (guaranteed to have >= min_count rows).
    """
    areas = saw.GetParametersMultipleElement("Area", ["AreaNum"])
    if areas is not None and len(areas) >= min_count:
        return areas
    existing = set(int(a) for a in areas["AreaNum"]) if areas is not None and not areas.empty else set()
    next_num = max(existing, default=0) + 1
    buses = saw.GetParametersMultipleElement("Bus", ["BusNum", "AreaNum"])
    assert buses is not None and not buses.empty, "Test case must contain buses"
    buses["BusNum"] = buses["BusNum"].astype(str)
    buses["AreaNum"] = buses["AreaNum"].astype(str)
    while len(existing) < min_count:
        saw.CreateData("Area", ["AreaNum", "AreaName"], [next_num, f"TestArea{next_num}"])
        area_counts = buses["AreaNum"].value_counts()
        largest_area = area_counts.index[0]
        donor_buses = buses[buses["AreaNum"] == largest_area]
        if len(donor_buses) > 1:
            bus_to_move = str(donor_buses.iloc[-1]["BusNum"])
            saw.ChangeParametersSingleElement(
                "Bus", ["BusNum", "AreaNum"], [bus_to_move, next_num]
            )
            buses.loc[buses["BusNum"] == bus_to_move, "AreaNum"] = str(next_num)
        existing.add(next_num)
        next_num += 1
    return saw.GetParametersMultipleElement("Area", ["AreaNum"])


@pytest.fixture(scope="class")
def save_restore_state(saw_session):
    """Saves case state before destructive tests and restores it after."""
    state_name = "__test_save_restore_state__"
    saw_session.StoreState(state_name)
    yield saw_session
    try:
        saw_session.RestoreState(state_name)
        saw_session.DeleteState(state_name)
    except Exception:
        pass


# -------------------------------------------------------------------------
# PW Log Capture — on test failure the PowerWorld message log is
# retrieved and printed so you can see exactly what PW did.
# -------------------------------------------------------------------------

_PW_LOG_PATH = os.path.join(tempfile.gettempdir(), "esapp_test_pw_log.txt")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Record whether the test call phase failed."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        item._pw_test_failed = True


@pytest.fixture(autouse=True)
def _capture_pw_log(request):
    """Clear the PW log before each test; on failure, dump it to stdout."""
    should_capture = (
        "saw_session" in request.fixturenames
        or request.node.get_closest_marker("integration") is not None
    )
    if not should_capture:
        yield
        return

    saw_session = request.getfixturevalue("saw_session")

    try:
        saw_session.LogClear()
    except Exception:
        pass

    yield

    # Only retrieve the log when the test failed
    if not getattr(request.node, "_pw_test_failed", False):
        return

    try:
        saw_session.LogSave(_PW_LOG_PATH)
        if os.path.exists(_PW_LOG_PATH):
            with open(_PW_LOG_PATH, "r", errors="replace") as f:
                pw_log = f.read().strip()
            if pw_log:
                # Print to stdout — pytest captures this and shows it
                # in the "Captured stdout teardown" section of the failure.
                print(f"\n{'=' * 60}")
                print(f"PW Log ({request.node.name})")
                print(f"{'=' * 60}")
                print(pw_log)
                print(f"{'=' * 60}")
    except Exception:
        pass
