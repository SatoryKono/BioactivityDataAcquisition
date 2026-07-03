"""Golden tests for Prometheus metrics outputs.

Tests that verify the structure and format of metrics emitted by the
PrometheusMetrics adapter against golden master baselines.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    HISTOGRAMS,
    PrometheusMetrics,
)

FIXTURE_DIR = Path("tests/fixtures/golden/observability")
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


def _save_fixture(name: str, payload: dict[str, object]) -> None:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_fixture(name: str) -> dict[str, object]:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _assert_matches_fixture(name: str, payload: dict[str, object]) -> None:
    if UPDATE_SNAPSHOTS:
        _save_fixture(name, payload)
        pytest.skip(f"Updated metrics golden fixture {name}")

    fixture_path = FIXTURE_DIR / f"{name}.json"
    if not fixture_path.exists():
        pytest.fail(
            f"Missing metrics golden fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    expected = _load_fixture(name)
    assert payload == expected, (
        f"Metrics output for {name} does not match golden fixture. "
        f"Run with UPDATE_SNAPSHOTS=1 to update."
    )


def _capture_counter_state() -> dict[str, object]:
    """Capture current state of all counters."""
    metrics = PrometheusMetrics()
    state = {}
    for name, counter in COUNTERS.items():
        state[name] = {
            "description": counter._description,
            "type": "counter",
        }
    return state


def _capture_histogram_state() -> dict[str, object]:
    """Capture current state of all histograms."""
    metrics = PrometheusMetrics()
    state = {}
    for name, histogram in HISTOGRAMS.items():
        state[name] = {
            "description": histogram._description,
            "type": "histogram",
            "buckets": [b for b in histogram._upperbounds],
        }
    return state


@pytest.mark.unit
def test_prometheus_counter_registry_matches_golden() -> None:
    """Prometheus counter registry must match golden baseline."""
    payload = _capture_counter_state()
    _assert_matches_fixture("prometheus_counter_registry", payload)


@pytest.mark.unit
def test_prometheus_histogram_registry_matches_golden() -> None:
    """Prometheus histogram registry must match golden baseline."""
    payload = _capture_histogram_state()
    _assert_matches_fixture("prometheus_histogram_registry", payload)


@pytest.mark.unit
def test_prometheus_metrics_increment_emits_expected_counter() -> None:
    """Counter increment produces expected counter state."""
    metrics = PrometheusMetrics()
    labels = {"pipeline": "test_pipe", "stage": "bronze", "run_type": "scheduled"}
    
    metrics.increment_counter("bioetl_records_processed_total", 5, labels)
    
    counter = COUNTERS["bioetl_records_processed_total"]
    payload = {
        "metric_name": "bioetl_records_processed_total",
        "labels": labels,
        "value": counter.labels(**labels)._value.get(),
        "description": counter._description,
    }
    _assert_matches_fixture("prometheus_counter_increment_sample", payload)


@pytest.mark.unit
def test_prometheus_metrics_observe_emits_expected_histogram() -> None:
    """Histogram observation produces expected histogram state."""
    metrics = PrometheusMetrics()
    labels = {
        "pipeline": "test_pipe",
        "stage": "transform",
        "status": "success",
        "run_type": "manual",
    }
    val = 15.5
    
    metrics.observe_histogram("bioetl_pipeline_duration_seconds", val, labels)
    
    histogram = HISTOGRAMS["bioetl_pipeline_duration_seconds"]
    payload = {
        "metric_name": "bioetl_pipeline_duration_seconds",
        "labels": labels,
        "value": val,
        "sum": histogram.labels(**labels)._sum.get(),
        "count": histogram.labels(**labels)._count.get(),
        "description": histogram._description,
    }
    _assert_matches_fixture("prometheus_histogram_observe_sample", payload)
