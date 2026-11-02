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
"""Unit tests for PubMed request-metadata behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from collections.abc import AsyncIterator

import httpx
import pytest

from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

pytestmark = pytest.mark.unit


async def test_stream_budget_rejects_partial_xml_and_closes_response(
    adapter: PubMedAdapter, mock_http_client: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.domain.exceptions import BioETLError
    from bioetl.infrastructure.adapters.pubmed import _fetch as subject

    response = MagicMock()
    response.aclose = AsyncMock()

    async def oversized_chunks():
        chunk = b"x" * (1024 * 1024)
        for _ in range(subject._MAX_XML_BYTES // len(chunk)):
            yield chunk
        yield b"x"

    response.aiter_bytes.return_value = oversized_chunks()
    mock_http_client.stream = AsyncMock(return_value=response)
    mock_http_client.timeout = 10.0
    mock_http_client.read_timeout_multiplier = 2.0
    parser = MagicMock()
    parse_response = MagicMock()
    monkeypatch.setattr(subject.PubMedXmlProcessor, "extract_all_records", parser)
    monkeypatch.setattr(subject.PubMedXmlProcessor, "parse_response", parse_response)
    with pytest.raises(BioETLError) as caught:
        await adapter._fetch_batch(["12345678"])
    assert isinstance(caught.value.__cause__, ValueError)
    assert (
        str(caught.value.__cause__)
        == f"PubMed XML response exceeds limit of {subject._MAX_XML_BYTES} bytes"
    )
    response.aclose.assert_awaited_once_with()
    parser.assert_not_called()
    parse_response.assert_not_called()
    assert adapter.get_source_metadata().total_requests == 0


_STREAM_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Stream Metadata Title</ArticleTitle>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create mock HTTP client for lightweight metadata tests."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client: AsyncMock, mock_logger: MagicMock) -> PubMedAdapter:
    """Create PubMed adapter instance."""
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        email="test@example.com",
        api_key=None,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


def test_request_metadata__count_starts_at_zero__ebe0eef7(
    adapter: PubMedAdapter,
) -> None:
    """New adapter instances should start with an empty request collector."""
    assert adapter.request_count == 0


def test_request_metadata__and_clears_requests__70bf0692(
    adapter: PubMedAdapter,
) -> None:
    """Metadata snapshot should reflect collector state and consume it."""
    adapter._request_collector.record_request(
        url=f"{ENTREZ_API_BASE}einfo.fcgi?db=pubmed",
        method="GET",
        duration_ms=18.0,
        status_code=200,
    )

    metadata = adapter.get_source_metadata(api_version="v1")

    assert metadata.type == "api"
    assert metadata.url == ENTREZ_API_BASE
    assert metadata.api_version == "v1"
    assert metadata.total_requests == 1
    assert adapter.request_count == 0


def test_request_metadata__resets_request_count__e1eb5603(
    adapter: PubMedAdapter,
) -> None:
    """Clearing the collector should drop accumulated request state."""
    adapter._request_collector.record_request(
        url=f"{ENTREZ_API_BASE}esearch.fcgi?db=pubmed&term=aspirin",
        method="GET",
        duration_ms=22.0,
        status_code=200,
    )

    assert adapter.request_count == 1

    adapter.clear_request_collector()

    assert adapter.request_count == 0


@pytest.mark.asyncio
async def test_fetch_batch_records_streamed_response_size(
    adapter: PubMedAdapter,
    mock_http_client: AsyncMock,
) -> None:
    """``_fetch_batch`` must record PseudoResponse.content size after streaming.

    Existing metadata tests only call ``record_request`` directly; this path
    exercises ``record_from_response`` via the streamed efetch body so a
    missing ``content`` attribute cannot regress silently.
    """
    xml_bytes = _STREAM_XML.encode("utf-8")
    efetch_response = MagicMock()
    efetch_response.status_code = 200
    efetch_response.headers = httpx.Headers({})
    efetch_response.url = httpx.URL(f"{ENTREZ_API_BASE}efetch.fcgi")
    efetch_response.request = MagicMock(method="GET")
    efetch_response.aclose = AsyncMock()

    async def mock_aiter() -> AsyncIterator[bytes]:
        yield xml_bytes

    efetch_response.aiter_bytes.return_value = mock_aiter()
    mock_http_client.stream = AsyncMock(return_value=efetch_response)
    mock_http_client.timeout = 10.0
    mock_http_client.read_timeout_multiplier = 2.0

    records = await adapter._fetch_batch(["12345678"])

    assert len(records) == 1
    assert adapter.request_count == 1
    metadata = adapter.get_source_metadata()
    assert metadata.total_requests == 1
    assert metadata.api_requests[0].response_size_bytes == len(xml_bytes)
    assert metadata.api_requests[0].status_code == 200


@pytest.mark.asyncio
async def test_request_metadata__redacts_email_and_api_key__12592(
    adapter: PubMedAdapter,
    mock_http_client: AsyncMock,
) -> None:
    """Metadata snapshot should redact sensitive query parameters but outbound request is unchanged."""
    adapter.email = "synthetic-user@example.invalid"
    adapter.api_key = "synthetic-placeholder"

    xml_bytes = _STREAM_XML.encode("utf-8")
    efetch_response = MagicMock()
    efetch_response.status_code = 200
    efetch_response.headers = httpx.Headers({})
    efetch_response.url = httpx.URL(
        f"{ENTREZ_API_BASE}efetch.fcgi?db=pubmed&email=synthetic-user@example.invalid&api_key=synthetic-placeholder&other=val"
    )
    efetch_response.request = MagicMock(method="GET")
    efetch_response.aclose = AsyncMock()

    async def mock_aiter() -> AsyncIterator[bytes]:
        yield xml_bytes

    efetch_response.aiter_bytes.return_value = mock_aiter()
    mock_http_client.stream = AsyncMock(return_value=efetch_response)
    mock_http_client.timeout = 10.0
    mock_http_client.read_timeout_multiplier = 2.0

    # Act
    await adapter._fetch_batch(["12345678"])

    # 1. Verify the outbound request is intact
    mock_http_client.stream.assert_called_once()
    args, kwargs = mock_http_client.stream.call_args
    assert "params" in kwargs
    params = kwargs["params"]
    assert "email" in params
    assert params["email"] == "synthetic-user@example.invalid"
    assert "api_key" in params
    assert params["api_key"] == "synthetic-placeholder"

    # Verify metadata is redacted
    metadata = adapter.get_source_metadata(api_version="v1")
    assert metadata.total_requests == 1
    req = metadata.api_requests[0]

    assert "email" in req.query_params
    assert req.query_params["email"] == "[REDACTED]"
    assert "api_key" in req.query_params
    assert req.query_params["api_key"] == "[REDACTED]"
    assert "other" in req.query_params
    assert req.query_params["other"] == "val"

    assert "synthetic-user" not in req.base_url
    assert "synthetic-placeholder" not in req.base_url
