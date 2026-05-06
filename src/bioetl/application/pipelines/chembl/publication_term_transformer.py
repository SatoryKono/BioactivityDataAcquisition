# mypy: disable-error-code="arg-type"
"""ChEMBL Publication Term Transformer.

Transforms Publication records to extract and flatten associated terms.
This is a derived entity transformer - it extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

Uses declarative field_specs DSL for mapping.

.. versionchanged:: 2.0.0
    Renamed from document_term_transformer to publication_term_transformer (ADR-024).
"""

from __future__ import annotations

__all__ = ["PublicationTermTransformer"]

from functools import partial
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.entity_id import compute_publication_term_entity_id
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import ChemblPublicationTerm
from bioetl.domain.types import GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


class PublicationTermTransformer(BaseChemblTransformer):
    """Flatten publication terms from ChEMBL publication records."""

    entity_class = ChemblPublicationTerm
    primary_id_field = "publication_id"

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate publication-term payload for application finalization."""
        del context, index
        prepared_record = _prepare_publication_term_record(record)
        primary_id = cast(
            "PrimaryId",
            self._get_required_field(prepared_record, self.primary_id_field),
        )
        business_data = self._extract_business_data(prepared_record, primary_id)
        if business_data is None or not _has_extractable_publication_term(
            business_data
        ):
            return None
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        entity_id = _resolve_publication_term_entity_id(self, normalized_business_data)
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=normalized_business_data,
            build_silver_record=partial(_build_publication_term_silver_record, self),
            apply_structural_policy=self._apply_structural_policy,
            apply_silver_filter=self._apply_silver_filter,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Override base implementation to use composite entity_id."""
        prepared_record = _prepare_publication_term_record(record)
        primary_id = cast(
            "PrimaryId",
            self._get_required_field(prepared_record, self.primary_id_field),
        )
        business_data = self._extract_business_data(prepared_record, primary_id)
        if business_data is None or not _has_extractable_publication_term(
            business_data
        ):
            return None
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        entity_id = _resolve_publication_term_entity_id(
            self,
            normalized_business_data,
        )
        content_hash = self.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )
        silver_record = _build_publication_term_silver_record(
            self,
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )
        return cast(
            "SilverRecord",
            normalizer.project_normalization_findings(
                silver_record,
                context=context,
                index=index,
            ),
        )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> GoldRecord:
        """Extract one normalized publication-term payload from the input."""
        if "term" in record and "term_type" in record:
            raw_term = record.get("term")
            raw_term_type = record.get("term_type")
            raw_mesh_id = record.get("mesh_id")
            raw_qualifier = record.get("qualifier")

            term = str(raw_term).strip() if raw_term else ""
            term_type = str(raw_term_type).strip() if raw_term_type else ""
            mesh_id = str(raw_mesh_id).strip() if raw_mesh_id else None
            qualifier = str(raw_qualifier).strip() if raw_qualifier else None

            return {
                "publication_id": str(record.get("publication_id", primary_id)),
                "term": term,
                "term_type": term_type,
                "mesh_id": mesh_id,
                "qualifier": qualifier,
            }

        terms = list(self.extract_terms_from_document(record, str(primary_id)))
        if not terms:
            return {
                "publication_id": str(record.get("publication_id", primary_id)),
                "term": "",
                "term_type": "",
                "mesh_id": None,
                "qualifier": None,
            }
        return terms[0]

    def extract_terms_from_document(
        self, record: BronzeRecord, publication_id: str
    ) -> list[GoldRecord]:
        """Extract every flattened term payload from one publication record."""
        terms: list[GoldRecord] = []

        raw_mesh_terms = record.get("mesh_terms")
        mesh_terms: list[Any] = (  # Any: untyped ChEMBL API JSON list elements
            raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
        )
        for mesh in mesh_terms:
            if not isinstance(mesh, dict):
                continue

            mesh_heading = mesh.get("mesh_heading")
            if mesh_heading:
                terms.append(
                    self._create_term_data(
                        publication_id=publication_id,
                        term=mesh_heading,
                        term_type="MESH_HEADING",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=mesh.get("mesh_qualifier"),
                    )
                )

            mesh_qualifier = mesh.get("mesh_qualifier")
            if mesh_qualifier:
                terms.append(
                    self._create_term_data(
                        publication_id=publication_id,
                        term=mesh_qualifier,
                        term_type="MESH_QUALIFIER",
                        mesh_id=mesh.get("mesh_id"),
                        qualifier=None,
                    )
                )

        raw_keywords = record.get("keywords")
        keywords: list[Any] = (  # Any: untyped ChEMBL API JSON
            raw_keywords if isinstance(raw_keywords, list) else []
        )
        for keyword in keywords:
            if isinstance(keyword, str):
                stripped = keyword.strip()
                if stripped:
                    terms.append(
                        self._create_term_data(
                            publication_id=publication_id,
                            term=stripped,
                            term_type="KEYWORD",
                            mesh_id=None,
                            qualifier=None,
                        )
                    )

        return terms

    def _create_term_data(
        self,
        publication_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> GoldRecord:
        """Build one normalized term payload."""
        return {
            "publication_id": publication_id,
            "term": term.strip() if term else term,
            "term_type": term_type,
            "mesh_id": mesh_id,
            "qualifier": qualifier,
        }

    def compute_term_entity_id(
        self, publication_id: str, term_type: str, term: str
    ) -> str:
        """Compute the stable publication-term entity id."""
        return compute_publication_term_entity_id(publication_id, term_type, term)


def _prepare_publication_term_record(record: BronzeRecord) -> BronzeRecord:
    """Normalize legacy ChEMBL publication-term input field names."""
    if "publication_id" not in record and record.get("document_chembl_id") is not None:
        normalized_record = dict(record)
        normalized_record["publication_id"] = record.get("document_chembl_id")
        return normalized_record
    return record


def _resolve_publication_term_entity_id(
    transformer: PublicationTermTransformer,
    business_data: GoldRecord,
) -> str:
    """Resolve publication-term entity id from canonical normalized business data."""
    return transformer.compute_term_entity_id(
        publication_id=str(business_data.get("publication_id", "")),
        term_type=str(business_data.get("term_type", "")),
        term=str(business_data.get("term", "")),
    )


def _has_extractable_publication_term(business_data: GoldRecord) -> bool:
    """Return True when extracted payload contains a meaningful term row."""
    term = str(business_data.get("term", "")).strip()
    term_type = str(business_data.get("term_type", "")).strip()
    return bool(term and term_type)


def _build_publication_term_silver_record(
    transformer: PublicationTermTransformer,
    context: PipelineContext,
    entity_id: str,
    content_hash: str,
    index: int,
    business_data: GoldRecord,
) -> SilverRecord:
    """Build a finalized Silver record from normalized publication-term data."""
    entity = transformer._create_entity(
        transformer.entity_class,
        context,
        entity_id=entity_id,
        content_hash=content_hash,
        index=index,
        **business_data,
    )
    return cast("SilverRecord", transformer.entity_to_silver_record(entity))
