"""Offline regression tests for the PWRaw component generator."""
import re
from pathlib import Path

import pytest

from esapp.components.generate_components import ComponentGenerator, FieldRole


RAW_FILE = Path(__file__).resolve().parents[1] / "esapp" / "components" / "PWRaw"


@pytest.fixture(scope="module")
def parsed_generator():
    generator = ComponentGenerator(str(RAW_FILE))
    generator.parse()
    return generator


def _class_block(text: str, class_name: str) -> str:
    match = re.search(
        rf"\n\nclass {re.escape(class_name)}\(GObject\):.*?(?=\n\nclass |\Z)",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, f"{class_name} was not generated"
    return match.group(0)


def test_substation_parsing_continues_after_wrapped_pwraw_row(parsed_generator):
    fields = {field.variable_name: field for field in parsed_generator.objects["Substation"].fields}

    assert "GICGeoMagGraphicScalar" in fields
    for field_name in [
        "GICGLatScalar",
        "GICQLosses",
        "GICSubGroundOhms",
        "GICUsedSubGroundOhms",
        "Latitude",
        "Longitude",
        "SubName",
        "SubNum",
    ]:
        assert field_name in fields

    assert fields["SubNum"].role & FieldRole.COMPOSITE_KEY_1
    assert fields["SubName"].role & FieldRole.ALTERNATE_KEY


def test_manual_fields_do_not_duplicate_existing_pw_names():
    generator = ComponentGenerator("unused")
    manual_field = ComponentGenerator.MANUAL_FIELDS["PlantController_REPCA1"][0]

    fields = generator._fields_with_manual_fields("PlantController_REPCA1", [manual_field])

    assert [field.variable_name for field in fields].count("Dbd:3") == 1


def test_hidden_deadband_fields_are_generated(parsed_generator, tmp_path):
    output_path = tmp_path / "grid.py"

    parsed_generator.generate_components(str(output_path))
    generated = output_path.read_text(encoding="utf-8")

    for class_name in ["PlantController_REPCA1", "PlantController_REPCTA1"]:
        block = _class_block(generated, class_name)
        assert 'Dbd__3 = ("Dbd:3", float, FieldPriority.OPTIONAL | FieldPriority.EDITABLE)' in block
