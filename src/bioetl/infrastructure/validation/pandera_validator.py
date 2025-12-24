"""Pandera-based Gold layer validator.

Implements GoldValidatorPort using Pandera for DataFrame validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import ValidationResult

if TYPE_CHECKING:
    import pandera as pa


class PanderaGoldValidator:
    """Gold validator using Pandera DataFrameSchema.

    Validates records against a Pandera schema before writing to Gold layer.
    Implements GoldValidatorPort protocol.

    Args:
        schema: Pandera DataFrameSchema for validation. If None, validation is skipped.

    """

    def __init__(self, schema: pa.DataFrameSchema | None = None) -> None:
        """Initialize Pandera validator.

        Args:
            schema: Pandera schema to validate against.

        """
        self._schema = schema

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Validate records using Pandera schema.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            ValidationResult with valid flag and any error messages.

        """
        if not self._schema or not records:
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
