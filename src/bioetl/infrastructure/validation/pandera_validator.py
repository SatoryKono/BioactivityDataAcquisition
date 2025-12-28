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
