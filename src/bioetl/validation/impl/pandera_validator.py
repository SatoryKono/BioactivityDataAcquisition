import pandas as pd
import pandera as pa

from bioetl.validation.contracts import ValidationResult, ValidatorABC


class PanderaValidatorImpl(ValidatorABC):
    """
    Реализация валидатора на основе Pandera.
    """

    def __init__(self, schema: pa.DataFrameModel) -> None:
        self.schema = schema

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        try:
            self.schema.validate(df, lazy=True)
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except pa.errors.SchemaErrors as e:
            return ValidationResult(
                is_valid=False,
                errors=e.failure_cases.to_dict("records"),
                warnings=[],
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
            )

    def is_valid(self, df: pd.DataFrame) -> bool:
        result = self.validate(df)
        return result.is_valid

