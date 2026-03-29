"""Unit tests for PipelineObserver.

Tests cover:
- O4: Observer tests for duration, errors, graceful shutdown
- Unified Observability: Lifecycle event emission tests
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
from bioetl.application.observability.observer import LifecyclePhase, PipelineObserver
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.observability_contract import (
    ObservabilityContractPayload,
    missing_observability_fields,
)
from bioetl.domain.types import RunType


@pytest.fixture
def metrics_mock():
    mock = MagicMock()
    mock.observe_histogram = MagicMock()
    mock.increment_counter = MagicMock()
    return mock


@pytest.fixture
def logger_mock():
    mock = MagicMock()
    mock.info = MagicMock()
    mock.error = MagicMock()
    mock.warning = MagicMock()
    mock.debug = MagicMock()
    return mock


@pytest.fixture
def tracer_mock():
    """Create a mock tracer that returns a mock span."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    mock_span.set_attribute = MagicMock()
    mock_span.record_exception = MagicMock()

    mock_otel_tracer = MagicMock()
    mock_otel_tracer.start_as_current_span = MagicMock(return_value=mock_span)

    mock_tracer = MagicMock()
    mock_tracer.get_tracer = MagicMock(return_value=mock_otel_tracer)
    mock_tracer.close = MagicMock()
    mock_tracer.flush = MagicMock()

    return mock_tracer


@pytest.fixture
def run_id():
    return uuid4()


def test_pipeline_observer_success(metrics_mock, logger_mock, run_id):
    """Test successful pipeline execution."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with observer:
        pass  # Successful execution

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[0][0] == "pipeline_duration_seconds"
    assert isinstance(call_args[0][1], float)
    assert call_args[1]["labels"]["status"] == "success"
    assert call_args[1]["labels"]["pipeline"] == "test_pipeline"

    # Verify run counter is emitted (along with unified observability counters)
    run_counter_calls = [
        call
        for call in metrics_mock.increment_counter.call_args_list
        if call[0][0] == "bioetl_pipeline_runs_total"
    ]
    assert len(run_counter_calls) == 1

    # Verify logs: start and finish
    assert logger_mock.info.call_count == 2


def test_pipeline_observer_failure(metrics_mock, logger_mock, run_id):
    """Test failed pipeline execution."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with pytest.raises(ValueError), observer:
        raise ValueError("Something went wrong")

    # Verify metrics
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[1]["labels"]["status"] == "failed"

    # Verify error was logged
    logger_mock.error.assert_called_once()


def test_pipeline_observer_shutdown(metrics_mock, logger_mock, run_id):
    """Test pipeline execution with shutdown signal."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with pytest.raises(PipelineShutdownError), observer:
        raise PipelineShutdownError()

    # Verify metrics show shutdown status
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[1]["labels"]["status"] == "shutdown"

    # Verify warning was logged
    logger_mock.warning.assert_called_once()


# ==================== O4: New Observer Tests ====================


def test_observer_records_duration(metrics_mock, logger_mock, run_id):
    """O4: Histogram records duration with correct labels."""
    observer = PipelineObserver(
        pipeline_name="chembl_activity",
        run_id=run_id,
        run_type=RunType.REBUILD,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with observer:
        pass  # Successful execution

    # Verify histogram was called with correct metric name
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args

    # Check metric name
    assert call_args[0][0] == "pipeline_duration_seconds"

    # Check duration is a positive float
    duration = call_args[0][1]
    assert isinstance(duration, float)
    assert duration >= 0

    # Check labels contain required fields
    labels = call_args[1]["labels"]
    assert labels["pipeline"] == "chembl_activity"
    assert labels["run_type"] == "rebuild"
    assert labels["status"] == "success"


def test_observer_tracks_errors(metrics_mock, logger_mock, run_id):
    """O4: Counter increments by error_type on failure."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
    )

    with pytest.raises(RuntimeError), observer:
        raise RuntimeError("Test error")

    # Verify run counter was incremented for failed status
    run_counter_calls = [
        call
        for call in metrics_mock.increment_counter.call_args_list
        if call[0][0] == "bioetl_pipeline_runs_total"
    ]
    assert len(run_counter_calls) == 1
    call_args = run_counter_calls[0]

    assert call_args[0][0] == "bioetl_pipeline_runs_total"
    assert call_args[0][1] == 1
    assert call_args[1]["labels"]["status"] == "failed"

    # Verify error was logged with error_type
    logger_mock.error.assert_called_once()
    error_call_args = logger_mock.error.call_args
    assert "error_type" in error_call_args[1]
    assert error_call_args[1]["error_type"] == "RuntimeError"


def test_observer_graceful_shutdown(metrics_mock, logger_mock, tracer_mock, run_id):
    """O4: Spans are flushed at close()."""
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
        tracer=tracer_mock,
    )

    with observer:
        pass  # Successful execution

    # Verify span was created and ended properly
    tracer_mock.get_tracer.assert_called_once_with("bioetl.pipeline")

    # Verify span __enter__ and __exit__ were called
    mock_span = tracer_mock.get_tracer.return_value.start_as_current_span.return_value
    mock_span.__enter__.assert_called_once()
    mock_span.__exit__.assert_called_once()
    tracer_mock.flush.assert_called_once()

    # Verify span attributes were set
    mock_span.set_attribute.assert_any_call("bioetl.status", "success")

    traced_run_calls = [
        call
        for call in metrics_mock.increment_counter.call_args_list
        if call[0][0] == "traced_runs_total"
    ]
    assert len(traced_run_calls) == 1
    assert traced_run_calls[0][1]["labels"] == {
        "pipeline": "test_pipeline",
        "run_type": "incremental",
    }


def test_observer_handles_close_error(metrics_mock, logger_mock, tracer_mock, run_id):
    """O4: Error at close() doesn't fail pipeline."""
    # Configure tracer to raise error on span exit
    mock_span = tracer_mock.get_tracer.return_value.start_as_current_span.return_value
    mock_span.__exit__ = MagicMock(side_effect=RuntimeError("Tracer close error"))

    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
        tracer=tracer_mock,
    )

    # Should not raise despite tracer error
    with observer:
        pass

    # Pipeline should still record success metrics
    metrics_mock.observe_histogram.assert_called_once()
    call_args = metrics_mock.observe_histogram.call_args
    assert call_args[1]["labels"]["status"] == "success"


def test_observer_does_not_emit_traced_run_metric_for_noop_tracing(
    metrics_mock, logger_mock, run_id
):
    observer = PipelineObserver(
        pipeline_name="test_pipeline",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        metrics=metrics_mock,
        logger=logger_mock,
        tracer=NoOpTracing(),
    )

    with observer:
        pass

    traced_run_calls = [
        call
        for call in metrics_mock.increment_counter.call_args_list
        if call[0][0] == "traced_runs_total"
    ]
    assert traced_run_calls == []


# ==================== Unified Observability: Lifecycle Event Tests ====================


class TestLifecyclePhase:
    """Tests for LifecyclePhase enum."""

    def test_lifecycle_phase_values(self):
        """Test that all expected phases are defined."""
        expected_phases = [
            "startup",
            "preflight",
            "lifecycle_clear",
            "execution",
            "postrun",
            "cleanup",
        ]
        actual_phases = [phase.value for phase in LifecyclePhase]
        assert actual_phases == expected_phases

    def test_lifecycle_phase_is_string_enum(self):
        """Test that LifecyclePhase values are strings."""
        for phase in LifecyclePhase:
            assert isinstance(phase.value, str)


class TestObserverEmitEvent:
    """Tests for emit_event() unified event emission."""

    def test_emit_event_logs_with_context(self, metrics_mock, logger_mock, run_id):
        """Test emit_event logs event with structured context."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_event(
            "custom_event",
            LifecyclePhase.PREFLIGHT,
            level="info",
            custom_key="custom_value",
        )

        logger_mock.info.assert_called_once()
        call_args = logger_mock.info.call_args
        assert call_args[0][0] == "custom_event"
        assert call_args[1]["phase"] == "preflight"
        assert call_args[1]["pipeline"] == "test_pipeline"
        assert call_args[1]["provider"] == "test"
        assert call_args[1]["run_id"] == str(run_id)
        assert call_args[1]["severity"] == "info"
        assert call_args[1]["error_type"] == "none"
        assert call_args[1]["custom_key"] == "custom_value"

        metrics_mock.increment_counter.assert_called_once_with(
            "observability_events_total",
            1,
            labels={
                "event": "custom_event",
                "provider": "test",
                "pipeline": "test_pipeline",
                "severity": "info",
                "error_type": "none",
            },
        )

    def test_emit_event_includes_extended_correlation_context(
        self,
        metrics_mock,
        logger_mock,
        run_id,
    ):
        observer = PipelineObserver(
            pipeline_name="chembl_activity",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
            manifest_id="manifest-1",
            effective_config_hash="sha256:abc",
            contract_ref="gold.activity",
            contract_version="1.0.0",
            composite_run_id="composite-7",
        )

        observer.emit_event(
            "preflight_started",
            LifecyclePhase.PREFLIGHT,
            level="info",
        )

        logger_mock.info.assert_called_once()
        context = logger_mock.info.call_args[1]
        assert context["event_family"] == "pipeline.phase"
        assert context["manifest_id"] == "manifest-1"
        assert context["entity"] == "activity"
        assert context["run_type"] == "incremental"
        assert context["effective_config_hash"] == "sha256:abc"
        assert context["contract_ref"] == "gold.activity"
        assert context["contract_version"] == "1.0.0"
        assert context["composite_run_id"] == "composite-7"

    def test_emit_event_uses_correct_log_level(self, metrics_mock, logger_mock, run_id):
        """Test emit_event routes to correct log level."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        # Test warning level
        observer.emit_event("warn_event", LifecyclePhase.POSTRUN, level="warning")
        logger_mock.warning.assert_called_once()

        # Test error level
        observer.emit_event("error_event", LifecyclePhase.POSTRUN, level="error")
        logger_mock.error.assert_called_once()

    def test_emit_event_adds_span_attribute(
        self, metrics_mock, logger_mock, tracer_mock, run_id
    ):
        """Test emit_event adds span attribute when tracing is active."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
            tracer=tracer_mock,
        )

        with observer:
            observer.emit_event("test_event", LifecyclePhase.EXECUTION)

        # Verify span attribute was set
        mock_span = (
            tracer_mock.get_tracer.return_value.start_as_current_span.return_value
        )
        mock_span.set_attribute.assert_any_call("bioetl.test_event", True)


class TestObserverEmitPhase:
    """Tests for phase start/complete event emission."""

    def test_emit_phase_started_returns_timestamp(
        self, metrics_mock, logger_mock, run_id
    ):
        """Test emit_phase_started returns valid timestamp."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        start_time = observer.emit_phase_started(LifecyclePhase.PREFLIGHT)

        assert isinstance(start_time, float)
        assert start_time > 0
        logger_mock.info.assert_called_once()
        call_args = logger_mock.info.call_args
        assert call_args[0][0] == "preflight_started"
        assert call_args[1]["phase"] == "preflight"
        assert call_args[1]["pipeline"] == "test_pipeline"
        assert call_args[1]["provider"] == "test"
        assert call_args[1]["run_id"] == str(run_id)
        assert call_args[1]["severity"] == "info"
        assert call_args[1]["error_type"] == "none"

    def test_emit_phase_completed_records_duration_metric(
        self, metrics_mock, logger_mock, run_id
    ):
        """Test emit_phase_completed records duration in histogram."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        start_time = observer.emit_phase_started(LifecyclePhase.EXECUTION)
        observer.emit_phase_completed(
            LifecyclePhase.EXECUTION, start_time, success=True
        )

        # Find the phase duration metric call
        histogram_calls = metrics_mock.observe_histogram.call_args_list
        phase_call = None
        for call in histogram_calls:
            if call[0][0] == "bioetl_phase_duration_seconds":
                phase_call = call
                break

        assert phase_call is not None
        assert phase_call[1]["labels"]["phase"] == "execution"
        assert phase_call[1]["labels"]["status"] == "success"

    def test_emit_phase_completed_logs_failure(self, metrics_mock, logger_mock, run_id):
        """Test emit_phase_completed logs error on failure."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        import time

        start_time = time.monotonic()
        observer.emit_phase_completed(
            LifecyclePhase.PREFLIGHT, start_time, success=False
        )

        # Verify error was logged for failed phase
        logger_mock.error.assert_called_once()


class TestObserverHealthCheckEvents:
    """Tests for health check event emission."""

    def test_emit_health_check_result_healthy(self, metrics_mock, logger_mock, run_id):
        """Test emit_health_check_result for healthy component."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_health_check_result(
            component="storage",
            healthy=True,
            duration_ms=50.0,
        )

        logger_mock.info.assert_called()
        metrics_mock.set_gauge.assert_called_with(
            "pipeline_health_check_passed",
            1.0,
            {"pipeline": "test_pipeline", "component": "storage"},
        )

    def test_emit_health_check_result_unhealthy(
        self, metrics_mock, logger_mock, run_id
    ):
        """Test emit_health_check_result for unhealthy component."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_health_check_result(
            component="data_source",
            healthy=False,
            duration_ms=100.0,
        )

        logger_mock.warning.assert_called()
        metrics_mock.set_gauge.assert_called_with(
            "pipeline_health_check_passed",
            0.0,
            {"pipeline": "test_pipeline", "component": "data_source"},
        )


class TestObserverDQEvents:
    """Tests for data quality anomaly event emission."""

    def test_emit_dq_anomaly_warning(self, metrics_mock, logger_mock, run_id):
        """Test emit_dq_anomaly for warning severity."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_dq_anomaly(
            metric_name="error_rate",
            severity="warning",
            anomaly_type="spike",
            current_value=0.15,
            baseline_mean=0.05,
        )

        logger_mock.warning.assert_called()
        metrics_mock.increment_counter.assert_called_with(
            "dq_anomaly_detected",
            1,
            {
                "pipeline": "test_pipeline",
                "metric": "error_rate",
                "severity": "warning",
                "anomaly_type": "spike",
            },
        )

    def test_emit_dq_anomaly_critical(self, metrics_mock, logger_mock, run_id):
        """Test emit_dq_anomaly for critical severity."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_dq_anomaly(
            metric_name="record_count",
            severity="critical",
            anomaly_type="drop",
            current_value=0.0,
            baseline_mean=1000.0,
        )

        # Critical uses error level
        logger_mock.error.assert_called()


class TestObserverVacuumEvents:
    """Tests for VACUUM operation event emission."""

    def test_emit_vacuum_result_success(self, metrics_mock, logger_mock, run_id):
        """Test emit_vacuum_result for successful operation."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_vacuum_result(
            layer="silver",
            table="chembl_activity",
            files_removed=42,
            success=True,
        )

        logger_mock.info.assert_called()
        metrics_mock.increment_counter.assert_called_with(
            "vacuum_files_removed_total",
            42,
            {"table": "chembl_activity", "layer": "silver"},
        )

    def test_emit_vacuum_result_failure(self, metrics_mock, logger_mock, run_id):
        """Test emit_vacuum_result for failed operation."""
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_vacuum_result(
            layer="gold",
            table="gold_table",
            files_removed=0,
            success=False,
            error="Table not found",
        )

        logger_mock.warning.assert_called()
        # VACUUM metric should NOT be incremented on failure.
        vacuum_calls = [
            call
            for call in metrics_mock.increment_counter.call_args_list
            if call[0][0] == "vacuum_files_removed_total"
        ]
        assert len(vacuum_calls) == 0


# ==================== Smoke Test: Key Lifecycle Events ====================


class TestObserverSmokeTest:
    """Smoke test covering key lifecycle events through unified observer."""

    def test_full_lifecycle_events_flow(self, metrics_mock, logger_mock, run_id):
        """Smoke test: Verify all key lifecycle events flow through observer."""
        observer = PipelineObserver(
            pipeline_name="chembl_activity",
            run_id=run_id,
            run_type=RunType.REBUILD,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        with observer:
            # 1. Preflight phase
            preflight_start = observer.emit_phase_started(LifecyclePhase.PREFLIGHT)
            observer.emit_health_check_result("storage", healthy=True)
            observer.emit_health_check_result("data_source", healthy=True)
            observer.emit_phase_completed(LifecyclePhase.PREFLIGHT, preflight_start)

            # 2. Execution phase
            exec_start = observer.emit_phase_started(LifecyclePhase.EXECUTION)
            observer.emit_event(
                "batch_processed",
                LifecyclePhase.EXECUTION,
                records=100,
            )
            observer.emit_phase_completed(LifecyclePhase.EXECUTION, exec_start)

            # 3. Postrun phase
            postrun_start = observer.emit_phase_started(LifecyclePhase.POSTRUN)
            observer.emit_vacuum_result("silver", "chembl_activity", 5)
            observer.emit_phase_completed(LifecyclePhase.POSTRUN, postrun_start)

        # Verify key events were logged
        assert logger_mock.info.call_count >= 8  # Multiple info events

        # Verify metrics were recorded
        histogram_calls = metrics_mock.observe_histogram.call_args_list
        phase_metrics = [
            c for c in histogram_calls if c[0][0] == "bioetl_phase_duration_seconds"
        ]
        assert len(phase_metrics) == 3  # preflight, execution, postrun

        # Verify health check gauges
        gauge_calls = metrics_mock.set_gauge.call_args_list
        health_gauges = [
            c for c in gauge_calls if c[0][0] == "pipeline_health_check_passed"
        ]
        assert len(health_gauges) == 2  # storage, data_source

        # Verify vacuum counter
        counter_calls = metrics_mock.increment_counter.call_args_list
        vacuum_counters = [
            c for c in counter_calls if c[0][0] == "vacuum_files_removed_total"
        ]
        assert len(vacuum_counters) == 1


class TestObserverContractSchema:
    """Contract-level checks for mandatory observability fields."""

    def test_emit_event_contains_required_canonical_fields(
        self, metrics_mock, logger_mock, run_id
    ):
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_event("contract_event", LifecyclePhase.EXECUTION, level="info")

        logger_mock.info.assert_called_once()
        event_name = logger_mock.info.call_args[0][0]
        context = {"event": event_name, **logger_mock.info.call_args[1]}
        assert missing_observability_fields(context) == ()

    def test_emit_event_ignores_legacy_keys_after_grace_period(
        self, metrics_mock, logger_mock, run_id
    ):
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        observer.emit_event(
            "contract_event",
            LifecyclePhase.EXECUTION,
            provider_name="legacy_provider",
            pipeline_name="legacy_pipeline",
            correlation_id="legacy-run-id",
            log_level="warning",
        )

        logger_mock.info.assert_called_once()
        context = logger_mock.info.call_args[1]
        assert context["provider"] == "test"
        assert context["pipeline"] == "test_pipeline"
        assert context["run_id"] == str(run_id)
        assert context["severity"] == "info"
        assert logger_mock.info.call_args[0][0] == "contract_event"
        # Legacy aliases are ignored and never emitted.
        assert "provider_name" not in context
        assert "pipeline_name" not in context
        assert "correlation_id" not in context
        assert "event_name" not in context

    def test_emit_event_uses_single_contract_validation_point(
        self, metrics_mock, logger_mock, run_id
    ):
        observer = PipelineObserver(
            pipeline_name="test_pipeline",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        payload = ObservabilityContractPayload(
            context={
                "event": "contract_event",
                "provider": "test",
                "pipeline": "test_pipeline",
                "run_id": str(run_id),
                "severity": "info",
                "error_type": "none",
            },
            metric_labels={
                "event": "contract_event",
                "provider": "test",
                "pipeline": "test_pipeline",
                "severity": "info",
                "error_type": "none",
            },
        )

        with patch(
            "bioetl.application.observability.observer.build_observability_contract_payload",
            return_value=payload,
        ) as build_mock:
            observer.emit_event("contract_event", LifecyclePhase.EXECUTION)

        build_mock.assert_called_once()

    def test_full_lifecycle_events_have_required_fields(
        self, metrics_mock, logger_mock, run_id
    ):
        observer = PipelineObserver(
            pipeline_name="chembl_activity",
            run_id=run_id,
            run_type=RunType.REBUILD,
            metrics=metrics_mock,
            logger=logger_mock,
        )

        with observer:
            preflight_start = observer.emit_phase_started(LifecyclePhase.PREFLIGHT)
            observer.emit_health_check_result("storage", healthy=True)
            observer.emit_phase_completed(LifecyclePhase.PREFLIGHT, preflight_start)

        calls = (
            logger_mock.debug.call_args_list
            + logger_mock.info.call_args_list
            + logger_mock.warning.call_args_list
            + logger_mock.error.call_args_list
        )
        assert calls
        for call in calls:
            event_name = call[0][0] if call[0] else ""
            context = {"event": event_name, **call[1]}
            assert missing_observability_fields(context) == ()

        metric_calls = [
            call
            for call in metrics_mock.increment_counter.call_args_list
            if call[0][0] == "observability_events_total"
        ]
        assert metric_calls
        required_metric_labels = {
            "event",
            "provider",
            "pipeline",
            "severity",
            "error_type",
        }
        for call in metric_calls:
            labels = call[1]["labels"]
            assert required_metric_labels.issubset(set(labels))
            for key in required_metric_labels:
                assert str(labels[key]).strip() != ""
