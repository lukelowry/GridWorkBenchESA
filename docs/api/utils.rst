Utilities & Analysis
====================

The ``esapp.utils`` package provides analysis modules, visualization tools, and general helpers.

Contingency Builder
-------------------

Fluent API for defining transient stability contingencies.

.. currentmodule:: esapp.utils.contingency

.. autoclass:: ContingencyBuilder
   :members:

.. autoclass:: SimAction
   :members:

GIC Analysis
------------

Geomagnetically Induced Current (GIC) analysis tools.

.. currentmodule:: esapp.utils.gic

.. autoclass:: GIC
   :members:
   :show-inheritance:

Network Topology
----------------

Network graph analysis including incidence matrices, Laplacians, and path calculations.

.. currentmodule:: esapp.utils.network

.. autoclass:: Network
   :members:
   :show-inheritance:

.. autoclass:: BranchType
   :members:

Bus Classification
------------------

Bus type classification engine for analyzing power flow Jacobian structure and voltage control.

.. currentmodule:: esapp.utils.buscat

.. autoclass:: BusCat
   :members:
   :show-inheritance:

.. autofunction:: parse_buscat

Dynamics
--------

Transient stability simulation utilities for field-watching and result processing.

.. currentmodule:: esapp.utils.dynamics

.. autoclass:: TSWatch
   :members:

.. autofunction:: get_ts_results

.. autofunction:: process_ts_results

B3D File Format
---------------

Binary 3D electric field data I/O.

.. currentmodule:: esapp.utils.b3d

.. automodule:: esapp.utils.b3d
   :members:

General Helpers
---------------

.. currentmodule:: esapp.utils.misc

.. automodule:: esapp.utils.misc
   :members:
