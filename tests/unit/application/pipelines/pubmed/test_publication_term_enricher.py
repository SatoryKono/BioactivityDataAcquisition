# pyright: reportArgumentType=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.pipelines.pubmed.publication_term_enricher import PubMedPublicationTermPayloadEnricher, parse_pubmed_mesh_xml, pubmed_term_payload, _as_pmid, _unique_pmids, _attach_pubmed_terms
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


def test_parse_pubmed_mesh_xml_empty():
    headings, keywords = parse_pubmed_mesh_xml("")
    assert headings == []
    assert keywords == []

def test_parse_pubmed_mesh_xml_valid():
    xml = """
    <root>
        <MeshHeadingList>
            <MeshHeading>
                <DescriptorName UI="D000001">Descriptor</DescriptorName>
                <QualifierName>Qualifier1</QualifierName>
                <QualifierName>Qualifier2</QualifierName>
            </MeshHeading>
        </MeshHeadingList>
        <KeywordList>
            <Keyword>Key1</Keyword>
            <Keyword>Key2</Keyword>
        </KeywordList>
    </root>
    """
    headings, keywords = parse_pubmed_mesh_xml(xml)
    assert len(headings) == 1
    assert headings[0]["descriptor_name"] == "Descriptor"
    assert headings[0]["descriptor_ui"] == "D000001"
    assert headings[0]["qualifiers"] == [{"name": "Qualifier1"}, {"name": "Qualifier2"}]
    assert keywords == ["Key1", "Key2"]

def test_pubmed_term_payload():
    record = {"mesh_headings": ["heading1"], "keywords": ["key1"], "_raw_xml": "xml"}
    headings, keywords = pubmed_term_payload(record)
    assert headings == ["heading1"]
    assert keywords == ["key1"]

def test_pubmed_term_payload_xml():
    xml = """
    <root>
        <KeywordList>
            <Keyword>Key1</Keyword>
        </KeywordList>
    </root>
    """
    record = {"_raw_xml": xml}
    headings, keywords = pubmed_term_payload(record)
    assert headings == []
    assert keywords == ["Key1"]

def test_as_pmid():
    assert _as_pmid(None) is None
    assert _as_pmid(True) is None
    assert _as_pmid(False) is None
    assert _as_pmid(123) == "123"
    assert _as_pmid(-1) is None
    assert _as_pmid(" 123 ") == "123"
    assert _as_pmid("  ") is None

def test_unique_pmids():
    records = [{"pubmed_id": "1"}, {"pubmed_id": "2"}, {"pubmed_id": "1"}, {}]
    assert _unique_pmids(records) == ["1", "2"]

def test_attach_pubmed_terms():
    records = [{"pubmed_id": "1"}, {"pubmed_id": "2"}]
    pubmed_by_pmid = {"1": {"mesh_headings": [{"descriptor_name": "D1", "descriptor_ui": "UI1"}], "keywords": ["K1"]}}
    enriched = _attach_pubmed_terms(records, pubmed_by_pmid)
    assert len(enriched) == 2
    assert enriched[0] == {"pubmed_id": "1", "mesh_terms": [{"mesh_heading": "D1", "mesh_id": "UI1", "mesh_qualifier": None}], "keywords": ["K1"]}
    assert enriched[1] == {"pubmed_id": "2"}

@pytest.mark.asyncio
async def test_fetch_pubmed_records():
    source = MagicMock()
    source.__aenter__ = AsyncMock()

    async def fetch_filtered(*args, **kwargs):
        yield {"pmid": "1"}
        yield {"pmid": "2"}

    source.fetch_filtered = fetch_filtered
    logger = MagicMock()
    enricher = PubMedPublicationTermPayloadEnricher(pubmed_source=source, logger=logger)
    result = await enricher._fetch_pubmed_records(["1", "2"])
    assert result == {"1": {"pmid": "1"}, "2": {"pmid": "2"}}

@pytest.mark.asyncio
async def test_enrich_many():
    source = MagicMock()

    async def fetch_filtered(*args, **kwargs):
        yield {"pmid": "1", "keywords": ["K1"]}

    source.fetch_filtered = fetch_filtered
    logger = MagicMock()
    enricher = PubMedPublicationTermPayloadEnricher(pubmed_source=source, logger=logger)
    records = [{"pubmed_id": "1"}, {"pubmed_id": "2"}]
    result = await enricher.enrich_many(records)
    assert len(result) == 2
    assert result[0] == {"pubmed_id": "1", "keywords": ["K1"]}
    assert result[1] == {"pubmed_id": "2"}

@pytest.mark.asyncio
async def test_enrich_many_empty():
    source = MagicMock()
    logger = MagicMock()
    enricher = PubMedPublicationTermPayloadEnricher(pubmed_source=source, logger=logger)
    result = await enricher.enrich_many([])
    assert result == []

@pytest.mark.asyncio
async def test_enrich_many_error():
    source = MagicMock()

    async def fetch_filtered(*args, **kwargs):
        raise BioETLError("error")
        yield {}

    source.fetch_filtered = fetch_filtered
    logger = MagicMock()
    enricher = PubMedPublicationTermPayloadEnricher(pubmed_source=source, logger=logger)
    records = [{"pubmed_id": "1"}]
    result = await enricher.enrich_many(records)
    assert result == records
    logger.warning.assert_called_once()
