import pandas as pd
from typing import Any, Type

from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginator
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser
from bioetl.domain.schemas.chembl.models import (
    ActivityModel,
    ChemblRecordModel,
)


class ChemblExtractionService:
    """
    Service to orchestrate data extraction from ChEMBL.
    Handles pagination and dataframe assembly.
    """

    def __init__(
        self, 
        client: ChemblDataClientABC,
        batch_size: int = 1000
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.paginator = ChemblPaginator()
        self.parser = ChemblResponseParser()

    def get_release_version(self) -> str:
        meta = self.client.metadata()
        # Assuming structure: {"chembl_release": "chembl_34", ...}
        return meta.get("chembl_release", "unknown")

    def _get_model_cls(self, entity: str) -> Type[ChemblRecordModel]:
        if entity == "activity":
            return ActivityModel
        if entity in {"assay", "target", "document", "testitem"}:
            return ChemblRecordModel
        raise ValueError(f"Unknown entity: {entity}")

    def extract_all(self, entity: str, **filters: Any) -> pd.DataFrame:
        """
        Extract all records for an entity.
        """
        records = []
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
            
            if entity == "activity":
                response = self.client.request_activity(**filters)
            elif entity == "assay":
                response = self.client.request_assay(**filters)
            elif entity == "target":
                response = self.client.request_target(**filters)
            elif entity == "document":
                response = self.client.request_document(**filters)
            elif entity == "testitem":
                response = self.client.request_molecule(**filters)

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
                # Trim if we got slightly more (unlikely with correct batch size but safe)
                records = records[:total_limit]
                break

            # Check for next
            if not self.paginator.has_more(response):
                break
            
            # Simple offset increment if has_more is true but paginator logic says next_marker is complicated
            # If ChemblPaginator.has_more returns true, we assume there are more items.
            # We increment offset.
            offset += current_batch_size
            
            # Safety break for large datasets if needed or check total count
            # meta = self.parser.extract_metadata(response)
            # total = meta.get("total_count", 0)
            # if offset >= total: break
            
        return pd.DataFrame(records)

