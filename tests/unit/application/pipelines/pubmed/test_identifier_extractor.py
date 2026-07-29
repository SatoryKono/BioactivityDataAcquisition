# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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

import pytest

from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)

pytestmark = pytest.mark.unit


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


# ---------------------------------------------------------------------------
# Tests merged from orphan tests/unit/pipelines/pubmed/extractors/test_identifier_extractor.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractDoi:
    """Tests for extract_doi method (raw XML construction)."""

    def test_doi_from_elocationid(self) -> None:
        """Test extracting DOI from ELocationID."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/test.2023</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/test.2023"

    def test_doi_from_articleidlist(self) -> None:
        """Test extracting DOI from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article>
                <Title>Test</Title>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="doi">10.5678/fallback.2023</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.5678/fallback.2023"

    def test_elocationid_takes_precedence(self) -> None:
        """Test that ELocationID DOI takes precedence over ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/primary.2023</ELocationID>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="doi">10.5678/secondary.2023</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/primary.2023"

    def test_no_doi_returns_none(self) -> None:
        """Test that missing DOI returns None."""
        xml = """
        <PubmedArticle>
            <Article>
                <Title>Test</Title>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_no_article_returns_none(self) -> None:
        """Test that missing Article element returns None."""
        xml = "<PubmedArticle></PubmedArticle>"
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_different_eidtype_ignored(self) -> None:
        """Test that non-DOI EIdTypes are ignored."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">S1234-5678(23)00001-2</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_doi_with_whitespace_stripped(self) -> None:
        """Test that DOI whitespace is stripped."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">  10.1234/test.2023  </ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/test.2023"


@pytest.mark.unit
class TestExtractPmcId:
    """Tests for extract_pmc_id method (raw XML construction)."""

    def test_pmc_id_extracted(self) -> None:
        """Test extracting PMC ID."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pmc">PMC123456</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id == "PMC123456"

    def test_no_pmc_id_returns_none(self) -> None:
        """Test that missing PMC ID returns None."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id is None

    def test_no_articleidlist_returns_none(self) -> None:
        """Test that missing ArticleIdList returns None."""
        xml = "<PubmedArticle></PubmedArticle>"
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id is None

    def test_pmc_id_with_whitespace_stripped(self) -> None:
        """Test that PMC ID whitespace is stripped."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pmc">  PMC789012  </ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id == "PMC789012"

    def test_multiple_article_ids(self) -> None:
        """Test extracting PMC ID from multiple ArticleIds."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
                <ArticleId IdType="doi">10.1234/test</ArticleId>
                <ArticleId IdType="pmc">PMC999888</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id == "PMC999888"


@pytest.mark.unit
class TestExtractPii:
    """Tests for extract_pii method (Publisher Item Identifier)."""

    def test_pii_from_elocationid(self) -> None:
        """Test extracting PII from ELocationID."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">S1234-5678(23)00001-2</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii == "S1234-5678(23)00001-2"

    def test_pii_from_articleidlist(self) -> None:
        """Test extracting PII from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article><Title>Test</Title></Article>
            <ArticleIdList>
                <ArticleId IdType="pii">S9876-5432(24)00002-3</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii == "S9876-5432(24)00002-3"

    def test_elocationid_pii_takes_precedence(self) -> None:
        """Test that ELocationID PII takes precedence over ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">PRIMARY-PII</ELocationID>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="pii">SECONDARY-PII</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii == "PRIMARY-PII"

    def test_no_pii_returns_none(self) -> None:
        """Test that missing PII returns None."""
        xml = """
        <PubmedArticle>
            <Article><Title>Test</Title></Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii is None


@pytest.mark.unit
class TestExtractMid:
    """Tests for extract_mid method (Manuscript ID)."""

    def test_mid_extracted(self) -> None:
        """Test extracting MID from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="mid">NIHMS123456</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        mid = IdentifierExtractor.extract_mid(root)
        assert mid == "NIHMS123456"

    def test_no_mid_returns_none(self) -> None:
        """Test that missing MID returns None."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        mid = IdentifierExtractor.extract_mid(root)
        assert mid is None


@pytest.mark.unit
class TestExtractPublisherId:
    """Tests for extract_publisher_id method."""

    def test_publisher_id_extracted(self) -> None:
        """Test extracting publisher-id from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="publisher-id">JCI-12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pub_id = IdentifierExtractor.extract_publisher_id(root)
        assert pub_id == "JCI-12345"

    def test_no_publisher_id_returns_none(self) -> None:
        """Test that missing publisher-id returns None."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pub_id = IdentifierExtractor.extract_publisher_id(root)
        assert pub_id is None


@pytest.mark.unit
class TestParseAllArticleIdsOrphan:
    """Tests for parse_all_article_ids method (raw XML construction)."""

    def test_all_standard_ids_extracted(self) -> None:
        """Test extracting all standard identifier types."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345678</ArticleId>
                <ArticleId IdType="doi">10.1234/test.2024</ArticleId>
                <ArticleId IdType="pmc">PMC9876543</ArticleId>
                <ArticleId IdType="pii">S1234-5678(24)00001-X</ArticleId>
                <ArticleId IdType="mid">NIHMS654321</ArticleId>
                <ArticleId IdType="publisher-id">PUB-2024-001</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] == "12345678"
        assert ids["doi"] == "10.1234/test.2024"
        assert ids["pmc"] == "PMC9876543"
        assert ids["pii"] == "S1234-5678(24)00001-X"
        assert ids["mid"] == "NIHMS654321"
        assert ids["publisher_id"] == "PUB-2024-001"

    def test_unknown_ids_stored_in_other_ids(self) -> None:
        """Test that unknown ID types are stored in other_ids."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
                <ArticleId IdType="custom-type">CUSTOM-VALUE</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] == "12345"
        assert ids["other_ids"]["custom-type"] == "CUSTOM-VALUE"

    def test_empty_articleidlist_returns_none_values(self) -> None:
        """Test that empty ArticleIdList returns None values."""
        xml = """
        <PubmedArticle>
            <ArticleIdList></ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] is None
        assert ids["doi"] is None
        assert ids["pmc"] is None
        assert ids["other_ids"] == {}

    def test_no_articleidlist_returns_none_values(self) -> None:
        """Test that missing ArticleIdList returns None values."""
        xml = "<PubmedArticle></PubmedArticle>"
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] is None
        assert ids["doi"] is None


@pytest.mark.unit
class TestExtractElocationIdsOrphan:
    """Tests for extract_elocation_ids method (raw XML construction)."""

    def test_both_doi_and_pii_extracted(self) -> None:
        """Test extracting both DOI and PII from ELocationID elements."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/test.2024</ELocationID>
                <ELocationID EIdType="pii">S1234-5678(24)00001</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        eloc_ids = IdentifierExtractor.extract_elocation_ids(root)

        assert eloc_ids["doi"] == "10.1234/test.2024"
        assert eloc_ids["pii"] == "S1234-5678(24)00001"

    def test_only_doi_present(self) -> None:
        """Test when only DOI is present in ELocationID."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.5678/only.doi</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        eloc_ids = IdentifierExtractor.extract_elocation_ids(root)

        assert eloc_ids["doi"] == "10.5678/only.doi"
        assert eloc_ids["pii"] is None

    def test_no_elocationid_returns_none_values(self) -> None:
        """Test that missing ELocationID elements return None values."""
        xml = """
        <PubmedArticle>
            <Article><Title>Test</Title></Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        eloc_ids = IdentifierExtractor.extract_elocation_ids(root)

        assert eloc_ids["doi"] is None
        assert eloc_ids["pii"] is None
