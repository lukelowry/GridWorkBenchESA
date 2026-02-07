SimAuto Wrapper (SAW)
=====================

The ``SAW`` (SimAuto Wrapper) class provides complete access to PowerWorld's SimAuto API.
It is organized into functional mixins for power flow, contingencies, optimization, sensitivity,
transient stability, GIC, ATC, topology, and data management. Access SAW through ``pw.esa``
from ``PowerWorld``.

.. currentmodule:: esapp.saw

.. autoclass:: SAW
   :show-inheritance:
   :no-members:

General Program Actions
-----------------------

.. autoclass:: esapp.saw.base.SAWBase
   :members:
   :noindex:

.. autoclass:: esapp.saw.general.GeneralMixin
   :members:
   :noindex:

Data Interaction
----------------

.. autoclass:: esapp.saw.data.DataMixin
   :members:
   :noindex:

Case Actions
------------

.. autoclass:: esapp.saw.case_actions.CaseActionsMixin
   :members:
   :noindex:

Modify Case Objects
-------------------

.. autoclass:: esapp.saw.modify.ModifyMixin
   :members:
   :noindex:

.. autoclass:: esapp.saw.topology.TopologyMixin
   :members:
   :noindex:

Power Flow
----------

.. autoclass:: esapp.saw.powerflow.PowerflowMixin
   :members:
   :noindex:

.. autoclass:: esapp.saw.matrices.MatrixMixin
   :members:
   :noindex:

Sensitivity Calculations
------------------------

.. autoclass:: esapp.saw.sensitivity.SensitivityMixin
   :members:
   :noindex:

Contingency Analysis
--------------------

.. autoclass:: esapp.saw.contingency.ContingencyMixin
   :members:
   :noindex:

Fault Analysis
--------------

.. autoclass:: esapp.saw.fault.FaultMixin
   :members:
   :noindex:

ATC (Available Transfer Capability)
------------------------------------

.. autoclass:: esapp.saw.atc.ATCMixin
   :members:
   :noindex:

GIC (Geomagnetically Induced Current)
--------------------------------------

.. autoclass:: esapp.saw.gic.GICMixin
   :members:
   :noindex:

OPF (Optimal Power Flow) and SCOPF
-----------------------------------

.. autoclass:: esapp.saw.opf.OPFMixin
   :members:
   :noindex:

PV Analysis
-----------

.. autoclass:: esapp.saw.pv.PVMixin
   :members:
   :noindex:

QV Analysis
-----------

.. autoclass:: esapp.saw.qv.QVMixin
   :members:
   :noindex:

Regions
-------

.. autoclass:: esapp.saw.regions.RegionsMixin
   :members:
   :noindex:

TS (Transient Stability)
------------------------

.. autoclass:: esapp.saw.transient.TransientMixin
   :members:
   :noindex:

Scheduled Actions
-----------------

.. autoclass:: esapp.saw.scheduled.ScheduledActionsMixin
   :members:
   :noindex:

Time Step Simulation
--------------------

.. autoclass:: esapp.saw.timestep.TimeStepMixin
   :members:
   :noindex:

Weather
-------

.. autoclass:: esapp.saw.weather.WeatherMixin
   :members:
   :noindex:

Type-Safe Enumerations
----------------------

ESA++ provides enumeration types for common PowerWorld string parameters. Using these
enums instead of raw strings provides IDE autocomplete, type checking, and prevents typos.

.. code-block:: python

    from esapp.saw import SolverMethod, FilterKeyword, BusType

    saw.SolvePowerFlow(SolverMethod.RECTNEWT)
    saw.GetParametersMultipleElement("Bus", ["BusNum"], FilterKeyword.ALL)

.. currentmodule:: esapp.saw

Power Flow & Matrices
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: SolverMethod
   :members:
   :undoc-members:

.. autoclass:: LinearMethod
   :members:
   :undoc-members:

.. autoclass:: JacobianForm
   :members:
   :undoc-members:

Bus Classification
~~~~~~~~~~~~~~~~~~

.. autoclass:: BusType
   :members:
   :undoc-members:

.. autoclass:: BusCtrl
   :members:
   :undoc-members:

.. autoclass:: Role
   :members:
   :undoc-members:

Data Filters & Object Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: FilterKeyword
   :members:
   :undoc-members:

.. autoclass:: ObjectType
   :members:
   :undoc-members:

.. autoclass:: KeyFieldType
   :members:
   :undoc-members:

Boolean & Option Flags
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: YesNo
   :members:

File Formats
~~~~~~~~~~~~

.. autoclass:: FileFormat
   :members:
   :undoc-members:

Transient Stability
~~~~~~~~~~~~~~~~~~~

.. autoclass:: TSGetResultsMode
   :members:
   :undoc-members:

Topology & Sensitivity
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: BranchDistanceMeasure
   :members:
   :undoc-members:

.. autoclass:: BranchFilterMode
   :members:
   :undoc-members:

.. autoclass:: ScalingBasis
   :members:
   :undoc-members:

.. autoclass:: IslandReference
   :members:
   :undoc-members:

.. autoclass:: InterfaceLimitSetting
   :members:
   :undoc-members:

Case Operations
~~~~~~~~~~~~~~~

.. autoclass:: StarBusHandling
   :members:
   :undoc-members:

.. autoclass:: MultiSectionLineHandling
   :members:
   :undoc-members:

.. autoclass:: OnelineLinkMode
   :members:
   :undoc-members:

.. autoclass:: ShuntModel
   :members:
   :undoc-members:

.. autoclass:: BranchDeviceType
   :members:
   :undoc-members:

.. autoclass:: ObjectIDHandling
   :members:
   :undoc-members:

Ratings
~~~~~~~

.. autoclass:: RatingSetPrecedence
   :members:
   :undoc-members:

.. autoclass:: RatingSet
   :members:
   :undoc-members:

Field Metadata
~~~~~~~~~~~~~~

.. autoclass:: FieldListColumn
   :members:

.. autoclass:: SpecificFieldListColumn
   :members:

Helper Functions
----------------

**Filter formatting:**

.. autofunction:: esapp.saw.format_filter

.. autofunction:: esapp.saw.format_filter_selected_only

.. autofunction:: esapp.saw.format_filter_areazone

**Data conversion:**

.. autofunction:: esapp.saw.df_to_aux

.. autofunction:: esapp.saw.create_object_string

.. autofunction:: esapp.saw.convert_to_windows_path

.. autofunction:: esapp.saw.convert_list_to_variant

.. autofunction:: esapp.saw.convert_df_to_variant

.. autofunction:: esapp.saw.convert_nested_list_to_variant

.. autofunction:: esapp.saw.get_temp_filepath

.. autofunction:: esapp.saw.format_list

.. autofunction:: esapp.saw.format_optional

.. autofunction:: esapp.saw.format_optional_numeric

Exceptions
----------

Exception classes for handling PowerWorld and COM errors.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Exception
     - Description
   * - ``Error``
     - Base class for all ESA++ exceptions
   * - ``PowerWorldError``
     - Generic error from PowerWorld following a SimAuto call. Parses error messages to extract source and details.
   * - ``SimAutoFeatureError``
     - Raised when a SimAuto feature is not supported for the given object or context (e.g., object types that don't support ``GetParameters``)
   * - ``PowerWorldPrerequisiteError``
     - Raised when a command fails due to missing prerequisite data (e.g., no contingencies defined for ``CTGSolve``)
   * - ``PowerWorldAddonError``
     - Raised when a command requires an unlicensed PowerWorld add-on (e.g., TransLineCalc)
   * - ``COMError``
     - Raised when COM communication fails (SimAuto crash, unresponsive, or invalid function call)
   * - ``CommandNotRespectedError``
     - Raised when PowerWorld silently ignores a command (e.g., setting a value outside allowed limits)
   * - ``GridObjDNE``
     - Raised when a grid object data query fails (object does not exist in the case)
   * - ``FieldDataException``
     - Raised when there is an issue with field data retrieval or parsing
   * - ``AuxParseException``
     - Raised when parsing an auxiliary file fails
   * - ``ContainerDeletedException``
     - Raised when attempting to access a container that has been deleted
   * - ``PowerFlowException``
     - Base class for power flow solution errors
   * - ``BifurcationException``
     - Raised when voltage bifurcation is suspected during power flow
   * - ``DivergenceException``
     - Raised when the power flow solution diverges
   * - ``GeneratorLimitException``
     - Raised when a generator has exceeded a limit during power flow
   * - ``GICException``
     - Raised when a GIC analysis error occurs

.. code-block:: text

    Exception
    └── Error (base for all ESA++ exceptions)
        ├── COMError
        ├── GridObjDNE
        ├── FieldDataException
        ├── AuxParseException
        ├── ContainerDeletedException
        ├── GICException
        ├── PowerFlowException
        │   ├── BifurcationException
        │   ├── DivergenceException
        │   └── GeneratorLimitException
        └── PowerWorldError
            ├── SimAutoFeatureError
            ├── PowerWorldPrerequisiteError
            ├── PowerWorldAddonError
            └── CommandNotRespectedError

.. code-block:: python

    from esapp.saw import SAW, PowerWorldError, PowerWorldPrerequisiteError

    try:
        saw.CTGSolveAll()
    except PowerWorldPrerequisiteError:
        print("No contingencies defined - add contingencies first")
    except PowerWorldError as e:
        print(f"PowerWorld error: {e.message}")
        print(f"Source: {e.source}")
