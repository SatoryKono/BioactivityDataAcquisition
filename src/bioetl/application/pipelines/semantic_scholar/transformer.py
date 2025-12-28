"""Semantic Scholar Publication Transformer.

Transforms Semantic Scholar API responses to Silver layer format.
Maps S2 paper fields to SemanticScholarPaper entity.

API Reference: https://api.semanticscholar.org/api-docs/graph
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import SemanticScholarPaper
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class S2PublicationTransformer(BaseTransformer):
    """Transformer for Semantic Scholar paper records.

    Maps S2 API response fields to SemanticScholarPaper entity:
    - paperId → semantic_scholar_id (primary key, 40-char hex)
    - externalIds.DOI → doi (lowercase)
    - externalIds.PubMed → pmid (integer)
    - title → title
    - authors[].name → authors (list[str])
    - venue → journal
    - year → year
    - abstract → abstract
    - citationCount → citation_count
    - influentialCitationCount → influential_citation_count
    - fieldsOfStudy → fields_of_study
    - embedding.vector → _embedding

    Content hash is computed based on semantic_scholar_id to ensure
    uniqueness even for papers without DOI.
    """

    def __init__(
        self,
        provider: str = "semantic_scholar",
        entity_type: str = "paper",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize Semantic Scholar publication transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
        )

    async def _transform_impl(
        self, context: PipelineContext, record: BronzeRecord, index: int
    ) -> SilverRecord | None:
        """Transform raw S2 API response to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from Semantic Scholar API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        """
        # Extract primary identifier (required)
        paper_id = record.get("paperId")
        if not paper_id or not isinstance(paper_id, str):
            context.logger.warning(
                "missing_paper_id",
                provider=self.provider,
                record_index=index,
            )
            return None

        # Extract business data
        business_data = self._extract_business_data(record, paper_id)

        # Generate entity ID using paper_id as primary key
        entity_id = generate_entity_id(
            record={"paper_id": paper_id},
            provider=self.provider,
            id_field="paper_id",
        )

        # Content hash based on semantic_scholar_id (stable even without DOI)
        content_hash = self.compute_content_hash(
            {k: v for k, v in business_data.items() if not k.startswith("_")},
            exclude_none=True,
        )

        # Create entity with lineage
        entity = self._create_entity(
            SemanticScholarPaper,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _extract_business_data(
        self, record: BronzeRecord, paper_id: str
    ) -> dict[str, Any]:
        """Extract all business fields from S2 API response.

        Args:
            record: Raw S2 API response.
            paper_id: Semantic Scholar paper ID.

        Returns:
            Dictionary of business data fields.

        """
        # Extract external identifiers safely
        external_ids_raw = record.get("externalIds")
        external_ids: dict[str, Any] = (
            external_ids_raw if isinstance(external_ids_raw, dict) else {}
        )
        doi = self._extract_doi(external_ids)
        pmid = self._extract_pmid(external_ids)

        # Extract author names
        authors_raw = record.get("authors")
        authors_list: list[dict[str, Any]] = (
            authors_raw if isinstance(authors_raw, list) else []
        )
        authors = self._extract_authors(authors_list)

        # Extract fields of study
        fields_raw = record.get("fieldsOfStudy")
        fields_list: list[str] | None = fields_raw if isinstance(fields_raw, list) else None
        fields_of_study = self._extract_fields_of_study(fields_list)

        # Extract embedding vector
        embedding_raw = record.get("embedding")
        embedding_obj: dict[str, Any] | None = (
            embedding_raw if isinstance(embedding_raw, dict) else None
        )
        embedding = self._extract_embedding(embedding_obj)

        return {
            "semantic_scholar_id": paper_id,
            "doi": doi,
            "pmid": pmid,
            "title": record.get("title"),
            "authors": authors,
            "journal": record.get("venue"),
            "year": record.get("year"),
            "abstract": record.get("abstract"),
            "citation_count": record.get("citationCount"),
            "influential_citation_count": record.get("influentialCitationCount"),
            "fields_of_study": fields_of_study,
            "_embedding": embedding,
        }

    @staticmethod
    def _extract_doi(external_ids: dict[str, Any]) -> str | None:
        """Extract and normalize DOI from externalIds.

        Args:
            external_ids: Dictionary of external identifiers.

        Returns:
            Lowercase DOI string or None if not present.

        """
        doi = external_ids.get("DOI")
        if isinstance(doi, str) and doi:
            return doi.lower().strip()
        return None

    @staticmethod
    def _extract_pmid(external_ids: dict[str, Any]) -> int | None:
        """Extract PubMed ID from externalIds.

        Args:
            external_ids: Dictionary of external identifiers.

        Returns:
            PubMed ID as integer or None if not present/invalid.

        """
        pmid = external_ids.get("PubMed")
        if pmid is None:
            return None

        # Handle both string and integer formats
        if isinstance(pmid, int):
            return pmid
        if isinstance(pmid, str) and pmid.isdigit():
            return int(pmid)
        return None

    @staticmethod
    def _extract_authors(authors_list: list[dict[str, Any]]) -> list[str]:
        """Extract author names from authors list.

        Args:
            authors_list: List of author objects with 'name' field.

        Returns:
            List of author name strings.

        """
        names = []
        for author in authors_list:
            if isinstance(author, dict):
                name = author.get("name")
                if name and isinstance(name, str):
                    names.append(name.strip())
        return names

    @staticmethod
    def _extract_fields_of_study(fields_list: list[str] | None) -> list[str]:
        """Extract and normalize fields of study.

        Args:
            fields_list: List of field names.

        Returns:
            List of normalized field names.

        """
        if not fields_list:
            return []
        return [f.strip() for f in fields_list if isinstance(f, str) and f.strip()]

    @staticmethod
    def _extract_embedding(embedding_obj: dict[str, Any] | None) -> list[float]:
        """Extract embedding vector from embedding object.

        Args:
            embedding_obj: Embedding object with 'vector' field.

        Returns:
            List of float values (768-dim SPECTER vector) or empty list.

        """
        if not embedding_obj or not isinstance(embedding_obj, dict):
            return []

        vector = embedding_obj.get("vector")
        if not vector or not isinstance(vector, list):
            return []

        # Ensure all values are floats
        return [float(v) for v in vector if isinstance(v, (int, float))]
