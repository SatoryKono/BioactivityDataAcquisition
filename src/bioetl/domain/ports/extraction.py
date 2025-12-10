"""Ports for extraction services (domain layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.record_source import RawRecord


class RecordFetcherABC(ABC):
    """Контракт поставщика сырых записей с поддержкой пагинации."""

    @abstractmethod
    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: object
    ) -> Iterable[list["RawRecord"]]:
        """Итерирует чанки сырых записей."""

    @abstractmethod
    def extract_all(self, entity: str, **filters: object) -> list["RawRecord"]:
        """Возвращает все записи указанной сущности."""


class VersionProviderABC(Protocol):
    """Провайдер версии источника данных."""

    def get_release_version(self) -> str:
        """Возвращает идентификатор релиза (например, chembl_34)."""


class VersionedRecordFetcherABC(RecordFetcherABC, VersionProviderABC, Protocol):
    """Fetcher с версией источника."""
    ...


class BatchAdapterABC(Protocol):
    """
    Protocol for adapting raw batches to list of RawRecord.

    Used to normalize different batch formats from extraction services
    into the expected list[RawRecord] format.
    """

    def process_batch(self, raw_batch: object) -> list["RawRecord"]:
        """
        Normalize a batch into a list of raw record mappings.

        Args:
            raw_batch: Raw batch from extraction service (DataFrame, dict, list, etc.)

        Returns:
            List of RawRecord dictionaries
        """
        ...


__all__ = [
    "RecordFetcherABC",
    "VersionProviderABC",
    "VersionedRecordFetcherABC",
    "BatchAdapterABC",
]
