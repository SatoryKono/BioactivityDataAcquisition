"""Security tests for XXE mitigation in PubMed pipeline."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor
from bioetl.domain.context import PipelineContext
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


def test_xml_processor_accepts_pubmed_doctype_without_loading_external_dtd():
    """Accept the normal PubMed declaration without fetching its external DTD."""
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<!ELEMENT PubmedArticleSet ANY>")

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = (
            '<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle//EN" '
            f'"http://127.0.0.1:{server.server_port}/pubmed.dtd">'
            "<PubmedArticleSet/>"
        )

        result = PubMedXmlProcessor.parse_response(payload)

        assert result is not None
        assert result.tag == "PubmedArticleSet"
        assert requests == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


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


def test_xml_processor_oversized_mitigation():
    """Verify that PubMedXmlProcessor blocks oversized payload > 31MB."""
    oversized_payload = "<root>" + "A" * (31457280 + 10) + "</root>"

    result = PubMedXmlProcessor.parse_response(oversized_payload)
    assert result is None


def test_xml_processor_blowup_mitigation():
    """Verify that PubMedXmlProcessor blocks quadratic blowup payload with massive number of elements."""
    blowup_payload = "<root>" + "<child></child>" * 100001 + "</root>"

    result = PubMedXmlProcessor.parse_response(blowup_payload)
    assert result is None
