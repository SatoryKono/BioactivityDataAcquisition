"""Runtime type metadata checks for the PubMed XML processor."""

from __future__ import annotations

from typing import get_type_hints

import xml.etree.ElementTree as ET

import pytest

from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor


pytestmark = pytest.mark.unit


def test_xml_processor_type_hints_resolve_at_runtime() -> None:
    hints = get_type_hints(PubMedXmlProcessor.extract_record)

    assert hints["article_node"] == ET.Element
