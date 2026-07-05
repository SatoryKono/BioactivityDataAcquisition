"""Golden tests for Prometheus metrics outputs.

Tests that verify the structure and format of metrics emitted by the
PrometheusMetrics adapter against golden master baselines.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    HISTOGRAMS,
    METRIC_REGISTRY_FAMILIES,
    METRIC_REGISTRY_INVENTORY,
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


def _capture_counter_registry_state() -> dict[str, object]:
    """Capture current state of all counter registries."""
    state = {}
    for family in METRIC_REGISTRY_FAMILIES:
        for name, counter in family.counters.items():
            state[name] = {
                "description": getattr(
                    counter,
                    "_documentation",
                    getattr(counter, "_description", ""),
                ),
                "type": "counter",
                "family": family.family,
            }
    return state


def _capture_histogram_registry_state() -> dict[str, object]:
    """Capture current state of all histogram registries."""
    state = {}
    for family in METRIC_REGISTRY_FAMILIES:
        for name, histogram in family.histograms.items():
            state[name] = {
                "description": getattr(
                    histogram,
                    "_documentation",
                    getattr(histogram, "_description", ""),
                ),
                "type": "histogram",
                "family": family.family,
                "buckets": [
                    b
                    for b in getattr(
                        histogram,
                        "_upper_bounds",
                        getattr(histogram, "_upperbounds", ()),
                    )
                ],
            }
    return state


def _capture_metric_inventory() -> dict[str, object]:
    """Capture metric registry inventory."""
    return {
        "families": {
            family.family: {
                "counters": list(family.counters.keys()),
                "gauges": list(family.gauges.keys()),
                "histograms": list(family.histograms.keys()),
            }
            for family in METRIC_REGISTRY_FAMILIES
        },
        "total_counters": len(COUNTERS),
        "total_histograms": len(HISTOGRAMS),
    }


@pytest.mark.unit
def test_prometheus_counter_registry_matches_golden() -> None:
    """Prometheus counter registry must match golden baseline."""
    payload = _capture_counter_registry_state()
    _assert_matches_fixture("prometheus_counter_registry", payload)


@pytest.mark.unit
def test_prometheus_histogram_registry_matches_golden() -> None:
    """Prometheus histogram registry must match golden baseline."""
    payload = _capture_histogram_registry_state()
    _assert_matches_fixture("prometheus_histogram_registry", payload)


@pytest.mark.unit
def test_prometheus_metric_inventory_matches_golden() -> None:
    """Prometheus metric inventory must match golden baseline."""
    payload = _capture_metric_inventory()
    _assert_matches_fixture("prometheus_metric_inventory", payload)
