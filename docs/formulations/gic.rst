GIC Analysis Formulation
========================

This section describes the mathematical model built by :meth:`~esapp.utils.gic.GIC.model`,
which constructs a sparse linear system relating geoelectric fields to transformer GICs.

.. contents:: On this page
   :local:
   :depth: 2

Conductance Network
-------------------

Overview
^^^^^^^^

The GIC model represents the power system as a DC resistive network. Unlike AC power flow,
which uses bus admittance, the GIC network is defined by branch conductances and substation
grounding resistances. The network nodes are substations (neutral points) and buses, ordered
as :math:`[n_s \text{ substations}, \; n_b \text{ buses}]`. Branches include transformer
windings, transmission lines, and implicit generator step-up (GSU) connections.

Let :math:`n_x`, :math:`n_w`, and :math:`n_\ell` denote the number of transformers, windings,
and lines. Each two-winding transformer contributes two winding branches (high and low), so
:math:`n_w = 2 n_x`. Generators that model an implicit GSU contribute :math:`n_g` additional
branches.

Branch and Grounding Conductances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The branch conductance diagonal :math:`\tilde{G}` and the grounding conductance diagonal
:math:`\tilde{G}_s` collect all network conductances into two sparse matrices:

.. math::

   \tilde{G} := \text{diag}\!\left(
   \begin{bmatrix}
       \mathbf{g}_w^T & \mathbf{g}_\ell^T & \mathbf{g}_{gsu}^T
   \end{bmatrix}\right),
   \qquad
   \tilde{G}_s := \text{diag}\!\left(
   \begin{bmatrix}
       \mathbf{g}_s^T & \mathbf{0}^T
   \end{bmatrix}\right)

where :math:`\mathbf{g}_w`, :math:`\mathbf{g}_\ell`, :math:`\mathbf{g}_{gsu}`, and
:math:`\mathbf{g}_s` are the vectors of winding, line, GSU, and substation grounding
conductances. Winding and line conductances are per-phase values scaled by 3 for the
three-phase equivalent; GSU conductances are already three-phase totals. Zero-valued
conductances are replaced by :math:`10^{-6}` S to avoid singularity.

Incidence Matrix
^^^^^^^^^^^^^^^^

The incidence matrix :math:`A` encodes how each branch connects to the network nodes. Its rows
correspond to branches and its columns to nodes :math:`[s_1, \dots, s_{n_s}, b_1, \dots, b_{n_b}]`.
The matrix is formed by stacking four blocks:

.. math::

   A :=
   \begin{bmatrix}
       A_{\text{high}} \\
       A_{\text{low}} \\
       A_\ell \\
       A_{gsu}
   \end{bmatrix}

Each winding row encodes a signed connection between two nodes. The specific pattern depends on
the transformer configuration (see :ref:`winding-config`).

Line branches connect two buses: row :math:`j` of :math:`A_\ell` has :math:`+1` at the from-bus
and :math:`-1` at the to-bus. GSU branches connect a generator bus to its substation neutral.

G-Matrix
^^^^^^^^

The conductance Laplacian (G-matrix) combines the branch conductances and grounding into a
single nodal conductance matrix:

.. math::

   G := A^T \tilde{G}\, A + \tilde{G}_s

Entry :math:`G_{ij}` gives the mutual DC conductance between nodes :math:`i` and :math:`j`.
This matrix is analogous to the :math:`Y_{bus}` used in AC analysis. It is accessible via the
:attr:`~esapp.utils.gic.GIC.G` property.


Computing GICs
--------------

Given a vector of induced branch voltages :math:`\mathbf{v}_{emf}`, the GIC calculation
proceeds through Norton equivalent injection and nodal voltage solution.

The Norton branch currents and their nodal aggregation are:

.. math::

   \mathbf{i}_{nort}^{\ell} = \tilde{G}\, \mathbf{v}_{emf},
   \qquad
   \mathbf{i}_{nort}^{b} = A^T \mathbf{i}_{nort}^{\ell}

The DC node voltages are obtained by solving the linear system, and the resulting branch
currents follow from Ohm's law:

.. math::

   \mathbf{v}_{dc}^{b} = -G^{-1} \mathbf{i}_{nort}^{b},
   \qquad
   \mathbf{i}_{dc}^{\ell} = \tilde{G}\, A\, \mathbf{v}_{dc}^{b}

The per-conductor GICs are the superposition of continuity and Norton currents, divided by
three for the single-phase equivalent:

.. math::

   \mathbf{i}_{gic} = \left( \mathbf{i}_{dc}^{\ell} + \mathbf{i}_{nort}^{\ell} \right) / 3


Transformer Impact
------------------

Effective GICs
^^^^^^^^^^^^^^

A transformer's susceptibility to half-cycle saturation depends on the *effective* GIC flowing
through its core, not the individual winding currents. The effective GIC combines the high- and
low-winding currents, weighted by the turns ratio :math:`N_t`:

.. math::

   \mathbf{i}_{eff} = \left( P_H + N_t^{-1}\, P_L \right) \mathbf{i}_{gic}

where :math:`P_H` and :math:`P_L` are selection matrices that extract the high and low winding
rows from the branch current vector. The combined extraction operator
:math:`(P_H + N_t^{-1} P_L)` is accessible via the :attr:`~esapp.utils.gic.GIC.eff` property.

H-Matrix
^^^^^^^^

Substituting the full GIC derivation into the effective current expression yields a single
linear operator :math:`\mathcal{H}` that maps induced branch voltages directly to effective
transformer GICs:

.. math::

   \mathcal{H} := \left( P_H + N_t^{-1}\, P_L \right)
   \left( \tilde{G} - \tilde{G}\, A\, G^{-1} A^T \tilde{G} \right) / 3

This is the **H-matrix**, accessible via the :attr:`~esapp.utils.gic.GIC.H` property.

Per-Unit Loss Model (:math:`\zeta`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To model GIC-driven reactive power losses in power flow studies, the effective GICs must be
expressed in per-unit. Each transformer has a loss coefficient :math:`k_i`
(``GICModelKUsed``) and an MVA base :math:`S_i` (``GICXFMVABase``). The per-unit base
current for transformer :math:`i` is:

.. math::

   I_{base,i} = \frac{1000 \, S_i \sqrt{2/3}}{V_{high,i}}

where :math:`V_{high,i}` is the high-side rated voltage in kV. Folding the loss coefficient
and base conversion into a single diagonal scaling matrix:

.. math::

   K := \text{diag}\!\left(
       \frac{k \cdot V_{high}}{1000 \, S_{base} \sqrt{2/3}}
   \right)

the per-unit GIC model reduces to:

.. math::

   \zeta := K\, \mathcal{H}

This is the :math:`\zeta` operator accessible via the :attr:`~esapp.utils.gic.GIC.zeta` property.
It maps induced branch voltages to per-unit transformer losses in a single matrix multiply.
The bus-level reactive power injection is then:

.. math::

   \mathbf{q}_{loss} = \mathbf{v} \circ P_x \left| \zeta \, \mathbf{v}_{emf} \right|

where :math:`\mathbf{v}` is the vector of AC bus voltage magnitudes (p.u.), :math:`P_x` assigns
each transformer to its modeled bus, and :math:`\circ` is the element-wise (Hadamard) product.


.. _winding-config:

Implementation Notes
--------------------

Code Mapping
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Symbol
     - Code
     - Description
   * - :math:`A`
     - :attr:`~esapp.utils.gic.GIC.A`
     - Branch incidence matrix :math:`\in \mathbb{R}^{(n_w + n_\ell + n_g) \times (n_s + n_b)}`
   * - :math:`G`
     - :attr:`~esapp.utils.gic.GIC.G`
     - Conductance Laplacian (G-matrix)
   * - :math:`\tilde{G}`
     - ``Gd`` (local)
     - Diagonal branch conductance matrix
   * - :math:`\tilde{G}_s`
     - ``Gs`` (local)
     - Diagonal grounding conductance
   * - :math:`\mathcal{H}`
     - :attr:`~esapp.utils.gic.GIC.H`
     - Maps :math:`\mathbf{v}_{emf} \mapsto \mathbf{i}_{eff}`
   * - :math:`P_H + N_t^{-1} P_L`
     - :attr:`~esapp.utils.gic.GIC.eff`
     - Effective GIC extraction operator
   * - :math:`K`
     - ``K`` (local)
     - Per-unit scaling diagonal (absorbs :math:`k` and :math:`I_{base}^{-1}`)
   * - :math:`\zeta`
     - :attr:`~esapp.utils.gic.GIC.zeta`
     - Per-unit model :math:`K\mathcal{H}`
   * - :math:`P_x`
     - :attr:`~esapp.utils.gic.GIC.Px`
     - Transformer-to-bus permutation

Winding Configuration Rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The structure of each winding's incidence row depends on the transformer type and winding
configuration. Let :math:`S_H, S_L` denote substation permutation rows and :math:`B_H, B_L`
denote bus permutation rows for the high and low sides.

**Standard (non-auto) transformers:**

- *Gwye high side:* :math:`A_{\text{high}} = -S_H + B_H` — connects bus to substation neutral.
- *Delta/other high side:* :math:`A_{\text{high}} = B_H - B_L` — connects high bus to low bus.
- *Gwye low side:* :math:`A_{\text{low}} = -S_L + B_L` — connects bus to substation neutral.
- *Delta/other low side:* :math:`A_{\text{low}} = 0` — no grounded path.

**Autotransformers:**

- *High (series) winding:* :math:`A_{\text{high}} = B_H - B_L` — always bus-to-bus.
- *Low (common) winding:* :math:`A_{\text{low}} = S_L - B_L` — connects substation neutral
  to low bus (if Gwye).

These rules are applied using boolean masks (``HWYE``, ``LWYE``, ``AUTO``, ``BD``) combined
with the ``_mask`` helper function.

GIC Blocking Devices
^^^^^^^^^^^^^^^^^^^^^

A blocking device on a winding sets its conductance to :math:`10^{-6}` S, effectively
removing that GIC path from the network.

Generator GSU Transformers
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implicit GSU transformers appear as branches from the generator bus to the substation
neutral. Their ``GICConductance`` is the three-phase total in Siemens. Generators with
``GICGenIncludeImplicitGSU`` set to ``NO`` are excluded.


See Also
--------

- :class:`~esapp.utils.gic.GIC` -- GIC analysis and model interface
- :meth:`~esapp.utils.gic.GIC.model` -- Build the conductance network model
