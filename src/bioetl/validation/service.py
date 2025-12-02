import pandas as pd

from bioetl.schemas.registry import registry
from bioetl.validation.impl.pandera_validator import PanderaValidatorImpl


class ValidationService:
    """
    Сервис валидации данных.
    """

    def validate(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        """
        Валидирует DataFrame по схеме.
        
        Returns:
            Валидированный DataFrame (Pandera может модифицировать типы).
            
        Raises:
            ValueError: Если валидация не прошла.
        """
        schema_cls = registry.get_schema(entity_name)
        
        # Pandera validation
        # We validate directly with schema to get typed dataframe back
        try:
            validated_df = schema_cls.validate(df, lazy=True)
            return validated_df  # type: ignore
        except Exception as e:
            # Re-raise with context
            raise ValueError(f"Validation failed for {entity_name}: {e}") from e

