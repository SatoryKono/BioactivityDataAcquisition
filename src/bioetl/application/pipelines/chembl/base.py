from abc import abstractmethod
from typing import Any
import pandas as pd

from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.application.pipelines.base import PipelineBase
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.contracts import OutputServiceABC
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService
from bioetl.domain.transform.hash_service import HashService
from bioetl.infrastructure.validation.contracts import ValidationServiceABC


class ChemblPipelineBase(PipelineBase):
    """
    Базовый класс для ChEMBL-пайплайнов.
    
    Расширяет PipelineBase функциональностью:
    - Определение версии релиза ChEMBL
    - Интеграция с ChemblExtractionService
    - Хуки pre_transform
    - Общая логика extraction
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationServiceABC,
        output_service: OutputServiceABC,
        extraction_service: ChemblExtractionService,
        hash_service: HashService | None = None,
    ) -> None:
        super().__init__(config, logger, validation_service, output_service, hash_service)
        self._extraction_service = extraction_service
        self._chembl_release: str | None = None
    
    def get_chembl_release(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is None:
            self._chembl_release = self._extraction_service.get_release_version()
        return self._chembl_release

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Извлекает все данные для текущей сущности.
        Использует self._config.entity_name для определения типа.
        """
        entity = self._config.entity_name
        self._logger.info(f"Extracting {entity}...")
        
        # Combine kwargs and pipeline specific config parameters
        filters = self._config.pipeline.copy()
        filters.update(kwargs)
        
        return self._extraction_service.extract_all(entity, **filters)
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Цепочка трансформаций для ChEMBL:
        pre_transform → base transform
        """
        df = self.pre_transform(df)
        df = self._do_transform(df)
        return df
    
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
    
    def _build_meta(self, context: RunContext, df: pd.DataFrame) -> dict[str, Any]:
        """Добавляет chembl_release в метаданные."""
        meta = super()._build_meta(context, df)
        meta["chembl_release"] = self.get_chembl_release()
        return meta
