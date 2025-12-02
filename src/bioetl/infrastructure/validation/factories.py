"""Factories for validation services."""
import pandas as pd

from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.validation.contracts import SchemaProviderABC
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.validation.contracts import ValidationServiceABC


class ValidationServiceProxy(ValidationServiceABC):
    """Adapter exposing the domain ValidationService via infrastructure contract."""

    def __init__(self, service: ValidationService) -> None:
        self._service = service

    def validate(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        return self._service.validate(df=df, entity_name=entity_name)


def default_validation_service(
    schema_provider: SchemaProviderABC | None = None,
) -> ValidationServiceABC:
    """Build validation service with default schema registry."""
    provider = schema_provider or _build_schema_registry()
    service = ValidationService(schema_provider=provider)
    return ValidationServiceProxy(service)


def _build_schema_registry() -> SchemaRegistry:
    registry = SchemaRegistry()
    register_schemas(registry)
    return registry
