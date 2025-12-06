"""
Pandera-based implementations of validation interfaces.
"""

from __future__ import annotations

import pandas as pd
from pandera.errors import SchemaErrors

from bioetl.domain.validation import ValidationResult, ValidatorABC
from bioetl.domain.validation.contracts import SchemaType


class PanderaValidatorImpl(ValidatorABC):
    """Реализация валидатора на основе Pandera."""

    def __init__(self, schema: SchemaType) -> None:
        self._schema = schema

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        try:
            validated_df = self._schema.validate(df, lazy=True)
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                validated_df=validated_df,  # type: ignore[return-value]
            )
        except SchemaErrors as exc:
            return ValidationResult(
                is_valid=False,
                errors=exc.failure_cases.to_dict("records"),
                warnings=[],
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return ValidationResult(
                is_valid=False,
                errors=[str(exc)],
                warnings=[],
            )

    def is_valid(self, df: pd.DataFrame) -> bool:
        return self.validate(df).is_valid
