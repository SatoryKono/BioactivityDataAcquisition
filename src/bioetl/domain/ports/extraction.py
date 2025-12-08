"""Ports for extraction services (domain layer)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from bioetl.domain.record_source import RawRecord


class ExtractionServiceABC(ABC):
    """Abstract base class for data extraction services.

    Defines the contract for services that extract data from external sources
    and return raw record dictionaries.
    """

    @abstractmethod
    def get_release_version(self) -> str:
        """Get the version/release identifier of the data source."""

    @abstractmethod
    def extract_all(self, entity: str, **filters: Any) -> list["RawRecord"]:
        """Extract all records for an entity with optional filters."""

    @abstractmethod
    def iter_extract(
        self,
        entity: str,
        *,
        chunk_size: int | None = None,
        **filters: Any,
    ) -> Iterable[list["RawRecord"]]:
        """Stream records for an entity in raw record batches."""

    @abstractmethod
    def request_batch(
        self,
        entity: str,
        batch_ids: list[str],
        filter_key: str,
    ) -> dict[str, Any]:
        """Request a batch of records by IDs."""

    @abstractmethod
    def parse_response(self, raw_response: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse raw API response into list of records."""

    @abstractmethod
    def serialize_records(
        self,
        entity: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Serialize records before DataFrame creation."""


class BatchAdapterABC(Protocol):
    """Protocol for adapting raw batches to list of RawRecord.

    Used to normalize different batch formats from extraction services
    into the expected ``list[RawRecord]`` format.
    """

    def process_batch(self, raw_batch: Any) -> list["RawRecord"]:
        """Normalize a batch into a list of raw record mappings."""


__all__ = [
    "ExtractionServiceABC",
    "BatchAdapterABC",
]
