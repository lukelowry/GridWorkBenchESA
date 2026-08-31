"""
esapp: A Pythonic Interface for PowerWorld Simulator
=====================================================

The ``esapp`` package provides a high-level, object-oriented interface for
interacting with PowerWorld Simulator's Automation Server (SimAuto). It aims
to simplify common power systems analysis tasks by providing a more Pythonic
and user-friendly API.

The main entry point is the :class:`~.PowerWorld` class.
"""

# Please keep the docstring above up to date with all the imports.
from .saw import (
    SAW,
    PowerWorldError,
    COMError,
    Error,
    SimAutoFeatureError,
    PowerWorldPrerequisiteError,
    PowerWorldAddonError,
)

# Main PowerWorld Interface Class
from .workbench import PowerWorld

# Transient Stability Field Constants for Intellisense
from .components import TS, TSField
