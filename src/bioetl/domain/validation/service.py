from typing import Type

import pandas as pd
import pandera.pandas as pa

from bioetl.domain.validation.contracts import SchemaProviderABC


class ValidationService:
    """
    Сервис валидации данных.
    """

    def __init__(self, schema_provider: SchemaProviderABC) -> None:
        self._schema_provider = schema_provider

    def get_schema(self, entity_name: str) -> Type[pa.DataFrameModel]:
        """Get schema class for entity."""
        return self._schema_provider.get_schema(entity_name)

    def get_schema_columns(self, entity_name: str) -> list[str]:
        """Get ordered list of column names for entity schema."""
        return self._schema_provider.get_schema_columns(entity_name)

    def validate(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        """
        Валидирует DataFrame по схеме.
        
        Returns:
            Валидированный DataFrame (Pandera может модифицировать типы).
            
        Raises:
            ValueError: Если валидация не прошла.
        """
        schema_cls = self._schema_provider.get_schema(entity_name)
        
        # Pandera validation
        # We validate directly with schema to get typed dataframe back
        try:
            validated_df = schema_cls.validate(df, lazy=True)
            return validated_df  # type: ignore
        except Exception as e:
            # Re-raise with context
            raise ValueError(f"Validation failed for {entity_name}: {e}") from e
