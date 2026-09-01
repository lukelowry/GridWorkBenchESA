from .saw import SAW, PowerWorldError, PowerWorldPrerequisiteError
from .components import GObject
from .components.gobject import bool_vocab
from typing import Type, Optional
from numbers import Real
from math import isfinite
from pandas import DataFrame
from pandas.api.types import is_bool_dtype
from os import path
from warnings import warn
import numpy as np


# Power World Read/Write
class Indexable:
    """
    PowerWorld Read/Write tool providing indexer-based access to grid components.

    This class enables DataFrame-like access to PowerWorld Simulator data,
    allowing users to retrieve and modify component parameters using familiar
    indexing syntax.

    Fields may be strings or ``GObject`` members. Writes serialize Python
    bools to PowerWorld strings (``True`` -> ``"Closed"`` for GenStatus);
    reads return PowerWorld's strings as-is.
    """
    esa: SAW
    fname: str

    def open(self):
        """
        Open the PowerWorld case and initialize transient stability.

        This method validates the case path, initializes the SimAuto COM object,
        and attempts to initialize transient stability to ensure initial values
        are available for dynamic models.

        Raises
        ------
        FileNotFoundError
            If the case file does not exist on disk.
        """
        # Validate Path Name
        if not path.isabs(self.fname):
            self.fname = path.abspath(self.fname)

        if not path.exists(self.fname):
            raise FileNotFoundError(
                f"Case file not found: '{self.fname}'\n"
                f"Please verify the file path is correct and the file exists."
            )

        # ESA Object & Transient Sim
        self.esa = SAW(self.fname, CreateIfNotFound=True, early_bind=True)
    
    def __getitem__(self, index) -> Optional[DataFrame]:
        """Retrieve data from PowerWorld using indexer notation.

        ``idx[GObject]`` returns key fields; ``idx[GObject, fields]`` adds
        the requested fields (a name, GObject member, list, or ``:`` for
        all). Returns a DataFrame, or ``None`` if nothing was retrieved.
        """
        # 1. Parse index to get gtype and what fields are requested.
        if isinstance(index, tuple):
            gtype, requested_fields = index
        else:
            gtype, requested_fields = index, None

        # 2. Determine the complete set of fields to retrieve.
        # Always start with the object's key fields.
        fields_to_get = set(gtype.keys())

        # 3. Add any additional fields based on the request.
        if requested_fields is None:
            # Case: pw[Bus] -> only key fields are needed.
            pass
        elif requested_fields == slice(None):
            # Case: pw[Bus, :] -> add all defined fields.
            fields_to_get.update(gtype.fields())
        else:
            # Case: pw[Bus, 'field'] or pw[Bus, ['f1', 'f2']]
            # Normalize to an iterable to handle single or multiple fields.
            if isinstance(requested_fields, (str, GObject)):
                requested_fields = [requested_fields]
            
            for field in requested_fields:
                if isinstance(field, slice):
                    raise ValueError("Only the full slice [:] is supported for selecting fields.")
                fields_to_get.add(self._field_name(field))

        # 4. Handle edge case where no fields are identified.
        if not fields_to_get:
            return None

        # 5. Retrieve data from PowerWorld
        return self.esa.GetParamsRectTyped(gtype.TYPE(), sorted(list(fields_to_get)))
    
    def __setitem__(self, args, value) -> None:
        """Write grid data using indexer notation.

        ``idx[GObject] = DataFrame``
            Bulk update. Columns may be strings or GObject members; bools
            are serialized. If the objects don't exist, falls back to
            row-by-row creation (requires ``CreateIfNotFound=True`` and
            EDIT mode), which needs a complete key set
            (``gtype.key_sets()``) in the DataFrame.

        ``idx[GObject, field(s)] = value``
            Broadcast a scalar or set per-object values on existing
            objects. Never creates new ones.

        Raises
        ------
        TypeError
            If the index or value types are unsupported.
        ValueError
            If a bool has no registered vocabulary, or creation lacks a
            complete key set.
        """
        # Case 1: Bulk update from a DataFrame. e.g., pw[Bus] = df
        if isinstance(args, type) and issubclass(args, GObject):
            self._bulk_update_from_df(args, value)
            return

        # Case 2: Broadcast update to specific fields. e.g., pw[Bus, 'BusPUVolt'] = 1.05
        if isinstance(args, tuple) and len(args) == 2:
            gtype, fields = args

            if not (isinstance(gtype, type) and issubclass(gtype, GObject)):
                raise TypeError(f"First element of index must be a GObject subclass, not {type(gtype)}")

            # Normalize fields to a list of PowerWorld field-name strings.
            # Accepts strings, GObject field members, or a mixed list of both.
            if isinstance(fields, (str, GObject)):
                fields = [fields]
            elif not isinstance(fields, (list, tuple)):
                raise TypeError(
                    "Fields must be a string or a list/tuple of strings "
                    "(or GObject field members)."
                )
            fields = [self._field_name(f) for f in fields]

            self._broadcast_update_to_fields(gtype, fields, value)
            return

        raise TypeError(f"Unsupported index for __setitem__: {args}")

    def _bulk_update_from_df(self, gtype: Type[GObject], df: DataFrame):
        """Bulk update (or create) objects from a DataFrame.

        Tries the fast Rect path first; on "not found", falls back to
        ``ChangeParametersMultipleElement``, which creates missing objects
        when ``CreateIfNotFound=True`` and PowerWorld is in EDIT mode.
        Creation requires a complete key set (``gtype.key_sets()``) —
        without one the fallback would silently write nothing, since its
        "not found" errors are suppressed as expected during creation.
        """
        if not isinstance(df, DataFrame):
            raise TypeError("A DataFrame is required for bulk updates.")

        df = self._prepare_write(gtype, df)

        try:
            self._send_rect(gtype, df)
        except PowerWorldPrerequisiteError as e:
            if "not found" in str(e).lower():
                key_sets = gtype.key_sets()
                columns = set(df.columns)
                if key_sets and not any(ks <= columns for ks in key_sets):
                    missing = key_sets[0] - columns
                    accepted = " or ".join(str(sorted(ks)) for ks in key_sets)
                    raise ValueError(
                        f"Cannot create {gtype.TYPE()}: missing key field(s) {missing}. "
                        f"Accepted key sets: {accepted}."
                    ) from e
                try:
                    self.esa.ChangeParametersMultipleElement(
                        gtype.TYPE(), df.columns.tolist(), df.values.tolist()
                    )
                except PowerWorldPrerequisiteError as create_err:
                    if 'not found' not in str(create_err).lower():
                        raise
            else:
                raise

    @staticmethod
    def _field_name(field) -> str:
        """Normalize a field given as a string or GObject member to its
        PowerWorld field-name string."""
        if isinstance(field, GObject):
            return str(field)
        if isinstance(field, str):
            return field
        raise TypeError(
            f"Field must be a string or GObject field member, not {type(field)}"
        )

    @staticmethod
    def _warn_unsettable(gtype: Type[GObject], names) -> None:
        """Warn on fields the local schema says are unknown or read-only.
        The write is still attempted — PowerWorld is the authority, and the
        generated schema may lag the installed Simulator version."""
        names = list(names)
        known = set(gtype.fields())
        unknown = [n for n in names if n not in known]
        if unknown:
            warn(f"Unknown field(s) for {gtype.TYPE()}: {unknown}")
        read_only = [n for n in names if n in known and not gtype.is_settable(n)]
        if read_only:
            warn(f"Read-only field(s) on {gtype.TYPE()}: {read_only}")

    def _prepare_write(self, gtype: Type[GObject], df: DataFrame) -> DataFrame:
        """The single write funnel: normalize GObject-member columns to
        field-name strings, warn on unknown/read-only columns, serialize
        bools. The caller's DataFrame is never mutated."""
        if any(isinstance(c, GObject) for c in df.columns):
            df = df.rename(
                columns=lambda c: str(c) if isinstance(c, GObject) else c
            )

        self._warn_unsettable(gtype, df.columns)

        return self._serialize_bools(gtype, df)

    @staticmethod
    def _serialize_bools(gtype: Type[GObject], df: DataFrame) -> DataFrame:
        """Map bool values to PowerWorld strings via ``BOOL_FIELD_VOCAB``.
        A bool aimed at an unregistered field raises ``ValueError`` rather
        than guessing between YES/NO, Closed/Open, etc."""
        out = df
        for col in df.columns:
            series = df[col]
            # is_bool_dtype covers numpy bool and pandas' nullable 'boolean'
            # dtype; NA values map to NaN and pass through like other NaNs.
            if is_bool_dtype(series.dtype):
                mask = None  # Whole column is bool.
            elif series.dtype == object:
                is_bool = series.map(lambda v: isinstance(v, (bool, np.bool_)))
                if not is_bool.any():
                    continue
                mask = is_bool
            else:
                continue

            vocab = bool_vocab(col)
            if vocab is None:
                raise ValueError(
                    f"No bool mapping for field '{col}' on {gtype.TYPE()}; pass "
                    f"PowerWorld's string (e.g. 'Closed'/'Open') or add the field "
                    f"to esapp.components.gobject.BOOL_FIELD_VOCAB."
                )

            true_str, false_str = vocab
            if out is df:
                out = df.copy()
            if mask is None:
                out[col] = series.map({True: true_str, False: false_str})
            else:
                out.loc[mask, col] = series[mask].map({True: true_str, False: false_str})
        return out

    @staticmethod
    def _raise_with_edit_hint(gtype: Type[GObject], fields, err: PowerWorldError):
        """Re-raise a failed write's error, appending an actionable hint when
        the write touched fields that are only enterable in EDIT mode."""
        edit_only = [f for f in fields if gtype.is_edit_mode_only(f)]
        if edit_only:
            raise type(err)(
                f"{err} (field(s) {edit_only} are only enterable in EDIT mode — "
                f"call esa.EnterMode('EDIT') first)"
            ) from err
        raise err

    def _send_rect(self, gtype: Type[GObject], df: DataFrame) -> None:
        """Send a prepared DataFrame via ChangeParametersMultipleElementRect,
        annotating failures on EDIT-mode-only fields with a usable hint."""
        try:
            self.esa.ChangeParametersMultipleElementRect(gtype.TYPE(), df.columns.tolist(), df)
        except PowerWorldError as e:
            self._raise_with_edit_hint(gtype, df.columns, e)

    @staticmethod
    def _as_scalar_broadcast(fields: list[str], value) -> Optional[list]:
        """Return one finite numeric value per field if `value` is a scalar
        broadcast (a single number, or one number per field), else None."""
        def ok(v):
            return isinstance(v, Real) and not isinstance(v, bool) and isfinite(float(v))

        if ok(value):
            return [value] * len(fields)
        if (
            isinstance(value, (list, tuple))
            and len(fields) > 1
            and len(value) == len(fields)
            and all(ok(v) for v in value)
        ):
            return list(value)
        return None

    def _broadcast_update_to_fields(self, gtype: Type[GObject], fields: list[str], value):
        """Broadcast `value` to `fields` on existing objects
        (``pw[Type, 'Field'] = value``). Numeric scalars dispatch as a
        single ``SetData`` script command; arrays and non-numeric values
        go through the Rect path after reading primary keys."""
        self._warn_unsettable(gtype, fields)

        # Fast path: numeric scalar broadcasts need no key read — a single
        # SetData script call updates every object of the type in place.
        # Per-object arrays and non-numeric values use the Rect path below.
        if gtype.keys():
            per_field = self._as_scalar_broadcast(fields, value)
            if per_field is not None:
                field_list = ", ".join(fields)
                value_list = ", ".join(str(v) for v in per_field)
                try:
                    self.esa.RunScriptCommand(
                        f"SetData({gtype.TYPE()}, [{field_list}], [{value_list}], ALL);"
                    )
                except PowerWorldError as e:
                    self._raise_with_edit_hint(gtype, fields, e)
                return

        # For objects without keys (e.g., Sim_Solution_Options), we construct
        # the change DataFrame directly without reading from PowerWorld first.
        if not gtype.keys():
            data_dict = {}
            if len(fields) == 1:
                data_dict[fields[0]] = [value]
            elif isinstance(value, (list, tuple)) and len(value) == len(fields):
                for i, field in enumerate(fields):
                    data_dict[field] = [value[i]]
            else:
                raise ValueError(
                    "For multiple fields on a keyless object, 'value' must be a list/tuple of the same length as the fields."
                )
            change_df = DataFrame(data_dict)
        
        # For objects with keys, we first get the keys (primary keys)
        # of all existing objects to ensure we only modify what's already there.
        else:
            keys = gtype.keys()
            change_df = self[gtype, keys]
            
            if change_df is None or change_df.empty:
                # No objects of this type exist, so there's nothing to modify.
                return

            # Add the new values to the DataFrame of keys.
            # Pandas will broadcast a scalar `value` or align a list/array `value`.
            # When fields has a single element, use the field name directly to avoid pandas treating it as multiple columns
            if len(fields) == 1:
                change_df[fields[0]] = value
            else:
                change_df[fields] = value
        
        # Fields were warned above; serialize and send like bulk writes.
        self._send_rect(gtype, self._serialize_bools(gtype, change_df))