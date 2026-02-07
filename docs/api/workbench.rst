PowerWorld
=============

The ``PowerWorld`` is the high-level entry point for interacting with PowerWorld via ESA++. It wraps
SimAuto with a Pythonic interface for case management, data access, and analysis helpers.

.. currentmodule:: esapp.workbench

.. autoclass:: PowerWorld
   :members:

Embedded Analysis Modules
--------------------------

``PowerWorld`` hosts three embedded analysis modules that share the parent's
SimAuto connection:

.. list-table::
   :widths: 20 80
   :header-rows: 0

   * - ``pw.network``
     - Network topology analysis (incidence, Laplacian, paths). See :class:`~esapp.utils.network.Network`.
   * - ``pw.gic``
     - GIC calculations and sensitivity. See :class:`~esapp.utils.gic.GIC`.
   * - ``pw.buscat``
     - Bus type classification for Jacobian structure. See :class:`~esapp.utils.buscat.BusCat`.

.. code-block:: python

    pw = PowerWorld("case.pwb")
    pw.pflow()

    bc = pw.buscat.refresh()
    pv_buses = bc.pv_idx()
    v_set = bc.v_setpoints()

Descriptors
-----------

Lightweight descriptor classes that map Python attributes to PowerWorld option fields.
Used by ``PowerWorld`` for solver options and by ``GIC`` for GIC analysis options.

.. currentmodule:: esapp._descriptors

.. autoclass:: SolverOption
   :members:

.. autoclass:: GICOption
   :members:
