"""ChEMBL Document Transformer.

Transforms Bronze records to Silver format (Document entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Document
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class DocumentTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze document records to silver."""

    entity_class = Document
    primary_id_field = "document_chembl_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Document business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated document_chembl_id value.

        Returns:
            Dictionary of Document business fields.

        """
        return {
            # Primary identifier
            "document_chembl_id": str(primary_id),
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
