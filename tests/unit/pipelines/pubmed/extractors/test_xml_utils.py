"""Unit tests for xml_utils module."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.xml_utils import get_int, get_text


class TestGetText:
    """Tests for get_text function."""

    def test_text_extracted(self):
        """Test extracting text from element."""
        xml = "<Element>Hello World</Element>"
        node = ET.fromstring(xml)
        result = get_text(node)
        assert result == "Hello World"

    def test_text_stripped(self):
        """Test that text is stripped."""
        xml = "<Element>  spaced text  </Element>"
        node = ET.fromstring(xml)
        result = get_text(node)
        assert result == "spaced text"

    def test_empty_element_returns_none(self):
        """Test that empty element returns None."""
        xml = "<Element></Element>"
        node = ET.fromstring(xml)
        result = get_text(node)
        assert result is None

    def test_whitespace_only_returns_none(self):
        """Test that whitespace-only text returns empty string after strip."""
        xml = "<Element>   </Element>"
        node = ET.fromstring(xml)
        result = get_text(node)
        assert result == ""

    def test_none_node_returns_none(self):
        """Test that None node returns None."""
        result = get_text(None)
        assert result is None


class TestGetInt:
    """Tests for get_int function."""

    def test_int_extracted(self):
        """Test extracting integer from element."""
        xml = "<Element>42</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result == 42

    def test_int_with_whitespace(self):
        """Test extracting integer with surrounding whitespace."""
        xml = "<Element>  123  </Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result == 123

    def test_negative_int(self):
        """Test extracting negative integer."""
        xml = "<Element>-99</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result == -99

    def test_non_numeric_returns_none(self):
        """Test that non-numeric text returns None."""
        xml = "<Element>not a number</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result is None

    def test_float_returns_none(self):
        """Test that float text returns None (int expected)."""
        xml = "<Element>3.14</Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result is None

    def test_empty_element_returns_none(self):
        """Test that empty element returns None."""
        xml = "<Element></Element>"
        node = ET.fromstring(xml)
        result = get_int(node)
        assert result is None

    def test_none_node_returns_none(self):
        """Test that None node returns None."""
        result = get_int(None)
        assert result is None
