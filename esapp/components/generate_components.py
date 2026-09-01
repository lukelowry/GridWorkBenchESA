"""
Parses the PowerWorld 'Case Objects Fields' Text File and generates a Python
module (components.py) containing the structured data.
"""
import os
import re
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Flag, auto
from typing import Iterator, Optional, List, Dict, Set


class FieldRole(Flag):
    """Maps to PWRaw Key/Required column symbols."""
    STANDARD = 0
    PRIMARY_KEY = auto()        # *
    ALTERNATE_KEY = auto()      # *A*
    COMPOSITE_KEY_1 = auto()    # *1*
    COMPOSITE_KEY_2 = auto()    # *2*
    COMPOSITE_KEY_3 = auto()    # *3*
    SECONDARY_ID = auto()       # *2B*
    CIRCUIT_ID = auto()         # *4B*
    BASE_VALUE = auto()         # **
    STANDARD_FIELD = auto()     # <


@dataclass
class FieldDefinition:
    """Represents a single field/variable within a PowerWorld object type."""
    variable_name: str
    python_name: str
    concise_name: str
    data_type: str
    description: str
    role: FieldRole
    enterable: bool
    edit_mode_only: bool = False
    available_list: str = ""

    @property
    def is_primary(self) -> bool:
        return bool(self.role & (
            FieldRole.PRIMARY_KEY | FieldRole.COMPOSITE_KEY_1 |
            FieldRole.COMPOSITE_KEY_2 | FieldRole.COMPOSITE_KEY_3 |
            FieldRole.SECONDARY_ID | FieldRole.CIRCUIT_ID
        ))

    @property
    def is_secondary(self) -> bool:
        return bool(self.role & (
            FieldRole.ALTERNATE_KEY | FieldRole.BASE_VALUE
        ))

    @property
    def is_base_value(self) -> bool:
        return bool(self.role & FieldRole.BASE_VALUE)


@dataclass
class ObjectTypeDefinition:
    """Represents a PowerWorld object type (e.g., Gen, Bus, Load)."""
    name: str
    subdata_allowed: bool
    fields: list = field(default_factory=list)


@dataclass
class TSFieldDefinition:
    """Represents a Transient Stability result field."""
    pw_field_name: str      # Full PowerWorld field name (e.g., "TSBusVPU")
    concise_name: str       # Short display name (e.g., "TSVpu")
    description: str        # Human-readable description
    python_attr: str        # Python-safe attribute name (e.g., "VPU")
    object_type: str        # Which GObject it belongs to (e.g., "Bus")


class ComponentGenerator:
    """Handles parsing of PowerWorld export files and generation of Python modules."""

    EXCLUDE_OBJECTS = {
        'AlarmOptions', 'GenMWMaxMin_GenMWMaxMinXYCurve',
        'GenMWMax_SolarPVBasic1', 'GenMWMax_SolarPVBasic2',
        'GenMWMax_TemperatureBasic1', 'GenMWMax_WindBasic',
        'GenMWMax_WindClass1', 'GenMWMax_WindClass2', 'GenMWMax_WindClass3',
        'GenMWMax_WindClass4', 'GICGeographicRegionSet', 'GIC_Options',
        'LPOPFMarginalControls', 'MvarMarginalCostValues', 'MWMarginalCostValues',
        'NEMGroupBranch', 'NEMGroupGroup', 'NEMGroupNode', 'PieSizeColorOptions',
        'PWBranchDataObject', 'RT_Study_Options', 'SchedSubscription',
        'TSFreqSummaryObject', 'TSModalAnalysisObject', 'TSSchedule',
        'Exciter_Generic', 'Governor_Generic',
        'InjectionGroupModel_GenericInjectionGroup', 'LoadCharacteristic_Generic',
        'WeatherPathPoint', 'TSTimePointSolutionDetails'
    }

    EXCLUDE_FIELDS = {
        'BusMarginalControl', 'BusMCMVARValue', 'BusMCMWValue', 'LoadGrounded',
        'GEDateIn', 'GEDateOut'
    }

    # Manual field definitions for fields not properly defined in PWRaw
    # Format: {ObjectType: [FieldDefinition, ...]}
    MANUAL_FIELDS = {
        'PlantController_REPCA1': [
            FieldDefinition(
                variable_name='Dbd:3',
                python_name='Dbd__3',
                concise_name='dbdupper',
                data_type='Real',
                description='Deadband upper in control',
                role=FieldRole.STANDARD_FIELD,
                enterable=True
            ),
        ],
        'PlantController_REPCTA1': [
            FieldDefinition(
                variable_name='Dbd:3',
                python_name='Dbd__3',
                concise_name='dbdupper',
                data_type='Real',
                description='Deadband upper in control',
                role=FieldRole.STANDARD_FIELD,
                enterable=True
            ),
        ],
    }

    DTYPE_MAP = {"String": "str", "Real": "float", "Integer": "int"}

    TS_OBJECT_MAPPING = {
        'TSBus': 'Bus',
        'TSGen': 'Gen',
        'TSACLine': 'Branch',
        'TSLoad': 'Load',
        'TSShunt': 'Shunt',
        'TSArea': 'Area',
        'TSSub': 'Substation',
        'TSSystem': 'System',
        'TSInjectionGroup': 'InjectionGroup',
    }

    def __init__(self, raw_file_path: str):
        self.raw_file_path = raw_file_path
        self.objects: OrderedDict[str, ObjectTypeDefinition] = OrderedDict()
        self.ts_fields: Dict[str, List[TSFieldDefinition]] = {}

    def parse(self) -> None:
        """Parses the raw file and populates internal structures."""
        self._parse_components()
        self._extract_ts_fields()

    def _parse_components(self) -> None:
        """Parses object definitions for components.py."""
        current_obj: Optional[ObjectTypeDefinition] = None

        for line in self._iter_raw_rows():
            parts = line.split('\t')

            if self._is_object_header(parts):
                obj_name = parts[0].strip()

                if obj_name in self.EXCLUDE_OBJECTS:
                    current_obj = None
                    continue

                subdata = self._get_column(parts, 1).lower() == 'yes'
                current_obj = ObjectTypeDefinition(name=obj_name, subdata_allowed=subdata)
                self.objects[obj_name] = current_obj

            elif current_obj is not None and self._is_field_row(line):
                field_def = self._parse_field_definition(parts)
                if field_def is not None:
                    current_obj.fields.append(field_def)

    def _extract_ts_fields(self) -> None:
        """Extracts TS fields for ts_fields.py."""
        # Track seen python attributes per object type to avoid duplicates (e.g. from indexed fields)
        seen_attrs: Dict[str, Set[str]] = defaultdict(set)

        for line in self._iter_raw_rows():
            if not self._is_field_row(line):
                continue

            parts = line.split('\t')
            var_name = self._get_column(parts, 3)
            if not var_name:
                continue

            matched_prefix = None
            matched_type = None
            for prefix, obj_type in self.TS_OBJECT_MAPPING.items():
                if var_name.startswith(prefix):
                    matched_prefix = prefix
                    matched_type = obj_type
                    break

            if not matched_prefix or not matched_type:
                continue

            if 'TSSave' in var_name or 'TSResult' in var_name:
                continue

            # Handle Indexed Fields (e.g. TSBusInput:1 -> TSBusInput)
            # We strip the index to create a base field.
            # The generated TSField class will support indexing.
            base_var_name = re.sub(r':\d+$', '', var_name)

            # Determine Python Attribute Name
            # Remove prefix (e.g. TSBus)
            python_attr = self._sanitize_for_python(base_var_name[len(matched_prefix):])

            if not python_attr:
                continue

            if python_attr in seen_attrs[matched_type]:
                continue

            seen_attrs[matched_type].add(python_attr)

            concise_name = self._get_column(parts, 4)
            description = self._get_column(parts, 6, strip_q=True)

            field_def = TSFieldDefinition(
                pw_field_name=base_var_name,
                concise_name=concise_name,
                description=description,
                python_attr=python_attr,
                object_type=matched_type
            )

            if matched_type not in self.ts_fields:
                self.ts_fields[matched_type] = []
            self.ts_fields[matched_type].append(field_def)

    def generate_components(self, output_path: str) -> None:
        """Writes grid.py to the components module."""
        preamble = """#
# -*- coding: utf-8 -*-
# This file is auto-generated by esapp/components/generate_components.py.
# Do not edit this file manually, as your changes will be overwritten.

from .gobject import *
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(preamble)

            for obj_name, obj_def in self.objects.items():
                cls_name = self._sanitize_for_python(obj_name.split(" ")[0])
                f.write(f'\n\nclass {cls_name}(GObject):')

                fields = self._fields_with_manual_fields(obj_name, obj_def.fields)
                fields.sort(key=self._get_sort_key)

                for field_def in fields:
                    dtype = self.DTYPE_MAP.get(field_def.data_type, "str")
                    pw_name = self._fix_pw_string(field_def.python_name)
                    flags = self._build_field_priority_flags(field_def)
                    safe_desc = self._sanitize_description(field_def.description)

                    f.write(f'\n\t{field_def.python_name} = ("{pw_name}", {dtype}, {flags})')
                    f.write(f'\n\t"""{safe_desc}"""')

                f.write(f"\n\n\tObjectString = '{obj_name}'\n")

    def generate_ts_fields(self, output_path: str) -> None:
        """Writes ts_fields.py to the components module."""
        preamble = '''#
# -*- coding: utf-8 -*-
# This file is auto-generated by esapp/components/generate_components.py.
# Do not edit this file manually, as your changes will be overwritten.
#
# Transient Stability Field Constants for IDE Intellisense
#
# Usage:
#   from esapp.components import TS, Gen
#   pw.dyn.watch(Gen, [TS.Gen.P, TS.Gen.Speed])
#

from dataclasses import dataclass


@dataclass(frozen=True)
class TSField:
    """
    Represents a Transient Stability result field.

    Attributes:
        name: The PowerWorld field name string
        description: Human-readable description of the field

    """
    name: str
    description: str = ""

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"TSField({self.name!r})"

    def __getitem__(self, index: int) -> "TSField":
        """Allows accessing indexed fields like TS.Bus.Input[1]."""
        return TSField(f"{self.name}:{index}", self.description)


class TS:
    """
    Transient Stability Field Constants for Intellisense.

    Provides IDE autocomplete for all available TS result fields organized
    by object type (Bus, Gen, Branch, Load, Shunt, Area, etc.).

    Example:
        >>> from esapp.components import TS, Gen
        >>> pw.dyn.watch(Gen, [TS.Gen.P, TS.Gen.Speed, TS.Gen.Delta])
    """
'''
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(preamble)

            for obj_type in sorted(self.ts_fields.keys()):
                fields = self.ts_fields[obj_type]

                f.write(f'\n    class {obj_type}:\n')
                f.write(f'        """TS result fields for {obj_type} objects."""\n')

                for field_def in sorted(fields, key=lambda x: x.python_attr):
                    safe_desc = self._sanitize_description(field_def.description)
                    f.write(f'        {field_def.python_attr} = TSField("{field_def.pw_field_name}", "{safe_desc}")\n')

            f.write('\n')
        
        total_fields = sum(len(v) for v in self.ts_fields.values())
        print(f"Generated {output_path} with {total_fields} TS fields")

    # --- Helpers ---

    def _iter_raw_rows(self) -> Iterator[str]:
        """Yields logical PWRaw rows, joining wrapped quoted field rows."""
        with open(self.raw_file_path, 'r', encoding='utf-8') as f:
            next(f, None)  # Skip header
            yield from self._join_continuation_lines(f)

    @classmethod
    def _join_continuation_lines(cls, lines) -> Iterator[str]:
        current = None
        for raw_line in lines:
            line = raw_line.rstrip('\n')
            if not line.strip():
                continue

            if current is None:
                current = line
                continue

            if cls._starts_logical_row(line):
                yield current
                current = line
            else:
                current = f"{current}\n{line}"

        if current is not None:
            yield current

    @classmethod
    def _starts_logical_row(cls, line: str) -> bool:
        return cls._is_field_row(line) or cls._is_object_header(line.split('\t'))

    @staticmethod
    def _is_field_row(line: str) -> bool:
        return line.startswith('\t')

    @classmethod
    def _is_object_header(cls, parts: list) -> bool:
        obj_name = cls._get_column(parts, 0)
        if not obj_name or len(obj_name) <= 1:
            return False

        subdata_value = cls._get_column(parts, 1).lower()
        maintainer_value = cls._get_column(parts, 9).lower()
        return subdata_value in {'yes', 'no'} or maintainer_value in {'yes', 'no', 'inheritalways'}

    def _parse_field_definition(self, parts: list) -> Optional[FieldDefinition]:
        var_name = self._get_column(parts, 3)
        if not var_name or var_name in self.EXCLUDE_FIELDS or '/' in var_name:
            return None

        key_str = self._get_column(parts, 2)
        enterable_value = self._normalize_enterable(self._get_column(parts, 8))
        return FieldDefinition(
            variable_name=var_name,
            python_name=self._sanitize_for_python(var_name),
            concise_name=self._get_column(parts, 4),
            data_type=self._get_column(parts, 5),
            description=self._get_column(parts, 6, strip_q=True),
            role=self._parse_key_symbol(key_str),
            enterable=enterable_value in ('yes', 'edit mode only'),
            edit_mode_only=enterable_value == 'edit mode only',
            available_list=self._get_column(parts, 7, strip_q=True)
        )

    def _fields_with_manual_fields(self, obj_name: str, fields: List[FieldDefinition]) -> List[FieldDefinition]:
        merged = list(fields)
        seen_pw_names = {field.variable_name for field in merged}
        seen_python_names = {field.python_name for field in merged}

        for manual_field in self.MANUAL_FIELDS.get(obj_name, []):
            if manual_field.variable_name in seen_pw_names or manual_field.python_name in seen_python_names:
                continue
            merged.append(manual_field)
            seen_pw_names.add(manual_field.variable_name)
            seen_python_names.add(manual_field.python_name)

        return merged

    @staticmethod
    def _get_column(parts: list, index: int, strip_q: bool = False) -> str:
        value = parts[index].strip() if index < len(parts) else ""
        if strip_q and value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        return value

    @staticmethod
    def _sanitize_for_python(name: str) -> str:
        new_name = name.replace(":", "__")
        new_name = new_name.replace(" ", "___")
        if new_name and new_name[0].isdigit():
            new_name = 'Three' + new_name[1:] if new_name.startswith('3') else '_' + new_name
        return new_name

    @staticmethod
    def _fix_pw_string(name: str) -> str:
        new_name = "3" + name[5:] if name.startswith("Three") else name
        new_name = new_name.replace('__', ':')
        new_name = new_name.replace('___', ' ')
        if new_name.startswith('_') and name.startswith('_') and not name.startswith('__'):
             # Revert leading underscore added for digit
             new_name = new_name[1:]
        return new_name

    @staticmethod
    def _sanitize_description(desc: str) -> str:
        desc = desc.replace("\\", "/")
        desc = desc.replace("\r\n", "\\n").replace("\n", "\\n")
        desc = desc.replace('"""', r'\"\"\"')
        desc = desc.replace('"', r'\"')
        return desc

    @staticmethod
    def _parse_key_symbol(symbol: str) -> FieldRole:
        symbol = symbol.strip()
        role = FieldRole.STANDARD
        if '*1*' in symbol: role |= FieldRole.COMPOSITE_KEY_1
        elif '*2B*' in symbol: role |= FieldRole.SECONDARY_ID
        elif '*4B*' in symbol: role |= FieldRole.CIRCUIT_ID
        elif '*2*' in symbol: role |= FieldRole.COMPOSITE_KEY_2
        elif '*3*' in symbol: role |= FieldRole.COMPOSITE_KEY_3
        elif '*A*' in symbol: role |= FieldRole.ALTERNATE_KEY
        elif '**' in symbol: role |= FieldRole.BASE_VALUE
        elif '*' in symbol: role |= FieldRole.PRIMARY_KEY
        if '<' in symbol: role |= FieldRole.STANDARD_FIELD
        return role

    @staticmethod
    def _normalize_enterable(value: str) -> str:
        value = value.strip().lower()
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        return value

    @staticmethod
    def _get_sort_key(field_def: FieldDefinition) -> int:
        role = field_def.role
        if role & FieldRole.COMPOSITE_KEY_1 or role & FieldRole.PRIMARY_KEY: return 0
        if role & FieldRole.COMPOSITE_KEY_2: return 1
        if role & FieldRole.COMPOSITE_KEY_3: return 2
        if role & FieldRole.ALTERNATE_KEY: return 3
        if role & FieldRole.SECONDARY_ID or role & FieldRole.CIRCUIT_ID: return 4
        if role & FieldRole.BASE_VALUE: return 5
        return 10

    @staticmethod
    def _build_field_priority_flags(field_def: FieldDefinition) -> str:
        flags = []
        if field_def.is_primary: flags.append('FieldPriority.PRIMARY')
        elif field_def.is_secondary: flags.append('FieldPriority.SECONDARY')
        else: flags.append('FieldPriority.OPTIONAL')
        if field_def.is_base_value: flags.append('FieldPriority.REQUIRED')
        if field_def.enterable: flags.append('FieldPriority.EDITABLE')
        if field_def.edit_mode_only: flags.append('FieldPriority.EDIT_MODE')
        return ' | '.join(flags)


if __name__ == "__main__":
    RAW_IN = 'PWRaw'

    script_dir = os.path.dirname(os.path.abspath(__file__))

    RAW_FILE_PATH = os.path.join(script_dir, RAW_IN)
    OUTPUT_PY_PATH = os.path.join(script_dir, 'grid.py')
    TS_OUTPUT_PATH = os.path.join(script_dir, 'ts_fields.py')

    generator = ComponentGenerator(RAW_FILE_PATH)
    generator.parse()
    print(f"\nParsing complete.\n")

    generator.generate_components(OUTPUT_PY_PATH)
    print(f"Successfully generated -> grid.py\n")

    generator.generate_ts_fields(TS_OUTPUT_PATH)
    print(f"Successfully generated -> ts_fields.py\n")
