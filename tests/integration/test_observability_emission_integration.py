"""Integration tests for runtime observability emission against recording ports."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bioetl.application.observability.observer import LifecyclePhase, PipelineObserver
from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import RunType
from tests.helpers.clock import FIXED_TEST_TIME, FixedClock
from tests.helpers.deterministic_ids import deterministic_uuid


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
        pipeline_name="chembl_activity",
        run_id=deterministic_uuid("observability.integration.run"),
        run_type=RunType.INCREMENTAL,
        metrics=metrics,
        logger=logger,  # type: ignore[arg-type]
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=NoOpTracing(),
        manifest_id="manifest-observability-integration",
        contract_ref="chembl/activity/gold",
        contract_version="1.0.0",
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
        and labels == {
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
