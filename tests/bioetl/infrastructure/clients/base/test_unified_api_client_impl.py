from unittest.mock import Mock

import pytest
import requests

from bioetl.domain.configs import ClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.base.impl.unified_api_client_impl import (
    UnifiedAPIClientImpl,
)
from bioetl.infrastructure.errors import ApiClientError, ApiTimeoutError


def test_request_call_wraps_timeout_error() -> None:
    base_client = Mock()
    base_client.request.side_effect = requests.Timeout("timeout")
    logger = Mock(spec=LoggingPortABC)
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(retry_enabled=False),
        base_client=base_client,
        logger=logger,
        metrics=metrics,
    )

    with pytest.raises(ApiTimeoutError) as err:
        client.request("GET", "https://example.org")

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "https://example.org"
    logger.error.assert_called_once()
    metrics.inc_counter.assert_any_call(
        "client_request_errors",
        {"provider": "chembl", "endpoint": "https://example.org", "status": "timeout"},
    )


def test_request_call_wraps_request_exception() -> None:
    base_client = Mock()
    base_client.request.side_effect = requests.RequestException("boom")
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(retry_enabled=False),
        base_client=base_client,
        metrics=metrics,
    )

    with pytest.raises(ApiClientError) as err:
        client.request("POST", "https://example.org", data={})

    assert err.value.provider == "chembl"
    assert err.value.endpoint == "https://example.org"
    metrics.inc_counter.assert_any_call(
        "client_request_errors",
        {
            "provider": "chembl",
            "endpoint": "https://example.org",
            "status": "ApiClientError",
        },
    )


def test_request_records_metrics_on_success() -> None:
    base_client = Mock()
    response = Mock()
    response.status_code = 200
    base_client.request.return_value = response
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(),
        base_client=base_client,
        metrics=metrics,
    )

    result = client.request("GET", "https://example.org")

    assert result is response
    metrics.inc_counter.assert_any_call(
        "client_request_total",
        {"provider": "chembl", "endpoint": "https://example.org", "status": "200"},
    )
    metrics.observe_histogram.assert_called_once()


def test_request_retries_on_timeout_until_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_client = Mock()
    response = Mock()
    response.status_code = 200
    base_client.request.side_effect = [requests.Timeout("timeout"), response]
    metrics = Mock(spec=MetricsPortABC)
    logger = Mock(spec=LoggingPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(max_retries=1, backoff_factor=0.1),
        base_client=base_client,
        metrics=metrics,
        logger=logger,
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.clients.base.impl.unified_api_client_impl.time.sleep",
        lambda *_: None,
    )

    result = client.request("GET", "https://example.org")

    assert result is response
    assert base_client.request.call_count == 2
    logger.warning.assert_called_once()


def test_request_retries_on_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    base_client = Mock()
    first = Mock()
    first.status_code = 500
    second = Mock()
    second.status_code = 200
    base_client.request.side_effect = [first, second]
    metrics = Mock(spec=MetricsPortABC)
    client = UnifiedAPIClientImpl(
        provider="chembl",
        config=ClientConfig(max_retries=1, backoff_factor=0.1),
        base_client=base_client,
        metrics=metrics,
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.clients.base.impl.unified_api_client_impl.time.sleep",
        lambda *_: None,
    )

    result = client.request("GET", "https://example.org")

    assert result is second
    assert base_client.request.call_count == 2
    metrics.inc_counter.assert_any_call(
        "client_request_errors",
        {"provider": "chembl", "endpoint": "https://example.org", "status": "500"},
    )
