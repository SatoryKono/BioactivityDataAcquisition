"""
Factories for validation components based on Pandera.
"""

from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.validation import (
    SchemaProviderABC,
    SchemaProviderFactoryABC,
    SchemaType,
    ValidatorABC,
    ValidatorFactoryABC,
)
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl


class PanderaValidatorFactory(ValidatorFactoryABC):
    """Фабрика валидаторов Pandera."""

    def create_validator(self, schema: SchemaType) -> ValidatorABC:
        return PanderaValidatorImpl(schema)


class PanderaSchemaProviderFactory(SchemaProviderFactoryABC):
    """Фабрика провайдеров схем для Pandera."""

    def create_schema_provider(self) -> SchemaProviderABC:
        return SchemaRegistry()


def default_validator_factory() -> ValidatorFactoryABC:
    """Возвращает фабрику валидаторов по умолчанию (Pandera)."""
    return PanderaValidatorFactory()


def default_schema_provider_factory() -> SchemaProviderFactoryABC:
    """Возвращает фабрику провайдера схем по умолчанию."""
    return PanderaSchemaProviderFactory()

