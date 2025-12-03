"""ID-only CSV adapter that enriches records via the extraction service."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from bioetl.clients.records.contracts import RecordSourceABC
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.records import RawRecord


def _chunk_list(data: list[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


class IdOnlyRecordSourceImpl(RecordSourceABC):
    """Fetch full records for ID-only CSV inputs."""

    def __init__(
        self,
        path: str,
        id_column: str,
        extraction_service: ExtractionServiceABC,
        *,
        entity: str,
        filter_key: str,
        batch_size: int,
        limit: int | None = None,
    ) -> None:
        self._path = path
        self._id_column = id_column
        self._extraction_service = extraction_service
        self._entity = entity
        self._filter_key = filter_key
        self._batch_size = batch_size
        self._limit = limit

    def iter_records(self) -> Iterator[RawRecord]:
        ids_df = pd.read_csv(self._path, usecols=[self._id_column])
        ids = ids_df[self._id_column].dropna().astype(str).tolist()
        if self._limit:
            ids = ids[: self._limit]

        for batch in _chunk_list(ids, self._batch_size):
            response = self._extraction_service.request_batch(
                self._entity, batch, self._filter_key
            )
            parsed = self._extraction_service.parse_response(response)
            serialized = self._extraction_service.serialize_records(
                self._entity, parsed
            )
            for record in serialized:
                yield record

    def metadata(self) -> dict[str, Any]:
        return {
            "source": "id_only_csv",
            "path": self._path,
            "id_column": self._id_column,
            "batch_size": self._batch_size,
            "limit": self._limit,
            "chembl_release": self._extraction_service.get_release_version(),
        }


__all__ = ["IdOnlyRecordSourceImpl"]
