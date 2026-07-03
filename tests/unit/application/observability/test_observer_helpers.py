"""Focused unit tests for low-level PipelineObserver helper branches."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bioetl.application.observability.observer import LifecyclePhase, PipelineObserver
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import RunType
from tests.helpers.clock import FIXED_TEST_TIME, FixedClock
from tests.helpers.deterministic_ids import deterministic_uuid


@dataclass
class _RecordingMetrics:
    counters: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)
    histograms: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)

    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        self.counters.append((name, value, labels))

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        self.histograms.append((name, value, labels))

    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        del name, value, labels

    def close(self) -> None:
        return None


@dataclass
class _RecordingLogger:
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


class _RaisingSpan:
    def set_attribute(self, key: str, value: object) -> None:
        del key, value
        raise ValueError("best effort")


def _build_observer(
    *,
    pipeline_name: str = "chembl_activity",
) -> tuple[PipelineObserver, _RecordingMetrics, _RecordingLogger]:
    metrics = _RecordingMetrics()
    logger = _RecordingLogger()
    observer = PipelineObserver(
        pipeline_name=pipeline_name,
        run_id=deterministic_uuid(f"observer.{pipeline_name}"),
        run_type=RunType.INCREMENTAL,
        metrics=metrics,
        logger=logger,  # type: ignore[arg-type]
        clock=FixedClock(FIXED_TEST_TIME),
        tracer=NoOpTracing(),
    )
    return observer, metrics, logger


@pytest.mark.unit
def test_resolve_domain_event_phase_prefers_fallback() -> None:
    result = PipelineObserver._resolve_domain_event_phase(
        "postrun",
        fallback=LifecyclePhase.PREFLIGHT,
    )

    assert result is LifecyclePhase.PREFLIGHT


@pytest.mark.unit
def test_resolve_domain_event_phase_invalid_hint_falls_back_to_execution() -> None:
    result = PipelineObserver._resolve_domain_event_phase(
        "not-a-phase",
        fallback=None,
    )

    assert result is LifecyclePhase.EXECUTION


@pytest.mark.unit
def test_emit_event_ignores_span_attribute_failures() -> None:
    observer, metrics, logger = _build_observer()
    observer.span = _RaisingSpan()

    observer.emit_event(
        "phase_started",
        LifecyclePhase.PREFLIGHT,
        level="warning",
        stage="preflight",
    )

    assert metrics.counters
    assert logger.entries[0][0] == "warning"
    assert logger.entries[0][1] == "phase_started"


@pytest.mark.unit
def test_emit_phase_completed_tracks_success_histogram_and_counter() -> None:
    observer, metrics, _logger = _build_observer()

    observer.emit_phase_completed(
        LifecyclePhase.PREFLIGHT,
        start_time=0.0,
        success=True,
        stage="preflight",
    )

    assert observer._completed_stage_count == 1
    assert metrics.histograms
    assert metrics.histograms[0][0] == "bioetl_phase_duration_seconds"
    assert metrics.histograms[0][2]["status"] == "success"


@pytest.mark.unit
def test_emit_phase_completed_failed_does_not_increment_completed_stage_count() -> None:
    observer, metrics, _logger = _build_observer()

    observer.emit_phase_completed(
        LifecyclePhase.EXECUTION,
        start_time=0.0,
        success=False,
        stage="execution",
    )

    assert observer._completed_stage_count == 0
    assert metrics.histograms[0][2]["status"] == "failed"


@pytest.mark.unit
def test_pipeline_name_derivation_handles_noncanonical_names() -> None:
    assert PipelineObserver._derive_provider_name("pubchem") == "pubchem"
    assert PipelineObserver._derive_provider_name("_compound") == "_compound"
    assert PipelineObserver._derive_entity_name("pubchem") is None
    assert PipelineObserver._derive_entity_name("pubchem_") is None


@pytest.mark.unit
def test_capture_execution_metrics_uses_max_terminal_count_and_clamps_negative() -> (
    None
):
    observer, _metrics, _logger = _build_observer(pipeline_name="custom_pipeline")

    observer.capture_execution_metrics(
        {
            "records_gold": 3,
            "records_silver": 8,
            "records_bronze": -5,
            "records_fetched": 6,
        }
    )
    assert observer._terminal_records_processed == 8

    observer.capture_execution_metrics({})
    assert observer._terminal_records_processed == 0
