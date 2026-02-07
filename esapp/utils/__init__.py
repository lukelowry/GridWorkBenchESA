"""
ESAplus utilities module.

Provides tools for:
- Binary data formats (B3D electric field data)
- Analysis modules (GIC, network topology, bus classification, dynamics, contingency)
- Function decorators for debugging and profiling
"""

from .misc import timing

from .b3d import B3D

from .gic import GIC
from .contingency import ContingencyBuilder, SimAction
from .network import Network, BranchType
from .dynamics import TSWatch, process_ts_results, get_ts_results
from .buscat import BusCat, parse_buscat

__all__ = [
    # misc
    'timing',
    # b3d
    'B3D',
    # gic
    'GIC',
    # contingency
    'ContingencyBuilder',
    'SimAction',
    # network
    'Network',
    'BranchType',
    # dynamics
    'TSWatch',
    'process_ts_results',
    'get_ts_results',
    # buscat
    'BusCat',
    'parse_buscat',
]
