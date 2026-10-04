"""PubMed MeSH enricher for chembl_publication_term composition wiring."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405 - parse-error type only
from collections.abc import Sequence
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, cast

import defusedxml.ElementTree as defused_ET

from bioetl.application.core.publication_term_runtime import (
    mesh_terms_from_pubmed_headings,
    publication_pubmed_id,
)
from bioetl.composition.providers._registration_biblio_adapters import (
    _build_pubmed_adapter_from_settings,
)
from bioetl.composition.providers._registration_contracts import (
    resolve_provider_assembly_support,
)
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderSettingsProtocol
    from bioetl.composition.providers._registration_contracts import (
        ProviderAssemblySupport,
    )
    from bioetl.domain.ports import FilterableDataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "PubMedPublicationTermPayloadEnricher",
    "create_pubmed_publication_term_enricher",
    "parse_pubmed_mesh_xml",
]


def parse_pubmed_mesh_xml(
    xml_text: str,
) -> tuple[list[dict[str, object]], list[str]]:
    """Parse MeshHeadingList and KeywordList from a PubMed efetch XML payload."""
    try:
        root = defused_ET.fromstring(xml_text)
    except (
        ET.ParseError,
        getattr(defused_ET, "EntitiesForbidden", ET.ParseError),
    ):
        return [], []

    headings: list[dict[str, object]] = []
    for heading in root.findall(".//MeshHeading"):
        descriptor = heading.find("DescriptorName")
        if descriptor is None:
            continue
        name = (descriptor.text or "").strip()
        if not name:
            continue
        qualifiers: list[dict[str, str]] = []
        for qualifier in heading.findall("QualifierName"):
            qualifier_name = (qualifier.text or "").strip()
            if qualifier_name:
                qualifiers.append({"name": qualifier_name})
        headings.append(
            {
                "descriptor_name": name,
                "descriptor_ui": descriptor.get("UI"),
                "qualifiers": qualifiers,
            }
        )

    keywords: list[str] = []
    for keyword in root.findall(".//Keyword"):
        text = (keyword.text or "").strip()
        if text:
            keywords.append(text)
    return headings, keywords


def pubmed_term_payload(record: BronzeRecord) -> tuple[object, object]:
    """Prefer structured PubMed fields, then ``_raw_xml`` MeshHeadingList."""
    headings = record.get("mesh_headings")
    keywords = record.get("keywords")
    raw_xml = record.get("_raw_xml")
    xml_headings: object = None
    xml_keywords: object = None
    if isinstance(raw_xml, str) and raw_xml.strip():
        xml_headings, xml_keywords = parse_pubmed_mesh_xml(raw_xml)
    if not headings:
        headings = xml_headings
    if not keywords:
        keywords = xml_keywords
    return headings, keywords


def _as_pmid(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value) if value > 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _resolve_pubmed_email(
    settings: ProviderSettingsProtocol | None,
    pipeline_config: PipelineYamlConfig | None,
) -> str | None:
    if pipeline_config is not None:
        source = getattr(pipeline_config, "source", None)
        raw_email = getattr(source, "email", None) if source is not None else None
        if isinstance(raw_email, str) and raw_email.strip():
            return raw_email.strip()
    default_email = (
        None if settings is None else getattr(settings, "default_email", None)
    )
    if isinstance(default_email, str) and default_email.strip():
        return default_email.strip()
    return None


class PubMedPublicationTermPayloadEnricher:
    """Attach PubMed MeSH/keywords onto ChEMBL document records via ``pubmed_id``."""

    def __init__(
        self,
        pubmed_source: FilterableDataSourcePort,
        logger: LoggerPort,
    ) -> None:
        self._pubmed_source = pubmed_source
        self._logger = logger

    async def enrich_many(
        self, records: Sequence[BronzeRecord]
    ) -> Sequence[BronzeRecord]:
        pmids: list[str] = []
        seen: set[str] = set()
        for record in records:
            pmid = publication_pubmed_id(record)
            if pmid is None or pmid in seen:
                continue
            seen.add(pmid)
            pmids.append(pmid)
        if not pmids:
            return list(records)

        pubmed_by_pmid: dict[str, BronzeRecord] = {}
        try:
            async with AsyncExitStack() as stack:
                enter = getattr(self._pubmed_source, "__aenter__", None)
                if callable(enter):
                    await stack.enter_async_context(self._pubmed_source)
                async for pubmed_record in self._pubmed_source.fetch_filtered(
                    entity_type="publication",
                    filter_ids=sorted(pmids),
                    filter_field="pmid",
                    limit=len(pmids),
                ):
                    pmid = _as_pmid(pubmed_record.get("pmid"))
                    if pmid is not None:
                        pubmed_by_pmid[pmid] = pubmed_record
        except Exception as exc:
            self._logger.warning(
                "publication_term_pubmed_enrichment_failed",
                error=str(exc),
                pmid_count=len(pmids),
            )
            return list(records)

        enriched: list[BronzeRecord] = []
        for record in records:
            pmid = publication_pubmed_id(record)
            matched_pubmed_record = (
                pubmed_by_pmid.get(pmid) if pmid is not None else None
            )
            if matched_pubmed_record is None:
                enriched.append(record)
                continue
            headings, keywords = pubmed_term_payload(matched_pubmed_record)
            mesh_terms, keyword_terms = mesh_terms_from_pubmed_headings(
                headings, keywords
            )
            if not mesh_terms and not keyword_terms:
                enriched.append(record)
                continue
            attached = dict(record)
            if mesh_terms:
                attached["mesh_terms"] = mesh_terms
            if keyword_terms:
                attached["keywords"] = keyword_terms
            enriched.append(attached)
        return enriched


def create_pubmed_publication_term_enricher(
    *,
    settings: ProviderSettingsProtocol,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    assembly_support: ProviderAssemblySupport | None = None,
    pipeline_config: PipelineYamlConfig | None = None,
) -> PubMedPublicationTermPayloadEnricher | None:
    """Build a PubMed enricher, or skip when email/adapter assembly is unavailable."""
    email = _resolve_pubmed_email(settings, pipeline_config)
    if email is None:
        logger.warning(
            "publication_term_pubmed_enricher_skipped",
            reason="missing_pubmed_email",
        )
        return None
    try:
        support = resolve_provider_assembly_support(assembly_support)
        http_client = support.create_http_client(
            "pubmed", settings, metrics=metrics, logger=logger
        )
        adapter = _build_pubmed_adapter_from_settings(
            adapter_cls=PubMedAdapter,
            http_client=cast("UnifiedHTTPClient", http_client),
            logger=logger,
            settings=settings,
            email=email,
            metrics=metrics,
        )
    except Exception as exc:
        logger.warning(
            "publication_term_pubmed_enricher_unavailable",
            error=str(exc),
        )
        return None
    return PubMedPublicationTermPayloadEnricher(
        pubmed_source=adapter,
        logger=logger,
    )
