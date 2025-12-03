"""
Base pipeline implementation for ChEMBL data extraction.
"""
from typing import Any

from bioetl.application.pipelines.base import PipelineBase
from bioetl.domain.models import RunContext
from bioetl.domain.records import NormalizationService, RawRecord, RecordSource
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter
class ChemblPipelineBase(PipelineBase):
    """
    Базовый класс для ChEMBL-пайплайнов.

    Расширяет PipelineBase функциональностью:
    - Определение версии релиза ChEMBL
    - Интеграция с ChemblExtractionService
    - Generic extract с поддержкой CSV input
    - Хуки pre_transform
    - Нормализация полей (NormalizationService)
    """

    # Entity-specific config (override in subclasses)
    ID_COLUMN: str = ""  # e.g. "activity_id", "assay_chembl_id"
    API_FILTER_KEY: str = ""  # e.g. "activity_id__in", "assay_chembl_id__in"

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: UnifiedOutputWriter,
        record_source: RecordSource,
        normalization_service: NormalizationService,
        hash_service: HashService | None = None,
    ) -> None:
        super().__init__(
            config,
            logger,
            validation_service,
            output_writer,
            hash_service,
        )
        self._record_source = record_source
        self._normalization_service = normalization_service
        self._chembl_release: str | None = None

    def get_version(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is None:
            meta = self._record_source.metadata()
            self._chembl_release = str(meta.get("chembl_release", "unknown"))
        return self._chembl_release
    
    # Alias for compatibility if needed elsewhere, but we use get_version now.
    def get_chembl_release(self) -> str:
        return self.get_version()

    def extract(self, **kwargs: Any) -> list[RawRecord]:
        """Итерирует записи из RecordSource и материализует в список."""
        return list(self._record_source.iter_records())

    def transform(self, data: Any) -> Any:
        """
        Цепочка трансформаций для ChEMBL:
        pre_transform → _do_transform → normalize → enforce_schema
        """
        df = self._to_dataframe(data)
        df = self.pre_transform(df)
        df = self._do_transform(df)

        normalized_records = list(
            self._normalization_service.normalize_many(
                df.to_dict(orient="records")
            )
        )

        df_normalized = self._to_dataframe(normalized_records)
        df_normalized = self._enforce_schema(df_normalized)
        df_normalized = self._drop_nulls_in_required_columns(df_normalized)

        return df_normalized

    def _drop_nulls_in_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Удаляет строки, где обязательные (non-nullable) колонки содержат NULL.
        Игнорирует генерируемые колонки (hash_row, hash_business_key),
        так как они вычисляются позже.
        """
        entity = self._config.entity_name
        schema_cls = self._validation_service.get_schema(entity)
        schema = schema_cls.to_schema()

        # Columns to ignore during this check because they are generated later
        ignored_cols = {"hash_row", "hash_business_key", "index", "database_version", "extracted_at"}

        required_cols = [
            name
            for name, col in schema.columns.items()
            if not col.nullable
            and name in df.columns
            and name not in ignored_cols
        ]

        if not required_cols:
            return df

        initial_count = len(df)
        df_clean = df.dropna(subset=required_cols)
        dropped_count = initial_count - len(df_clean)

        if dropped_count > 0:
            self._logger.warning(
                f"Dropped {dropped_count} rows with nulls in required columns: {required_cols}"
            )

        return df_clean

    def pre_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Хук для предварительной обработки (можно переопределить)."""
        return df

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Основная логика трансформации.
        По умолчанию возвращает DataFrame как есть.
        Наследники могут переопределить или расширить.
        """
        return df

    def _enforce_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Приводит DataFrame к схеме: заполняет отсутствующие колонки None,
        оставляет только колонки из схемы в правильном порядке.
        """
        entity = self._config.entity_name
        schema_columns = self._validation_service.get_schema_columns(entity)

        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        return df[schema_columns]

    def _enrich_context(self, context: RunContext) -> None:
        """Добавляет chembl_release в метаданные контекста."""
        context.metadata["chembl_release"] = self.get_version()
