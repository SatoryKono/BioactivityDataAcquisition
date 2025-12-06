from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.domain.validation.contracts import (
    SchemaProviderABC,
    ValidationResult,
    ValidatorABC,
    ValidatorFactoryABC,
)
from bioetl.domain.validation.service import ValidationService


@dataclass
class _FakeValidator(ValidatorABC):
    should_pass: bool
    validated: pd.DataFrame | None = None

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        if self.should_pass:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                validated_df=self.validated or df,
            )
        return ValidationResult(is_valid=False, errors=["fail"], warnings=[])

    def is_valid(self, df: pd.DataFrame) -> bool:
        return self.should_pass


class _FakeValidatorFactory(ValidatorFactoryABC):
    def __init__(self, should_pass: bool) -> None:
        self.should_pass = should_pass

    def create_validator(self, schema: Any) -> ValidatorABC:
        return _FakeValidator(self.should_pass)


def test_validation_service_success():
    schema_provider = MagicMock(spec=SchemaProviderABC)
    schema_provider.get_schema.return_value = object()
    schema_provider.get_schema_columns.return_value = ["id", "name"]

    service = ValidationService(
        schema_provider=schema_provider,
        validator_factory=_FakeValidatorFactory(should_pass=True),
    )
    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})

    result = service.validate(df, "entity")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    schema_provider.get_schema.assert_called_with("entity")


def test_validation_service_failure():
    schema_provider = MagicMock(spec=SchemaProviderABC)
    schema_provider.get_schema.return_value = object()

    service = ValidationService(
        schema_provider=schema_provider,
        validator_factory=_FakeValidatorFactory(should_pass=False),
    )

    with pytest.raises(ValueError, match="Validation failed for test_entity"):
        service.validate(pd.DataFrame(), "test_entity")
