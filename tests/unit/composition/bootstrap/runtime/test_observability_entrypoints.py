"""Tests for runtime observability bootstrap entrypoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
class TestBootstrapLoggerPort:
    """Tests for bootstrap_logger_port runtime entrypoint."""

    @patch("bioetl.composition.bootstrap.runtime.observability.UnifiedLogger")
    def test_bootstrap_logger_port_delegates_to_unified_logger(
        self,
        mock_unified_logger: MagicMock,
    ) -> None:
        """bootstrap_logger_port should pass runtime metadata to UnifiedLogger."""
        from bioetl.composition.bootstrap import bootstrap_logger_port

        run_id = uuid4()
        expected_logger = MagicMock()
        mock_unified_logger.return_value = expected_logger

        logger = bootstrap_logger_port(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="INFO",
        )

        assert logger is expected_logger
        mock_unified_logger.assert_called_once_with(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="INFO",
            json_format=True,
        )


@pytest.mark.unit
class TestMaybeStartMetricsServer:
    """Tests for maybe_start_metrics_server runtime entrypoint."""

    @patch("bioetl.composition.bootstrap.runtime.observability.start_metrics_server")
    def test_passes_config_params(
        self,
        mock_start_server: MagicMock,
    ) -> None:
        """Runtime wrapper should pass settings through to server startup."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.metrics_port = 9090
        settings.metrics_addr = "0.0.0.0"
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 5
        settings.observability.metrics_retry_delay = 2.0

        mock_start_server.return_value = True

        result = maybe_start_metrics_server(settings)

        assert result is True
        mock_start_server.assert_called_once_with(
            port=9090,
            addr="0.0.0.0",
            fail_fast=False,
            retry_count=5,
            retry_delay=2.0,
        )

    @patch("bioetl.composition.bootstrap.runtime.observability.start_metrics_server")
    def test_fail_fast_true_raises_error(
        self,
        mock_start_server: MagicMock,
    ) -> None:
        """Fail-fast mode should propagate MetricsServerError to callers."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server
        from bioetl.interfaces.observability import MetricsServerError

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = True
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        mock_start_server.side_effect = MetricsServerError(
            port=8000,
            reason="port_in_use",
        )

        with pytest.raises(MetricsServerError) as exc_info:
            maybe_start_metrics_server(settings)

        assert exc_info.value.port == 8000
        assert exc_info.value.reason == "port_in_use"

    @patch("bioetl.composition.bootstrap.runtime.observability.start_metrics_server")
    def test_fail_fast_false_propagates_error(
        self,
        mock_start_server: MagicMock,
    ) -> None:
        """Unexpected startup errors should still bubble up to entrypoints."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        mock_start_server.side_effect = Exception("Random failure")

        with pytest.raises(Exception, match="Random failure"):
            maybe_start_metrics_server(settings)

    def test_disabled_metrics_returns_false(self) -> None:
        """Disabled metrics should short-circuit without server startup."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = maybe_start_metrics_server(settings)

        assert result is False

    def test_disabled_metrics_server_returns_false(self) -> None:
        """Disabled metrics server should short-circuit without startup."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False

        result = maybe_start_metrics_server(settings)

        assert result is False
