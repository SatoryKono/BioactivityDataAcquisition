from typing import Any
import pandas as pd

from bioetl.pipelines.chembl.base import ChemblPipelineBase


class ChemblCommonPipeline(ChemblPipelineBase):
    """
    Базовый класс для ChEMBL сущностных пайплайнов.
    Реализует общие методы извлечения.
    """

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

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Базовая трансформация.
        Пока просто заглушка, возвращает как есть.
        Наследники могут переопределить или расширить.
        """
        return df

