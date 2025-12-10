"""
Factories for validation components based on Pandera.

This module provides factory implementations for validation components,
following the dependency inversion principle by depending on abstractions
from the domain layer rather than concrete implementations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.validation import (
    SchemaProviderABC,
    SchemaProviderFactoryABC,
    ValidatorABC,
    ValidatorFactoryABC,
    schema_type,
)
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl

if TYPE_CHECKING:
    pass  # No type-only imports needed currently


class PanderaValidatorFactory(ValidatorFactoryABC):
    """Фабрика валидаторов Pandera."""

    def create_validator(self, schema: schema_type) -> ValidatorABC:
        """Instantiate a Pandera-backed validator for given schema."""
        return PanderaValidatorImpl(schema)


class PanderaSchemaProviderFactory(SchemaProviderFactoryABC):
    """Фабрика провайдеров схем для Pandera.

    This factory supports dependency injection via constructor parameter,
    allowing tests to provide mock schema providers. When no factory is
    provided, it uses the default schema registry from the domain layer
    via lazy import to avoid module-level coupling.
    """

    def __init__(
        self,
        schema_provider_factory: Callable[[], SchemaProviderABC] | None = None,
    ) -> None:
        """Initialize with optional schema provider factory.

        Args:
            schema_provider_factory: Callable that creates SchemaProviderABC instances.
                If None, uses default factory from domain via lazy import.
        """
        self._schema_provider_factory = schema_provider_factory

    def create_schema_provider(self) -> SchemaProviderABC:
        """Create schema provider backed by in-memory registry.

        Uses lazy import to avoid module-level domain coupling.
        This maintains architectural boundaries while providing
        sensible defaults.
        """
        if self._schema_provider_factory is not None:
            return self._schema_provider_factory()
        # Lazy import to avoid module-level domain schema coupling
        from bioetl.domain.schemas.registry import get_default_schema_registry

        return get_default_schema_registry()


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
