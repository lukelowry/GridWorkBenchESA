[0.2.1] - 2026-09-01
--------------------

**Added**
- Typed writes through the indexable interface: DataFrame columns and field arguments accept component members (`pw[Gen] = pd.DataFrame({Gen.BusNum: ...})`)
- Bool serialization on writes via a per-field vocabulary registry (`True` -> `"Closed"`/`"YES"`; see `BOOL_FIELD_VOCAB`)
- Alternate key sets for identifying and creating objects (`GObject.key_sets()`, e.g. Branch by `BusNum`/`BusNum:1`/`LineCircuit`)
- `FieldPriority.EDIT_MODE` field metadata; failed writes on EDIT-mode-only fields now hint to call `EnterMode('EDIT')`

**Changed**
- Unknown or read-only columns on writes now warn instead of raising, so a newer Simulator's fields are never blocked by the generated schema
- Consolidated all write paths through a single normalize/validate/serialize funnel
- Condensed indexable docstrings and error messages

[0.2.0] - 2026-08-31
--------------------

**Added**
- Added a PEP 561 `py.typed` marker for downstream type checking
- Added a faster single-command path for numeric scalar broadcasts
- Added environment-variable configuration for PowerWorld integration test cases

**Changed**
- Streamlined package discovery, optional dependencies, and Read the Docs installation
- Consolidated the maintained examples and moved GIC formulations into the main documentation
- Reduced SimAuto logging overhead by avoiding expensive debug formatting unless enabled
- Modernized supported Simulator field metadata and property behavior

**Removed**
- Removed deprecated or unused APIs: `ATCWriteAllOptions`, `CommandNotRespectedError`, `esapp.utils.timing`, and the `pw_order` constructor argument
- Removed legacy four-column field metadata handling and compatibility fallbacks for older Simulator properties
- Removed obsolete reference files, unrelated examples, bundled shapefiles, and machine-specific case paths

[0.1.5] - 2026-08-05
--------------------

**Changed**
- Corrected the supported Python range to 3.9 through 3.14
- Removed the NumPy 1.x restriction to support NumPy 2
- Made CI install ESApp and run the offline test suite across every supported Python version

[0.1.4] - 2026-06-05
--------------------

**Added**
- `BusCat` module (`esapp.utils.buscat`) for bus type classification and Jacobian structure analysis
- `BusType`, `BusCtrl`, `Role` enums for type-safe bus classification
- API documentation for BusCat, embedded modules, and new enums

**Changed**
- Moved plotting and geospatial dependencies out of core install requirements and into optional extras

**Fixed**
- Fixed PWRaw component generation so wrapped field rows no longer truncate generated objects
- Restored complete generated `Substation` metadata, including key, location, and GIC fields
- Added generated metadata for hidden `Dbd:3` fields on `PlantController_REPCA1` and `PlantController_REPCTA1`
- Fixed `BusCat` control flag formatting so `NONE` is not combined with active control flags

[0.1.3] - 2026-02-03
--------------------

**Changed**
- Replaced deprecated `@classmethod @property` pattern in `GObject` with standard `@classmethod` methods for Python 3.13 compatibility (e.g. `Bus.keys` is now `Bus.keys()`)
- Added Python 3.12 and 3.13 to CI test matrix

[0.1.2] - 2026-02-03
--------------------

**Changed**
- Completed SimAuto Wrapper mixin implementations for full API coverage
- Renamed GridWorkbench to PowerWorld
- Miscellaneous performance improvements

**Added**
- Transient stability field helpers (TS class with IDE intellisense)
- GICOption and SolverOption descriptor classes

**Removed**
- Legacy application-specific code

[0.1.1] - 2026-01-25
--------------------

**Changed**
- Improved component generation tool
- Added helper functions for data conversion
- Expanded test coverage

**Added**
- SubData helper functions
