"""ChEMBL Document Transformer.

Transforms Bronze records to Silver format (Document entity inflation).
Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.field_specs import (
    FieldGroup,
    int_fields,
    map_field_groups,
    pmid_fields,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Document

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Declarative field groups for Document entity
_PUBLICATION_IDS = FieldGroup(
    name="publication_ids",
    fields=(
        *pmid_fields("pubmed_id"),
        *simple_fields("doi", "patent_id"),
    ),
)

_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=simple_fields("title", "authors", "abstract", "doc_type"),
)

_JOURNAL_INFO = FieldGroup(
    name="journal_info",
    fields=(
        *simple_fields(
            "journal",
            "journal_full_title",
            "volume",
            "issue",
            "first_page",
            "last_page",
        ),
        *int_fields("year"),
    ),
)

_SOURCE_INFO = FieldGroup(
    name="source_info",
    fields=int_fields("src_id"),
)

# All field groups for Document entity
_DOCUMENT_GROUPS: tuple[FieldGroup, ...] = (
    _PUBLICATION_IDS,
    _CORE_METADATA,
    _JOURNAL_INFO,
    _SOURCE_INFO,
)


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
        # Extract base fields using declarative DSL
        data = {
            "document_chembl_id": str(primary_id),
            **map_field_groups(record, _DOCUMENT_GROUPS),
        }

        # Hash PII field (RULES.md §5.4)
        # ChEMBL authors is a single string, not a list
        if data.get("authors"):
            data["authors"] = self.hash_pii_value(data["authors"])

        return data
