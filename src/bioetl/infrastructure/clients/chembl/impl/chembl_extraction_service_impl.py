"""
ChEMBL Extraction Service implementation for the infrastructure layer.

Orchestrates data extraction from ChEMBL API using infrastructure clients and
domain contracts.
"""

from collections.abc import Iterable
from typing import Any

from bioetl.domain.clients.chembl.contracts import ChemblDataClientABC
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)
from bioetl.infrastructure.clients.chembl.serializers import serialize_chembl_payload


class ChemblExtractionServiceImpl(ExtractionServiceABC):
    """
    Service to orchestrate data extraction from ChEMBL.

    Handles pagination and record assembly.
    """

    def __init__(
        self,
        client: ChemblDataClientABC,
        batch_size: int = 1000,
        *,
        flatten_enabled: bool = True,
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.paginator = ChemblPaginatorImpl()
        self.parser = ChemblResponseParserImpl()
        self.flatten_enabled = flatten_enabled

    def get_release_version(self) -> str:
        """Get ChEMBL release version from API metadata."""
        try:
            meta = self.client.metadata()
            return meta.get("chembl_release") or meta.get(
                "chembl_db_version", "unknown"
            )
        except Exception:
            # Fallback if metadata endpoint fails (e.g. timeout or bad response)
            return "unknown"

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
            "molecule": self.client.request_molecule,
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
        filter_kwargs = self._attach_entity_fields(entity, {filter_key: str_ids})
        return self._request_entity(entity, **filter_kwargs)

    def parse_response(self, raw_response: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse raw API response into list of records."""
        return self.parser.parse_response(raw_response)

    def serialize_records(
        self, entity: str, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Serialize records using flatten helper."""
        if not self.flatten_enabled:
            return records
        return [serialize_chembl_payload(record) for record in records]

    def extract_all(self, entity: str, **filters: Any) -> list[dict[str, Any]]:
        """
        Extract all records for an entity.

        Args:
            entity: Entity name (activity, assay, target, document, molecule)
            **filters: API filters including optional 'limit'

        Returns:
            List of extracted records
        """
        chunks = list(self.iter_extract(entity, **filters))
        records: list[dict[str, Any]] = []
        for chunk in chunks:
            records.extend(chunk)
        return records

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: Any
    ) -> Iterable[list[dict[str, Any]]]:
        """Stream records for an entity respecting pagination and limits."""
        filters = self._attach_entity_fields(entity, dict(filters))
        offset = int(filters.pop("offset", 0))
        remaining = filters.pop("limit", None)
        page_size = chunk_size or self.batch_size

        while remaining is None or remaining > 0:
            current_limit, request_filters = self._build_request_filters(
                base_filters=filters,
                offset=offset,
                page_size=page_size,
                remaining=remaining,
            )

            response = self._request_entity(entity, **request_filters)
            batch_records = self.parser.parse_response(response)
            if not batch_records:
                break

            serialized_records = self.serialize_records(entity, batch_records)
            if remaining is not None:
                serialized_records = serialized_records[:remaining]

            if serialized_records:
                yield serialized_records

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

    def _attach_entity_fields(
        self, entity: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Ensure critical fields are requested from ChEMBL API.

        Assay endpoint не возвращает все колонки без параметра fields.
        Если пользователь не задал fields/only, добавляем список из схемы.
        """
        if entity != "assay":
            return filters

        if "fields" in filters or "only" in filters:
            return filters

        try:
            from bioetl.domain.schemas.chembl.assay import OUTPUT_COLUMN_ORDER
        except Exception:
            return filters

        skip_meta = {
            "hash_row",
            "hash_business_key",
            "index",
            "database_version",
            "extracted_at",
        }
        field_names = [col for col in OUTPUT_COLUMN_ORDER if col not in skip_meta]
        filters["fields"] = ",".join(field_names)
        return filters


__all__ = ["ChemblExtractionServiceImpl"]
