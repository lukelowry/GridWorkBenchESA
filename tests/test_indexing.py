"""
Unit tests for the Indexable class data access (wb[GObject, "field"] syntax).

These are **unit tests** that do NOT require PowerWorld Simulator. All
PowerWorld COM interactions are mocked. They test __getitem__ and __setitem__
for reading/writing PowerWorld data, including broadcast, bulk update,
keyless objects, and error handling.

USAGE:
    pytest tests/test_indexing.py -v
"""
import pytest
from unittest.mock import Mock, patch
from typing import Type
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np

from esapp.indexable import Indexable
from esapp import components as grid
from tests.conftest import get_sample_gobject_subclasses


def pytest_generate_tests(metafunc):
    """Dynamically parametrize tests that use the g_object fixture."""
    if "g_object" in metafunc.fixturenames:
        classes = get_sample_gobject_subclasses()
        ids = [c.TYPE() if hasattr(c, 'TYPE') else c.__name__ for c in classes]
        metafunc.parametrize("g_object", classes, ids=ids)
    elif "g_object_keyed" in metafunc.fixturenames:
        # Objects that have keys (for tests that require GetParamsRectTyped to return key data)
        classes = get_sample_gobject_subclasses(require_keys=True)
        ids = [c.TYPE() if hasattr(c, 'TYPE') else c.__name__ for c in classes]
        metafunc.parametrize("g_object_keyed", classes, ids=ids)
    elif "g_object_keyed_editable" in metafunc.fixturenames:
        # Objects with keys AND at least 1 editable non-key field
        classes = get_sample_gobject_subclasses(require_keys=True, require_editable_non_key=True)
        ids = [c.TYPE() if hasattr(c, 'TYPE') else c.__name__ for c in classes]
        metafunc.parametrize("g_object_keyed_editable", classes, ids=ids)
    elif "g_object_multi_editable" in metafunc.fixturenames:
        # Objects with at least 2 editable non-key fields
        classes = get_sample_gobject_subclasses(require_multiple_editable=True)
        ids = [c.TYPE() if hasattr(c, 'TYPE') else c.__name__ for c in classes]
        metafunc.parametrize("g_object_multi_editable", classes, ids=ids)


@pytest.fixture
def indexable_instance() -> Indexable:
    """Provides an Indexable instance with a mocked SAW dependency."""
    with patch('esapp.indexable.SAW') as mock_saw_class:
        mock_esa = Mock()
        mock_saw_class.return_value = mock_esa
        instance = Indexable()
        instance.esa = mock_esa
        yield instance


# =============================================================================
# __getitem__ tests
# =============================================================================

def test_getitem_key_fields(indexable_instance: Indexable, g_object: Type[grid.GObject]):
    """idx[GObject] retrieves only key fields."""
    mock_esa = indexable_instance.esa
    unique_keys = sorted(list(set(g_object.keys())))

    if not unique_keys:
        result = indexable_instance[g_object]
        assert result is None
        mock_esa.GetParamsRectTyped.assert_not_called()
        return

    mock_df = pd.DataFrame({k: [1, 2] for k in unique_keys})
    mock_esa.GetParamsRectTyped.return_value = mock_df

    result_df = indexable_instance[g_object]
    mock_esa.GetParamsRectTyped.assert_called_once_with(g_object.TYPE(), unique_keys)
    assert_frame_equal(result_df, mock_df)


def test_getitem_all_fields(indexable_instance: Indexable, g_object: Type[grid.GObject]):
    """idx[GObject, :] retrieves all fields."""
    mock_esa = indexable_instance.esa
    expected_fields = sorted(list(set(g_object.keys()) | set(g_object.fields())))

    if not expected_fields:
        result = indexable_instance[g_object, :]
        assert result is None
        return

    mock_df = pd.DataFrame({f: [1] for f in expected_fields})
    mock_esa.GetParamsRectTyped.return_value = mock_df

    result_df = indexable_instance[g_object, :]
    mock_esa.GetParamsRectTyped.assert_called_once_with(g_object.TYPE(), expected_fields)
    assert_frame_equal(result_df, mock_df)


def test_getitem_specific_fields(indexable_instance: Indexable, g_object: Type[grid.GObject]):
    """idx[GObject, ['Field1']] retrieves specific fields plus all keys."""
    mock_esa = indexable_instance.esa
    specific_fields = [f for f in g_object.fields() if f not in g_object.keys()]
    if not specific_fields:
        pytest.skip(f"{g_object.__name__} has no non-key fields.")

    field = specific_fields[0]
    expected = sorted(list(set(g_object.keys()) | {field}))
    mock_df = pd.DataFrame({f: [1, 2] for f in expected})
    mock_esa.GetParamsRectTyped.return_value = mock_df

    result_df = indexable_instance[g_object, [field]]
    mock_esa.GetParamsRectTyped.assert_called_once_with(g_object.TYPE(), expected)
    assert_frame_equal(result_df, mock_df)


def test_getitem_empty_dataframe(indexable_instance: Indexable):
    """Empty DataFrame returned from PowerWorld."""
    indexable_instance.esa.GetParamsRectTyped.return_value = pd.DataFrame()
    result = indexable_instance[grid.Bus]
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_getitem_none_return(indexable_instance: Indexable):
    """None returned from PowerWorld."""
    indexable_instance.esa.GetParamsRectTyped.return_value = None
    assert indexable_instance[grid.Bus] is None


# =============================================================================
# __setitem__ tests
# =============================================================================

def test_setitem_broadcast(indexable_instance: Indexable, g_object: Type[grid.GObject]):
    """idx[GObject, 'Field'] = value broadcasts to all rows."""
    mock_esa = indexable_instance.esa
    editable_fields = [f for f in g_object.editable() if f not in g_object.keys()]
    if not editable_fields:
        pytest.skip(f"{g_object.__name__} has no editable non-key fields.")

    field = editable_fields[0]
    unique_keys = sorted(list(set(g_object.keys())))

    if not unique_keys:
        # Keyless objects build the change DataFrame directly.
        indexable_instance[g_object, field] = 1.234
        expected_df = pd.DataFrame({field: [1.234]})
        mock_esa.ChangeParametersMultipleElementRect.assert_called_once()
        sent_df = mock_esa.ChangeParametersMultipleElementRect.call_args[0][2]
        assert_frame_equal(sent_df, expected_df)
    else:
        # Keyed objects take the SetData fast path for numeric scalars:
        # no key read, no Rect write.
        indexable_instance[g_object, field] = 1.234
        mock_esa.RunScriptCommand.assert_called_once_with(
            f"SetData({g_object.TYPE()}, [{field}], [1.234], ALL);"
        )
        mock_esa.GetParamsRectTyped.assert_not_called()
        mock_esa.ChangeParametersMultipleElementRect.assert_not_called()


def test_setitem_bulk_update_from_df(indexable_instance: Indexable, g_object: Type[grid.GObject]):
    """idx[GObject] = df performs bulk update."""
    mock_esa = indexable_instance.esa
    settable_cols = list(g_object.settable())
    if not settable_cols:
        pytest.skip(f"{g_object.__name__} has no settable fields.")

    update_df = pd.DataFrame({f: [10, 20] for f in settable_cols})
    indexable_instance[g_object] = update_df

    mock_esa.ChangeParametersMultipleElementRect.assert_called_once_with(
        g_object.TYPE(), update_df.columns.tolist(), update_df
    )


def test_setitem_broadcast_multiple_fields(indexable_instance: Indexable, g_object_multi_editable: Type[grid.GObject]):
    """idx[GObject, ['F1','F2']] = [v1, v2] broadcasts multiple values."""
    mock_esa = indexable_instance.esa
    g_object = g_object_multi_editable
    editable_fields = [f for f in g_object.editable() if f not in g_object.keys()]
    # Filtering already ensures at least 2 editable non-key fields
    assert len(editable_fields) >= 2, f"{g_object.__name__} should have >= 2 editable fields"

    fields = editable_fields[:2]
    values = [1.1, 2.2]
    unique_keys = sorted(list(set(g_object.keys())))

    if not unique_keys:
        indexable_instance[g_object, fields] = values
        sent_df = mock_esa.ChangeParametersMultipleElementRect.call_args[0][2]
        assert len(sent_df) == 1
        assert sent_df.iloc[0][fields[0]] == values[0]
        return

    # One numeric value per field takes the SetData fast path.
    indexable_instance[g_object, fields] = values
    mock_esa.RunScriptCommand.assert_called_once_with(
        f"SetData({g_object.TYPE()}, [{fields[0]}, {fields[1]}], [1.1, 2.2], ALL);"
    )
    mock_esa.ChangeParametersMultipleElementRect.assert_not_called()


def test_setitem_broadcast_array_uses_rect_path(indexable_instance: Indexable):
    """Per-object array broadcasts read keys and use the Rect write path."""
    mock_esa = indexable_instance.esa
    keys = sorted(set(grid.Bus.keys()))
    field = [f for f in grid.Bus.editable() if f not in grid.Bus.keys()][0]
    mock_key_df = pd.DataFrame({k: [1, 2, 3] for k in keys})
    mock_esa.GetParamsRectTyped.return_value = mock_key_df

    indexable_instance[grid.Bus, field] = [1.0, 2.0, 3.0]

    mock_esa.RunScriptCommand.assert_not_called()
    mock_esa.ChangeParametersMultipleElementRect.assert_called_once()
    sent_df = mock_esa.ChangeParametersMultipleElementRect.call_args[0][2]
    assert list(sent_df[field]) == [1.0, 2.0, 3.0]


def test_setitem_broadcast_string_uses_rect_path(indexable_instance: Indexable):
    """Non-numeric scalar broadcasts read keys and use the Rect write path."""
    mock_esa = indexable_instance.esa
    keys = sorted(set(grid.Bus.keys()))
    field = [f for f in grid.Bus.editable() if f not in grid.Bus.keys()][0]
    mock_key_df = pd.DataFrame({k: [1, 2] for k in keys})
    mock_esa.GetParamsRectTyped.return_value = mock_key_df

    indexable_instance[grid.Bus, field] = "Connected"

    mock_esa.RunScriptCommand.assert_not_called()
    mock_esa.ChangeParametersMultipleElementRect.assert_called_once()


# =============================================================================
# Error handling
# =============================================================================

def test_setitem_invalid_index(indexable_instance: Indexable):
    """TypeError for unsupported index types."""
    with pytest.raises(TypeError, match="Unsupported index for __setitem__"):
        indexable_instance[123] = "value"
    with pytest.raises(TypeError, match="First element of index must be a GObject subclass"):
        indexable_instance[(123, "field")] = "value"


def test_setitem_non_settable_field(indexable_instance: Indexable):
    """ValueError when setting a read-only field."""
    non_settable = [f for f in grid.Bus.fields() if f not in grid.Bus.settable()]
    if not non_settable:
        pytest.skip("Bus has no non-settable fields.")
    with pytest.raises(ValueError, match="Cannot set read-only field"):
        indexable_instance[grid.Bus, non_settable[0]] = 1.0


def test_setitem_bulk_non_settable_column(indexable_instance: Indexable):
    """ValueError when bulk update includes a read-only column."""
    non_settable = [f for f in grid.Bus.fields() if f not in grid.Bus.settable()]
    if not non_settable:
        pytest.skip("Bus has no non-settable fields.")
    update_df = pd.DataFrame({"BusNum": [1, 2], non_settable[0]: [100, 200]})
    with pytest.raises(ValueError, match="Cannot set read-only field"):
        indexable_instance[grid.Bus] = update_df


# =============================================================================
# Secondary identifiers and keyless objects
# =============================================================================

def test_setitem_allows_secondary_identifier_fields(indexable_instance: Indexable):
    """Bulk update with SECONDARY identifier fields is allowed (e.g. LoadID)."""
    mock_esa = indexable_instance.esa
    assert "LoadID" in grid.Load.settable()
    update_df = pd.DataFrame({
        "BusNum": [1, 2], "LoadID": ["1", "2"], "LoadSMW": [10.0, 20.0]
    })
    indexable_instance[grid.Load] = update_df
    mock_esa.ChangeParametersMultipleElementRect.assert_called_once()


def test_gobject_identifiers_property():
    """identifiers includes both primary and secondary keys."""
    assert "BusNum" in grid.Load.identifiers()
    assert "LoadID" in grid.Load.identifiers()
    assert "BusNum" in grid.Gen.identifiers()
    assert "GenID" in grid.Gen.identifiers()


def test_keyless_object_single_field(indexable_instance: Indexable):
    """Setting a field on a keyless object creates a single-row DataFrame."""
    mock_esa = indexable_instance.esa
    assert not grid.Sim_Solution_Options.keys()
    editable = list(grid.Sim_Solution_Options.editable())
    assert len(editable) > 0

    indexable_instance[grid.Sim_Solution_Options, editable[0]] = "YES"

    sent_df = mock_esa.ChangeParametersMultipleElementRect.call_args[0][2]
    assert len(sent_df) == 1
    assert sent_df.iloc[0][editable[0]] == "YES"
    mock_esa.GetParamsRectTyped.assert_not_called()


def test_keyless_object_multiple_fields(indexable_instance: Indexable):
    """Setting multiple fields on a keyless object."""
    mock_esa = indexable_instance.esa
    editable = list(grid.Sim_Solution_Options.editable())
    assert len(editable) >= 2

    fields = editable[:2]
    indexable_instance[grid.Sim_Solution_Options, fields] = ["YES", "NO"]

    sent_df = mock_esa.ChangeParametersMultipleElementRect.call_args[0][2]
    assert len(sent_df) == 1
    assert sent_df.iloc[0][fields[0]] == "YES"
    assert sent_df.iloc[0][fields[1]] == "NO"


def test_keyless_object_value_length_mismatch(indexable_instance: Indexable):
    """Mismatched field/value counts on keyless object raises ValueError."""
    editable = list(grid.Sim_Solution_Options.editable())
    fields = editable[:2]
    with pytest.raises(ValueError, match="must be a list/tuple of the same length"):
        indexable_instance[grid.Sim_Solution_Options, fields] = ["YES", "NO", "EXTRA"]


def test_setitem_with_nan_values(indexable_instance: Indexable):
    """NaN values are passed through to PowerWorld unchanged."""
    mock_esa = indexable_instance.esa
    editable_fields = [f for f in grid.Bus.editable() if f not in grid.Bus.keys()]
    if not editable_fields:
        pytest.skip("Bus has no editable non-key fields.")
    key_field = grid.Bus.keys()[0]

    update_df = pd.DataFrame({
        key_field: [1, 2, 3],
        editable_fields[0]: [1.0, np.nan, 1.02]
    })
    indexable_instance[grid.Bus] = update_df

    sent_df = mock_esa.ChangeParametersMultipleElementRect.call_args[0][2]
    assert pd.isna(sent_df.iloc[1][editable_fields[0]])


# =============================================================================
# Additional coverage tests
# =============================================================================

def test_open_relative_path():
    """open() converts relative path to absolute."""
    from os import path as ospath
    with patch('esapp.indexable.SAW') as mock_saw_class, \
         patch('esapp.indexable.path.isabs', return_value=False), \
         patch('esapp.indexable.path.abspath', return_value='/abs/path/case.pwb'), \
         patch('esapp.indexable.path.exists', return_value=True):

        mock_esa = Mock()
        mock_saw_class.return_value = mock_esa

        instance = Indexable()
        instance.fname = 'relative/case.pwb'
        instance.open()

        assert instance.fname == '/abs/path/case.pwb'
        mock_saw_class.assert_called_once_with('/abs/path/case.pwb', CreateIfNotFound=True, early_bind=True)


def test_open_absolute_path():
    """open() preserves absolute path."""
    with patch('esapp.indexable.SAW') as mock_saw_class, \
         patch('esapp.indexable.path.isabs', return_value=True), \
         patch('esapp.indexable.path.exists', return_value=True):

        mock_esa = Mock()
        mock_saw_class.return_value = mock_esa

        instance = Indexable()
        instance.fname = '/absolute/path/case.pwb'
        instance.open()

        assert instance.fname == '/absolute/path/case.pwb'
        mock_saw_class.assert_called_once_with('/absolute/path/case.pwb', CreateIfNotFound=True, early_bind=True)



def test_getitem_with_gobject_enum_field(indexable_instance: Indexable):
    """idx[GObject, GObject.Field] retrieves field using enum member."""
    mock_esa = indexable_instance.esa

    # Get a GObject field enum member
    bus_fields = list(grid.Bus)
    field_member = None
    for member in bus_fields:
        if hasattr(member, 'value') and isinstance(member.value, tuple) and len(member.value) >= 2:
            field_member = member
            break

    if field_member is None:
        pytest.skip("Could not find a suitable GObject field member.")

    field_name = field_member.value[1]
    expected_fields = sorted(list(set(grid.Bus.keys()) | {field_name}))

    mock_df = pd.DataFrame({f: [1, 2] for f in expected_fields})
    mock_esa.GetParamsRectTyped.return_value = mock_df

    result_df = indexable_instance[grid.Bus, field_member]
    mock_esa.GetParamsRectTyped.assert_called_once_with(grid.Bus.TYPE(), expected_fields)
    assert_frame_equal(result_df, mock_df)


def test_getitem_invalid_slice(indexable_instance: Indexable):
    """ValueError when using unsupported slice for fields."""
    with pytest.raises(ValueError, match="Only the full slice"):
        indexable_instance[grid.Bus, [slice(1, 2)]]


def test_setitem_invalid_fields_type(indexable_instance: Indexable):
    """TypeError when fields is not a string or list."""
    with pytest.raises(TypeError, match="Fields must be a string or a list/tuple"):
        indexable_instance[grid.Bus, 123] = "value"


def test_setitem_bulk_update_not_dataframe(indexable_instance: Indexable):
    """TypeError when bulk update value is not a DataFrame."""
    with pytest.raises(TypeError, match="A DataFrame is required"):
        indexable_instance[grid.Bus] = "not a dataframe"


def test_setitem_broadcast_empty_dataframe(indexable_instance: Indexable, g_object_keyed_editable: Type[grid.GObject]):
    """Setting field on objects when no objects exist (empty DataFrame) is a no-op."""
    mock_esa = indexable_instance.esa
    g_object = g_object_keyed_editable
    editable_fields = [f for f in g_object.editable() if f not in g_object.keys()]

    # Filtering already ensures keys exist and at least 1 editable non-key field
    assert g_object.keys(), f"{g_object.__name__} should have keys"
    assert editable_fields, f"{g_object.__name__} should have editable non-key fields"

    mock_esa.GetParamsRectTyped.return_value = pd.DataFrame()

    indexable_instance[g_object, editable_fields[0]] = 1.0

    # Should not call ChangeParametersMultipleElementRect since no objects exist
    mock_esa.ChangeParametersMultipleElementRect.assert_not_called()


def test_setitem_broadcast_none_dataframe(indexable_instance: Indexable):
    """Setting field when GetParamsRectTyped returns None is a no-op."""
    mock_esa = indexable_instance.esa
    editable_fields = [f for f in grid.Bus.editable() if f not in grid.Bus.keys()]

    if not editable_fields:
        pytest.skip("Bus has no editable non-key fields.")

    mock_esa.GetParamsRectTyped.return_value = None

    indexable_instance[grid.Bus, editable_fields[0]] = 1.0

    mock_esa.ChangeParametersMultipleElementRect.assert_not_called()


def test_bulk_update_not_found_missing_identifiers(indexable_instance: Indexable):
    """ValueError when bulk update fails with missing primary keys."""
    from esapp.saw import PowerWorldPrerequisiteError
    mock_esa = indexable_instance.esa

    # Create a DataFrame missing the primary key (GenID)
    update_df = pd.DataFrame({
        "BusNum": [1, 2],
        "GenMW": [100.0, 200.0]
    })

    # Mock ChangeParametersMultipleElementRect to raise "not found" error
    mock_esa.ChangeParametersMultipleElementRect.side_effect = PowerWorldPrerequisiteError(
        "Object not found in case"
    )

    with pytest.raises(ValueError, match="Missing required primary key field"):
        indexable_instance[grid.Gen] = update_df


def test_bulk_update_not_found_all_keys_present_falls_back(indexable_instance: Indexable):
    """When primary keys are present and Rect fails with 'not found',
    falls back to ChangeParametersMultipleElement to create the objects."""
    from esapp.saw import PowerWorldPrerequisiteError
    mock_esa = indexable_instance.esa

    # Create a DataFrame with all primary keys present
    update_df = pd.DataFrame({
        "BusNum": [999, 1000],
        "GenID": ["1", "1"],
        "GenMW": [100.0, 200.0],
    })

    # Mock ChangeParametersMultipleElementRect to raise "not found" error
    mock_esa.ChangeParametersMultipleElementRect.side_effect = PowerWorldPrerequisiteError(
        "Object not found in case"
    )

    # The fallback ChangeParametersMultipleElement should be called instead of raising
    indexable_instance[grid.Gen] = update_df

    mock_esa.ChangeParametersMultipleElement.assert_called_once()
    call_args = mock_esa.ChangeParametersMultipleElement.call_args
    assert call_args[0][0] == "Gen"  # ObjectType
    assert "BusNum" in call_args[0][1]  # field list includes keys


def test_bulk_update_other_error(indexable_instance: Indexable):
    """Other PowerWorldPrerequisiteError is re-raised without modification."""
    from esapp.saw import PowerWorldPrerequisiteError
    mock_esa = indexable_instance.esa

    update_df = pd.DataFrame({
        "BusNum": [1, 2],
        "GenID": ["1", "1"]
    })

    # Mock with a different error message (not "not found")
    mock_esa.ChangeParametersMultipleElementRect.side_effect = PowerWorldPrerequisiteError(
        "Some other PowerWorld error"
    )

    with pytest.raises(PowerWorldPrerequisiteError, match="Some other PowerWorld error"):
        indexable_instance[grid.Gen] = update_df


def test_getitem_single_string_field(indexable_instance: Indexable):
    """idx[GObject, 'FieldName'] works with a single string field."""
    mock_esa = indexable_instance.esa

    non_key_fields = [f for f in grid.Bus.fields() if f not in grid.Bus.keys()]
    if not non_key_fields:
        pytest.skip("Bus has no non-key fields.")

    field = non_key_fields[0]
    expected_fields = sorted(list(set(grid.Bus.keys()) | {field}))

    mock_df = pd.DataFrame({f: [1, 2] for f in expected_fields})
    mock_esa.GetParamsRectTyped.return_value = mock_df

    result_df = indexable_instance[grid.Bus, field]
    mock_esa.GetParamsRectTyped.assert_called_once_with(grid.Bus.TYPE(), expected_fields)
    assert_frame_equal(result_df, mock_df)
