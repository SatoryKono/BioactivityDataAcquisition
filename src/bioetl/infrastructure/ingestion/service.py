"""Ingestion service implementation based on normalization and schema rules."""

from typing import Iterable

import pandas as pd

from bioetl.domain.ingestion.contracts import IngestionServiceABC
from bioetl.domain.transform.impl.normalize import NormalizationService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


class NormalizationIngestionService(IngestionServiceABC):
    """Сервис нормализации и приведения данных к схеме."""

    def __init__(
        self,
        normalization_service: NormalizationService,
        validation_service: ValidationService,
        logger: LoggerAdapterABC,
    ) -> None:
        self._normalization_service = normalization_service
        self._validation_service = validation_service
        self._logger = logger

    def ingest(self, df: pd.DataFrame, *, entity_name: str) -> pd.DataFrame:
        """Выполняет цепочку нормализации и очистки."""
        df = self._normalization_service.normalize_fields(df)
        df = self._enforce_schema(df, entity_name)
        return self._drop_nulls_in_required_columns(df, entity_name)

    def _enforce_schema(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        schema_columns = self._validation_service.get_schema_columns(entity_name)

        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        return df[schema_columns]

    def _drop_nulls_in_required_columns(
        self, df: pd.DataFrame, entity_name: str
    ) -> pd.DataFrame:
        schema_cls = self._validation_service.get_schema(entity_name)
        schema = schema_cls.to_schema()

        ignored_cols: set[str] = {
            "hash_row",
            "hash_business_key",
            "index",
            "database_version",
            "extracted_at",
        }

        required_cols: Iterable[str] = [
            name
            for name, col in schema.columns.items()
            if not col.nullable and name in df.columns and name not in ignored_cols
        ]

        if not required_cols:
            return df

        initial_count = len(df)
        df_clean = df.dropna(subset=list(required_cols))
        dropped_count = initial_count - len(df_clean)

        if dropped_count > 0:
            self._logger.warning(
                "Dropped rows with nulls in required columns",
                dropped_count=dropped_count,
                required_columns=list(required_cols),
            )

        return df_clean
