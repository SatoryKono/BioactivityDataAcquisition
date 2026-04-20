"""Unit tests for pubmed AuthorExtractor.

Tests covering:
- extract() with AuthorList
- extract() with None element / missing AuthorList
- Individual authors (LastName, Initials, ForeName)
- Collective authors
- Affiliations (simple and structured)
- _find_identifier() with ROR/GRID/ISNI/RINGGOLD priority
- _extract_structured_affiliation()
- _extract_email_from_text()
- normalize() formatting
- process() template method
- parse_authors() classmethod
- parse_affiliations() classmethod
- parse_structured_affiliations() classmethod
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_article_with_authors(authors_xml: str) -> ET.Element:
    """Wrap author XML inside an Article element."""
    xml_str = f"<Article><AuthorList>{authors_xml}</AuthorList></Article>"
    return ET.fromstring(xml_str)


def _simple_author(
    last: str = "Smith",
    initials: str = "J",
    fore_name: str | None = None,
) -> str:
    parts = f"<LastName>{last}</LastName><Initials>{initials}</Initials>"
    if fore_name:
        parts += f"<ForeName>{fore_name}</ForeName>"
    return f"<Author>{parts}</Author>"


def _collective_author(name: str = "ENCODE Consortium") -> str:
    return f"<Author><CollectiveName>{name}</CollectiveName></Author>"


def _author_with_affiliation(
    last: str = "Doe",
    initials: str = "J",
    affiliation_text: str = "MIT, Cambridge, MA",
) -> str:
    return (
        f"<Author><LastName>{last}</LastName><Initials>{initials}</Initials>"
        f"<AffiliationInfo><Affiliation>{affiliation_text}</Affiliation></AffiliationInfo>"
        "</Author>"
    )


def _author_with_ror(
    last: str = "Lee",
    initials: str = "K",
    affiliation_text: str = "Harvard University",
    ror_id: str = "https://ror.org/03vek6s52",
) -> str:
    return (
        f"<Author><LastName>{last}</LastName><Initials>{initials}</Initials>"
        "<AffiliationInfo>"
        f"<Affiliation>{affiliation_text}</Affiliation>"
        f'<Identifier Source="ROR">{ror_id}</Identifier>'
        "</AffiliationInfo>"
        "</Author>"
    )


# ---------------------------------------------------------------------------
# extract()
# ---------------------------------------------------------------------------


class TestExtract:
    """Tests for AuthorExtractor.extract()."""

    def test_returns_none_for_none_element(self) -> None:
        extractor = AuthorExtractor()
        assert extractor.extract(None) is None

    def test_returns_none_when_no_author_list(self) -> None:
        element = ET.fromstring("<Article></Article>")
        extractor = AuthorExtractor()
        assert extractor.extract(element) is None

    def test_returns_none_for_empty_author_list(self) -> None:
        element = ET.fromstring("<Article><AuthorList></AuthorList></Article>")
        extractor = AuthorExtractor()
        assert extractor.extract(element) is None

    def test_extracts_single_author(self) -> None:
        element = _make_article_with_authors(_simple_author("Smith", "JA"))
        extractor = AuthorExtractor()
        result = extractor.extract(element)
        assert result is not None
        assert len(result) == 1
        assert result[0]["last_name"] == "Smith"
        assert result[0]["initials"] == "JA"

    def test_extracts_multiple_authors(self) -> None:
        xml = _simple_author("Smith", "J") + _simple_author("Jones", "AB")
        element = _make_article_with_authors(xml)
        extractor = AuthorExtractor()
        result = extractor.extract(element)
        assert result is not None
        assert len(result) == 2

    def test_extracts_collective_author(self) -> None:
        element = _make_article_with_authors(_collective_author("ENCODE Project"))
        extractor = AuthorExtractor()
        result = extractor.extract(element)
        assert result is not None
        assert result[0]["collective_name"] == "ENCODE Project"
        assert result[0]["last_name"] is None

    def test_extracts_fore_name(self) -> None:
        element = _make_article_with_authors(
            _simple_author("Brown", "CB", "Christopher")
        )
        extractor = AuthorExtractor()
        result = extractor.extract(element)
        assert result is not None
        assert result[0]["fore_name"] == "Christopher"

    def test_extracts_affiliations(self) -> None:
        element = _make_article_with_authors(
            _author_with_affiliation("Doe", "JD", "MIT, Cambridge, MA")
        )
        extractor = AuthorExtractor()
        result = extractor.extract(element)
        assert result is not None
        affs = result[0]["affiliations"]
        assert affs is not None
        assert "MIT" in affs[0]

    def test_no_affiliations_returns_none(self) -> None:
        element = _make_article_with_authors(_simple_author())
        extractor = AuthorExtractor()
        result = extractor.extract(element)
        assert result is not None
        assert result[0]["affiliations"] is None


# ---------------------------------------------------------------------------
# _find_identifier
# ---------------------------------------------------------------------------


class TestFindIdentifier:
    """Tests for _find_identifier() priority ordering."""

    def test_ror_preferred_over_grid(self) -> None:
        xml_str = (
            "<AffiliationInfo>"
            '<Identifier Source="GRID">grid.1234</Identifier>'
            '<Identifier Source="ROR">https://ror.org/abc</Identifier>'
            "</AffiliationInfo>"
        )
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        ident, source = extractor._find_identifier(aff_info)
        assert source == "ROR"
        assert ident == "https://ror.org/abc"

    def test_grid_preferred_over_isni(self) -> None:
        xml_str = (
            "<AffiliationInfo>"
            '<Identifier Source="ISNI">0000 0001</Identifier>'
            '<Identifier Source="GRID">grid.9999</Identifier>'
            "</AffiliationInfo>"
        )
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        _ident, source = extractor._find_identifier(aff_info)
        assert source == "GRID"

    def test_fallback_to_first_available(self) -> None:
        """When no priority source found, falls back to first identifier."""
        xml_str = (
            "<AffiliationInfo>"
            '<Identifier Source="CUSTOM">custom-123</Identifier>'
            "</AffiliationInfo>"
        )
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        ident, source = extractor._find_identifier(aff_info)
        assert ident == "custom-123"
        assert source == "CUSTOM"

    def test_returns_none_when_no_identifiers(self) -> None:
        xml_str = "<AffiliationInfo><Affiliation>No identifiers</Affiliation></AffiliationInfo>"
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        ident, source = extractor._find_identifier(aff_info)
        assert ident is None
        assert source is None


# ---------------------------------------------------------------------------
# _extract_email_from_text
# ---------------------------------------------------------------------------


class TestExtractEmailFromText:
    """Tests for _extract_email_from_text()."""

    def test_extracts_email_from_affiliation_text(self) -> None:
        extractor = AuthorExtractor()
        text = "Harvard Medical School. Electronic address: jdoe@hms.harvard.edu"
        assert extractor._extract_email_from_text(text) == "jdoe@hms.harvard.edu"

    def test_returns_none_when_no_email(self) -> None:
        extractor = AuthorExtractor()
        text = "MIT, Cambridge, Massachusetts, USA."
        assert extractor._extract_email_from_text(text) is None

    def test_extracts_first_email_when_multiple(self) -> None:
        extractor = AuthorExtractor()
        text = "Email: first@example.com or second@example.com"
        result = extractor._extract_email_from_text(text)
        assert result is not None
        assert "@" in result


# ---------------------------------------------------------------------------
# _extract_structured_affiliation
# ---------------------------------------------------------------------------


class TestExtractStructuredAffiliation:
    """Tests for _extract_structured_affiliation()."""

    def test_returns_structured_affiliation_with_ror(self) -> None:
        xml_str = (
            "<AffiliationInfo>"
            "<Affiliation>Harvard University, Cambridge, MA</Affiliation>"
            '<Identifier Source="ROR">https://ror.org/03vek6s52</Identifier>'
            "</AffiliationInfo>"
        )
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        result = extractor._extract_structured_affiliation(aff_info)
        assert result is not None
        assert result["text"] == "Harvard University, Cambridge, MA"
        assert result["identifier_source"] == "ROR"
        assert result["ror_id"] == "https://ror.org/03vek6s52"
        assert result["grid_id"] is None

    def test_returns_none_when_no_affiliation_text(self) -> None:
        xml_str = "<AffiliationInfo></AffiliationInfo>"
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        assert extractor._extract_structured_affiliation(aff_info) is None

    def test_extracts_email_from_affiliation_text(self) -> None:
        xml_str = (
            "<AffiliationInfo>"
            "<Affiliation>Some University. Electronic address: author@university.edu</Affiliation>"
            "</AffiliationInfo>"
        )
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        result = extractor._extract_structured_affiliation(aff_info)
        assert result is not None
        assert result["email"] == "author@university.edu"

    def test_grid_id_set_correctly(self) -> None:
        xml_str = (
            "<AffiliationInfo>"
            "<Affiliation>Some Institute</Affiliation>"
            '<Identifier Source="GRID">grid.12345.6</Identifier>'
            "</AffiliationInfo>"
        )
        aff_info = ET.fromstring(xml_str)
        extractor = AuthorExtractor()
        result = extractor._extract_structured_affiliation(aff_info)
        assert result is not None
        assert result["grid_id"] == "grid.12345.6"
        assert result["ror_id"] is None


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


class TestNormalize:
    """Tests for normalize() formatting."""

    def test_last_name_with_initials(self) -> None:
        extractor = AuthorExtractor()
        raw = [
            {
                "last_name": "Smith",
                "initials": "JA",
                "fore_name": None,
                "collective_name": None,
            }
        ]
        result = extractor.normalize(raw)  # type: ignore[arg-type]
        assert result == ["Smith, JA"]

    def test_last_name_with_fore_name_fallback(self) -> None:
        extractor = AuthorExtractor()
        raw = [
            {
                "last_name": "Brown",
                "initials": None,
                "fore_name": "Christopher",
                "collective_name": None,
            }
        ]
        result = extractor.normalize(raw)  # type: ignore[arg-type]
        assert result == ["Brown, Christopher"]

    def test_last_name_only(self) -> None:
        extractor = AuthorExtractor()
        raw = [
            {
                "last_name": "Jones",
                "initials": None,
                "fore_name": None,
                "collective_name": None,
            }
        ]
        result = extractor.normalize(raw)  # type: ignore[arg-type]
        assert result == ["Jones"]

    def test_collective_name(self) -> None:
        extractor = AuthorExtractor()
        raw = [
            {
                "last_name": None,
                "initials": None,
                "fore_name": None,
                "collective_name": "ENCODE",
            }
        ]
        result = extractor.normalize(raw)  # type: ignore[arg-type]
        assert result == ["ENCODE"]

    def test_author_with_no_name_skipped(self) -> None:
        extractor = AuthorExtractor()
        raw = [
            {
                "last_name": None,
                "initials": None,
                "fore_name": None,
                "collective_name": None,
            }
        ]
        result = extractor.normalize(raw)  # type: ignore[arg-type]
        assert result == []


# ---------------------------------------------------------------------------
# parse_authors() / parse_affiliations() / parse_structured_affiliations()
# ---------------------------------------------------------------------------


class TestClassMethods:
    """Tests for parse_authors, parse_affiliations, parse_structured_affiliations."""

    def test_parse_authors_basic(self) -> None:
        element = _make_article_with_authors(
            _simple_author("Smith", "J") + _simple_author("Jones", "AB")
        )
        result = AuthorExtractor.parse_authors(element)
        assert "Smith, J" in result
        assert "Jones, AB" in result

    def test_parse_authors_empty(self) -> None:
        element = ET.fromstring("<Article></Article>")
        result = AuthorExtractor.parse_authors(element)
        assert result == []

    def test_parse_affiliations_deduplicates(self) -> None:
        xml = (
            _author_with_affiliation("Smith", "J", "MIT, Cambridge")
            + _author_with_affiliation(
                "Jones", "K", "MIT, Cambridge"
            )  # same affiliation
        )
        element = _make_article_with_authors(xml)
        result = AuthorExtractor.parse_affiliations(element)
        assert result.count("MIT, Cambridge") == 1

    def test_parse_affiliations_sorted(self) -> None:
        xml = _author_with_affiliation(
            "B", "B", "Zzz University"
        ) + _author_with_affiliation("A", "A", "Aaa Institute")
        element = _make_article_with_authors(xml)
        result = AuthorExtractor.parse_affiliations(element)
        assert result == sorted(result)

    def test_parse_affiliations_empty(self) -> None:
        element = ET.fromstring("<Article></Article>")
        assert AuthorExtractor.parse_affiliations(element) == []

    def test_parse_structured_affiliations_with_ror(self) -> None:
        element = _make_article_with_authors(_author_with_ror())
        result = AuthorExtractor.parse_structured_affiliations(element)
        assert len(result) >= 1
        assert result[0]["identifier_source"] == "ROR"

    def test_parse_structured_affiliations_deduplicates_by_text(self) -> None:
        xml = _author_with_ror("Lee", "K") + _author_with_ror("Park", "M")
        element = _make_article_with_authors(xml)
        result = AuthorExtractor.parse_structured_affiliations(element)
        # Same affiliation text → deduplicated to 1
        assert len(result) == 1

    def test_parse_structured_affiliations_empty(self) -> None:
        element = ET.fromstring("<Article></Article>")
        assert AuthorExtractor.parse_structured_affiliations(element) == []


# ---------------------------------------------------------------------------
# process()
# ---------------------------------------------------------------------------


class TestProcess:
    """Tests for process() template method."""

    def test_process_returns_names(self) -> None:
        element = _make_article_with_authors(_simple_author("Taylor", "TJ"))
        extractor = AuthorExtractor()
        result = extractor.process(element)
        assert "Taylor, TJ" in result

    def test_process_returns_empty_list_for_none(self) -> None:
        extractor = AuthorExtractor()
        result = extractor.process(None)
        assert result == []


# ---------------------------------------------------------------------------
# Tests merged from orphan tests/unit/pipelines/pubmed/extractors/test_author_extractor.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseAuthorsEdgeCases:
    """Edge-case tests for parse_authors (merged from orphan)."""

    def test_author_with_both_initials_and_forename(self) -> None:
        """Test author with both Initials and ForeName (Initials takes precedence)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>JM</Initials>
                    <ForeName>John Michael</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, JM"]

    def test_author_with_empty_elements(self) -> None:
        """Test author with empty text elements."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName></LastName>
                    <Initials></Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []
