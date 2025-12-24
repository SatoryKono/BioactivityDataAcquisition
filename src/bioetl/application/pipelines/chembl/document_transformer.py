"""ChEMBL Document Transformer.

Transforms Bronze records to Silver format (Document entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Document
from bioetl.domain.transformations import generate_entity_id, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class DocumentTransformer(BaseTransformer):
    """Transforms ChEMBL bronze document records to silver."""

    def __init__(self, provider: str = "chembl"):
        """Initialize ChEMBL document transformer.

        Args:
            provider: Data provider identifier.

        """
        super().__init__(provider)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL document to normalized format using Domain Entity."""
        # Validate required field
        document_chembl_id = self._get_required_field(record, "document_chembl_id")

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

        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Create entity using helper method
        entity = self._create_entity(
            Document,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # Convert Entity to SilverRecord for storage
        return cast("SilverRecord", self.entity_to_silver_record(entity))
