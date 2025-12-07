"""
Factories for validation components based on Pandera.
"""

from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.validation import (
    SchemaProviderABC,
    SchemaProviderFactoryABC,
    ValidatorABC,
    ValidatorFactoryABC,
    schema_type,
)
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl


class PanderaValidatorFactory(ValidatorFactoryABC):
    """Фабрика валидаторов Pandera."""

    def create_validator(self, schema: schema_type) -> ValidatorABC:
        """Instantiate a Pandera-backed validator for given schema."""
        return PanderaValidatorImpl(schema)


class PanderaSchemaProviderFactory(SchemaProviderFactoryABC):
    """Фабрика провайдеров схем для Pandera."""

    def create_schema_provider(self) -> SchemaProviderABC:
        """Create schema provider backed by in-memory registry."""
        return SchemaRegistry()


def default_validator_factory() -> ValidatorFactoryABC:
    """Возвращает фабрику валидаторов по умолчанию (Pandera)."""
    return PanderaValidatorFactory()


def default_schema_provider_factory() -> SchemaProviderFactoryABC:
    """Возвращает фабрику провайдера схем по умолчанию."""
    return PanderaSchemaProviderFactory()


def default_validator() -> ValidatorABC:
    """Stub default validator until configured."""

    raise NotImplementedError("ValidatorABC default factory is not configured")


__all__ = [
    "PanderaValidatorFactory",
    "PanderaSchemaProviderFactory",
    "default_validator_factory",
    "default_schema_provider_factory",
    "default_validator",
]