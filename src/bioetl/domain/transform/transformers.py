"""
Domain-level transformers used in pipelines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import pandas as pd

from bioetl.domain.models import RunContext
from bioetl.domain.transform.hash_service import HashService


class TransformerABC(ABC):
    """Базовый интерфейс для DataFrame-трансформеров."""

    @abstractmethod
    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Выполняет преобразование DataFrame."""


class TransformerChain(TransformerABC):
    """Комбинирует несколько трансформеров в последовательность."""

    def __init__(self, transformers: list[TransformerABC]) -> None:
        self._transformers = transformers

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        result = df
        for transformer in self._transformers:
            result = transformer.apply(result, context)
        return result


class HashColumnsTransformer(TransformerABC):
    """Добавляет hash_business_key и hash_row."""

    def __init__(
        self, hash_service: HashService, business_key_fields: list[str] | None
    ) -> None:
        self._hash_service = hash_service
        self._business_key_fields = business_key_fields or []

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        if df.empty:
            return df.assign(hash_business_key=None, hash_row=None)

        return self._hash_service.add_hash_columns(
            df, business_key_cols=self._business_key_fields
        )


class IndexColumnTransformer(TransformerABC):
    """Добавляет индексную колонку."""

    def __init__(self, hash_service: HashService) -> None:
        self._hash_service = hash_service

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        return self._hash_service.add_index_column(df)


class DatabaseVersionTransformer(TransformerABC):
    """Добавляет колонку с версией базы данных."""

    def __init__(
        self,
        hash_service: HashService,
        database_version_provider: Callable[[], str | None],
    ) -> None:
        self._hash_service = hash_service
        self._database_version_provider = database_version_provider

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        version = self._database_version_provider()
        if version is None:
            return df
        return self._hash_service.add_database_version_column(df, version)


class FulldateTransformer(TransformerABC):
    """Добавляет колонку extracted_at с таймстампом."""

    def __init__(self, hash_service: HashService) -> None:
        self._hash_service = hash_service

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        return self._hash_service.add_fulldate_column(df)


__all__ = [
    "TransformerABC",
    "TransformerChain",
    "HashColumnsTransformer",
    "IndexColumnTransformer",
    "DatabaseVersionTransformer",
    "FulldateTransformer",
]
