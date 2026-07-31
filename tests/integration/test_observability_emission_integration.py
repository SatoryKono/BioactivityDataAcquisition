# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for runtime observability emission against recording ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType

import pytest

from bioetl.application.observability.observer import (
    LifecyclePhase,
    PipelineObserver,
    PipelineObserverParams,
)
from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import RunType
from tests.helpers.clock import FIXED_TEST_TIME, FixedClock
from tests.helpers.deterministic_ids import deterministic_uuid


@dataclass
class RecordingSpan:
    """Recording span handle that mirrors the OTel context-manager surface."""

    name: str
    attributes: dict[str, object]
    entered: bool = False
    exited: bool = False
    exceptions: list[BaseException] = field(default_factory=list)

    def __enter__(self) -> RecordingSpan:
        self.entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        del exc_type, exc_tb
        self.exited = True
        if exc_val is not None:
            self.exceptions.append(exc_val)

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def record_exception(self, exception: BaseException) -> None:
        self.exceptions.append(exception)


@dataclass
class RecordingOtelTracer:
    """Recording OTel-compatible tracer returned by RecordingTracing."""

    spans: list[RecordingSpan] = field(default_factory=list)

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
    ) -> RecordingSpan:
        span = RecordingSpan(name=name, attributes=dict(attributes or {}))
        self.spans.append(span)
        return span


@dataclass
class RecordingTracing:
    """Recording TracingPort implementation for emission-level assertions."""

    is_noop = False
    tracers: dict[str, RecordingOtelTracer] = field(default_factory=dict)
    flushed: int = 0
    closed: bool = False

    def get_tracer(self, name: str) -> RecordingOtelTracer:
        return self.tracers.setdefault(name, RecordingOtelTracer())

    def flush(self) -> None:
        self.flushed += 1

    def close(self) -> None:
        self.closed = True
        self.flush()

    @property
    def spans(self) -> list[RecordingSpan]:
        return [span for tracer in self.tracers.values() for span in tracer.spans]


@dataclass
class RecordingMetrics:
    """Recording MetricsPort implementation for integration assertions."""

    counters: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)
    histograms: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        self.counters.append((name, value, labels))

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        self.histograms.append((name, value, labels))

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        del name, value, labels

    def close(self) -> None:
        return None


@dataclass
class RecordingLogger:
    """Recording LoggerPort implementation for integration assertions."""

    entries: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)

    def bind(self, **kwargs):  # type: ignore[override]
        del kwargs
        return self

    def info(self, event: str, **kwargs) -> None:  # type: ignore[override]
        self.entries.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs) -> None:  # type: ignore[override]
        self.entries.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs) -> None:  # type: ignore[override]
        self.entries.append(("error", event, kwargs))

    def debug(self, event: str, **kwargs) -> None:  # type: ignore[override]
        self.entries.append(("debug", event, kwargs))

    def exception(self, event: str, **kwargs) -> None:  # type: ignore[override]
        self.entries.append(("exception", event, kwargs))


@pytest.mark.integration
def test_pipeline_observer_emits_metrics_and_logs_through_recording_ports() -> None:
    metrics = RecordingMetrics()
    logger = RecordingLogger()
    observer = PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid("observability.integration.run"),
            run_type=RunType.INCREMENTAL,
            manifest_id="manifest-observability-integration",
            contract_ref="chembl/activity/gold",
            contract_version="1.0.0",
        ),
        metrics=metrics,
        logger=logger,
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=NoOpTracing(),
    )

    with observer:
        started = observer.emit_phase_started(LifecyclePhase.PREFLIGHT)
        observer.emit_event(
            PipelineEvent.PREFLIGHT_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            stage="preflight",
        )
        observer.emit_phase_completed(
            LifecyclePhase.PREFLIGHT,
            started,
            success=True,
            stage="preflight",
        )

    assert any(
        name == "bioetl_observability_events_total"
        and labels["event"] == "preflight_started"
        and labels["pipeline"] == "chembl_activity"
        and labels["provider"] == "chembl"
        for name, _value, labels in metrics.counters
    )
    assert any(
        name == "bioetl_phase_duration_seconds"
        and labels
        == {
            "pipeline": "chembl_activity",
            "phase": "preflight",
            "status": "success",
        }
        for name, _value, labels in metrics.histograms
    )
    assert any(
        level == "info"
        and event == PipelineEvent.PREFLIGHT_COMPLETED
        and context["pipeline"] == "chembl_activity"
        and context["provider"] == "chembl"
        and context["manifest_id"] == "manifest-observability-integration"
        for level, event, context in logger.entries
    )


@pytest.mark.integration
def test_pipeline_observer_emits_tracing_spans_through_recording_port() -> None:
    metrics = RecordingMetrics()
    logger = RecordingLogger()
    tracer = RecordingTracing()
    observer = PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid("observability.integration.tracing.run"),
            run_type=RunType.BACKFILL,
            manifest_id="manifest-observability-tracing",
            contract_ref="chembl/activity/gold",
            contract_version="1.0.0",
        ),
        metrics=metrics,
        logger=logger,
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=tracer,
    )

    with observer:
        observer.emit_event(
            PipelineEvent.PREFLIGHT_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            stage="preflight",
        )

    assert any(
        name == "bioetl_traced_runs_total"
        and labels
        == {
            "pipeline": "chembl_activity",
            "run_type": RunType.BACKFILL.value,
        }
        for name, _value, labels in metrics.counters
    )
    assert len(tracer.spans) == 1
    span = tracer.spans[0]
    assert span.name == "pipeline.chembl_activity"
    assert span.entered is True
    assert span.exited is True
    assert span.exceptions == []
    assert tracer.flushed == 1
    assert span.attributes["bioetl.pipeline"] == "chembl_activity"
    assert span.attributes["bioetl.run_type"] == RunType.BACKFILL.value
    assert span.attributes["bioetl.manifest_id"] == "manifest-observability-tracing"
    assert span.attributes["bioetl.contract_ref"] == "chembl/activity/gold"
    assert span.attributes["bioetl.contract_version"] == "1.0.0"
    assert span.attributes["bioetl.preflight_completed"] is True
    assert span.attributes["bioetl.status"] == "success"
    assert "bioetl.duration_ms" in span.attributes


@pytest.mark.integration
def test_pipeline_observer_emits_failure_signals_through_recording_ports() -> None:
    metrics = RecordingMetrics()
    logger = RecordingLogger()
    tracer = RecordingTracing()
    observer = PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid("observability.integration.failure.run"),
            run_type=RunType.INCREMENTAL,
            manifest_id="manifest-observability-failure",
            contract_ref="chembl/activity/gold",
            contract_version="1.0.0",
        ),
        metrics=metrics,
        logger=logger,
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=tracer,
    )

    expected = RuntimeError("forced failure for observability contract")
    with pytest.raises(RuntimeError, match="forced failure"):
        with observer:
            raise expected

    assert any(
        name == "bioetl_pipeline_runs_total"
        and labels
        == {
            "pipeline": "chembl_activity",
            "run_type": RunType.INCREMENTAL.value,
            "status": "failed",
        }
        for name, _value, labels in metrics.counters
    )
    assert any(
        name == "bioetl_observability_events_total"
        and labels["event"] == PipelineEvent.FAILED
        and labels["severity"] == "error"
        and labels["error_type"] == "runtimeerror"
        for name, _value, labels in metrics.counters
    )
    assert any(
        level == "error"
        and event == PipelineEvent.FAILED
        and context["manifest_id"] == "manifest-observability-failure"
        and context["error_type"] == "RuntimeError"
        for level, event, context in logger.entries
    )
    assert len(tracer.spans) == 1
    span = tracer.spans[0]
    assert span.exited is True
    assert expected in span.exceptions
    assert span.attributes["bioetl.status"] == "failed"
    assert span.attributes["error"] is True


@pytest.mark.integration
def test_pipeline_observer_records_failure_span_and_error_metrics() -> None:
    metrics = RecordingMetrics()
    logger = RecordingLogger()
    tracer = RecordingTracing()
    observer = PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid("observability.integration.failure.run"),
            run_type=RunType.INCREMENTAL,
            manifest_id="manifest-observability-failure",
            contract_ref="chembl/activity/gold",
            contract_version="1.0.0",
        ),
        metrics=metrics,
        logger=logger,
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=tracer,
    )

    with pytest.raises(RuntimeError, match="observer boom"):
        with observer:
            raise RuntimeError("observer boom")

    assert any(
        name == "bioetl_pipeline_runs_total"
        and labels["pipeline"] == "chembl_activity"
        and labels["status"] == "failed"
        for name, _value, labels in metrics.counters
    )
    assert len(tracer.spans) == 1
    span = tracer.spans[0]
    assert span.exited is True
    assert len(span.exceptions) == 2
    assert all(isinstance(exc, RuntimeError) for exc in span.exceptions)
    assert all(str(exc) == "observer boom" for exc in span.exceptions)
    assert span.attributes["bioetl.status"] == "failed"
    assert span.attributes["error"] is True
    assert tracer.flushed == 1


@pytest.mark.integration
def test_composite_pipeline_observer_emits_composite_provider_labels() -> None:
    metrics = RecordingMetrics()
    logger = RecordingLogger()
    observer = PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name="composite_publication",
            run_id=deterministic_uuid("observability.integration.composite.run"),
            run_type=RunType.INCREMENTAL,
            manifest_id="manifest-composite-observability",
            contract_ref="composite/publication/gold",
            contract_version="1.0.0",
        ),
        metrics=metrics,
        logger=logger,
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=NoOpTracing(),
    )

    with observer:
        observer.emit_event(
            PipelineEvent.PREFLIGHT_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            stage="preflight",
        )

    assert any(
        name == "bioetl_observability_events_total"
        and labels["pipeline"] == "composite_publication"
        and labels["provider"] == "composite"
        for name, _value, labels in metrics.counters
    )


@pytest.mark.integration
def test_pipeline_observer_emits_checkpoint_finalize_execution_span() -> None:
    metrics = RecordingMetrics()
    logger = RecordingLogger()
    tracer = RecordingTracing()
    observer = PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid("observability.integration.checkpoint.run"),
            run_type=RunType.INCREMENTAL,
            manifest_id="manifest-checkpoint-observability",
            contract_ref="chembl/activity/gold",
            contract_version="1.0.0",
        ),
        metrics=metrics,
        logger=logger,
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=tracer,
    )

    with observer:
        started = observer.emit_phase_started(LifecyclePhase.EXECUTION)
        observer.emit_event(
            PipelineEvent.EXECUTION_STARTED,
            LifecyclePhase.EXECUTION,
            stage="checkpoint_finalize",
        )
        observer.emit_phase_completed(
            LifecyclePhase.EXECUTION,
            started,
            success=True,
            stage="checkpoint_finalize",
        )

    assert any(
        name == "bioetl_observability_events_total"
        and labels.get("event") == "execution_started"
        for name, _value, labels in metrics.counters
    )
    assert any(span.name == "pipeline.chembl_activity" for span in tracer.spans)
    assert tracer.flushed == 1
