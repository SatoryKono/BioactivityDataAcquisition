"""Unit tests for BaseFieldExtractor."""

from __future__ import annotations

import pytest

import xml.etree.ElementTree as ET
from typing import Any

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


pytestmark = pytest.mark.unit


class ConcreteExtractor(BaseFieldExtractor):
    """Concrete implementation for testing."""

    def extract(self, element: ET.Element | None) -> str | None:
        """Extract text from element."""
        if element is None:
            return None
        text_elem = element.find("Text")
        if text_elem is not None and text_elem.text:
            return text_elem.text
        return None

    def normalize(self, raw_value: str) -> str:
        """Normalize by stripping and uppercasing."""
        return raw_value.strip().upper()


class TestBaseFieldExtractor:
    """Tests for BaseFieldExtractor template method."""

    def test_process_with_valid_element(self):
        """Test process with valid element returns normalized value."""
        xml = "<Root><Text>  hello world  </Text></Root>"
        element = ET.fromstring(xml)
        extractor = ConcreteExtractor()

        result = extractor.process(element)

        assert result == "HELLO WORLD"

    def test_process_with_none_element(self):
        """Test process with None element returns None."""
        extractor = ConcreteExtractor()

        result = extractor.process(None)

        assert result is None

    def test_process_with_empty_element(self):
        """Test process with element missing Text child returns None."""
        xml = "<Root></Root>"
        element = ET.fromstring(xml)
        extractor = ConcreteExtractor()

        result = extractor.process(element)

        assert result is None

    def test_extract_returns_raw_value(self):
        """Test extract returns raw unprocessed value."""
        xml = "<Root><Text>  raw text  </Text></Root>"
        element = ET.fromstring(xml)
        extractor = ConcreteExtractor()

        result = extractor.extract(element)

        assert result == "  raw text  "  # Unchanged

    def test_normalize_transforms_value(self):
        """Test normalize applies transformation."""
        extractor = ConcreteExtractor()

        result = extractor.normalize("  test value  ")

        assert result == "TEST VALUE"


class NullNormalizeExtractor(BaseFieldExtractor):
    """Extractor that returns None from extract."""

    def extract(self, element: ET.Element | None) -> Any:
        """Always return None."""
        return None

    def normalize(self, raw_value: Any) -> Any:
        """Should not be called when extract returns None."""
        raise AssertionError("normalize should not be called when extract returns None")


class TestNullExtractHandling:
    """Tests for handling None from extract."""

    def test_process_skips_normalize_when_extract_returns_none(self):
        """Test that normalize is not called when extract returns None."""
        xml = "<Root><Text>ignored</Text></Root>"
        element = ET.fromstring(xml)
        extractor = NullNormalizeExtractor()

        result = extractor.process(element)

        assert result is None
