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
