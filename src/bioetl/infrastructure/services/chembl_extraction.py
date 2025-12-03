"""
ChEMBL Extraction Service.

Orchestrates data extraction from ChEMBL API.
"""
from typing import Any, Type

import pandas as pd

from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.schemas.chembl.models import (
    ActivityModel,
    ChemblRecordModel,
)
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginator
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParser,
)


class ChemblExtractionService(ExtractionServiceABC):
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
        self.paginator = ChemblPaginator()
        self.parser = ChemblResponseParser()

    def get_release_version(self) -> str:
        """Get ChEMBL release version from API metadata."""
        meta = self.client.metadata()
        return meta.get("chembl_release", "unknown")

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

    def extract_all(self, entity: str, **filters: Any) -> pd.DataFrame:
        """
        Extract all records for an entity.

        Args:
            entity: Entity name (activity, assay, target, document, testitem)
            **filters: API filters including optional 'limit'

        Returns:
            DataFrame with extracted records
        """
        records: list[dict[str, Any]] = []
        offset = 0
        model_cls = self._get_model_cls(entity)

        # Check for explicit limit in filters
        total_limit = filters.pop("limit", None)

        while True:
            filters["offset"] = offset

            # Determine current batch size
            current_batch_size = self.batch_size
            if total_limit is not None:
                remaining = total_limit - len(records)
                if remaining <= 0:
                    break
                current_batch_size = min(self.batch_size, remaining)

            filters["limit"] = current_batch_size

            response = self._request_entity(entity, **filters)

            batch_records = self.parser.parse(response)
            if not batch_records:
                break

            serialized_records = [
                model_cls(**batch_record).model_dump()
                for batch_record in batch_records
            ]
            records.extend(serialized_records)

            # Check for total limit reach
            if total_limit is not None and len(records) >= total_limit:
                records = records[:total_limit]
                break

            # Check for next page
            if not self.paginator.has_more(response):
                break

            offset += current_batch_size

        return pd.DataFrame(records)
