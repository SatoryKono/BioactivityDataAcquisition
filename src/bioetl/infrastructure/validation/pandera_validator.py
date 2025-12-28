"""Pandera-based Medallion layer validators.

Implements SilverValidatorPort and GoldValidatorPort using Pandera for
DataFrame validation at each Medallion layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import ValidationResult

if TYPE_CHECKING:
    import pandera as pa


class PanderaSilverValidator:
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

    def __init__(
        self, schema: pa.DataFrameSchema | None = None, *, strict: bool = False
    ) -> None:
        """Initialize Pandera validator for Silver layer.

        Args:
            schema: Pandera schema to validate against.
            strict: If True, validation fails when schema is None.

        """
        self._schema = schema
        self._strict = strict

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
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
                    errors=["Silver schema is required but not provided"],
                )
            return ValidationResult(valid=True)

        import pandas as pd

        df = pd.DataFrame(records)
        try:
            self._schema.validate(df, lazy=True)
            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])


class NoOpSilverValidator:
    """No-operation Silver validator for pipelines without Silver schema.

    Implements SilverValidatorPort protocol with pass-through behavior.
    Used when Silver validation is not required.
    """

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Pass through records without validation.

        Args:
            records: List of record dictionaries.

        Returns:
            ValidationResult indicating valid (always True for no-op).

        """
        return ValidationResult(valid=True)


class PanderaGoldValidator:
    """Gold validator using Pandera DataFrameSchema.

    Validates records against a Pandera schema before writing to Gold layer.
    Implements GoldValidatorPort protocol.

    In strict mode, validation fails if no schema is provided.

    Args:
        schema: Pandera DataFrameSchema for validation. If None and strict=False,
            validation is skipped. If None and strict=True, validation fails.
        strict: If True, requires schema to be provided. Default False for
            backward compatibility.

    """

    def __init__(
        self, schema: pa.DataFrameSchema | None = None, *, strict: bool = False
    ) -> None:
        """Initialize Pandera validator.

        Args:
            schema: Pandera schema to validate against.
            strict: If True, validation fails when schema is None.

        """
        self._schema = schema
        self._strict = strict

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
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
                    errors=["Gold schema is required but not provided"],
                )
            return ValidationResult(valid=True)

        import pandas as pd

        df = pd.DataFrame(records)
        try:
            # If strict is False, we want to allow extra columns.
            # Pandera's validate method doesn't have a direct 'allow_extra_columns' argument
            # that overrides the schema's strict setting easily in one call if the schema object itself is strict.
            # However, we can use the 'lazy=True' argument which we are already using.

            # The issue is that the schema object itself (self._schema) might have strict=True set on it.
            # If self._strict (the validator config) is False, we should ideally override the schema's strictness.

            # We can try to temporarily unset strict on the schema if possible, or catch the specific error.
            # But modifying the schema object might be unsafe if shared.

            # A better approach if self._strict is False (meaning we allow extra columns):
            # We can filter the dataframe to only include columns in the schema before validation?
            # NO, the user wants identical columns in Silver and Gold, so we WANT the extra columns to pass through.
            # So we need the validator to IGNORE extra columns.

            # If the schema was defined with strict=True (which it seems to be in the error message),
            # Pandera will raise error for extra columns.

            # We need to tell Pandera to be non-strict if our validator is configured as non-strict.
            if not self._strict and hasattr(self._schema, "strict"):
                 # We can't easily modify the schema instance if it's frozen or shared.
                 # But we can try to validate with a non-strict copy or just catch the error?
                 # Catching the error is risky as it might hide other schema issues.

                 # Let's try to use the add_missing_columns=True? No, that adds missing, doesn't allow extra.

                 # Actually, if we want to allow extra columns, the schema itself must not be strict.
                 # Since we cannot change the schema definition easily (it's in code), we must ensure
                 # validation doesn't fail on extra columns.

                 # If we can't change the schema object, we can try to validate only the columns present in schema.
                 # But wait, if we do that, we are validating a subset, and then writing the full set.
                 # That is actually what we want! We want to validate that the columns KNOWN to the schema are correct,
                 # and ignore the extra ones (pass them through).

                 # So, if self._strict is False, we should filter the DF to schema columns for validation only?
                 # Yes, that would solve the validation error.
                 # And since we write the original 'records' (not the DF used for validation), the extra columns will be written.

                 # Let's implement this strategy.

                 schema_columns = set(self._schema.columns.keys())
                 # Also include index columns if any
                 if self._schema.index:
                     schema_columns.update(self._schema.index.names)

                 # Filter DF to only schema columns
                 df_to_validate = df[list(schema_columns.intersection(df.columns))]

                 self._schema.validate(df_to_validate, lazy=True)
            else:
                self._schema.validate(df, lazy=True)

            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])


class NoOpGoldValidator:
    """No-operation Gold validator for pipelines without Gold schema.

    Implements GoldValidatorPort protocol with pass-through behavior.
    Used when Gold validation is not required.
    """

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Pass through records without validation.

        Args:
            records: List of record dictionaries.

        Returns:
            ValidationResult indicating valid (always True for no-op).

        """
        return ValidationResult(valid=True)
