# ESA++ Examples

Example application classes, reusable utilities, and Jupyter notebooks
demonstrating advanced usage of the `esapp` package.

The notebooks add the `examples/` directory to `sys.path`
(`import sys; sys.path.insert(0, "..")`) and import the helper modules
directly (e.g. `from plot_helpers import ...`). Run them with the
notebook's own directory as the working directory (the Jupyter default).

## Application Classes

| Module | Description |
|---|---|
| `statics.py` | Continuation power flow, state chain management, ZIP load interface, and generator limit checking |
| `dynamics.py` | Transient stability simulation with contingency definition, execution, and result retrieval |

## Utilities

| Module | Description |
|---|---|
| `plot_helpers.py` | Shared plotting functions for all notebooks |

## Notebooks

| Directory | Contents |
|---|---|
| `dynamics/` | Transient stability simulation examples |
| `steady_state/` | Contingency analysis, SCOPF, ATC, and CPF examples |
| `network/` | Network topology and matrix extraction examples |

## Case Configuration

The notebooks read a machine-local PowerWorld case path from
`examples/data/case.txt` (and `case_B.txt` where a second case is compared).
These files are gitignored — copy `examples/data/case.txt.example` and point
it at a case on your machine.
