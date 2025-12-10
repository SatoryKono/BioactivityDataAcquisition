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


class VersionProviderABC(ABC):
    """Провайдер версии источника данных."""

    @abstractmethod
    def get_release_version(self) -> str:
        """Возвращает идентификатор релиза (например, chembl_34)."""


class ExtractionServiceABC(RecordFetcherABC):
    """Расширенный сервис извлечения с поддержкой версионирования и сериализации.

    Наследует базовые методы iter_extract() и extract_all() от RecordFetcherABC.
    Добавляет методы для работы с версиями, батчами и сериализацией.
    """

    @abstractmethod
    def get_release_version(self) -> str:
        """Получить версию источника данных."""

    @abstractmethod
    def request_batch(
        self, entity: str, batch_ids: list[str], filter_key: str
    ) -> dict[str, object]:
        """Запросить батч по идентификаторам."""

    @abstractmethod
    def parse_response(self, raw_response: object) -> list["RawRecord"]:
        """Разобрать сырой ответ в записи."""

    @abstractmethod
    def serialize_records(self, entity: str, records: list[object]) -> list[object]:
        """Сериализовать записи для вывода."""


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
    "BatchAdapterABC",
    "ExtractionServiceABC",
]
