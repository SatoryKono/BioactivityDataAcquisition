from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.domain.data import MutableTabularData
from bioetl.domain.validation.contracts import (
    SchemaProviderABC,
    ValidationResult,
    ValidatorABC,
    ValidatorFactoryABC,
    schema_type,
)
from bioetl.domain.validation.service import ValidationService

pytestmark = pytest.mark.unit


@dataclass
class _FakeValidator(ValidatorABC):
    should_pass: bool
    validated: MutableTabularData | None = None

    def validate(self, df: MutableTabularData) -> ValidationResult:
        if self.should_pass:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                validated_data=df if self.validated is None else self.validated,
            )
        return ValidationResult(is_valid=False, errors=["fail"], warnings=[])

    def is_valid(self, df: MutableTabularData) -> bool:  # pragma: no cover - unused
        return self.should_pass


class _FakeValidatorFactory(ValidatorFactoryABC):
    def __init__(self, should_pass: bool, validated: MutableTabularData | None = None) -> None:
        self.should_pass = should_pass
        self.validated = validated

    def create_validator(self, schema: schema_type) -> ValidatorABC:
        return _FakeValidator(self.should_pass, validated=self.validated)


def test_validation_service_success_selects_schema_columns() -> None:
    schema_provider = MagicMock(spec=SchemaProviderABC)
    schema_provider.get_schema.return_value = object()
    schema_provider.get_schema_columns.return_value = ["name", "id"]

    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"], "extra": [10, 20]})
    service = ValidationService(
        schema_provider=schema_provider,
        validator_factory=_FakeValidatorFactory(should_pass=True),
    )

    result = service.validate(df.copy(), "entity")

    assert list(result.columns) == ["name", "id"]
    schema_provider.get_schema.assert_called_once_with("entity")
    schema_provider.get_schema_columns.assert_called_with("entity")


def test_validation_service_raises_on_failed_validation() -> None:
    schema_provider = MagicMock(spec=SchemaProviderABC)
    schema_provider.get_schema.return_value = object()

    service = ValidationService(
        schema_provider=schema_provider,
        validator_factory=_FakeValidatorFactory(should_pass=False),
    )

    with pytest.raises(ValueError, match="Validation failed for test_entity"):
        service.validate(pd.DataFrame(), "test_entity")


def test_validation_service_validated_dataframe_missing_columns_raises() -> None:
    schema_provider = MagicMock(spec=SchemaProviderABC)
    schema_provider.get_schema.return_value = object()
    schema_provider.get_schema_columns.return_value = ["id", "name"]

    validated_df = pd.DataFrame({"id": [1, 2]})
    validator_factory = _FakeValidatorFactory(should_pass=True, validated=validated_df)

    service = ValidationService(
        schema_provider=schema_provider,
        validator_factory=validator_factory,
    )

    with pytest.raises(ValueError, match="missing columns"):
        service.validate(cast(MutableTabularData, pd.DataFrame({"id": [1, 2]})), "entity")
