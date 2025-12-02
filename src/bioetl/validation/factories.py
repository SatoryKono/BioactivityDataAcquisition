"""
Factories for validation components.
"""
import pandera.pandas as pa

from bioetl.validation.contracts import SchemaProviderABC, ValidatorABC
from bioetl.validation.impl.pandera_validator import PanderaValidatorImpl
from bioetl.schemas.registry import registry


def default_validator(schema: pa.DataFrameModel) -> ValidatorABC:
    """Создает валидатор по умолчанию."""
    return PanderaValidatorImpl(schema)


def default_schema_provider() -> SchemaProviderABC:
    """Возвращает провайдер схем по умолчанию."""
    return registry
