"""
Domain-level transformers used in pipelines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timezone
from typing import Callable, cast

import pandas as pd

from bioetl.domain.data import TabularData
from bioetl.domain.models import RunContext
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    TimestampProviderABC,
)


class TransformerABC(ABC):
    """Базовый интерфейс для DataFrame-трансформеров."""

    @abstractmethod
    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Выполняет преобразование DataFrame."""


class TransformerChainImpl(TransformerABC):
    """Комбинирует несколько трансформеров в последовательность."""

    def __init__(self, transformers: list[TransformerABC]) -> None:
        self._transformers = transformers

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Последовательно применяет зарегистрированные трансформеры."""
        result = df
        for transformer in self._transformers:
            result = transformer.apply(result, context)
        return result


class HashColumnsTransformerImpl(TransformerABC):
    """Добавляет hash_business_key и hash_row."""

    def __init__(
        self, hash_service: HashServiceABC, business_key_fields: list[str] | None
    ) -> None:
        self._hash_service = hash_service
        self._business_key_fields = business_key_fields or []

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Добавляет hash_business_key и hash_row, если DataFrame не пуст."""
        if df.empty:
            return df.assign(hash_business_key=None, hash_row=None)

        return cast(
            pd.DataFrame,
            self._hash_service.add_hash_columns(
                cast(TabularData, df), business_key_cols=self._business_key_fields
            ),
        )


class IndexColumnTransformerImpl(TransformerABC):
    """Добавляет индексную колонку."""

    def __init__(self, index_generator: IndexGeneratorABC) -> None:
        self._index_generator = index_generator

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Добавляет порядковый индекс строк."""
        df = df.copy()
        start_index = self._index_generator.next_index()
        # Generate range of indices for the batch
        # We need to adjust counter for remaining rows
        for _ in range(len(df) - 1):
            self._index_generator.next_index()
        end_index = start_index + len(df)
        df["index"] = list(range(start_index, end_index))
        return df


class DatabaseVersionTransformerImpl(TransformerABC):
    """Добавляет колонку с версией базы данных."""

    def __init__(
        self,
        database_version_provider: Callable[[], str | None],
    ) -> None:
        self._database_version_provider = database_version_provider

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Добавляет database_version, если значение предоставлено."""
        version = self._database_version_provider()
        if version is None:
            return df
        df = df.copy()
        df["database_version"] = str(version)
        return df


class FulldateTransformerImpl(TransformerABC):
    """Добавляет колонку acquisition_timestamp с таймстампом."""

    def __init__(self, timestamp_provider: TimestampProviderABC) -> None:
        self._timestamp_provider = timestamp_provider

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        """Добавляет acquisition_timestamp (UTC ISO-8601)."""
        df = df.copy()
        ts = self._timestamp_provider.get_extraction_timestamp()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        df["acquisition_timestamp"] = ts.isoformat()
        return df


__all__ = [
    "TransformerABC",
    "TransformerChainImpl",
    "HashColumnsTransformerImpl",
    "IndexColumnTransformerImpl",
    "DatabaseVersionTransformerImpl",
    "FulldateTransformerImpl",
]
