"""API-backed record source for ChEMBL entities."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from bioetl.clients.records.contracts import RecordSourceABC
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.records import RawRecord


class ChemblApiRecordSourceImpl(RecordSourceABC):
    """
    Record source that fetches records directly from the ChEMBL API.

    Uses the configured ``ExtractionServiceABC`` to fetch all records with
    optional filters and returns them as an iterator of ``RawRecord``.
    """

    def __init__(
        self,
        extraction_service: ExtractionServiceABC,
        entity: str,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._entity = entity
        self._filters = filters or {}
        self._limit = limit
        self._metadata: dict[str, Any] | None = None

    def iter_records(self) -> Iterator[RawRecord]:
        df = self._extraction_service.extract_all(self._entity, **self._filters)
        if self._limit:
            df = df.head(self._limit)
        yield from df.to_dict(orient="records")

    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            version = self._extraction_service.get_release_version()
            self._metadata = {
                "chembl_release": version,
                "entity": self._entity,
                "filters": self._filters,
                "limit": self._limit,
            }
        return self._metadata


__all__ = ["ChemblApiRecordSourceImpl"]
