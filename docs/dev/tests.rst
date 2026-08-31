Testing Suite
=============

The test suite includes unit tests (no PowerWorld required) and integration tests
(requires PowerWorld Simulator with a valid case file).

Test Coverage
-------------

**Unit Tests** — Run without PowerWorld

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - File
     - Coverage
   * - ``test_gobject.py``
     - GObject base class, FieldPriority flags, repr/str methods
   * - ``test_grid_components.py``
     - Field collection, key/editable/settable classification
   * - ``test_indexing.py``
     - Indexable data access syntax, broadcast, bulk update
   * - ``test_helpers_unit.py``
     - SAW helpers: df_to_aux, path conversion, formatting, GICOption descriptor mechanics
   * - ``test_dynamics.py``
     - Dynamics module: ContingencyBuilder, SimAction enum
   * - ``test_utils.py``
     - Utility modules: B3D file format
   * - ``test_buscat_unit.py``
     - BusCat string parsing: all known PowerWorld BusCat variants (Slack, PV, PQ with controls/roles/limits)

**Integration Tests** — Require PowerWorld

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - File
     - Coverage
   * - ``test_integration_saw_core.py``
     - Core SAW operations, file I/O, data retrieval
   * - ``test_integration_workbench.py``
     - PowerWorld data access, indexing, solver option descriptors, convenience features (flows, overloads, snapshot, PTDF, LODF, properties, summary)
   * - ``test_integration_saw_powerflow.py``
     - Power flow, matrices (Ybus, Jacobian), PTDF/LODF
   * - ``test_integration_saw_contingency.py``
     - Contingency auto-insertion, solving, OTDF
   * - ``test_integration_buscat.py``
     - BusCat module: refresh, index methods, voltage setpoints, classification DataFrame
   * - ``test_integration_network.py``
     - Network topology, incidence matrices, graph analysis
   * - ``test_integration_saw_gic.py``
     - GIC analysis, calculations, GIC option descriptors, G-matrix comparison
   * - ``test_integration_saw_modify.py``
     - Case modification and data manipulation
   * - ``test_integration_saw_operations.py``
     - Scheduled actions, weather, OPF, extended methods
   * - ``test_integration_saw_transient.py``
     - Transient stability simulation

Configuration
-------------

Preferred — environment variables (keeps machine-specific paths out of the repo):

1. Set ``SAW_TEST_CASE`` to your PowerWorld case path
2. Optionally set ``SAW_GIC_TEST_CASES`` to a ``;``-separated list of case
   paths for the parametrized GIC tests

Alternative — copy ``tests/config_test.example.py`` to ``tests/config_test.py``
and set the same names there (the file is gitignored).

Running Tests
-------------

.. code-block:: bash

    pytest tests/                           # Full suite
    pytest tests/ -m unit                   # Unit only
    pytest tests/ -m integration            # Integration only
    pytest tests/ --cov=esapp --cov-report=html  # With coverage

Troubleshooting
---------------

- **PowerWorld not found**: Ensure ``SAW_TEST_CASE`` is set (or ``tests/config_test.py`` exists) with a valid case path
- **Integration tests slow**: Use ``pytest -m "not integration"`` for unit-only runs
- **Import errors**: Install in editable mode with ``pip install -e .``
