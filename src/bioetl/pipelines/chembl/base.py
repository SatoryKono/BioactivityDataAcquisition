from abc import abstractmethod
from typing import Any
import pandas as pd

from bioetl.config.models import PipelineConfig
from bioetl.core.models import RunContext
from bioetl.core.pipeline_base import PipelineBase
from bioetl.logging.contracts import LoggerAdapterABC
from bioetl.output.unified_writer import UnifiedOutputWriter
from bioetl.services.chembl_extraction_service import ChemblExtractionService
from bioetl.validation.service import ValidationService


class ChemblPipelineBase(PipelineBase):
    """
    Базовый класс для ChEMBL-пайплайнов.
    
    Расширяет PipelineBase функциональностью:
    - Определение версии релиза ChEMBL
    - Интеграция с ChemblExtractionService
    - Хуки pre_transform
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: UnifiedOutputWriter,
        extraction_service: ChemblExtractionService,
    ) -> None:
        super().__init__(config, logger, validation_service, output_writer)
        self._extraction_service = extraction_service
        self._chembl_release: str | None = None
    
    def get_chembl_release(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is None:
            self._chembl_release = self._extraction_service.get_release_version()
        return self._chembl_release
    
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
    
    @abstractmethod
    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Основная логика трансформации (абстрактный)."""
    
    def _build_meta(self, context: RunContext, df: pd.DataFrame) -> dict[str, Any]:
        """Добавляет chembl_release в метаданные."""
        meta = super()._build_meta(context, df)
        meta["chembl_release"] = self.get_chembl_release()
        return meta

