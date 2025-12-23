"""Pandera-based Gold layer validator.

Implements GoldValidatorPort using Pandera for DataFrame validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
        self._schema = schema

    def validate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate records using Pandera schema.

        Args:
            records: List of record dictionaries to validate.

        Returns:
            List of validated records (unchanged if valid).

        Raises:
            pandera.errors.SchemaError: If validation fails.
        """
        if not self._schema or not records:
            return records

        import pandas as pd

        df = pd.DataFrame(records)
        self._schema.validate(df, lazy=True)
        return records


class NoOpGoldValidator:
    """No-operation Gold validator for pipelines without Gold schema.

    Implements GoldValidatorPort protocol with pass-through behavior.
    Used when Gold validation is not required.
    """

    def validate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pass through records without validation.

        Args:
            records: List of record dictionaries.

        Returns:
            Same list of records unchanged.
        """
        return records
