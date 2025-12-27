"""Unit tests for DateExtractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor


class TestFormatDate:
    """Tests for format_date method."""

    def test_full_date_numeric_month(self):
        """Test formatting a complete date with numeric month."""
        result = DateExtractor.format_date("2023", "03", "15")
        assert result == "2023-03-15"

    def test_full_date_named_month(self):
        """Test formatting a complete date with month name."""
        result = DateExtractor.format_date("2023", "Mar", "15")
        assert result == "2023-03-15"

    def test_full_date_lowercase_month(self):
        """Test formatting with lowercase month name."""
        result = DateExtractor.format_date("2023", "january", "01")
        assert result == "2023-01-01"

    def test_year_month_only(self):
        """Test formatting with year and month only."""
        result = DateExtractor.format_date("2023", "06", None)
        assert result == "2023-06"

    def test_year_only(self):
        """Test formatting with year only."""
        result = DateExtractor.format_date("2023", None, None)
        assert result == "2023"

    def test_no_year_returns_none(self):
        """Test that missing year returns None."""
        result = DateExtractor.format_date(None, "03", "15")
        assert result is None

    def test_single_digit_month_padded(self):
        """Test that single digit months are zero-padded."""
        result = DateExtractor.format_date("2023", "3", "15")
        assert result == "2023-03-15"

    def test_single_digit_day_padded(self):
        """Test that single digit days are zero-padded."""
        result = DateExtractor.format_date("2023", "03", "5")
        assert result == "2023-03-05"

    def test_all_month_names(self):
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


class TestExtractDate:
    """Tests for extract_date method."""

    def test_complete_date_element(self):
        """Test extracting a complete date from XML element."""
        xml = "<PubDate><Year>2023</Year><Month>Mar</Month><Day>15</Day></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str == "2023-03-15"
        assert year_int == 2023

    def test_year_month_only_element(self):
        """Test extracting year-month date."""
        xml = "<PubDate><Year>2023</Year><Month>06</Month></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str == "2023-06"
        assert year_int == 2023

    def test_year_only_element(self):
        """Test extracting year-only date."""
        xml = "<PubDate><Year>2023</Year></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str == "2023"
        assert year_int == 2023

    def test_none_node_returns_none_tuple(self):
        """Test that None node returns (None, None)."""
        date_str, year_int = DateExtractor.extract_date(None)
        assert date_str is None
        assert year_int is None

    def test_empty_element_returns_none(self):
        """Test that empty element returns None values."""
        xml = "<PubDate></PubDate>"
        node = ET.fromstring(xml)
        date_str, year_int = DateExtractor.extract_date(node)
        assert date_str is None
        assert year_int is None


class TestExtractHistoryDate:
    """Tests for extract_history_date method."""

    @pytest.fixture
    def history_xml(self):
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

    def test_extract_received_date(self, history_xml):
        """Test extracting received date."""
        result = DateExtractor.extract_history_date(history_xml, "received")
        assert result == "2022-12-01"

    def test_extract_revised_date(self, history_xml):
        """Test extracting revised date."""
        result = DateExtractor.extract_history_date(history_xml, "revised")
        assert result == "2023-01-15"

    def test_extract_accepted_date(self, history_xml):
        """Test extracting accepted date."""
        result = DateExtractor.extract_history_date(history_xml, "accepted")
        assert result == "2023-02-20"

    def test_unknown_status_returns_none(self, history_xml):
        """Test that unknown PubStatus returns None."""
        result = DateExtractor.extract_history_date(history_xml, "unknown")
        assert result is None

    def test_none_history_returns_none(self):
        """Test that None history returns None."""
        result = DateExtractor.extract_history_date(None, "accepted")
        assert result is None


class TestExtractArticleDate:
    """Tests for extract_article_date method."""

    @pytest.fixture
    def article_xml(self):
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

    def test_extract_electronic_date(self, article_xml):
        """Test extracting Electronic date."""
        result = DateExtractor.extract_article_date(article_xml, "Electronic")
        assert result == "2023-03-10"

    def test_extract_print_date(self, article_xml):
        """Test extracting Print date."""
        result = DateExtractor.extract_article_date(article_xml, "Print")
        assert result == "2023-04-01"

    def test_unknown_type_returns_none(self, article_xml):
        """Test that unknown DateType returns None."""
        result = DateExtractor.extract_article_date(article_xml, "Unknown")
        assert result is None

    def test_none_article_returns_none(self):
        """Test that None article returns None."""
        result = DateExtractor.extract_article_date(None, "Electronic")
        assert result is None
