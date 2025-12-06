"""
ChEMBL Extraction Service implementation for the infrastructure layer.

Orchestrates data extraction from ChEMBL API using infrastructure clients and
domain contracts.
"""
from collections.abc import Iterable
from typing import Any, Type

import pandas as pd

from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.schemas.chembl.models import (
    ActivityModel,
    ChemblRecordModel,
)
from bioetl.domain.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)


class ChemblExtractionServiceImpl(ExtractionServiceABC):
    """
    Service to orchestrate data extraction from ChEMBL.

    Handles pagination and dataframe assembly.
    """

    def __init__(
        self,
        client: ChemblDataClientABC,
        batch_size: int = 1000,
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.paginator = ChemblPaginatorImpl()
        self.parser = ChemblResponseParserImpl()

    def get_release_version(self) -> str:
        """Get ChEMBL release version from API metadata."""
        try:
            meta = self.client.metadata()
            return meta.get("chembl_release") or meta.get("chembl_db_version", "unknown")
        except Exception:
            # Fallback if metadata endpoint fails (e.g. timeout or bad response)
            return "unknown"

    def _get_model_cls(self, entity: str) -> Type[ChemblRecordModel]:
        """Get Pydantic model class for entity."""
        if entity == "activity":
            return ActivityModel
        if entity in {"assay", "target", "document", "testitem"}:
            return ChemblRecordModel
        raise ValueError(f"Unknown entity: {entity}")

    def _request_entity(
        self,
        entity: str,
        **filters: Any,
    ) -> dict[str, Any]:
        """Dispatch request to appropriate client method."""
        dispatch = {
            "activity": self.client.request_activity,
            "assay": self.client.request_assay,
            "target": self.client.request_target,
            "document": self.client.request_document,
            "testitem": self.client.request_molecule,
        }
        if entity not in dispatch:
            raise ValueError(f"Unknown entity: {entity}")
        return dispatch[entity](**filters)

    def request_batch(
        self,
        entity: str,
        batch_ids: list[str],
        filter_key: str,
    ) -> dict[str, Any]:
        """Request a batch of records by IDs from the API."""
        str_ids = ",".join(batch_ids)
        filter_kwargs = {filter_key: str_ids}
        return self._request_entity(entity, **filter_kwargs)

    def parse_response(
        self, raw_response: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse raw API response into list of records."""
        return self.parser.parse(raw_response)

    def serialize_records(self, entity: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serialize records using the entity's Pydantic model."""
        model_cls = self._get_model_cls(entity)
        return [
            model_cls(**record).model_dump()
            for record in records
        ]

    def extract_all(self, entity: str, **filters: Any) -> pd.DataFrame:
        """
        Extract all records for an entity.

        Args:
            entity: Entity name (activity, assay, target, document, testitem)
            **filters: API filters including optional 'limit'

        Returns:
            DataFrame with extracted records
        """
        chunks = list(self.iter_extract(entity, **filters))
        if not chunks:
            return pd.DataFrame()
        return pd.concat(chunks, ignore_index=True)

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: Any
    ) -> Iterable[pd.DataFrame]:
        """Stream records for an entity respecting pagination and limits."""
        offset = int(filters.pop("offset", 0))
        remaining = filters.pop("limit", None)
        model_cls = self._get_model_cls(entity)
        page_size = chunk_size or self.batch_size

        while remaining is None or remaining > 0:
            current_limit, request_filters = self._build_request_filters(
                base_filters=filters,
                offset=offset,
                page_size=page_size,
                remaining=remaining,
            )

            response = self._request_entity(entity, **request_filters)
            batch_records = self.parser.parse(response)
            if not batch_records:
                break

            serialized_records = self._serialize_records(model_cls, batch_records)
            if remaining is not None:
                serialized_records = serialized_records[:remaining]

            if serialized_records:
                yield pd.DataFrame(serialized_records)

            if remaining is not None:
                remaining -= len(serialized_records)
                if remaining <= 0:
                    break

            if not self.paginator.has_more(response):
                break

            offset += current_limit

    def _build_request_filters(
        self,
        *,
        base_filters: dict[str, Any],
        offset: int,
        page_size: int,
        remaining: int | None,
    ) -> tuple[int, dict[str, Any]]:
        current_limit = page_size if remaining is None else min(page_size, remaining)
        request_filters = {
            **base_filters,
            "offset": offset,
            "limit": current_limit,
        }
        return current_limit, request_filters

    def _serialize_records(
        self, model_cls: Type[ChemblRecordModel], batch_records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [model_cls(**batch_record).model_dump() for batch_record in batch_records]


__all__ = ["ChemblExtractionServiceImpl"]
