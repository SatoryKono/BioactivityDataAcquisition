"""Security tests for XXE mitigation in PubMed pipeline."""

import pytest
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor
from bioetl.domain.context import PipelineContext
from unittest.mock import MagicMock
from tests.helpers.transformer_dependencies import instantiate_test_transformer


pytestmark = pytest.mark.security


def test_transformer_xxe_mitigation():
    """Verify that PubMedPublicationTransformer blocks XXE via defusedxml."""
    transformer = instantiate_test_transformer(
        PubMedPublicationTransformer,
        provider="pubmed",
    )

    # Payload with DTD entity
    xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE root [
      <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <root>&xxe;</root>"""

    record = {"_raw_xml": xxe_payload, "pmid": "12345"}
    context = MagicMock(spec=PipelineContext)

    # In transformer.py, EntitiesForbidden is caught and re-raised as ValueError
    with pytest.raises(ValueError, match="XML parse error"):
        transformer._pre_extract_validation(context, record, 0)


def test_xml_processor_xxe_mitigation():
    """Verify that PubMedXmlProcessor blocks XXE via defusedxml."""
    # Payload with DTD entity
    xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE root [
      <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <root>&xxe;</root>"""

    # PubMedXmlProcessor.parse_response catches (ET.ParseError, defused_ET.EntitiesForbidden)
    # and returns None.
    result = PubMedXmlProcessor.parse_response(xxe_payload)
    assert result is None


def test_transformer_billion_laughs_mitigation():
    """Verify that PubMedPublicationTransformer blocks Entity Expansion (Billion Laughs)."""
    transformer = instantiate_test_transformer(
        PubMedPublicationTransformer,
        provider="pubmed",
    )

    # Billion Laughs payload
    payload = """<?xml version="1.0"?>
    <!DOCTYPE lolz [
     <!ENTITY lol "lol">
     <!ELEMENT lolz (#PCDATA)>
     <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
     <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
     <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
    ]>
    <lolz>&lol3;</lolz>"""

    record = {"_raw_xml": payload, "pmid": "12345"}
    context = MagicMock(spec=PipelineContext)

    # Should also be caught by defusedxml and re-raised as ValueError in transformer
    with pytest.raises(ValueError, match="XML parse error"):
        transformer._pre_extract_validation(context, record, 0)
