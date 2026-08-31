# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESA++ (`esapp`) is a Python toolkit for power system automation, providing a high-performance interface to PowerWorld Simulator's Automation Server (SimAuto) via COM on Windows. It requires Windows with PowerWorld Simulator installed.

## Environment Setup

This project uses a **conda environment** named `esapp` (Python 3.11). On this machine it lives at `C:\Users\wyattluke.lowery\AppData\Local\miniconda3\envs\esapp`. All commands (pytest, pip, flake8, etc.) should be run using this environment.

```bash
# Activate the environment
conda activate esapp
```

## Common Commands

```bash
# Install for development
pip install -e ".[test]"

# Run all tests
pytest

# Run only unit tests (no PowerWorld needed)
pytest -m unit

# Run only integration tests (requires PowerWorld + case file)
pytest -m integration

# Run a single test file
pytest tests/test_helpers_unit.py

# Run a single test
pytest tests/test_helpers_unit.py::TestClassName::test_name

# Run with coverage
pytest --cov=esapp --cov-report=term-missing --cov-report=html:htmlcov

# Lint (CI uses flake8 for syntax errors and undefined names)
flake8 . --select=E9,F63,F7,F82 --show-source

# Regenerate auto-generated component definitions from PWRaw schema
cd esapp/components && python generate_components.py

# Build docs
cd docs && sphinx-build -b html . _build
```

## Test Configuration

Integration tests require a PowerWorld case file path, configured via:
1. Environment variables `SAW_TEST_CASE` and optionally `SAW_GIC_TEST_CASES` (`;`-separated list), or
2. `tests/config_test.py` (user-created, not committed)

On this machine the env vars point at `C:\Users\wyattluke.lowery\Documents\GitHub\cases` (Hawaii40.SimpleDynamics as the main case). Integration tests never modify the case file.

Tests without PowerWorld access should use `-m unit`. The `--maxfail=5` default stops early on failures.

## Architecture

### Entry Point: `PowerWorld` ([workbench.py](esapp/workbench.py))
The main user-facing class. Creates a SAW connection, provides high-level grid analysis methods, and hosts embedded application modules (`network`, `gic`).

### SAW (SimAuto Wrapper): [esapp/saw/](esapp/saw/)
`SAW` class in [saw.py](esapp/saw/saw.py) is composed via **mixin pattern** from ~18 focused modules:
- **SAWBase** ([base.py](esapp/saw/base.py)) - Core COM interface, case management, generic data retrieval
- **PowerflowMixin** - Power flow solvers (Newton-Raphson, Gauss-Seidel, DC, etc.)
- **ContingencyMixin** - Contingency analysis
- **MatrixMixin** - Y-bus, Jacobian, GIC conductance matrix extraction
- **TransientMixin** - Transient stability simulation
- **SensitivityMixin** - PTDF, LODF, shift factors
- Other mixins: `GeneralMixin`, `ModifyMixin`, `TopologyMixin`, `GICMixin`, `OPFMixin`, `PVMixin`, `QVMixin`, `ATCMixin`, `FaultMixin`, `RegionsMixin`, `CaseActionsMixin`, `ScheduledActionsMixin`, `TimeStepMixin`, `WeatherMixin`

### Indexable Interface ([indexable.py](esapp/indexable.py))
Pythonic `__getitem__` access for grid data: `pw[Bus, ["BusNum", "BusName"]]` returns a DataFrame. Both `PowerWorld` and `SAW` implement this.

### Component Definitions: [esapp/components/](esapp/components/)
- **grid.py** (auto-generated, ~13MB) - `GObject` subclasses for all PowerWorld object types (Bus, Gen, Load, Branch, etc.)
- **ts_fields.py** (auto-generated) - Transient stability field constants for IDE autocomplete
- **gobject.py** - Base `GObject` class
- **generate_components.py** - Regeneration script reading from `PWRaw` schema file
- Do not manually edit `grid.py` or `ts_fields.py`; regenerate them instead.

### Utility Modules: [esapp/utils/](esapp/utils/)
Embedded analysis applications accessible from `PowerWorld`:
- **GIC** ([gic.py](esapp/utils/gic.py)) - Geomagnetically Induced Currents analysis, G-matrix, E-field Jacobians
- **Network** ([network.py](esapp/utils/network.py)) - Incidence matrices, Laplacians, bus mapping
- **Dynamics** ([dynamics.py](esapp/utils/dynamics.py)) - Transient stability result monitoring
- **Contingency** ([contingency.py](esapp/utils/contingency.py)) - Programmatic contingency definition
- **B3D** ([b3d.py](esapp/utils/b3d.py)) - Binary 3D electric field file I/O

### Helpers and Types
- **_helpers.py** - Data conversion (Windows paths, COM variants, AUX files), TS result processing
- **_enums.py** - Type-safe enumerations (`SolverMethod`, `LinearMethod`, `FileFormat`, `ObjectType`, filter keywords like `SELECTED`, `ALL`)
- **_exceptions.py** - Exception hierarchy rooted at `PowerWorldError` with analysis-specific subtypes (`PowerFlowException`, `DivergenceException`, `GICException`, etc.)

## Key Constraints

- **Windows-only**: Depends on `pywin32` for COM interop with PowerWorld
- **Python >= 3.9**: Minimum supported version (numpy 2.x is supported)
- CI runs on Python 3.9 through 3.14
