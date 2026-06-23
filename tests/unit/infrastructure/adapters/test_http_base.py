"""Tests for BaseHttpAdapter health_check logging.

Tests verify that health_check uses HealthCheckMixin for unified
observability across BaseHttpAdapter and BaseSyncAdapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import (
    BaseHttpAdapter,
    build_json_accept_headers,
    build_mailto_user_agent_headers,
)
from bioetl.infrastructure.adapters.common import HttpAdapterDependencyContext


pytestmark = pytest.mark.unit


class StubHttpAdapter(BaseHttpAdapter):
    """Concrete adapter for testing BaseHttpAdapter."""

    provider_name: str = "test_provider"

    def __init__(
        self,
        http_client: Any,
        logger: Any,
        metrics: Any = None,
        dependency_context: HttpAdapterDependencyContext | None = None,
        fail_probe: bool = False,
        probe_error: Exception | None = None,
        probe_status: HealthStatus = HealthStatus.HEALTHY,
        health_endpoint: str = "/health",
    ) -> None:
        super().__init__(
            http_client=http_client,
            logger=logger,
            metrics=metrics,
            dependency_context=dependency_context,
        )
        self._fail_probe = fail_probe
        self._probe_error = probe_error or Exception("Probe failed")
        self._probe_status = probe_status
        self._health_endpoint = health_endpoint

    async def _probe_health(self) -> HealthStatus:
        """Test implementation that can be configured to fail."""
        if self._fail_probe:
            raise self._probe_error
        return self._probe_status

    def _get_health_endpoint(self) -> str:
        """Return test health endpoint."""
        return self._health_endpoint

    async def fetch(
        self,
        entity: str,
        query: str | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Not used in these tests."""
        yield {}  # pragma: no cover


@dataclass
class DataclassBootstrapStub(BaseHttpAdapter):
    """Dataclass-style adapter using shared BaseHttpAdapter helpers."""

    http_client: Any
    logger: Any
    metrics: Any = None
    dependency_context: HttpAdapterDependencyContext | None = None
    provider_name: str = "dataclass_stub"

    def __post_init__(self) -> None:
        self._bootstrap_dataclass_http_adapter()

    async def _probe_health(self) -> HealthStatus:
        return HealthStatus.HEALTHY

    def _get_health_endpoint(self) -> str:
        return "/health"

    async def fetch(
        self,
        entity: str,
        query: str | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Any:
        yield {}  # pragma: no cover


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port for testing."""
    return MagicMock()


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for testing."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    # Mock circuit breaker for fallback health status
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = MagicMock(value="closed")
    client.circuit_breaker.get_failure_count.return_value = 0
    return client


class TestHealthCheckLogging:
    """Tests for health_check logging behavior via HealthCheckMixin."""

    def test_init_uses_default_error_handler_factory(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that constructor delegates default error handler creation."""
        error_handler = MagicMock()

        with patch(
            "bioetl.infrastructure.adapters.base.create_default_error_handler",
            return_value=error_handler,
        ) as factory:
            adapter = StubHttpAdapter(
                http_client=mock_http_client,
                logger=mock_logger,
                metrics=mock_metrics,
            )

        assert adapter._error_handler is error_handler
        factory.assert_called_once_with(logger=mock_logger, metrics=mock_metrics)

    def test_init_uses_default_metrics_helpers(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that constructor delegates default metrics helper creation."""
        adapter_metrics = MagicMock()
        request_collector = MagicMock()

        with (
            patch(
                "bioetl.infrastructure.adapters.base.create_default_error_handler",
                return_value=MagicMock(),
            ),
            patch(
                "bioetl.infrastructure.adapters.base.create_default_adapter_metrics",
                return_value=adapter_metrics,
            ) as metrics_factory,
            patch(
                "bioetl.infrastructure.adapters.base.create_default_request_collector",
                return_value=request_collector,
            ) as collector_factory,
        ):
            adapter = StubHttpAdapter(
                http_client=mock_http_client,
                logger=mock_logger,
                metrics=mock_metrics,
            )

        assert adapter._adapter_metrics is adapter_metrics
        assert adapter._request_collector is request_collector
        metrics_factory.assert_called_once_with(
            metrics=mock_metrics,
            provider="test_provider",
        )
        collector_factory.assert_called_once_with()

    def test_init_uses_dependency_context_without_default_factories(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Dependency context should bypass inline helper construction."""
        dependency_context = HttpAdapterDependencyContext(
            metrics=mock_metrics,
            error_handler=MagicMock(name="error_handler"),
            adapter_metrics=MagicMock(name="adapter_metrics"),
            request_collector=MagicMock(name="request_collector"),
        )

        with (
            patch(
                "bioetl.infrastructure.adapters.base.create_default_error_handler",
            ) as error_factory,
            patch(
                "bioetl.infrastructure.adapters.base.create_default_adapter_metrics",
            ) as metrics_factory,
            patch(
                "bioetl.infrastructure.adapters.base.create_default_request_collector",
            ) as collector_factory,
        ):
            adapter = StubHttpAdapter(
                http_client=mock_http_client,
                logger=mock_logger,
                dependency_context=dependency_context,
            )

        assert adapter.metrics is mock_metrics
        assert adapter._error_handler is dependency_context.error_handler
        assert adapter._adapter_metrics is dependency_context.adapter_metrics
        assert adapter._request_collector is dependency_context.request_collector
        error_factory.assert_not_called()
        metrics_factory.assert_not_called()
        collector_factory.assert_not_called()

    def test_dataclass_bootstrap_helper_initializes_base_runtime(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Dataclass-style adapters can reuse centralized BaseHttpAdapter bootstrap."""
        adapter = DataclassBootstrapStub(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
        )

        assert adapter._http_client is mock_http_client
        assert adapter._logger is mock_logger
        assert adapter.metrics is mock_metrics
        assert adapter._adapter_metrics is not None
        assert adapter._request_collector is not None

    def test_bind_fallback_fetch_service_helper_sets_canonical_attribute(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Fallback-aware adapters can bind the shared orchestrator via base helper."""
        adapter = DataclassBootstrapStub(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        fallback_service = MagicMock(name="fallback_fetch_service")

        adapter._bind_fallback_fetch_service(fallback_service)

        assert adapter._fallback_fetch_service is fallback_service

    def test_build_json_accept_headers_supports_optional_fields(self) -> None:
        headers = build_json_accept_headers(
            "agent/1.0",
            correlation_id=123,
            extra_headers={"X-Test": "yes"},
        )

        assert headers == {
            "User-Agent": "agent/1.0",
            "Accept": "application/json",
            "X-Correlation-ID": "123",
            "X-Test": "yes",
        }

    def test_build_mailto_user_agent_headers_uses_polite_pool_format(self) -> None:
        headers = build_mailto_user_agent_headers("bioetl@example.org")

        assert headers == {
            "User-Agent": "BioETL/1.0 (mailto:bioetl@example.org)",
            "Accept": "application/json",
        }

    def test_getattr_resolves_public_aliases_for_dataclass_style_runtime(self) -> None:
        adapter = object.__new__(DataclassBootstrapStub)
        http_client = MagicMock(name="http_client")
        logger = MagicMock(name="logger")
        adapter.__dict__.update(
            {
                "http_client": http_client,
                "logger": logger,
                "metrics": None,
            }
        )

        assert adapter._http_client is http_client
        assert adapter._logger is logger
        assert adapter._metrics is None
        assert adapter.__dict__["_http_client"] is http_client
        assert adapter.__dict__["_logger"] is logger
        assert "_metrics" in adapter.__dict__

    def test_getattr_raises_for_unknown_private_alias(self) -> None:
        adapter = object.__new__(DataclassBootstrapStub)
        adapter.__dict__.update(
            {
                "http_client": MagicMock(),
                "logger": MagicMock(),
                "metrics": None,
            }
        )

        with pytest.raises(AttributeError, match="missing_attr"):
            _ = adapter.missing_attr

    @pytest.mark.asyncio
    async def test_async_context_methods_delegate_to_http_client(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        adapter = DataclassBootstrapStub(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        entered = await adapter.__aenter__()
        await adapter.__aexit__(RuntimeError, RuntimeError("boom"), None)
        await adapter._close_http_client_context()
        await adapter.aclose()

        assert entered is adapter
        mock_http_client.__aenter__.assert_awaited_once()
        assert mock_http_client.__aexit__.await_count == 2

    async def test_health_check_logs_warning_on_exception(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check logs warning when _probe_health raises."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=True,
            probe_error=ConnectionError("Connection refused"),
        )

        status = await adapter.health_check()

        # Verify warning was logged with correct parameters (via HealthCheckMixin)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["error_type"] == "ConnectionError"
        assert call_kwargs["error_message"] == "Connection refused"
        assert call_kwargs["endpoint"] == "/health"
        assert "latency_seconds" in call_kwargs

        # Fallback status should be returned
        assert status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    async def test_health_check_increments_failure_metric_on_exception(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check increments failure metric when _probe_health raises."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=True,
        )

        await adapter.health_check()

        # Verify failure metric was incremented (via HealthCheckMixin)
        calls = mock_metrics.increment_counter.call_args_list
        failure_call = next(
            (c for c in calls if c[0][0] == "bioetl_health_check_failures_total"),
            None,
        )
        assert failure_call is not None
        assert failure_call[0][1] == 1
        assert failure_call[0][2] == {"provider": "test_provider"}

    async def test_health_check_logs_debug_and_increments_success_on_success(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check logs debug and increments success metric on success."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=False,
        )

        status = await adapter.health_check()

        # No warning should be logged on success
        mock_logger.warning.assert_not_called()

        # Debug log should be emitted (via HealthCheckMixin)
        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["status"] == HealthStatus.HEALTHY.value
        assert "latency_seconds" in call_kwargs

        # Success metric should be incremented
        calls = mock_metrics.increment_counter.call_args_list
        success_call = next(
            (c for c in calls if c[0][0] == "bioetl_health_check_success_total"),
            None,
        )
        assert success_call is not None
        assert success_call[0][2] == {"provider": "test_provider"}

        assert status == HealthStatus.HEALTHY

    async def test_health_check_increments_degraded_metric_on_degraded_result(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that DEGRADED probe results are counted separately from healthy success."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            probe_status=HealthStatus.DEGRADED,
        )

        status = await adapter.health_check()

        degraded_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_degraded_total"
            ),
            None,
        )
        success_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_success_total"
            ),
            None,
        )

        assert degraded_call is not None
        assert degraded_call[0][2] == {"provider": "test_provider"}
        assert success_call is None
        mock_logger.warning.assert_called_once()
        assert status == HealthStatus.DEGRADED

    async def test_health_check_records_latency_histogram(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check records latency histogram for both success and failure."""
        # Test success case
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=False,
        )

        await adapter.health_check()

        # Verify histogram was observed (via HealthCheckMixin)
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "bioetl_health_check_latency_seconds"
        assert isinstance(call_args[0][1], float)  # latency value
        assert call_args[0][2] == {"provider": "test_provider"}

    async def test_health_check_uses_noop_metrics_by_default(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that health_check works without explicit metrics (uses NoOpMetrics)."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            fail_probe=True,
        )

        # Should not raise even without explicit metrics
        status = await adapter.health_check()

        # Should still log warning
        mock_logger.warning.assert_called_once()
        assert status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    async def test_health_check_logs_correct_error_type(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check logs the correct error type name."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=True,
            probe_error=TimeoutError("Request timed out"),
        )

        await adapter.health_check()

        # Verify error_type is the exception class name (via HealthCheckMixin)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "TimeoutError"
        assert call_kwargs["error_message"] == "Request timed out"

    async def test_check_health_also_uses_mixin_for_observability(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that check_health() also uses HealthCheckMixin for observability."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=False,
        )

        result = await adapter.check_health()

        # Debug log should be emitted (via HealthCheckMixin)
        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["status"] == HealthStatus.HEALTHY.value

        # Result should contain expected fields
        assert result.status == HealthStatus.HEALTHY
        assert result.provider == "test_provider"
        assert result.endpoint == "/health"
        assert result.latency_ms > 0

    async def test_check_health_failure_also_uses_mixin_for_observability(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that check_health() uses HealthCheckMixin on failure."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=True,
            probe_error=ConnectionError("Connection refused"),
        )

        result = await adapter.check_health()

        # Warning log should be emitted (via HealthCheckMixin)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "ConnectionError"
        assert call_kwargs["error_message"] == "Connection refused"

        # Result should contain error details
        assert result.status == HealthStatus.UNHEALTHY
        assert result.last_error == "Connection refused"
        assert result.provider == "test_provider"
