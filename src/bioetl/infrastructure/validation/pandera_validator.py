"""Pandera-based Medallion layer validators.

Implements SilverValidatorPort and GoldValidatorPort using Pandera for
DataFrame validation at each Medallion layer.

Refactored to extract common validation logic into BasePanderaValidator.
"""

from __future__ import annotations

__all__ = [
    "BasePanderaValidator",
    "NoOpValidator",
    "PanderaGoldValidator",
    "PanderaSilverValidator",
]

from typing import TYPE_CHECKING, ClassVar

from bioetl.domain.types import JsonDict, ValidationResult

if TYPE_CHECKING:
    import pandas as pd
    import pandera as pa


class BasePanderaValidator:
    """Base Pandera validator with common validation logic.

    Provides shared initialization and validation flow for Silver and Gold
    layer validators. Subclasses can override _validate_with_schema() for
    layer-specific validation behavior.

    Attributes:
        layer_name: Name of the Medallion layer ("Silver" or "Gold").
        _schema: Pandera DataFrameSchema for validation.
        _strict: If True, validation fails when schema is None.

    """

    layer_name: ClassVar[str] = "Base"

    def __init__(
        self, schema: pa.DataFrameSchema | None = None, *, strict: bool = False
    ) -> None:
        """Initialize Pandera validator.

        Args:
            schema: Pandera DataFrameSchema for validation. If None and strict=False,
                validation is skipped. If None and strict=True, validation fails.
            strict: If True, requires schema to be provided. Default False for
                backward compatibility.

        """
        self._schema = schema
        self._strict = strict

    def validate(
        self,
        records: list[
            JsonDict  # Any: validated records have heterogeneous field types
        ],  # Any: validated records have heterogeneous field types
    ) -> ValidationResult:  # Any: validated records have heterogeneous field types
        """Validate records using Pandera schema.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            ValidationResult with valid flag and any error messages.

        """
        if not records:
            return ValidationResult(valid=True)

        if not self._schema:
            if self._strict:
                return ValidationResult(
                    valid=False,
                    errors=[f"{self.layer_name} schema is required but not provided"],
                )
            return ValidationResult(valid=True)

        import pandas as pd

        df = pd.DataFrame(records)
        return self._validate_with_schema(df)

    def _reorder_to_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reorder DataFrame columns to match schema definition order.

        Preserves extra columns at the end so strict=True still catches them.
        Skips reordering for DataFrameModel classes that lack .columns.

        Returns:
            DataFrame with schema-defined columns first, followed by extra columns.
        """
        assert self._schema is not None
        if not hasattr(self._schema, "columns"):
            return df
        schema_cols = list(self._schema.columns.keys())
        df_cols = df.columns.tolist()
        schema_set = set(schema_cols)
        ordered = [c for c in schema_cols if c in df_cols]
        extra = [c for c in df_cols if c not in schema_set]
        return df[ordered + extra]

    def _normalize_nullable_integer_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cast nullable integer schema columns away from pandas object dtype.

        Single-record validation commonly builds DataFrames where nullable integer
        fields become `object` because the row contains `None`. Pandera then sees a
        dtype mismatch before semantic checks run. Normalize only columns that the
        schema explicitly marks as nullable integers, and leave non-castable values
        untouched so validation can still fail normally.
        """
        assert self._schema is not None
        if not hasattr(self._schema, "columns"):
            return df

        normalized = df.copy()
        for name, column in self._schema.columns.items():
            if name not in normalized.columns:
                continue
            if not getattr(column, "nullable", False):
                continue

            dtype_name = str(getattr(column, "dtype", "")).lower()
            if "int" not in dtype_name:
                continue

            series = normalized[name]
            if str(series.dtype) != "object":
                continue

            try:
                normalized[name] = series.astype("Int64")
            except (TypeError, ValueError):
                continue

        return normalized

    def _normalize_nullable_boolean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cast nullable boolean schema columns away from pandas object dtype.

        Single-record and sparse batches commonly build DataFrames where nullable
        boolean fields become `object` because rows contain `None`. Pandera then
        rejects the column before semantic checks run. Normalize only columns the
        schema explicitly marks as nullable booleans, and leave non-castable
        values untouched so validation can still fail normally.
        """
        assert self._schema is not None
        if not hasattr(self._schema, "columns"):
            return df

        normalized = df.copy()
        for name, column in self._schema.columns.items():
            if name not in normalized.columns:
                continue
            if not getattr(column, "nullable", False):
                continue

            dtype_name = str(getattr(column, "dtype", "")).lower()
            if "bool" not in dtype_name:
                continue

            series = normalized[name]
            if str(series.dtype) != "object":
                continue

            try:
                normalized[name] = series.astype("boolean")
            except (TypeError, ValueError):
                continue

        return normalized

    def _validate_with_schema(self, df: pd.DataFrame) -> ValidationResult:
        """Validate DataFrame against schema.

        Override in subclasses for layer-specific validation behavior.

        Note: This method is only called when self._schema is not None,
        as verified by the validate() method.

        Args:
            df: Pandas DataFrame to validate.

        Returns:
            ValidationResult with valid flag and any error messages.

        """
        assert self._schema is not None  # Guaranteed by validate()
        from pandera.errors import SchemaError, SchemaErrors

        try:
            df_to_validate = df
            if hasattr(self._schema, "columns"):
                missing = [
                    name for name in self._schema.columns if name not in df.columns
                ]
                if missing:
                    df_to_validate = df.copy()
                    for name in missing:
                        column = self._schema.columns[name]
                        if getattr(column, "nullable", False):
                            df_to_validate[name] = None
            df_to_validate = self._normalize_nullable_integer_columns(df_to_validate)
            df_to_validate = self._normalize_nullable_boolean_columns(
                df_to_validate
            )
            df_to_validate = self._reorder_to_schema(df_to_validate)
            self._schema.validate(df_to_validate, lazy=True)
            return ValidationResult(valid=True)
        except (SchemaError, SchemaErrors, KeyError, TypeError, ValueError) as e:
            return ValidationResult(valid=False, errors=[str(e)])


class PanderaSilverValidator(BasePanderaValidator):
    """Silver validator using Pandera DataFrameSchema.

    Validates records against a Pandera schema before writing to Silver layer.
    Implements SilverValidatorPort protocol.

    In strict mode, validation fails if no schema is provided.

    Args:
        schema: Pandera DataFrameSchema for validation. If None and strict=False,
            validation is skipped. If None and strict=True, validation fails.
        strict: If True, requires schema to be provided. Default False for
            backward compatibility.

    """

    layer_name: ClassVar[str] = "Silver"


class PanderaGoldValidator(BasePanderaValidator):
    """Gold validator using Pandera DataFrameSchema.

    Validates records against a Pandera schema before writing to Gold layer.
    Implements GoldValidatorPort protocol.

    In strict mode, validation fails if no schema is provided.
    When strict=False, allows extra columns by validating only schema columns.

    Args:
        schema: Pandera DataFrameSchema for validation. If None and strict=False,
            validation is skipped. If None and strict=True, validation fails.
        strict: If True, requires schema to be provided. Default True to enforce
            strict Gold validation.

    """

    layer_name: ClassVar[str] = "Gold"

    def __init__(
        self, schema: pa.DataFrameSchema | None = None, *, strict: bool = True
    ) -> None:
        """Initialize Gold validator with strict validation by default."""
        super().__init__(schema=schema, strict=strict)

    def _validate_with_schema(self, df: pd.DataFrame) -> ValidationResult:
        """Validate DataFrame with Gold-specific handling for extra columns.

        When strict=False, filters DataFrame to schema columns only before
        validation. This allows extra columns to pass through to Gold layer
        without failing validation.

        Note: This method is only called when self._schema is not None,
        as verified by the validate() method.

        Args:
            df: Pandas DataFrame to validate.

        Returns:
            ValidationResult with valid flag and any error messages.

        """
        assert self._schema is not None  # Guaranteed by validate()
        from pandera.errors import SchemaError, SchemaErrors

        try:
            # If strict is False, we want to allow extra columns.
            # Filter DataFrame to only include columns in the schema before validation.
            # This way we validate that columns KNOWN to the schema are correct,
            # and ignore extra ones (pass them through).
            if not self._strict and hasattr(self._schema, "columns"):
                schema_columns = set(self._schema.columns.keys())
                # Also include index columns if any
                if self._schema.index:
                    schema_columns.update(self._schema.index.names)

                # Filter DF to only schema columns
                # Handle case where schema column is NOT in df (missing column) - Pandera handles that.
                cols_to_keep = list(schema_columns.intersection(df.columns))
                df_to_validate = self._reorder_to_schema(df[cols_to_keep])

                self._schema.validate(df_to_validate, lazy=True)
            else:
                df_to_validate = self._reorder_to_schema(df)
                self._schema.validate(df_to_validate, lazy=True)

            return ValidationResult(valid=True)
        except (SchemaError, SchemaErrors, KeyError, TypeError, ValueError) as e:
            return ValidationResult(valid=False, errors=[str(e)])


class NoOpValidator:
    """No-operation validator for pipelines without schema validation.

    Implements both SilverValidatorPort and GoldValidatorPort protocols
    with pass-through behavior. Used when validation is not required.
    """

    def validate(
        self,
        records: list[
            JsonDict  # Any: validated records have heterogeneous field types
        ],  # Any: validated records have heterogeneous field types
    ) -> ValidationResult:  # Any: validated records have heterogeneous field types
        """Pass through records without validation.

        Args:
            records: List of record dictionaries (ignored).

        Returns:
            ValidationResult indicating valid (always True for no-op).

        """
        del records  # Unused - NoOp always returns valid
        return ValidationResult(valid=True)
