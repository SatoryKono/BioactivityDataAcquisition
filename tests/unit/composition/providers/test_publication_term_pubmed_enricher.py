# pyright: reportArgumentType=false
"""Unit tests for PubMed MeSH enricher used by chembl_publication_term."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.providers.publication_term_pubmed_enricher import (
    PubMedPublicationTermPayloadEnricher,
    create_pubmed_publication_term_enricher,
    parse_pubmed_mesh_xml,
    pubmed_term_payload,
)

pytestmark = pytest.mark.unit

_SAMPLE_PUBMED_XML = """
<PubmedArticle>
  <MedlineCitation>
    <PMID>17827018</PMID>
    <MeshHeadingList>
      <MeshHeading>
        <DescriptorName UI="D000114" MajorTopicYN="N">Acetylene</DescriptorName>
        <QualifierName UI="Q000494" MajorTopicYN="Y">pharmacology</QualifierName>
        <QualifierName UI="Q000627" MajorTopicYN="N">chemistry</QualifierName>
      </MeshHeading>
      <MeshHeading>
        <DescriptorName UI="D006801" MajorTopicYN="Y">Humans</DescriptorName>
      </MeshHeading>
    </MeshHeadingList>
    <KeywordList>
      <Keyword>bioactivity</Keyword>
    </KeywordList>
  </MedlineCitation>
</PubmedArticle>
"""


def test_parse_pubmed_mesh_xml_extracts_headings_qualifiers_and_keywords() -> None:
    headings, keywords = parse_pubmed_mesh_xml(_SAMPLE_PUBMED_XML)

    assert headings[0]["descriptor_name"] == "Acetylene"
    assert headings[0]["descriptor_ui"] == "D000114"
    assert headings[0]["qualifiers"] == [
        {"name": "pharmacology"},
        {"name": "chemistry"},
    ]
    assert headings[1]["descriptor_name"] == "Humans"
    assert keywords == ["bioactivity"]


def test_parse_pubmed_mesh_xml_returns_empty_on_invalid_xml() -> None:
    headings, keywords = parse_pubmed_mesh_xml("<not-xml")
    assert headings == []
    assert keywords == []


def test_pubmed_term_payload_prefers_structured_headings() -> None:
    headings, keywords = pubmed_term_payload(
        {
            "mesh_headings": [
                {"descriptor_name": "Neoplasms", "descriptor_ui": "D009369"}
            ],
            "keywords": ["tumor"],
            "_raw_xml": _SAMPLE_PUBMED_XML,
        }
    )
    assert headings[0]["descriptor_name"] == "Neoplasms"
    assert keywords == ["tumor"]


class _PubmedSource:
    def __init__(self, records: list[dict[str, object]]) -> None:
        self._records = records
        self.calls: list[dict[str, object]] = []

    async def fetch_filtered(self, **kwargs: object):
        self.calls.append(kwargs)
        for record in self._records:
            yield record


@pytest.mark.asyncio
async def test_enrich_many_attaches_mesh_terms_from_raw_xml() -> None:
    pubmed = _PubmedSource([{"pmid": "17827018", "_raw_xml": _SAMPLE_PUBMED_XML}])
    enricher = PubMedPublicationTermPayloadEnricher(
        pubmed_source=pubmed,  # type: ignore[arg-type]
        logger=MagicMock(),
    )
    chembl_doc = {
        "publication_id": "CHEMBL1137491",
        "pubmed_id": 17827018,
        "title": "No mesh on ChEMBL /document",
    }

    enriched = await enricher.enrich_many([chembl_doc])

    assert pubmed.calls[0]["filter_field"] == "pmid"
    assert pubmed.calls[0]["filter_ids"] == ["17827018"]
    attached = enriched[0]
    assert attached["mesh_terms"][0]["mesh_heading"] == "Acetylene"
    assert attached["mesh_terms"][0]["mesh_id"] == "D000114"
    assert attached["keywords"] == ["bioactivity"]


@pytest.mark.asyncio
async def test_enrich_many_enters_pubmed_source_context() -> None:
    class _ContextPubmed(_PubmedSource):
        def __init__(self) -> None:
            super().__init__(
                [
                    {
                        "pmid": "1",
                        "mesh_headings": [
                            {"descriptor_name": "Humans", "descriptor_ui": "D006801"}
                        ],
                    }
                ]
            )
            self.entered = False

        async def __aenter__(self):
            self.entered = True
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def fetch_filtered(self, **kwargs: object):
            if not self.entered:
                raise RuntimeError(
                    "UnifiedHTTPClient must be used within async context manager"
                )
            async for record in super().fetch_filtered(**kwargs):
                yield record

    pubmed = _ContextPubmed()
    enricher = PubMedPublicationTermPayloadEnricher(
        pubmed_source=pubmed,  # type: ignore[arg-type]
        logger=MagicMock(),
    )
    enriched = await enricher.enrich_many(
        [{"publication_id": "CHEMBL1", "pubmed_id": "1"}]
    )
    assert pubmed.entered is True
    assert enriched[0]["mesh_terms"][0]["mesh_heading"] == "Humans"


@pytest.mark.asyncio
async def test_enrich_many_keeps_original_when_pubmed_fetch_fails() -> None:
    class _FailingPubmed:
        async def fetch_filtered(self, **kwargs: object):
            raise RuntimeError("ncbi down")
            yield {}  # pragma: no cover

    logger = MagicMock()
    enricher = PubMedPublicationTermPayloadEnricher(
        pubmed_source=_FailingPubmed(),  # type: ignore[arg-type]
        logger=logger,
    )
    original = {"publication_id": "CHEMBL1", "pubmed_id": "1"}

    enriched = await enricher.enrich_many([original])

    assert enriched == [original]
    logger.warning.assert_called_once()


def test_create_enricher_skips_without_email() -> None:
    logger = MagicMock()
    settings = MagicMock()
    settings.default_email = None

    result = create_pubmed_publication_term_enricher(
        settings=settings,
        logger=logger,
        pipeline_config=None,
    )

    assert result is None
    logger.warning.assert_called_once()
    assert logger.warning.call_args.kwargs["reason"] == "missing_pubmed_email"


@pytest.mark.parametrize("pipeline_email", [None, " pipeline@example.test "])
def test_create_enricher_wires_resolved_email_and_provider_support(
    monkeypatch: pytest.MonkeyPatch, pipeline_email: str | None
) -> None:
    from types import SimpleNamespace

    import bioetl.composition.providers.publication_term_pubmed_enricher as module

    settings = MagicMock(default_email=" default@example.test ")
    config = SimpleNamespace(source=SimpleNamespace(email=pipeline_email))
    support = MagicMock()
    adapter = _PubmedSource([])
    build_adapter = MagicMock(return_value=adapter)
    monkeypatch.setattr(module, "resolve_provider_assembly_support", lambda _: support)
    monkeypatch.setattr(module, "_build_pubmed_adapter_from_settings", build_adapter)
    logger, metrics = MagicMock(), MagicMock()

    enricher = create_pubmed_publication_term_enricher(
        settings=settings, logger=logger, metrics=metrics, pipeline_config=config
    )

    assert isinstance(enricher, PubMedPublicationTermPayloadEnricher)
    assert enricher._pubmed_source is adapter
    support.create_http_client.assert_called_once_with(
        "pubmed", settings, metrics=metrics, logger=logger
    )
    build_adapter.assert_called_once_with(
        adapter_cls=module.PubMedAdapter,
        http_client=support.create_http_client.return_value,
        logger=logger,
        settings=settings,
        email="pipeline@example.test" if pipeline_email else "default@example.test",
        metrics=metrics,
    )
    logger.warning.assert_not_called()


def test_create_enricher_reports_adapter_assembly_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.composition.providers.publication_term_pubmed_enricher as module

    settings = MagicMock(default_email="owner@example.test")
    support = MagicMock()
    support.create_http_client.side_effect = RuntimeError("adapter unavailable")
    monkeypatch.setattr(module, "resolve_provider_assembly_support", lambda _: support)
    logger = MagicMock()

    assert (
        create_pubmed_publication_term_enricher(settings=settings, logger=logger)
        is None
    )
    logger.warning.assert_called_once_with(
        "publication_term_pubmed_enricher_unavailable", error="adapter unavailable"
    )
