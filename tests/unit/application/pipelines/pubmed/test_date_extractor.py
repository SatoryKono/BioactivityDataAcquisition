
import pytest
from xml.etree.ElementTree import Element, SubElement
from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor, MedlineDateParser

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

        assert raw['year'] == "2023"
        assert raw['month'] == "Feb"

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
