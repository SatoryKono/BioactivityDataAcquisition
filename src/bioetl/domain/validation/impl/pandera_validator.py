"""
Pandera validator implementation.

This module provides a Pandera-based validator implementation.
"""
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

from bioetl.domain.validation.contracts import ValidationResult, ValidatorABC


class PanderaValidatorImpl(ValidatorABC):
    """
    Реализация валидатора на основе Pandera.

    Attributes:
        schema (pa.DataFrameModel): Pandera schema for validation.
    """

    def __init__(self, schema: pa.DataFrameModel) -> None:
        self.schema = schema

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validates a DataFrame against the schema.

        Args:
            df (pd.DataFrame): DataFrame to validate.

        Returns:
            ValidationResult: Validation result.
        """
        try:
            self.schema.validate(df, lazy=True)
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except SchemaErrors as e:
            return ValidationResult(
                is_valid=False,
                errors=e.failure_cases.to_dict("records"),
                warnings=[],
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
            )

    def is_valid(self, df: pd.DataFrame) -> bool:
        """Проверяет валидность DataFrame."""
        result = self.validate(df)
        return result.is_valid
