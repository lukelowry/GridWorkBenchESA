"""
Unit tests for GObject classmethods and auto-generated component classes.

These are **unit tests** that do NOT require PowerWorld Simulator. They test
field collection, key/editable/settable classification, and validate that all
auto-generated component classes from grid.py are well-formed.

USAGE:
    pytest tests/test_grid_components.py -v
"""
import pytest
from typing import Type

from esapp import components as grid
from tests.conftest import get_all_gobject_subclasses


@pytest.fixture(scope="module")
def test_gobject_class() -> Type[grid.GObject]:
    """A simple GObject subclass for testing classmethod behavior."""
    class TestGObject(grid.GObject):
        ID = ("id", int, grid.FieldPriority.PRIMARY)
        NAME = ("name", str, grid.FieldPriority.SECONDARY | grid.FieldPriority.REQUIRED)
        VALUE = ("value", float, grid.FieldPriority.OPTIONAL | grid.FieldPriority.EDITABLE)
        DUPLICATE_KEY = ("duplicate_key", str, grid.FieldPriority.PRIMARY | grid.FieldPriority.SECONDARY)
        ObjectString = "TestGObject"
    return TestGObject


def test_gobject_fields_are_collected(test_gobject_class):
    """All field names are collected in the .fields() method."""
    assert test_gobject_class.fields() == ['id', 'name', 'value', 'duplicate_key']


def test_gobject_keys_are_collected(test_gobject_class):
    """PRIMARY fields are collected in .keys()."""
    assert test_gobject_class.keys() == ['id', 'duplicate_key']


def test_gobject_editable_fields(test_gobject_class):
    """EDITABLE fields are collected in .editable()."""
    assert test_gobject_class.editable() == ['value']


def test_gobject_secondary_fields(test_gobject_class):
    """SECONDARY fields are collected in .secondary()."""
    assert test_gobject_class.secondary() == ['name', 'duplicate_key']


def test_gobject_identifiers(test_gobject_class):
    """identifiers() returns union of primary + secondary keys."""
    assert test_gobject_class.identifiers() == {'id', 'name', 'duplicate_key'}


def test_gobject_settable_fields(test_gobject_class):
    """settable() returns identifiers + editable fields."""
    assert test_gobject_class.settable() == {'id', 'name', 'duplicate_key', 'value'}


def test_gobject_is_editable(test_gobject_class):
    assert test_gobject_class.is_editable('value') is True
    assert test_gobject_class.is_editable('id') is False
    assert test_gobject_class.is_editable('nonexistent') is False


def test_gobject_is_settable(test_gobject_class):
    assert test_gobject_class.is_settable('value') is True
    assert test_gobject_class.is_settable('id') is True
    assert test_gobject_class.is_settable('name') is True
    assert test_gobject_class.is_settable('nonexistent') is False


def test_generated_substation_metadata_contains_expected_fields():
    """Substation should include fields after the wrapped PWRaw row."""
    for field_name in [
        "SubNum",
        "SubName",
        "Latitude",
        "Longitude",
        "GICSubGroundOhms",
        "GICUsedSubGroundOhms",
    ]:
        assert field_name in grid.Substation.fields()

    assert "SubNum" in grid.Substation.keys()
    assert "SubName" in grid.Substation.secondary()


@pytest.mark.parametrize("g_object_class", get_all_gobject_subclasses())
def test_real_gobject_subclass_is_well_formed(g_object_class: Type[grid.GObject]):
    """Validates every auto-generated GObject subclass has correct structure."""
    assert g_object_class.TYPE() != 'NO_OBJECT_NAME', f"{g_object_class.__name__} missing ObjectString"
    assert isinstance(g_object_class.TYPE(), str)
    assert isinstance(g_object_class.fields(), list)
    assert isinstance(g_object_class.keys(), list)
    assert isinstance(g_object_class.editable(), list)

    assert set(g_object_class.keys()).issubset(set(g_object_class.fields()))
    assert set(g_object_class.editable()).issubset(set(g_object_class.fields()))
    assert set(g_object_class.secondary()).issubset(set(g_object_class.fields()))

    expected_identifiers = set(g_object_class.keys()) | set(g_object_class.secondary())
    assert g_object_class.identifiers() == expected_identifiers

    expected_settable = expected_identifiers | set(g_object_class.editable())
    assert g_object_class.settable() == expected_settable
