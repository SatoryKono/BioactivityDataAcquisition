import pandas as pd
from typing import Any, Iterator

from bioetl.clients.chembl.contracts import ChemblDataClientABC
from bioetl.clients.chembl.paginator import ChemblPaginator
from bioetl.clients.chembl.response_parser import ChemblResponseParser
from bioetl.clients.chembl.request_builder import ChemblRequestBuilder


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
        # We also need access to builder if we want to rebuild URLs for pagination
        # But usually client methods return one page or we control the loop here.
        # Let's assume we use client's specific methods to get first page, then iterate.
        # However, the client methods in current ABC return `Any` (response dict).
        # So we implement pagination loop here.

    def get_release_version(self) -> str:
        meta = self.client.metadata()
        # Assuming structure: {"chembl_release": "chembl_34", ...}
        return meta.get("chembl_release", "unknown")

    def extract_all(self, entity: str, **filters: Any) -> pd.DataFrame:
        """
        Extract all records for an entity.
        """
        records = []
        offset = 0
        
        # Get request builder from client? No, client abstracts it.
        # We need to modify filters for pagination.
        
        while True:
            filters["offset"] = offset
            filters["limit"] = self.batch_size
            
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
            else:
                raise ValueError(f"Unknown entity: {entity}")
            
            batch_records = self.parser.parse(response)
            if not batch_records:
                break
                
            records.extend(batch_records)
            
            # Check for next
            if not self.paginator.has_more(response):
                break
            
            # Simple offset increment if has_more is true but paginator logic says next_marker is complicated
            # If ChemblPaginator.has_more returns true, we assume there are more items.
            # We increment offset.
            offset += self.batch_size
            
            # Safety break for large datasets if needed or check total count
            # meta = self.parser.extract_metadata(response)
            # total = meta.get("total_count", 0)
            # if offset >= total: break
            
        return pd.DataFrame(records)

