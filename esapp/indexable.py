from .saw import SAW, PowerWorldError, PowerWorldPrerequisiteError
from .components import GObject
from .components.gobject import bool_vocab
from typing import Type, Optional
from numbers import Real
from math import isfinite
from pandas import DataFrame
from os import path
import numpy as np


# Power World Read/Write
class Indexable:
    """
    PowerWorld Read/Write tool providing indexer-based access to grid components.

    This class enables DataFrame-like access to PowerWorld Simulator data,
    allowing users to retrieve and modify component parameters using familiar
    indexing syntax.
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

        This method allows for flexible querying of grid component data directly
        from the PowerWorld simulation instance.

        Parameters
        ----------
        index : Union[Type[GObject], Tuple[Type[GObject], Any]]
            Can be a `GObject` type to get key fields, or a tuple of
            (GObject type, fields) to specify fields. `fields` can be a
            single field name (str), a list of names, or `slice(None)` (:)
            to retrieve all available fields.

        Returns
        -------
        Optional[pandas.DataFrame]
            A DataFrame containing the requested data, or ``None`` if no
            data could be retrieved.

        Raises
        ------
        ValueError
            If an unsupported slice is used for field selection.
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
        """
        Set grid data in PowerWorld using indexer notation.

        Two write modes are supported:

        **Case 1 — Bulk update** ``idx[GObject] = DataFrame``:
            Sends every column in *value* to PowerWorld via
            ``ChangeParametersMultipleElementRect``.  If the objects do
            not yet exist (PowerWorld returns *"not found"*), the method
            falls back to ``ChangeParametersMultipleElement`` which can
            create new objects **provided the SAW instance was opened
            with** ``CreateIfNotFound=True`` **and PowerWorld is in EDIT
            mode** (see ``esa.EnterMode('EDIT')``).  If primary keys are
            missing from the DataFrame, a ``ValueError`` is raised
            immediately — secondary keys are *not* required.

        **Case 2 — Broadcast update** ``idx[GObject, field(s)] = value``:
            Reads existing objects' primary keys, appends *value* as new
            column(s), and writes the result back.  This path only
            *updates* existing objects; it never creates new ones.

        Parameters
        ----------
        args : Union[Type[GObject], Tuple[Type[GObject], Union[str, List[str]]]]
            The target object type and optional fields.
        value : Union[pandas.DataFrame, Any]
            The data to write. If `args` is just a GObject type, `value`
            must be a DataFrame containing primary keys. If `args` includes
            fields, `value` can be a scalar (which is broadcast) or a
            list/array matching the number of objects.

        Raises
        ------
        TypeError
            If the index or value types are mismatched or unsupported.
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
                raise TypeError("Fields must be a string or a list/tuple of strings.")
            fields = [self._field_name(f) for f in fields]

            self._broadcast_update_to_fields(gtype, fields, value)
            return

        raise TypeError(f"Unsupported index for __setitem__: {args}")

    def _bulk_update_from_df(self, gtype: Type[GObject], df: DataFrame):
        """Update (or create) objects from a DataFrame.

        Execution flow
        --------------
        1. Validate that every column is *settable* (key, secondary, or
           editable).  Reject read-only fields early.
        2. Call ``ChangeParametersMultipleElementRect`` — this is the fast
           path that updates all rows in a single COM round-trip.
        3. **If** the call raises ``PowerWorldPrerequisiteError`` with
           *"not found"*:

           a. Check whether the DataFrame contains a **complete key set**
              (``gtype.key_sets()`` — the primary keys or a registered
              alternate).  If none is complete, raise ``ValueError``
              — we cannot identify/create objects without one.
           b. Fall back to ``ChangeParametersMultipleElement`` which
              iterates row-by-row.  When the SAW property
              ``CreateIfNotFound`` is ``True`` **and** PowerWorld is in
              **EDIT mode**, this variant creates objects that do not yet
              exist.  *"not found"* messages from this call are silently
              suppressed (they are expected for newly created rows).

        4. Any *other* ``PowerWorldPrerequisiteError`` (not "not found")
           is re-raised immediately.

        Prerequisites for object creation
        ----------------------------------
        * ``SAW(path, CreateIfNotFound=True)``
        * ``esa.EnterMode('EDIT')`` before the call

        Parameters
        ----------
        gtype : Type[GObject]
            The GObject subclass representing the type of objects to update.
        df : pandas.DataFrame
            The DataFrame containing object data.  Must include all
            primary key columns (``gtype.keys()``).

        Raises
        ------
        TypeError
            If *df* is not a DataFrame.
        ValueError
            If any column is not settable, or if primary keys are missing
            when object creation is required.
        """
        if not isinstance(df, DataFrame):
            raise TypeError("A DataFrame is required for bulk updates.")

        df = self._prepare_write(gtype, df)

        try:
            self._send_rect(gtype, df)
        except PowerWorldPrerequisiteError as e:
            if "not found" in str(e).lower():
                # Objects must be identified by a complete key set — the
                # primary keys, or any registered alternate (e.g. name-based
                # Branch keys). See GObject.key_sets().
                key_sets = gtype.key_sets()
                columns = set(df.columns)
                if key_sets and not any(ks <= columns for ks in key_sets):
                    missing_keys = key_sets[0] - columns
                    accepted = " or ".join(str(sorted(ks)) for ks in key_sets)
                    raise ValueError(
                        f"Missing required primary key field(s) for {gtype.TYPE()}: {missing_keys}. "
                        f"A complete key set ({accepted}) must be included to create new objects."
                    ) from e
                # A complete key set is present — fall back to
                # ChangeParametersMultipleElement which creates objects
                # that do not yet exist.  The "not found" message from
                # this call is expected and suppressed.
                cols = df.columns.tolist()
                values = df.values.tolist()
                try:
                    self.esa.ChangeParametersMultipleElement(gtype.TYPE(), cols, values)
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

    def _prepare_write(self, gtype: Type[GObject], df: DataFrame) -> DataFrame:
        """Normalize, validate, and serialize a DataFrame for writing.

        The single funnel every write path goes through:

        1. Rename GObject-member columns to PowerWorld field-name strings,
           so ``pd.DataFrame({Gen.BusNum: ..., Gen.GenMW: ...})`` works.
        2. Reject read-only columns.
        3. Serialize Python bools into the field's PowerWorld vocabulary
           (e.g. ``True`` -> ``"Closed"`` for GenStatus).

        The input DataFrame is never mutated; a copy is made only when a
        transformation is actually needed.
        """
        if any(isinstance(c, GObject) for c in df.columns):
            df = df.rename(
                columns=lambda c: str(c) if isinstance(c, GObject) else c
            )

        non_settable = [c for c in df.columns if not gtype.is_settable(c)]
        if non_settable:
            raise ValueError(
                f"Cannot set read-only field(s) on {gtype.TYPE()}: {non_settable}"
            )

        return self._serialize_bools(gtype, df)

    @staticmethod
    def _serialize_bools(gtype: Type[GObject], df: DataFrame) -> DataFrame:
        """Convert Python bool values into PowerWorld vocabulary strings.

        Columns of bool dtype (and bools inside object columns) are mapped
        via the ``BOOL_FIELD_VOCAB`` registry in ``components.gobject``.
        A bool in a field with no registered vocabulary raises ``ValueError``
        rather than guessing between YES/NO, Closed/Open, etc.
        """
        out = df
        for col in df.columns:
            series = df[col]
            if series.dtype == bool:
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
                    f"Field '{col}' on {gtype.TYPE()} received Python bool values but has "
                    f"no registered vocabulary; pass the string PowerWorld expects "
                    f"(e.g. 'YES'/'NO' or 'Closed'/'Open'), or register the field in "
                    f"esapp.components.gobject.BOOL_FIELD_VOCAB."
                )

            true_str, false_str = vocab
            if out is df:
                out = df.copy()
            if mask is None:
                out[col] = series.map({True: true_str, False: false_str})
            else:
                out.loc[mask, col] = series[mask].map({True: true_str, False: false_str})
        return out

    def _send_rect(self, gtype: Type[GObject], df: DataFrame) -> None:
        """Send a prepared DataFrame via ChangeParametersMultipleElementRect,
        annotating failures on EDIT-mode-only fields with a usable hint."""
        try:
            self.esa.ChangeParametersMultipleElementRect(gtype.TYPE(), df.columns.tolist(), df)
        except PowerWorldError as e:
            edit_only = [c for c in df.columns if gtype.is_edit_mode_only(c)]
            if not edit_only:
                raise
            raise type(e)(
                f"{e} (field(s) {edit_only} are only enterable in EDIT mode — "
                f"call esa.EnterMode('EDIT') first)"
            ) from e

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
        """Modifies specific fields for existing objects by broadcasting a value.

        This corresponds to the use case: `pw[ObjectType, 'FieldName'] = value`.
        Numeric scalar broadcasts are dispatched as a single ``SetData`` script
        command (no key read); arrays and non-numeric values are written via
        ``ChangeParametersMultipleElementRect`` after reading the primary keys.

        Parameters
        ----------
        gtype : Type[GObject]
            The GObject subclass representing the type of objects to update.
        fields : List[str]
            A list of field names to update.
        value : Any
            The value to broadcast to the specified fields. Can be a scalar or
            a list/array if updating multiple fields on a keyless object.

        Raises
        ------
        ValueError
            If value length doesn't match field length for keyless objects,
            or if any specified field is not editable (excluding key fields).
        """
        # Validate all fields are settable (keys or editable)
        non_settable = [f for f in fields if not gtype.is_settable(f)]
        if non_settable:
            raise ValueError(
                f"Cannot set read-only field(s) on {gtype.TYPE()}: {non_settable}"
            )

        # Fast path: numeric scalar broadcasts need no key read — a single
        # SetData script call updates every object of the type in place.
        # Per-object arrays and non-numeric values use the Rect path below.
        if gtype.keys():
            per_field = self._as_scalar_broadcast(fields, value)
            if per_field is not None:
                field_list = ", ".join(fields)
                value_list = ", ".join(str(v) for v in per_field)
                self.esa.RunScriptCommand(
                    f"SetData({gtype.TYPE()}, [{field_list}], [{value_list}], ALL);"
                )
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
        
        # Send the minimal DataFrame through the same funnel as bulk writes.
        self._send_rect(gtype, self._serialize_bools(gtype, change_df))