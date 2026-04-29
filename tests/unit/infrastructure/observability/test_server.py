"""Unit tests for Prometheus metrics server."""

from __future__ import annotations

import errno
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.server import (
    delete_metrics_from_gateway,
    get_metrics_server_runtime_status,
    MetricsServerError,
    is_metrics_server_running,
    push_metrics_to_gateway,
    reset_server_state,
    start_metrics_server,
)

_STARTED_AT = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_server():
    """Reset server state before each test."""
    reset_server_state()
    yield
    reset_server_state()


@pytest.mark.unit
class TestStartMetricsServer:
    """Tests for start_metrics_server function."""

    def test_returns_true_on_success(self):
        """Test successful server start returns True."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            result = start_metrics_server(port=9999, started_at=_STARTED_AT)

            assert result is True
            mock_server.assert_called_once_with(9999, addr="0.0.0.0")

    def test_successful_start_emits_metrics_server_publication_event(self):
        """Server startup should publish bounded self-telemetry before runs exit."""
        with (
            patch("bioetl.infrastructure.observability.server.start_http_server"),
            patch(
                "bioetl.infrastructure.observability.server."
                "METRICS_PUBLICATION_EVENTS_TOTAL"
            ) as mock_metric,
        ):
            result = start_metrics_server(port=9999, started_at=_STARTED_AT)

        assert result is True
        mock_metric.labels.assert_called_once_with(
            pipeline="unknown",
            run_type="unknown",
            target="metrics_server",
            status="success",
        )
        mock_metric.labels().inc.assert_called_once_with()

    def test_idempotent_multiple_calls(self):
        """Test server is only started once."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            result1 = start_metrics_server(port=9999, started_at=_STARTED_AT)
            result2 = start_metrics_server(port=9999, started_at=_STARTED_AT)

            assert result1 is True
            assert result2 is True
            # Should only be called once
            mock_server.assert_called_once()

    def test_runtime_status_tracks_live_server_metadata(self):
        """Test runtime status exposes port, addr, and start time after startup."""
        with patch("bioetl.infrastructure.observability.server.start_http_server"):
            result = start_metrics_server(
                port=9999,
                addr="127.0.0.1",
                started_at=_STARTED_AT,
            )

        assert result is True
        status = get_metrics_server_runtime_status()
        assert status.running is True
        assert status.port == 9999
        assert status.addr == "127.0.0.1"
        assert status.started_at == _STARTED_AT

    def test_lenient_mode_returns_false_on_port_conflict(self):
        """Test fail_fast=False returns False on port conflict instead of raising."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
            )

            assert result is False

    def test_lenient_port_conflict_emits_metrics_server_failure_event(self):
        """Fail-open server startup must be visible as failed publication telemetry."""
        with (
            patch(
                "bioetl.infrastructure.observability.server.start_http_server"
            ) as mock_server,
            patch(
                "bioetl.infrastructure.observability.server."
                "METRICS_PUBLICATION_EVENTS_TOTAL"
            ) as mock_metric,
        ):
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
            )

        assert result is False
        mock_metric.labels.assert_called_once_with(
            pipeline="unknown",
            run_type="unknown",
            target="metrics_server",
            status="failed",
        )
        mock_metric.labels().inc.assert_called_once_with()

    def test_fail_fast_raises_on_port_conflict(self):
        """Test fail_fast=True raises MetricsServerError on port conflict."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            with pytest.raises(MetricsServerError) as exc_info:
                start_metrics_server(
                    port=8000,
                    started_at=_STARTED_AT,
                    fail_fast=True,
                )

            assert exc_info.value.port == 8000
            assert exc_info.value.reason == "port_in_use"
            assert exc_info.value.original_error is error

    def test_fail_fast_raises_on_other_os_error(self):
        """Test fail_fast=True raises on other OS errors."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EACCES  # Permission denied
            mock_server.side_effect = error

            with pytest.raises(MetricsServerError) as exc_info:
                start_metrics_server(
                    port=80,
                    started_at=_STARTED_AT,
                    fail_fast=True,
                    retry_count=1,
                )

            assert exc_info.value.reason == "os_error"

    def test_fail_fast_raises_on_unexpected_error(self):
        """Test fail_fast=True raises on unexpected exceptions."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            mock_server.side_effect = RuntimeError("Unexpected")

            with pytest.raises(MetricsServerError) as exc_info:
                start_metrics_server(
                    port=8000,
                    started_at=_STARTED_AT,
                    fail_fast=True,
                )

            assert exc_info.value.reason == "unexpected"

    def test_lenient_mode_returns_false_on_unexpected_error(self):
        """Test fail_fast=False returns False on unexpected error."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            mock_server.side_effect = RuntimeError("Unexpected")

            result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
            )

            assert result is False

    def test_retry_on_transient_os_error(self):
        """Test retries on transient OS errors (not EADDRINUSE)."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.ECONNREFUSED
            # Fail twice, succeed on third attempt
            mock_server.side_effect = [error, error, None]

            with patch("bioetl.infrastructure.observability.server.time.sleep"):
                result = start_metrics_server(
                    port=8000,
                    started_at=_STARTED_AT,
                    fail_fast=False,
                    retry_count=3,
                    retry_delay=0.01,
                )

            assert result is True
            assert mock_server.call_count == 3

    def test_no_retry_on_port_conflict(self):
        """Test no retries when port is in use (EADDRINUSE)."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
                retry_count=3,
            )

            assert result is False
            # Should only try once for EADDRINUSE
            mock_server.assert_called_once()

    def test_port_conflict_does_not_mark_server_running(self):
        """A foreign port conflict must not flip the in-process running flag."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
            )

            assert result is False
            assert is_metrics_server_running() is False

    def test_port_conflict_allows_future_start_attempt(self):
        """A failed foreign bind must not short-circuit a later retry as healthy."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = [error, None]

            first_result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
            )
            second_result = start_metrics_server(
                port=8000,
                started_at=_STARTED_AT,
                fail_fast=False,
            )

            assert first_result is False
            assert second_result is True
            assert mock_server.call_count == 2
            assert is_metrics_server_running() is True

    def test_lenient_mode_returns_false_on_os_error_after_retries(self):
        """Test fail_fast=False returns False after exhausting all retries."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.ECONNREFUSED
            mock_server.side_effect = error

            with patch("bioetl.infrastructure.observability.server.time.sleep"):
                result = start_metrics_server(
                    port=8000,
                    started_at=_STARTED_AT,
                    fail_fast=False,
                    retry_count=2,
                    retry_delay=0.01,
                )

            assert result is False

    def test_with_custom_logger(self):
        """Test server start with custom logger."""
        logger = MagicMock()
        with patch("bioetl.infrastructure.observability.server.start_http_server"):
            result = start_metrics_server(
                port=9999,
                started_at=_STARTED_AT,
                logger=logger,
            )

        assert result is True
        logger.info.assert_called_once()

    def test_already_started_with_logger_debug(self):
        """Test debug log when server already started."""
        logger = MagicMock()
        with patch("bioetl.infrastructure.observability.server.start_http_server"):
            start_metrics_server(port=9999, started_at=_STARTED_AT)
            # Second call should hit the debug path
            result = start_metrics_server(port=9999, logger=logger)

        assert result is True
        logger.debug.assert_called_once_with("Metrics server already started")


@pytest.mark.unit
class TestPushMetricsToGateway:
    """Tests for push_metrics_to_gateway function."""

    def test_push_success(self):
        """Should return True on successful push."""
        with patch("bioetl.infrastructure.observability.server.push_to_gateway"):
            result = push_metrics_to_gateway(gateway="localhost:9091")

        assert result is True

    def test_push_success_with_logger(self):
        """Should log info on successful push."""
        logger = MagicMock()
        with patch("bioetl.infrastructure.observability.server.push_to_gateway"):
            result = push_metrics_to_gateway(
                gateway="localhost:9091",
                run_label="test_job",
                logger=logger,
            )

        assert result is True
        logger.info.assert_called_once()

    def test_push_success_with_grouping_key(self):
        """Should pass grouping_key to push_to_gateway."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway(
                gateway="localhost:9091",
                grouping_key={"pipeline": "chembl_activity"},
            )

        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["grouping_key"] == {"pipeline": "chembl_activity"}

    def test_push_success_emits_publication_metric(self):
        """Successful push should emit one bounded publication success event."""
        with (
            patch("bioetl.infrastructure.observability.server.push_to_gateway"),
            patch(
                "bioetl.infrastructure.observability.server."
                "METRICS_PUBLICATION_EVENTS_TOTAL"
            ) as mock_metric,
        ):
            push_metrics_to_gateway(
                gateway="localhost:9091",
                grouping_key={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                },
            )

        mock_metric.labels.assert_called_once_with(
            pipeline="chembl_activity",
            run_type="incremental",
            target="pushgateway",
            status="success",
        )
        mock_metric.labels().inc.assert_called_once_with()

    def test_push_success_with_multiple_grouping_labels(self):
        """Should preserve all low-cardinality grouping labels."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway(
                gateway="localhost:9091",
                grouping_key={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                },
            )

        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["grouping_key"] == {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
        }

    def test_push_grouping_key_drops_forensic_high_cardinality_labels(self):
        """Pushgateway bridge must use only bounded aggregate grouping labels."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway(
                gateway="localhost:9091",
                grouping_key={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "run_id": "run-123",
                    "request_id": "req-456",
                    "payload_hash": "abcdef",
                },
            )

        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["grouping_key"] == {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
        }

    def test_push_default_gateway(self):
        """Should use localhost:9091 when gateway is None."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway()

        mock_push.assert_called_once()
        assert mock_push.call_args[0][0] == "localhost:9091"
        assert mock_push.call_args[1]["timeout"] == pytest.approx(1.0)

    def test_push_failure_oserror(self):
        """Should return False on OSError."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway",
            side_effect=OSError("Connection refused"),
        ):
            result = push_metrics_to_gateway()

        assert result is False

    def test_push_failure_emits_publication_metric(self):
        """Failed push should emit one bounded publication failure event."""
        with (
            patch(
                "bioetl.infrastructure.observability.server.push_to_gateway",
                side_effect=OSError("Connection refused"),
            ),
            patch(
                "bioetl.infrastructure.observability.server."
                "METRICS_PUBLICATION_EVENTS_TOTAL"
            ) as mock_metric,
        ):
            push_metrics_to_gateway(
                gateway="localhost:9091",
                grouping_key={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                },
            )

        mock_metric.labels.assert_called_once_with(
            pipeline="chembl_activity",
            run_type="incremental",
            target="pushgateway",
            status="failed",
        )
        mock_metric.labels().inc.assert_called_once_with()

    def test_push_failure_connection_error(self):
        """Should return False on ConnectionError."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway",
            side_effect=ConnectionError("Failed"),
        ):
            result = push_metrics_to_gateway()

        assert result is False

    def test_push_failure_timeout_error(self):
        """Should return False on TimeoutError."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway",
            side_effect=TimeoutError("Timed out"),
        ):
            result = push_metrics_to_gateway()

        assert result is False

    def test_push_failure_runtime_error(self):
        """Should return False on RuntimeError."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway",
            side_effect=RuntimeError("Failed"),
        ):
            result = push_metrics_to_gateway()

        assert result is False

    def test_push_failure_logs_warning(self):
        """Should log warning on push failure."""
        logger = MagicMock()
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway",
            side_effect=OSError("Connection refused"),
        ):
            push_metrics_to_gateway(logger=logger)

        logger.warning.assert_called_once()

    def test_push_default_job_label(self):
        """Should use 'bioetl' as default job label."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway()

        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["job"] == "bioetl"

    def test_push_empty_grouping_key_default(self):
        """Should pass empty dict when grouping_key is None."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway()

        call_kwargs = mock_push.call_args[1]
        assert call_kwargs["grouping_key"] == {}

    def test_push_uses_replace_style_gateway_publication(self):
        """Pushgateway publication must replace, not add to, a bounded group."""
        with patch(
            "bioetl.infrastructure.observability.server.push_to_gateway"
        ) as mock_push:
            push_metrics_to_gateway(
                gateway="localhost:9091",
                grouping_key={"pipeline": "chembl_activity"},
            )

        mock_push.assert_called_once()


@pytest.mark.unit
class TestDeleteMetricsFromGateway:
    """Tests for Pushgateway cleanup lifecycle."""

    def test_delete_success_with_grouping_key(self):
        """Should delete only the bounded aggregate grouping key."""
        with patch(
            "bioetl.infrastructure.observability.server.delete_from_gateway"
        ) as mock_delete:
            result = delete_metrics_from_gateway(
                gateway="localhost:9091",
                grouping_key={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "run_id": "run-123",
                    "payload_hash": "abcdef",
                },
            )

        assert result is True
        mock_delete.assert_called_once_with(
            "localhost:9091",
            job="bioetl",
            grouping_key={
                "pipeline": "chembl_activity",
                "run_type": "incremental",
            },
            timeout=pytest.approx(1.0),
        )

    def test_delete_success_emits_publication_metric(self):
        """Successful cleanup should emit one bounded publication success event."""
        with (
            patch("bioetl.infrastructure.observability.server.delete_from_gateway"),
            patch(
                "bioetl.infrastructure.observability.server."
                "METRICS_PUBLICATION_EVENTS_TOTAL"
            ) as mock_metric,
        ):
            delete_metrics_from_gateway(
                gateway="localhost:9091",
                grouping_key={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                },
            )

        mock_metric.labels.assert_called_once_with(
            pipeline="chembl_activity",
            run_type="incremental",
            target="pushgateway",
            status="success",
        )
        mock_metric.labels().inc.assert_called_once_with()

    def test_delete_failure_returns_false_and_emits_publication_metric(self):
        """Failed cleanup should stay best-effort and expose failure telemetry."""
        with (
            patch(
                "bioetl.infrastructure.observability.server.delete_from_gateway",
                side_effect=OSError("Connection refused"),
            ),
            patch(
                "bioetl.infrastructure.observability.server."
                "METRICS_PUBLICATION_EVENTS_TOTAL"
            ) as mock_metric,
        ):
            result = delete_metrics_from_gateway(
                gateway="localhost:9091",
                grouping_key={"pipeline": "chembl_activity"},
            )

        assert result is False
        mock_metric.labels.assert_called_once_with(
            pipeline="chembl_activity",
            run_type="unknown",
            target="pushgateway",
            status="failed",
        )
        mock_metric.labels().inc.assert_called_once_with()


@pytest.mark.unit
class TestResetServerState:
    """Tests for reset_server_state function."""

    def test_reset_allows_restart(self):
        """Should allow starting server again after reset."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            start_metrics_server(port=9999)
            reset_server_state()
            start_metrics_server(port=9999)

            assert mock_server.call_count == 2

    def test_reset_clears_runtime_status_metadata(self):
        """Reset should clear all runtime metadata, not only the running flag."""
        with patch("bioetl.infrastructure.observability.server.start_http_server"):
            start_metrics_server(port=9999, addr="127.0.0.1")

        reset_server_state()
        status = get_metrics_server_runtime_status()
        assert status.running is False
        assert status.port is None
        assert status.addr is None
        assert status.started_at is None


@pytest.mark.unit
class TestMetricsServerError:
    """Tests for MetricsServerError exception."""

    def test_error_attributes(self):
        """Test MetricsServerError has correct attributes."""
        original = OSError("original")
        error = MetricsServerError(port=8000, reason="test", original_error=original)

        assert error.port == 8000
        assert error.reason == "test"
        assert error.original_error is original
        assert "8000" in str(error)
        assert "test" in str(error)

    def test_error_without_original(self):
        """Test MetricsServerError works without original_error."""
        error = MetricsServerError(port=9000, reason="timeout")

        assert error.port == 9000
        assert error.reason == "timeout"
        assert error.original_error is None
