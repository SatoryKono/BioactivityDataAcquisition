"""Focused tests for UniProt ID-mapping polling and retry mixin."""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.uniprot._idmapping_errors import (
    IDMappingJobError,
    IDMappingTimeoutError,
)
from bioetl.infrastructure.adapters.uniprot._idmapping_retry import (
    IDMappingRetryMixin,
)


pytestmark = pytest.mark.unit


class _RetryHost(IDMappingRetryMixin):
    POLLING_INTERVAL = 0.0
    MAX_POLL_ATTEMPTS = 3
    base_url = "https://rest.uniprot.org"

    def __init__(self) -> None:
        self.logger = MagicMock()
        self.http_client = MagicMock()
        self.http_client.get = AsyncMock()
        self._adapter_metrics = MagicMock()
        self._adapter_metrics.measure_request.return_value = nullcontext()


def _response(
    *,
    status_code: int = 200,
    url: str = "https://rest.uniprot.org/idmapping/status/job-1",
    payload: dict[str, object] | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.url = url
    response.json.return_value = payload or {}
    return response


def test_check_redirect_to_results_supports_redirect_and_non_response_objects() -> None:
    redirected = _response(url="https://rest.uniprot.org/idmapping/results/job-1")

    assert (
        IDMappingRetryMixin._check_redirect_to_results(redirected)
        == "https://rest.uniprot.org/idmapping/results/job-1"
    )
    assert IDMappingRetryMixin._check_redirect_to_results(object()) is None


def test_resolve_job_status_prefers_results_then_redirect_then_payload() -> None:
    assert (
        IDMappingRetryMixin._resolve_job_status(
            _response(status_code=200),
            {"results": [{"from": "A"}]},
        )
        == "HAS_RESULTS"
    )
    assert (
        IDMappingRetryMixin._resolve_job_status(_response(status_code=303), {})
        == "FINISHED"
    )
    assert (
        IDMappingRetryMixin._resolve_job_status(
            _response(status_code=200),
            {"jobStatus": "RUNNING"},
        )
        == "RUNNING"
    )
    assert (
        IDMappingRetryMixin._resolve_job_status(_response(status_code=200), {})
        == "UNKNOWN"
    )


@pytest.mark.asyncio
async def test_poll_until_ready_returns_redirect_url() -> None:
    host = _RetryHost()
    host.http_client.get.return_value = _response(
        url="https://rest.uniprot.org/idmapping/uniprotkb/results/job-1"
    )

    results_url = await host._poll_until_ready("job-1")

    assert results_url == "https://rest.uniprot.org/idmapping/uniprotkb/results/job-1"
    host.logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_poll_until_ready_retries_after_status_error_and_finishes() -> None:
    host = _RetryHost()
    host.http_client.get.side_effect = [
        _response(status_code=500),
        _response(status_code=303, payload={}),
    ]

    with pytest.MonkeyPatch.context() as monkeypatch:
        sleep = AsyncMock()
        monkeypatch.setattr(
            "bioetl.infrastructure.adapters.uniprot._idmapping_retry.asyncio.sleep",
            sleep,
        )
        results_url = await host._poll_until_ready("job-2")

    assert results_url is None
    host.logger.warning.assert_called_once()
    sleep.assert_awaited_once_with(0.0)


@pytest.mark.asyncio
async def test_poll_until_ready_returns_response_url_when_results_embedded() -> None:
    host = _RetryHost()
    host.http_client.get.return_value = _response(
        payload={"results": [{"from": "CHEMBL1"}]},
        url="https://rest.uniprot.org/idmapping/status/job-3",
    )

    results_url = await host._poll_until_ready("job-3")

    assert results_url == "https://rest.uniprot.org/idmapping/status/job-3"


@pytest.mark.asyncio
async def test_poll_until_ready_raises_job_error_on_error_status() -> None:
    host = _RetryHost()
    host.http_client.get.return_value = _response(
        payload={"jobStatus": "ERROR", "errorMessage": "broken mapping"},
    )

    with pytest.raises(IDMappingJobError, match="broken mapping"):
        await host._poll_until_ready("job-4")

    host.logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_poll_until_ready_times_out_after_max_attempts() -> None:
    host = _RetryHost()
    host.http_client.get.return_value = _response(payload={"jobStatus": "RUNNING"})

    with pytest.MonkeyPatch.context() as monkeypatch:
        sleep = AsyncMock()
        monkeypatch.setattr(
            "bioetl.infrastructure.adapters.uniprot._idmapping_retry.asyncio.sleep",
            sleep,
        )
        with pytest.raises(IDMappingTimeoutError, match="job-5"):
            await host._poll_until_ready("job-5")

    assert sleep.await_count == host.MAX_POLL_ATTEMPTS
