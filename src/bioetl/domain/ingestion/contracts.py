"""Domain contracts for ingestion services."""

from abc import ABC, abstractmethod

import pandas as pd


class IngestionServiceABC(ABC):
    """Сервис приведения DataFrame к стандартизированному виду."""

    @abstractmethod
    def ingest(self, df: pd.DataFrame, *, entity_name: str) -> pd.DataFrame:
        """
        Выполняет нормализацию полей, приведение к схеме и очистку обязательных
        колонок от NULL.
        """
