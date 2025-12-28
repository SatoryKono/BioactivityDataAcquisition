"""OpenAlex Work Transformer.

Transforms pre-processed OpenAlex work records (from adapter) into Silver format.
See: https://docs.openalex.org/api-entities/works
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import OpenAlexWork
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class OpenAlexWorkTransformer(BaseTransformer):
    """Transformer for OpenAlex work records.

    Expects records pre-processed by OpenAlexAdapter (DOI normalized,
    abstract reconstructed, authors extracted).
    """

    def __init__(
        self,
        provider: str = "openalex",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize OpenAlex work transformer.

        Args:
            provider: Data provider identifier.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider,
            entity_type="work",
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform OpenAlex work record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Pre-processed record from OpenAlexAdapter.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If OpenAlexWork entity validation fails.

        """
        # Step 1: Validate required fields
        openalex_id: str = str(self._get_required_field(record, "openalex_id"))
        display_name: str = str(self._get_required_field(record, "display_name"))
        work_type: str = str(record.get("type", "other"))

        # Step 2: Build business data
        business_data = self._build_business_data(record, openalex_id, display_name, work_type)

        # Step 3: Generate entity_id
        entity_id = generate_entity_id(
            record={"openalex_id": openalex_id},
            provider=self.provider,
            id_field="openalex_id",
        )

        # Step 4: Compute content_hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity
        entity = self._create_entity(
            OpenAlexWork,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _build_business_data(
        self,
        record: BronzeRecord,
        openalex_id: str,
        display_name: str,
        work_type: str,
    ) -> dict[str, Any]:
        """Build business data dictionary from OpenAlex record.

        Args:
            record: Raw record from OpenAlex.
            openalex_id: Validated OpenAlex ID.
            display_name: Validated title.
            work_type: Work type.

        Returns:
            Business data dictionary for entity creation.

        """
        # Primary location (flattened)
        primary_location = self._flatten_primary_location(record)

        # Open access info (flattened)
        oa_info = self._flatten_open_access(record)

        # Primary topic (flattened)
        topic_info = self._flatten_primary_topic(record)

        # Bibliographic info
        biblio = self._flatten_biblio(record)

        # IDs from ids object
        ids: dict[str, Any] = cast(dict[str, Any], record.get("ids", {}) or {})

        return {
            # Primary fields
            "openalex_id": openalex_id,
            "display_name": display_name,
            "type": work_type,
            # External identifiers
            "doi": record.get("doi"),
            "pmid": record.get("pmid") or self._extract_pmid(ids),
            "pmcid": self._extract_id(ids, "pmcid"),
            "mag_id": self._extract_id(ids, "mag"),
            # Publication info
            "publication_year": record.get("publication_year"),
            "publication_date": record.get("publication_date"),
            "language": record.get("language"),
            # Primary location
            **primary_location,
            # Open access
            **oa_info,
            # Citations
            "cited_by_count": record.get("cited_by_count"),
            "cited_by_percentile_year": self._extract_nested(
                record, "cited_by_percentile_year.value"
            ),
            "referenced_works_count": record.get("referenced_works_count"),
            # Bibliographic
            **biblio,
            # Flags
            "is_retracted": record.get("is_retracted"),
            "is_paratext": record.get("is_paratext"),
            "has_fulltext": record.get("has_fulltext"),
            "fulltext_origin": record.get("fulltext_origin"),
            # Abstract (already reconstructed by adapter)
            "abstract": record.get("abstract"),
            "abstract_inverted_index": self._serialize_inverted_index(record),
            # Primary topic
            **topic_info,
            # Aggregated fields
            "keywords": self._extract_keywords(record),
            "sustainable_development_goals": self._extract_sdgs(record),
            "grants": self._extract_grants(record),
            "indexed_in": self._extract_indexed_in(record),
            "related_works": self._extract_related_works(record),
            # Metrics
            "fwci": record.get("fwci"),
            "countries_distinct_count": record.get("countries_distinct_count"),
            "institutions_distinct_count": record.get("institutions_distinct_count"),
            # Corresponding authors
            "corresponding_author_ids": self._extract_corresponding_authors(record),
            "corresponding_institution_ids": self._extract_corresponding_institutions(
                record
            ),
            # Convenience fields (already extracted by adapter)
            "authors": record.get("authors", []),
            "institutions": record.get("institutions", []),
            "concept_names": record.get("concept_names", []),
        }

    def _flatten_primary_location(self, record: BronzeRecord) -> dict[str, Any]:
        """Flatten primary_location nested structure.

        Args:
            record: OpenAlex work record.

        Returns:
            Flattened primary location fields.

        """
        location: dict[str, Any] = cast(
            dict[str, Any], record.get("primary_location") or {}
        )
        source: dict[str, Any] = cast(dict[str, Any], location.get("source") or {})

        return {
            "primary_location_source_id": self._extract_id_from_url(
                cast(str | None, source.get("id"))
            ),
            "primary_location_source_name": source.get("display_name"),
            "primary_location_source_issn": source.get("issn_l"),
            "primary_location_source_type": source.get("type"),
            "primary_location_landing_page": location.get("landing_page_url"),
            "primary_location_pdf_url": location.get("pdf_url"),
            "primary_location_version": location.get("version"),
            "primary_location_license": location.get("license"),
        }

    def _flatten_open_access(self, record: BronzeRecord) -> dict[str, Any]:
        """Flatten open_access nested structure.

        Args:
            record: OpenAlex work record.

        Returns:
            Flattened open access fields.

        """
        oa: dict[str, Any] = cast(dict[str, Any], record.get("open_access") or {})

        return {
            "is_oa": oa.get("is_oa"),
            "oa_status": oa.get("oa_status"),
            "oa_url": oa.get("oa_url"),
            "any_repository_has_fulltext": oa.get("any_repository_has_fulltext"),
        }

    def _flatten_primary_topic(self, record: BronzeRecord) -> dict[str, Any]:
        """Flatten primary_topic nested structure.

        Args:
            record: OpenAlex work record.

        Returns:
            Flattened primary topic fields.

        """
        topic: dict[str, Any] = cast(
            dict[str, Any], record.get("primary_topic") or {}
        )
        if not topic:
            return {
                "primary_topic_id": None,
                "primary_topic_name": None,
                "primary_topic_score": None,
                "primary_topic_subfield": None,
                "primary_topic_field": None,
                "primary_topic_domain": None,
            }

        subfield: dict[str, Any] = cast(dict[str, Any], topic.get("subfield") or {})
        field_info: dict[str, Any] = cast(dict[str, Any], topic.get("field") or {})
        domain: dict[str, Any] = cast(dict[str, Any], topic.get("domain") or {})

        return {
            "primary_topic_id": self._extract_id_from_url(
                cast(str | None, topic.get("id"))
            ),
            "primary_topic_name": topic.get("display_name"),
            "primary_topic_score": topic.get("score"),
            "primary_topic_subfield": subfield.get("display_name"),
            "primary_topic_field": field_info.get("display_name"),
            "primary_topic_domain": domain.get("display_name"),
        }

    def _flatten_biblio(self, record: BronzeRecord) -> dict[str, Any]:
        """Flatten biblio nested structure.

        Args:
            record: OpenAlex work record.

        Returns:
            Flattened bibliographic fields.

        """
        biblio: dict[str, Any] = cast(dict[str, Any], record.get("biblio") or {})

        return {
            "biblio_volume": biblio.get("volume"),
            "biblio_issue": biblio.get("issue"),
            "biblio_first_page": biblio.get("first_page"),
            "biblio_last_page": biblio.get("last_page"),
        }

    def _extract_id_from_url(self, url: str | None) -> str | None:
        """Extract OpenAlex ID from full URL.

        Args:
            url: Full URL like https://openalex.org/W2741809807

        Returns:
            ID part (e.g., W2741809807) or None.

        """
        if not url:
            return None
        return url.split("/")[-1] if "/" in url else url

    def _extract_id(self, ids: dict[str, Any], key: str) -> str | None:
        """Extract and clean ID from ids object.

        Args:
            ids: IDs dictionary from OpenAlex.
            key: Key to extract.

        Returns:
            Extracted ID or None.

        """
        value = ids.get(key)
        if not value:
            return None
        if isinstance(value, str) and "/" in value:
            return value.split("/")[-1]
        return str(value)

    def _extract_pmid(self, ids: dict[str, Any]) -> str | None:
        """Extract PMID from ids object.

        Args:
            ids: IDs dictionary from OpenAlex.

        Returns:
            PMID string or None.

        """
        pmid = ids.get("pmid")
        if not pmid:
            return None
        if isinstance(pmid, str):
            # Handle full URL: https://pubmed.ncbi.nlm.nih.gov/12345
            if "pubmed.ncbi.nlm.nih.gov" in pmid:
                return pmid.rstrip("/").split("/")[-1]
            return pmid
        return str(pmid)

    def _serialize_inverted_index(self, record: BronzeRecord) -> str | None:
        """Serialize abstract inverted index to JSON for forensics.

        Args:
            record: OpenAlex work record.

        Returns:
            JSON string of inverted index or None.

        """
        inverted_index = record.get("abstract_inverted_index")
        if not inverted_index:
            return None
        return json.dumps(inverted_index, ensure_ascii=False)

    def _extract_keywords(self, record: BronzeRecord) -> str | None:
        """Extract keywords as semicolon-separated string.

        Args:
            record: OpenAlex work record.

        Returns:
            Keywords joined by '; ' or None.

        """
        keywords: list[dict[str, Any]] = cast(
            list[dict[str, Any]], record.get("keywords") or []
        )
        if not keywords:
            return None
        keyword_names: list[str] = [
            str(kw.get("display_name"))
            for kw in keywords
            if kw.get("display_name")
        ]
        return "; ".join(keyword_names) if keyword_names else None

    def _extract_sdgs(self, record: BronzeRecord) -> str | None:
        """Extract Sustainable Development Goals as formatted string.

        Args:
            record: OpenAlex work record.

        Returns:
            SDGs in 'id:name:score' format joined by '; ' or None.

        """
        sdgs: list[dict[str, Any]] = cast(
            list[dict[str, Any]], record.get("sustainable_development_goals") or []
        )
        if not sdgs:
            return None
        parts: list[str] = []
        for sdg in sdgs:
            sdg_id = self._extract_id_from_url(cast(str | None, sdg.get("id")))
            name = sdg.get("display_name")
            score = sdg.get("score")
            if sdg_id and name:
                parts.append(f"{sdg_id}:{name}:{score:.2f}" if score else f"{sdg_id}:{name}")
        return "; ".join(parts) if parts else None

    def _extract_grants(self, record: BronzeRecord) -> str | None:
        """Extract grants as formatted string.

        Args:
            record: OpenAlex work record.

        Returns:
            Grants in 'funder_id:award_id' format joined by '; ' or None.

        """
        grants: list[dict[str, Any]] = cast(
            list[dict[str, Any]], record.get("grants") or []
        )
        if not grants:
            return None
        parts: list[str] = []
        for grant in grants:
            funder_id = self._extract_id_from_url(cast(str | None, grant.get("funder")))
            award_id = grant.get("award_id")
            if funder_id:
                parts.append(f"{funder_id}:{award_id}" if award_id else funder_id)
        return "; ".join(parts) if parts else None

    def _extract_indexed_in(self, record: BronzeRecord) -> str | None:
        """Extract indexed_in as semicolon-separated string.

        Args:
            record: OpenAlex work record.

        Returns:
            Indexes joined by '; ' or None.

        """
        indexed_in: list[str] = cast(list[str], record.get("indexed_in") or [])
        if not indexed_in:
            return None
        return "; ".join(indexed_in) if indexed_in else None

    def _extract_related_works(self, record: BronzeRecord) -> str | None:
        """Extract related works IDs as semicolon-separated string.

        Args:
            record: OpenAlex work record.

        Returns:
            Related work IDs joined by '; ' or None.

        """
        related: list[str] = cast(list[str], record.get("related_works") or [])
        if not related:
            return None
        ids = [self._extract_id_from_url(url) for url in related if url]
        return "; ".join(filter(None, ids)) if ids else None

    def _extract_corresponding_authors(self, record: BronzeRecord) -> str | None:
        """Extract corresponding author IDs.

        Args:
            record: OpenAlex work record.

        Returns:
            Corresponding author IDs joined by '; ' or None.

        """
        author_ids: list[str] = cast(
            list[str], record.get("corresponding_author_ids") or []
        )
        if not author_ids:
            return None
        ids = [self._extract_id_from_url(url) for url in author_ids if url]
        return "; ".join(filter(None, ids)) if ids else None

    def _extract_corresponding_institutions(self, record: BronzeRecord) -> str | None:
        """Extract corresponding institution IDs.

        Args:
            record: OpenAlex work record.

        Returns:
            Corresponding institution IDs joined by '; ' or None.

        """
        inst_ids: list[str] = cast(
            list[str], record.get("corresponding_institution_ids") or []
        )
        if not inst_ids:
            return None
        ids = [self._extract_id_from_url(url) for url in inst_ids if url]
        return "; ".join(filter(None, ids)) if ids else None
