"""Enum types and constants for SimAuto wrapper.

This module defines standardized types for string literals used throughout
the SAW module, replacing hardcoded strings with type-safe enumerations.
"""

from enum import Enum, IntFlag, auto
from typing import Union


class _StrEnum(str, Enum):
    """Base class for string-valued enums with correct ``str()`` behavior.

    Python 3.11+ changed ``str()`` on ``str, Enum`` to return
    ``'ClassName.MEMBER'`` instead of the value. This base class
    restores the expected behavior so enums can be passed directly
    to ``_run_script`` and pandas comparisons.
    """

    def __str__(self):
        return self.value


class YesNo(_StrEnum):
    """Boolean flag values for PowerWorld commands.

    PowerWorld uses "YES" and "NO" strings for boolean parameters in
    script commands rather than true/false.
    """
    YES = "YES"
    """Affirmative / enable option."""
    NO = "NO"
    """Negative / disable option."""

    @classmethod
    def from_bool(cls, value: bool) -> "YesNo":
        """Convert a Python boolean to YesNo enum.

        Parameters
        ----------
        value : bool
            The boolean value to convert.

        Returns
        -------
        YesNo
            YesNo.YES if value is True, YesNo.NO otherwise.
        """
        return cls.YES if value else cls.NO


class FilterKeyword(_StrEnum):
    """Special filter keywords for PowerWorld commands.

    These keywords are passed unquoted to PowerWorld, unlike custom
    filter names which must be quoted.
    """
    SELECTED = "SELECTED"
    """Only objects currently selected in PowerWorld."""
    AREAZONE = "AREAZONE"
    """Objects in the active area/zone filter."""
    ALL = "ALL"
    """Select all objects of the type."""


class SolverMethod(_StrEnum):
    """Power flow solution methods.

    These are the available solver algorithms for the SolvePowerFlow command.
    """
    RECTNEWT = "RECTNEWT"
    """Rectangular Newton-Raphson (default)."""
    POLARNEWT = "POLARNEWT"
    """Polar Newton-Raphson."""
    GAUSSSEIDEL = "GAUSSSEIDEL"
    """Gauss-Seidel iterative method."""
    FASTDEC = "FASTDEC"
    """Fast Decoupled method."""
    ROBUST = "ROBUST"
    """Robust solver for difficult cases."""
    DC = "DC"
    """DC power flow (linear approximation)."""


class LinearMethod(_StrEnum):
    """Linear calculation methods for sensitivity analysis.

    Used in PTDF, LODF, shift factor, and related calculations.
    """
    DC = "DC"
    """DC linear method (most common default)."""
    AC = "AC"
    """AC linear method."""
    DCPS = "DCPS"
    """DC linear with post-solution adjustment."""


class FileFormat(_StrEnum):
    """File format types for import/export operations."""
    CSV = "CSV"
    """Comma-separated values."""
    CSVCOLHEADER = "CSVCOLHEADER"
    """CSV with column headers."""
    CSVNOHEADER = "CSVNOHEADER"
    """CSV without headers."""
    AUX = "AUX"
    """PowerWorld auxiliary format."""
    AUXCSV = "AUXCSV"
    """Hybrid auxiliary/CSV format."""
    TAB = "TAB"
    """Tab-separated format."""
    PTI = "PTI"
    """PTI/PSS-E format."""
    TXT = "TXT"
    """Text format."""
    PWB = "PWB"
    """PowerWorld case format."""
    AXD = "AXD"
    """Oneline diagram format."""
    GE = "GE"
    """GE EPC format."""
    CF = "CF"
    """Custom format."""
    UCTE = "UCTE"
    """UCTE format."""
    AREVAHDB = "AREVAHDB"
    """AREVA HDB format."""
    OPENNETEMS = "OPENNETEMS"
    """OPENNET EMS format."""


class InterfaceLimitSetting(_StrEnum):
    """Interface limit configuration values."""
    AUTO = "AUTO"
    """Automatic limit calculation."""
    NONE = "NONE"
    """No limit applied."""


class ObjectType(_StrEnum):
    """PowerWorld object type identifiers.

    These are used for filtering and operations on specific element types.
    """
    BUS = "BUS"
    """Bus/node."""
    BRANCH = "BRANCH"
    """Branch (line or transformer)."""
    GEN = "GEN"
    """Generator."""
    LOAD = "LOAD"
    """Load."""
    SHUNT = "SHUNT"
    """Shunt device."""
    AREA = "AREA"
    """Control area."""
    ZONE = "ZONE"
    """Zone."""
    OWNER = "OWNER"
    """Owner."""
    INTERFACE = "INTERFACE"
    """Interface (flowgate)."""
    INJECTIONGROUP = "INJECTIONGROUP"
    """Injection group."""
    BUSSHUNT = "BUSSHUNT"
    """Bus shunt."""
    SUPERBUS = "SUPERBUS"
    """Super bus (aggregated)."""
    TRANSFORMER = "TRANSFORMER"
    """Transformer specifically."""
    LINE = "LINE"
    """Transmission line specifically."""
    SUPERAREA = "SUPERAREA"
    """Super area (aggregated)."""


class KeyFieldType(_StrEnum):
    """Key field types for result output."""
    PRIMARY = "PRIMARY"
    """Primary key fields (e.g., BusNum)."""
    SECONDARY = "SECONDARY"
    """Secondary key fields (e.g., BusName)."""
    LABEL = "LABEL"
    """Label-based identification."""


class StarBusHandling(_StrEnum):
    """Star bus handling options for case append operations."""
    NEAR = "NEAR"
    """Map to nearest bus (default)."""
    MAX = "MAX"
    """Map to maximum impedance bus."""


class MultiSectionLineHandling(_StrEnum):
    """Multi-section line handling options for case append operations."""
    MAINTAIN = "MAINTAIN"
    """Maintain multisection line structure (default)."""
    EQUIVALENCE = "EQUIVALENCE"
    """Convert to equivalent circuits."""


class IslandReference(_StrEnum):
    """Island reference options for sensitivity analysis."""
    EXISTING = "EXISTING"
    """Use existing island configuration."""
    NO = "NO"
    """No area reference."""


class OnelineLinkMode(_StrEnum):
    """Oneline diagram linking modes."""
    LABELS = "LABELS"
    """Link objects by labels (default)."""
    NUMBERS = "NUMBERS"
    """Link objects by numbers."""


class ShuntModel(_StrEnum):
    """Shunt model types for line tapping operations."""
    CAPACITANCE = "CAPACITANCE"
    """Capacitive shunt model."""
    INDUCTANCE = "INDUCTANCE"
    """Inductive shunt model."""


class BranchDeviceType(_StrEnum):
    """Branch device types for bus splitting operations."""
    LINE = "Line"
    """Transmission line."""
    TRANSFORMER = "Transformer"
    """Transformer."""
    BREAKER = "Breaker"
    """Circuit breaker."""


class TSGetResultsMode(_StrEnum):
    """Mode for saving transient stability results."""
    SINGLE = "SINGLE"
    """Single combined output file."""
    SEPARATE = "SEPARATE"
    """Separate files per object."""
    JSIS = "JSIS"
    """JSIS format output."""


class JacobianForm(_StrEnum):
    """Jacobian matrix coordinate forms."""
    RECTANGULAR = "R"
    """AC Jacobian in Rectangular coordinates."""
    POLAR = "P"
    """AC Jacobian in Polar coordinates."""
    DC = "DC"
    """B' matrix / DC approximation."""


class BranchDistanceMeasure(_StrEnum):
    """Branch distance measurement types for topology analysis."""
    REACTANCE = "X"
    """Use reactance (X) as distance measure."""
    IMPEDANCE = "Z"
    """Use impedance magnitude (Z) as distance measure."""


class BranchFilterMode(_StrEnum):
    """Branch filter modes for topology traversal."""
    ALL = "ALL"
    """All branches."""
    SELECTED = "SELECTED"
    """Only selected branches."""
    CLOSED = "CLOSED"
    """Only closed branches."""


class ScalingBasis(_StrEnum):
    """Scaling basis for load/generation scaling operations."""
    MW = "MW"
    """Absolute MW/MVAR values."""
    FACTOR = "FACTOR"
    """Multiplier factor."""


class ObjectIDHandling(_StrEnum):
    """Object ID handling modes for contingency export."""
    NO = "NO"
    """Standard object references."""
    YES_MS_3W = "YES_MS_3W"
    """Include multi-section and 3-winding IDs."""


class RatingSetPrecedence(_StrEnum):
    """Rating set precedence for weather-based ratings."""
    NORMAL = "NORMAL"
    """Use normal rating set."""
    CTG = "CTG"
    """Use contingency rating set."""


class RatingSet(_StrEnum):
    """Rating set identifiers for branch limits."""
    DEFAULT = "DEFAULT"
    """Use default rating."""
    NO = "NO"
    """Don't update rating."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"
    J = "J"
    K = "K"
    L = "L"
    M = "M"
    N = "N"
    O = "O"


class FieldListColumn(_StrEnum):
    """Column names for GetFieldList results.

    PowerWorld returns field metadata with these column headers. Different
    Simulator versions may return different subsets of these columns.
    """
    KEY_FIELD = "key_field"
    """Whether the field is a key field."""
    INTERNAL_FIELD_NAME = "internal_field_name"
    """PowerWorld internal field name."""
    FIELD_DATA_TYPE = "field_data_type"
    """Data type of the field."""
    DESCRIPTION = "description"
    """Human-readable description."""
    DISPLAY_NAME = "display_name"
    """Display name in PowerWorld UI."""
    ENTERABLE = "enterable"
    """Whether the field can be edited."""

    @classmethod
    def base_columns(cls) -> list:
        """Returns the standard 5-column format (most common)."""
        return [
            cls.KEY_FIELD.value,
            cls.INTERNAL_FIELD_NAME.value,
            cls.FIELD_DATA_TYPE.value,
            cls.DESCRIPTION.value,
            cls.DISPLAY_NAME.value,
        ]

    @classmethod
    def old_columns(cls) -> list:
        """Returns the legacy 4-column format (older Simulator versions)."""
        return [
            cls.KEY_FIELD.value,
            cls.INTERNAL_FIELD_NAME.value,
            cls.FIELD_DATA_TYPE.value,
            cls.DESCRIPTION.value,
        ]

    @classmethod
    def new_columns(cls) -> list:
        """Returns the extended 6-column format (newer Simulator versions)."""
        return [
            cls.KEY_FIELD.value,
            cls.INTERNAL_FIELD_NAME.value,
            cls.FIELD_DATA_TYPE.value,
            cls.DESCRIPTION.value,
            cls.DISPLAY_NAME.value,
            cls.ENTERABLE.value,
        ]


class SpecificFieldListColumn(_StrEnum):
    """Column names for GetSpecificFieldList results.

    PowerWorld returns specific field metadata with these column headers.
    """
    VARIABLENAME_LOCATION = "variablename:location"
    """Variable name with location."""
    FIELD = "field"
    """Field identifier."""
    COLUMN_HEADER = "column header"
    """Column header label."""
    FIELD_DESCRIPTION = "field description"
    """Human-readable description."""
    ENTERABLE = "enterable"
    """Whether the field can be edited."""

    @classmethod
    def base_columns(cls) -> list:
        """Returns the standard 4-column format."""
        return [
            cls.VARIABLENAME_LOCATION.value,
            cls.FIELD.value,
            cls.COLUMN_HEADER.value,
            cls.FIELD_DESCRIPTION.value,
        ]

    @classmethod
    def new_columns(cls) -> list:
        """Returns the extended 5-column format (newer Simulator versions)."""
        return [
            cls.VARIABLENAME_LOCATION.value,
            cls.FIELD.value,
            cls.COLUMN_HEADER.value,
            cls.FIELD_DESCRIPTION.value,
            cls.ENTERABLE.value,
        ]


# Type aliases for flexibility - allows either enum or raw string
FilterType = Union[FilterKeyword, str]


def format_filter(filter_name: FilterType) -> str:
    """Format a filter name for use in PowerWorld commands.

    Special filter keywords (SELECTED, AREAZONE, ALL) are passed unquoted,
    while custom filter names are quoted.

    Parameters
    ----------
    filter_name : FilterType
        The filter name to format. Can be a FilterKeyword enum or a string.

    Returns
    -------
    str
        The formatted filter string for use in script commands.
    """
    if not filter_name:
        return ""

    # Handle enum values
    if isinstance(filter_name, FilterKeyword):
        return filter_name.value

    # Handle string values - check if it's a special keyword
    if filter_name in (FilterKeyword.SELECTED.value, FilterKeyword.AREAZONE.value, FilterKeyword.ALL.value):
        return filter_name

    # Custom filter name - needs quotes
    return f'"{filter_name}"'


def format_filter_selected_only(filter_name: FilterType) -> str:
    """Format a filter name, treating only SELECTED as special.

    Only SELECTED is passed unquoted; other values including AREAZONE and ALL
    are quoted like custom filter names.

    Parameters
    ----------
    filter_name : FilterType
        The filter name to format.

    Returns
    -------
    str
        The formatted filter string.
    """
    if not filter_name:
        return ""

    if isinstance(filter_name, FilterKeyword) and filter_name == FilterKeyword.SELECTED:
        return filter_name.value

    if filter_name == FilterKeyword.SELECTED.value:
        return filter_name

    return f'"{filter_name}"'


def format_filter_areazone(filter_name: FilterType) -> str:
    """Format a filter name, treating SELECTED and AREAZONE as special.

    SELECTED and AREAZONE are passed unquoted; ALL and custom names are quoted.

    Parameters
    ----------
    filter_name : FilterType
        The filter name to format.

    Returns
    -------
    str
        The formatted filter string.
    """
    if not filter_name:
        return ""

    if isinstance(filter_name, FilterKeyword):
        if filter_name in (FilterKeyword.SELECTED, FilterKeyword.AREAZONE):
            return filter_name.value
        return f'"{filter_name.value}"'

    if filter_name in (FilterKeyword.SELECTED.value, FilterKeyword.AREAZONE.value):
        return filter_name

    return f'"{filter_name}"'


class PowerWorldMode(_StrEnum):
    """PowerWorld Simulator operating modes."""
    RUN = "RUN"
    """Run mode for executing simulations."""
    EDIT = "EDIT"
    """Edit mode for modifying case data."""


class FaultType(_StrEnum):
    """Fault types for fault analysis calculations."""
    SLG = "SLG"
    """Single Line to Ground fault."""
    LL = "LL"
    """Line to Line fault."""
    THREE_PHASE = "3PB"
    """Three Phase Balanced fault."""
    DLG = "DLG"
    """Double Line to Ground fault."""


class GICCalcMode(_StrEnum):
    """GIC calculation mode options."""
    SNAPSHOT = "SnapShot"
    """Single time point calculation."""
    TIME_VARYING = "TimeVarying"
    """Time series from uniform field."""
    NON_UNIFORM_TIME_VARYING = "NonUniformTimeVarying"
    """Time series with spatial variation."""
    SPATIALLY_UNIFORM_TIME_VARYING = "SpatiallyUniformTimeVarying"
    """Spatially uniform time series."""


# ---------------------------------------------------------------------------
# Bus Category Classification
# ---------------------------------------------------------------------------


class BusType(_StrEnum):
    """Power flow bus type from the BusCat field.

    The three fundamental bus types that determine which equations
    a bus contributes to the power flow Jacobian.

    Attributes
    ----------
    SLACK : str
        Reference bus — fixes voltage magnitude and angle.
    PV : str
        Generator bus — specifies P injection and V magnitude.
    PQ : str
        Load bus — specifies P and Q injection.
    """
    SLACK = "Slack"
    PV = "PV"
    PQ = "PQ"


class BusCtrl(IntFlag):
    """Voltage control modifier flags from BusCat qualifiers.

    Bitwise-combinable flags describing how a bus participates in
    voltage regulation. A remotely regulated bus with droop control
    would have ``BusCtrl.REMOTE | BusCtrl.DROOP``.

    Attributes
    ----------
    NONE : int
        No special control.
    REMOTE : int
        Remote voltage regulation (controls voltage at another bus).
    DROOP : int
        Voltage droop control with deadband.
    LDC : int
        Line drop compensation.
    TOL : int
        Voltage setpoint tolerance band (PVTol mode).
    """
    NONE   = 0
    REMOTE = auto()
    DROOP  = auto()
    LDC    = auto()
    TOL    = auto()


class Role(_StrEnum):
    """Bus role in a voltage regulation group.

    When multiple generators coordinate to regulate voltage at a
    remote bus, each participating bus takes on a distinct role.

    Attributes
    ----------
    NONE : str
        Not part of a regulation group (local control only).
    PRIMARY : str
        Enforces the voltage equation at the regulated bus.
    SECONDARY : str
        Shares reactive power proportionally with the primary.
    TARGET : str
        The bus whose voltage is being regulated remotely.
    """
    NONE      = "None"
    PRIMARY   = "Primary"
    SECONDARY = "Secondary"
    TARGET    = "Target"
