"""Unit tests for SemanticScholar batch request mixin."""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.semanticscholar.batch_request_mixin import (
    SemanticScholarBatchRequestMixin,
)

pytestmark = pytest.mark.unit

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1000/xyz"


class _MetricsStub:
    def measure_request(
        self, _endpoint: str
    ) -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()


class _ResponseStub:
    def __init__(self, payload: list[dict[str, object] | None]) -> None:
        self._payload = payload

    def json(self) -> list[dict[str, object] | None]:
        return self._payload


class _SemanticScholarHarness(SemanticScholarBatchRequestMixin):
    def __init__(self, payload: list[dict[str, object] | None]) -> None:
        self._logger = MagicMock()
        self.fields = "paperId,title"
        self._adapter_metrics = _MetricsStub()
        self._http_client = MagicMock()
        self._http_client.post = AsyncMock(return_value=_ResponseStub(payload))
        self._request_collector = MagicMock()

    def _build_headers(self) -> dict[str, str]:
        return {"x-api-key": "test-key"}


@pytest.mark.asyncio
async def test_fetch_batch_with_nulls_returns_empty_for_empty_input() -> None:
    harness = _SemanticScholarHarness(payload=[])

    result = await harness._fetch_batch_with_nulls([])

    assert result == []
    harness._http_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_by_dois_filters_out_null_records() -> None:
    harness = _SemanticScholarHarness(
        payload=[{"paperId": "A"}, None, {"paperId": "B"}]
    )

    records = await collect_async_iterator(harness._fetch_by_dois(["10.1/a", "10.1/b"]))

    assert records == [{"paperId": "A"}, {"paperId": "B"}]


@pytest.mark.asyncio
async def test_fetch_batch_raw_uses_expected_url_payload_and_headers() -> None:
    harness = _SemanticScholarHarness(payload=[{"paperId": "A"}])

    result = await harness._fetch_batch_raw(["DOI:10.1/a"])

    assert result == [{"paperId": "A"}]
    harness._http_client.post.assert_awaited_once()
    called_url = harness._http_client.post.call_args.args[0]
    assert called_url.startswith("https://api.semanticscholar.org/graph/v1/paper/batch")
    assert "fields=paperId,title" in called_url
    assert harness._http_client.post.call_args.kwargs["json"] == {"ids": ["DOI:10.1/a"]}
    assert harness._http_client.post.call_args.kwargs["headers"] == {
        "x-api-key": "test-key"
    }
    harness._request_collector.record_from_response.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_batch_raw_suppresses_collector_errors() -> None:
    harness = _SemanticScholarHarness(payload=[{"paperId": "A"}])
    harness._request_collector.record_from_response.side_effect = RuntimeError(
        "telemetry failure"
    )

    result = await harness._fetch_batch_raw(["DOI:10.1/a"])

    assert result == [{"paperId": "A"}]


@pytest.mark.asyncio
async def test_fetch_batch_raw_normalizes_malformed_payload_entries() -> None:
    harness = _SemanticScholarHarness(payload=[{"paperId": "A"}, "bad", None])

    result = await harness._fetch_batch_raw(["DOI:10.1/a"])

    assert result == [{"paperId": "A"}, None, None]


def test_normalize_doi_handles_all_supported_prefixes() -> None:
    normalize = _SemanticScholarHarness._normalize_doi
    assert normalize("https://doi.org/10.1000/xyz") == "10.1000/xyz"
    assert normalize(LEGACY_HTTP_DOI) == "10.1000/xyz"
    assert normalize("doi:10.1000/xyz") == "10.1000/xyz"
    assert normalize("DOI:10.1000/xyz") == "10.1000/xyz"
    assert normalize("10.1000/xyz") == "10.1000/xyz"
