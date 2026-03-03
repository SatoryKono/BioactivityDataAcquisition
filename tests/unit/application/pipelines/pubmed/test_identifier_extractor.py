"""Unit tests for pubmed IdentifierExtractor.

Tests for IdentifierExtractor covering:
- extract() with valid element
- extract() with None element
- normalize() behavior
- extract_doi() classmethod
- extract_pmc_id() classmethod
- extract_pii() classmethod
- extract_mid() classmethod
- extract_publisher_id() classmethod
- extract_all_identifiers() single-pass scan
- parse_all_article_ids() complete extraction
- extract_elocation_ids() classmethod
- _scan_elocation_ids() priority: doi first, then pii
- _scan_article_id_list() fallback extraction
- _process_article_id() key mapping
- Edge cases: empty texts, missing IdType, duplicate keys
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)


def _make_article(
    *,
    doi: str | None = None,
    pmc_id: str | None = None,
    pii: str | None = None,
    mid: str | None = None,
    publisher_id: str | None = None,
    eloc_doi: str | None = None,
    eloc_pii: str | None = None,
) -> ET.Element:
    """Build a minimal PubmedArticle XML element."""
    root = ET.Element("PubmedArticle")
    article = ET.SubElement(root, "Article")

    # ELocationID elements
    if eloc_doi is not None:
        el = ET.SubElement(article, "ELocationID")
        el.set("EIdType", "doi")
        el.text = eloc_doi
    if eloc_pii is not None:
        el = ET.SubElement(article, "ELocationID")
        el.set("EIdType", "pii")
        el.text = eloc_pii

    # ArticleIdList
    id_list = ET.SubElement(root, "ArticleIdList")
    if doi is not None:
        el = ET.SubElement(id_list, "ArticleId")
        el.set("IdType", "doi")
        el.text = doi
    if pmc_id is not None:
        el = ET.SubElement(id_list, "ArticleId")
        el.set("IdType", "pmc")
        el.text = pmc_id
    if pii is not None:
        el = ET.SubElement(id_list, "ArticleId")
        el.set("IdType", "pii")
        el.text = pii
    if mid is not None:
        el = ET.SubElement(id_list, "ArticleId")
        el.set("IdType", "mid")
        el.text = mid
    if publisher_id is not None:
        el = ET.SubElement(id_list, "ArticleId")
        el.set("IdType", "publisher-id")
        el.text = publisher_id

    return root


class TestExtractMethod:
    """Tests for extract() instance method."""

    def test_extract_returns_none_for_none_element(self) -> None:
        extractor = IdentifierExtractor()
        assert extractor.extract(None) is None

    def test_extract_doi_from_article_id_list(self) -> None:
        root = _make_article(doi="10.1234/test.2024")
        extractor = IdentifierExtractor()
        result = extractor.extract(root)
        assert result is not None
        assert result["doi"] == "10.1234/test.2024"

    def test_extract_pmc_from_article_id_list(self) -> None:
        root = _make_article(pmc_id="PMC1234567")
        extractor = IdentifierExtractor()
        result = extractor.extract(root)
        assert result is not None
        assert result["pmc_id"] == "PMC1234567"

    def test_extract_doi_priority_elocation_over_article_list(self) -> None:
        """ELocationID DOI takes priority over ArticleIdList DOI."""
        root = _make_article(
            doi="10.fallback/article",
            eloc_doi="10.priority/elocation",
        )
        result = IdentifierExtractor().extract(root)
        assert result is not None
        assert result["doi"] == "10.priority/elocation"

    def test_extract_no_identifiers_returns_empty(self) -> None:
        root = ET.Element("PubmedArticle")
        ET.SubElement(root, "Article")
        result = IdentifierExtractor().extract(root)
        assert result is not None
        assert result["doi"] is None
        assert result["pmc_id"] is None


class TestNormalizeMethod:
    """Tests for normalize() instance method."""

    def test_normalize_strips_whitespace(self) -> None:
        extractor = IdentifierExtractor()
        raw = {"doi": "  10.1234/test  ", "pmc_id": "  PMC123  "}
        result = extractor.normalize(raw)
        assert result["doi"] == "10.1234/test"
        assert result["pmc_id"] == "PMC123"

    def test_normalize_handles_none_values(self) -> None:
        extractor = IdentifierExtractor()
        raw = {"doi": None, "pmc_id": None}
        result = extractor.normalize(raw)
        assert result["doi"] is None
        assert result["pmc_id"] is None

    def test_normalize_empty_string_to_none(self) -> None:
        extractor = IdentifierExtractor()
        raw = {"doi": "", "pmc_id": "PMC999"}
        result = extractor.normalize(raw)
        assert result["doi"] is None


class TestClassMethods:
    """Tests for classmethods on IdentifierExtractor."""

    def test_extract_doi_classmethod(self) -> None:
        root = _make_article(doi="10.1234/classmethod")
        assert IdentifierExtractor.extract_doi(root) == "10.1234/classmethod"

    def test_extract_pmc_id_classmethod(self) -> None:
        root = _make_article(pmc_id="PMC9999")
        assert IdentifierExtractor.extract_pmc_id(root) == "PMC9999"

    def test_extract_pii_classmethod(self) -> None:
        root = _make_article(pii="S1234-5678(24)00123-4")
        assert IdentifierExtractor.extract_pii(root) == "S1234-5678(24)00123-4"

    def test_extract_mid_classmethod(self) -> None:
        root = _make_article(mid="NIHMS123456")
        assert IdentifierExtractor.extract_mid(root) == "NIHMS123456"

    def test_extract_publisher_id_classmethod(self) -> None:
        root = _make_article(publisher_id="pub-456")
        assert IdentifierExtractor.extract_publisher_id(root) == "pub-456"

    def test_extract_doi_returns_none_when_missing(self) -> None:
        root = _make_article()
        assert IdentifierExtractor.extract_doi(root) is None


class TestExtractAllIdentifiers:
    """Tests for extract_all_identifiers() single-pass method."""

    def test_returns_all_keys(self) -> None:
        root = _make_article(
            doi="10.1234/multi",
            pmc_id="PMC111",
            pii="S0000",
            mid="NIHMS999",
            publisher_id="pub-x",
        )
        result = IdentifierExtractor.extract_all_identifiers(root)
        assert set(result.keys()) >= {"doi", "pii", "pmc_id", "mid", "publisher_id"}

    def test_eloc_doi_overrides_article_list(self) -> None:
        root = _make_article(doi="10.fallback", eloc_doi="10.priority")
        result = IdentifierExtractor.extract_all_identifiers(root)
        assert result["doi"] == "10.priority"

    def test_empty_element_returns_all_none(self) -> None:
        root = ET.Element("PubmedArticle")
        ET.SubElement(root, "Article")
        result = IdentifierExtractor.extract_all_identifiers(root)
        assert all(v is None for v in result.values())

    def test_whitespace_stripped_in_identifiers(self) -> None:
        root = _make_article(doi="  10.1234/spaced  ")
        result = IdentifierExtractor.extract_all_identifiers(root)
        assert result["doi"] == "10.1234/spaced"


class TestParseAllArticleIds:
    """Tests for parse_all_article_ids() comprehensive extraction."""

    def test_extracts_all_known_id_types(self) -> None:
        root = _make_article(doi="10.1234/x", pmc_id="PMC999")
        # Add pubmed ID directly
        id_list = root.find(".//ArticleIdList")
        assert id_list is not None
        pubmed_el = ET.SubElement(id_list, "ArticleId")
        pubmed_el.set("IdType", "pubmed")
        pubmed_el.text = "38123456"

        result = IdentifierExtractor.parse_all_article_ids(root)
        assert result["doi"] == "10.1234/x"
        assert result["pmc"] == "PMC999"
        assert result["pubmed"] == "38123456"

    def test_unknown_id_type_in_other_ids(self) -> None:
        root = ET.Element("PubmedArticle")
        id_list = ET.SubElement(root, "ArticleIdList")
        unknown_el = ET.SubElement(id_list, "ArticleId")
        unknown_el.set("IdType", "custom-source")
        unknown_el.text = "CUSTOM-123"

        result = IdentifierExtractor.parse_all_article_ids(root)
        assert result["other_ids"]["custom-source"] == "CUSTOM-123"

    def test_no_article_id_list_returns_empty(self) -> None:
        root = ET.Element("PubmedArticle")
        result = IdentifierExtractor.parse_all_article_ids(root)
        assert result["doi"] is None
        assert result["pmc"] is None
        assert result["other_ids"] == {}

    def test_empty_text_element_skipped(self) -> None:
        root = ET.Element("PubmedArticle")
        id_list = ET.SubElement(root, "ArticleIdList")
        el = ET.SubElement(id_list, "ArticleId")
        el.set("IdType", "doi")
        el.text = ""  # empty text

        result = IdentifierExtractor.parse_all_article_ids(root)
        assert result["doi"] is None


class TestExtractELocationIds:
    """Tests for extract_elocation_ids() classmethod."""

    def test_extracts_doi_from_elocation(self) -> None:
        root = _make_article(eloc_doi="10.1234/eloc")
        result = IdentifierExtractor.extract_elocation_ids(root)
        assert result["doi"] == "10.1234/eloc"
        assert result["pii"] is None

    def test_extracts_pii_from_elocation(self) -> None:
        root = _make_article(eloc_pii="S0000-1111(24)00001-0")
        result = IdentifierExtractor.extract_elocation_ids(root)
        assert result["pii"] == "S0000-1111(24)00001-0"

    def test_no_article_element_returns_empty(self) -> None:
        root = ET.Element("PubmedArticle")
        result = IdentifierExtractor.extract_elocation_ids(root)
        assert result["doi"] is None
        assert result["pii"] is None

    def test_unknown_elocation_type_ignored(self) -> None:
        root = ET.Element("PubmedArticle")
        article = ET.SubElement(root, "Article")
        el = ET.SubElement(article, "ELocationID")
        el.set("EIdType", "unknown-type")
        el.text = "some-value"

        result = IdentifierExtractor.extract_elocation_ids(root)
        assert result["doi"] is None
        assert result["pii"] is None
