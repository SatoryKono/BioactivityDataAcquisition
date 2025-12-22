"""ChEMBL Document Transformer.

Transforms Bronze records to Silver format (Document entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.entities import Document
from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    safe_int,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class DocumentTransformer:
    """Transforms ChEMBL bronze document records to silver."""

    def __init__(self, provider: str = "chembl"):
        self.provider = provider

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL document to normalized format using Domain Entity."""
        document_chembl_id = record.get("document_chembl_id")

        if not document_chembl_id:
            return None

        try:
            entity_id = generate_entity_id(
                record={"document_chembl_id": str(document_chembl_id)},
                provider=self.provider,
                id_field="document_chembl_id",
            )

            business_data: dict[str, Any] = {
                # Primary identifier
                "document_chembl_id": str(document_chembl_id),
                # Publication identifiers
                "pubmed_id": safe_int(record.get("pubmed_id")),
                "doi": record.get("doi"),
                "patent_id": record.get("patent_id"),
                # Core metadata
                "title": record.get("title"),
                "authors": record.get("authors"),
                "abstract": record.get("abstract"),
                "doc_type": record.get("doc_type"),
                # Journal information
                "journal": record.get("journal"),
                "journal_full_title": record.get("journal_full_title"),
                "year": safe_int(record.get("year")),
                "volume": record.get("volume"),
                "issue": record.get("issue"),
                "first_page": record.get("first_page"),
                "last_page": record.get("last_page"),
                # Source information
                "src_id": safe_int(record.get("src_id")),
            }

            content_hash = generate_content_hash(
                business_data,
                self.provider,
                exclude_none=True,
            )

            entity = Document(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )

        except ValueError as e:
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                document_chembl_id=document_chembl_id,
            )
            return None

        # Convert Entity to SilverRecord for storage
        silver_record = entity.__dict__.copy()

        # Handle lineage fields renaming and formatting
        silver_record["_run_id"] = str(silver_record.pop("run_id"))
        silver_record["_run_type"] = str(silver_record.pop("run_type").value)
        silver_record["_source_batch_id"] = str(silver_record.pop("source_batch_id"))
        silver_record["_ingestion_ts"] = silver_record.pop("ingestion_ts").isoformat()

        return cast("SilverRecord", silver_record)
