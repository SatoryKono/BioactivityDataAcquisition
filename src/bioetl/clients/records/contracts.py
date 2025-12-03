"""Contracts for record sources and normalization services."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import Any

from bioetl.domain.records import NormalizationService, RawRecord


class RecordSourceABC(ABC):
    """
    Abstract contract for record-level sources.

    Provides streaming access to raw records along with optional metadata
    (release versions, file paths, etc.).
    Default factory: ``bioetl.clients.records.factories.default_record_source``
    Implementations: ``CsvRecordSourceImpl``, ``IdOnlyRecordSourceImpl``
    """

    @abstractmethod
    def iter_records(self) -> Iterator[RawRecord]:
        """Return an iterator over raw records."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return source metadata for observability."""


class RecordNormalizationServiceABC(NormalizationService, ABC):
    """
    Abstract contract for record-level normalization.

    Default factory: ``bioetl.clients.records.factories.default_normalization_service``
    Implementations: ``ChemblNormalizationServiceImpl``
    """

    @abstractmethod
    def normalize(self, record: RawRecord) -> RawRecord:  # type: ignore[override]
        """Normalize a single record."""

    @abstractmethod
    def normalize_many(self, records: Iterable[RawRecord]) -> Iterable[RawRecord]:  # type: ignore[override]
        """Normalize multiple records preserving order."""


__all__ = ["RecordSourceABC", "RecordNormalizationServiceABC"]
