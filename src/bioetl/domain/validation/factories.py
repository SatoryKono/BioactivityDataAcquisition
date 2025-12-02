"""
Factories for validation components.
"""
import pandera.pandas as pa

from bioetl.domain.validation.contracts import SchemaProviderABC, ValidatorABC
from bioetl.domain.validation.impl.pandera_validator import PanderaValidatorImpl
from bioetl.domain.schemas.registry import registry


def default_validator(schema: pa.DataFrameModel) -> ValidatorABC:
    """Создает валидатор по умолчанию."""
    return PanderaValidatorImpl(schema)


def default_schema_provider() -> SchemaProviderABC:
    """Возвращает провайдер схем по умолчанию."""
    return registry
