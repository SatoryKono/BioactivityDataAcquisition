import xml.etree.ElementTree as ET

import pytest
from xml.etree.ElementTree import Element, SubElement

from bioetl.application.pipelines.pubmed.extractors.date import (
    DateExtractor,
    MedlineDateParser,
)


@pytest.mark.unit
class TestDateExtractorSingleton:
    def test_singleton_instance(self):
        """Test that DateExtractor returns the same instance."""
        e1 = DateExtractor()
        e2 = DateExtractor()
        assert e1 is e2
        assert id(e1) == id(e2)

    def test_medline_parser_class_var(self):
        """Test that _MEDLINE_PARSER is a class variable and shared."""
        e1 = DateExtractor()
        e2 = DateExtractor()
        assert e1._MEDLINE_PARSER is e2._MEDLINE_PARSER
        assert isinstance(e1._MEDLINE_PARSER, MedlineDateParser)

    def test_extract_date_method(self):
        """Test extract_date method works correctly with singleton."""
        root = Element("Date")
        SubElement(root, "Year").text = "2023"
        SubElement(root, "Month").text = "Jan"
        SubElement(root, "Day").text = "01"

        date_str, year = DateExtractor.extract_date(root)
        assert date_str == "2023-01-01"
        assert year == 2023

    def test_extract_medline_date(self):
        """Test MedlineDate parsing through Extractor."""
        root = Element("Date")
        SubElement(root, "MedlineDate").text = "2023 Jan-Feb"

        # Uses DateExtractor().extract() internally
        extractor = DateExtractor()
        raw = extractor.extract(root)

        assert raw["year"] == "2023"
        assert raw["month"] == "Feb"

    def test_calendar_import_moved(self):
        """Test that calendar logic still works correctly."""
        # This implicitly tests the calendar import logic inside _format_date
        # Case: Month with 30 days
        date_str = DateExtractor.format_date("2023", "Apr", None)
        assert date_str == "2023-04-30"

        # Case: February in non-leap year
        date_str = DateExtractor.format_date("2023", "Feb", None)
        assert date_str == "2023-02-28"

        # Case: February in leap year
        date_str = DateExtractor.format_date("2024", "Feb", None)
        assert date_str == "2024-02-29"


# ---------------------------------------------------------------------------
# Tests merged from orphan tests/unit/pipelines/pubmed/extractors/test_date_extractor.py
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatDate:
    """Tests for format_date method."""

    def test_full_date_numeric_month(self) -> None:
        """Test formatting a complete date with numeric month."""
        result = DateExtractor.format_date("2023", "03", "15")
        assert result == "2023-03-15"

    def test_full_date_named_month(self) -> None:
        """Test formatting a complete date with month name."""
        result = DateExtractor.format_date("2023", "Mar", "15")
        assert result == "2023-03-15"

    def test_full_date_lowercase_month(self) -> None:
        """Test formatting with lowercase month name."""
        result = DateExtractor.format_date("2023", "january", "01")
        assert result == "2023-01-01"

    def test_extractor_format_date__year_month_only__28b81c08(self) -> None:
        """Test formatting with year and month only (end-of-period: day 30)."""
        result = DateExtractor.format_date("2023", "06", None)
        assert result == "2023-06-30"

    def test_extractor_format_date__year_only__06face95(self) -> None:
        """Test formatting with year only (end-of-period: Dec 31)."""
        result = DateExtractor.format_date("2023", None, None)
        assert result == "2023-12-31"

    def test_no_year_returns_none(self) -> None:
        """Test that missing year returns None."""
        result = DateExtractor.format_date(None, "03", "15")
        assert result is None

    def test_single_digit_month_padded(self) -> None:
        """Test that single digit months are zero-padded."""
        result = DateExtractor.format_date("2023", "3", "15")
        assert result == "2023-03-15"

    def test_single_digit_day_padded(self) -> None:
        """Test that single digit days are zero-padded."""
        result = DateExtractor.format_date("2023", "03", "5")
        assert result == "2023-03-05"

    def test_all_month_names(self) -> None:
        """Test all month name mappings."""
        months = [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ]
        expected = [
            "01",
            "02",
            "03",
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
            "11",
            "12",
        ]

        for month, exp in zip(months, expected, strict=True):
            result = DateExtractor.format_date("2023", month, "01")
            assert result == f"2023-{exp}-01"


@pytest.mark.unit
class TestExtractDate:
    """Tests for extract_date method."""

    def test_complete_date_element(self) -> None:
        """Test extracting a complete date from XML element."""
        xml = "<PubDate><Year>2023</Year><Month>Mar</Month><Day>15</Day></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str == "2023-03-15"
        assert year_int == 2023

    def test_year_month_only_element(self) -> None:
        """Test extracting year-month date (end-of-period: day 30)."""
        xml = "<PubDate><Year>2023</Year><Month>06</Month></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str == "2023-06-30"
        assert year_int == 2023

    def test_year_only_element(self) -> None:
        """Test extracting year-only date (end-of-period: Dec 31)."""
        xml = "<PubDate><Year>2023</Year></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str == "2023-12-31"
        assert year_int == 2023

    def test_none_node_returns_none_tuple(self) -> None:
        """Test that None node returns (None, None)."""
        date_str, year_int = DateExtractor.extract_date(None)
        assert date_str is None
        assert year_int is None

    def test_empty_element_returns_none(self) -> None:
        """Test that empty element returns None values."""
        xml = "<PubDate></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str is None
        assert year_int is None


@pytest.mark.unit
class TestExtractHistoryDate:
    """Tests for extract_history_date method."""

    @pytest.fixture
    def history_xml(self) -> ET.Element:
        """Create a History XML element fixture."""
        xml = """
        <History>
            <PubMedPubDate PubStatus="received">
                <Year>2022</Year><Month>12</Month><Day>01</Day>
            </PubMedPubDate>
            <PubMedPubDate PubStatus="revised">
                <Year>2023</Year><Month>01</Month><Day>15</Day>
            </PubMedPubDate>
            <PubMedPubDate PubStatus="accepted">
                <Year>2023</Year><Month>02</Month><Day>20</Day>
            </PubMedPubDate>
        </History>
        """
        return ET.fromstring(xml)

    def test_extract_received_date(self, history_xml: ET.Element) -> None:
        """Test extracting received date."""
        result = DateExtractor.extract_history_date(history_xml, "received")
        assert result == "2022-12-01"

    def test_extract_revised_date(self, history_xml: ET.Element) -> None:
        """Test extracting revised date."""
        result = DateExtractor.extract_history_date(history_xml, "revised")
        assert result == "2023-01-15"

    def test_extract_accepted_date(self, history_xml: ET.Element) -> None:
        """Test extracting accepted date."""
        result = DateExtractor.extract_history_date(history_xml, "accepted")
        assert result == "2023-02-20"

    def test_unknown_status_returns_none(self, history_xml: ET.Element) -> None:
        """Test that unknown PubStatus returns None."""
        result = DateExtractor.extract_history_date(history_xml, "unknown")
        assert result is None

    def test_none_history_returns_none(self) -> None:
        """Test that None history returns None."""
        result = DateExtractor.extract_history_date(None, "accepted")
        assert result is None


@pytest.mark.unit
class TestExtractArticleDate:
    """Tests for extract_article_date method."""

    @pytest.fixture
    def article_xml(self) -> ET.Element:
        """Create an Article XML element with ArticleDate."""
        xml = """
        <Article>
            <ArticleDate DateType="Electronic">
                <Year>2023</Year><Month>03</Month><Day>10</Day>
            </ArticleDate>
            <ArticleDate DateType="Print">
                <Year>2023</Year><Month>04</Month><Day>01</Day>
            </ArticleDate>
        </Article>
        """
        return ET.fromstring(xml)

    def test_extract_electronic_date(self, article_xml: ET.Element) -> None:
        """Test extracting Electronic date."""
        result = DateExtractor.extract_article_date(article_xml, "Electronic")
        assert result == "2023-03-10"

    def test_extract_print_date(self, article_xml: ET.Element) -> None:
        """Test extracting Print date."""
        result = DateExtractor.extract_article_date(article_xml, "Print")
        assert result == "2023-04-01"

    def test_unknown_type_returns_none(self, article_xml: ET.Element) -> None:
        """Test that unknown DateType returns None."""
        result = DateExtractor.extract_article_date(article_xml, "Unknown")
        assert result is None

    def test_extract_article_date__article_returns_none__d70f6b70(self) -> None:
        """Test that None article returns None."""
        result = DateExtractor.extract_article_date(None, "Electronic")
        assert result is None
