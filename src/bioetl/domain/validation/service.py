import pandas as pd

from bioetl.domain.validation.contracts import (
    SchemaProviderABC,
    SchemaType,
    ValidationResult,
    ValidatorFactoryABC,
)


class ValidationService:
    """
    Сервис валидации данных, работающий через доменные интерфейсы.
    """

    def __init__(
        self,
        *,
        schema_provider: SchemaProviderABC,
        validator_factory: ValidatorFactoryABC,
    ) -> None:
        self._schema_provider = schema_provider
        self._validator_factory = validator_factory

    def get_schema(self, entity_name: str) -> SchemaType:
        """Возвращает схему для сущности."""
        return self._schema_provider.get_schema(entity_name)

    def get_schema_columns(self, entity_name: str) -> list[str]:
        """Возвращает упорядоченный список колонок схемы."""
        return self._schema_provider.get_schema_columns(entity_name)

    def validate(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        """
        Валидирует DataFrame по схеме, используя валидатор фабрики.

        Возвращает валидированный DataFrame (если валидатор его модифицирует),
        либо исходный df при успешной проверке без преобразований.

        Raises:
            ValueError: если валидация не пройдена.
        """
        schema = self._schema_provider.get_schema(entity_name)
        validator = self._validator_factory.create_validator(schema)
        result: ValidationResult = validator.validate(df)

        if not result.is_valid:
            raise ValueError(f"Validation failed for {entity_name}: {result.errors}")

        return result.validated_df if result.validated_df is not None else df
