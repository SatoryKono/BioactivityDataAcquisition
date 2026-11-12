"""A real local scan detects newly introduced drift without stale caches."""

from __future__ import annotations

from types import SimpleNamespace
import pytest
from bioetl.infrastructure.observability import metric_inventory as subject
from bioetl.infrastructure.observability import (
    metric_inventory_ast,
    metric_inventory_events,
    metric_inventory_scan,
)

pytestmark = pytest.mark.unit


def test_collection_reconciles_fixture_emitters_and_reloads_new_drift(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        subject,
        "COUNTERS",
        {"bioetl_example_total": SimpleNamespace(_labelnames=("endpoint",))},
    )
    monkeypatch.setattr(subject, "GAUGES", {})
    monkeypatch.setattr(subject, "HISTOGRAMS", {})
    monkeypatch.setattr(
        subject, "_installed_registered_metric_names", lambda: {"bioetl_example_total"}
    )
    for module in (
        metric_inventory_ast,
        metric_inventory_events,
        metric_inventory_scan,
    ):
        monkeypatch.setattr(module, "REGISTERED_PROMETHEUS_METRIC_LABELS", {})
    source = tmp_path / "src/bioetl/application/example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'def execute(metrics):\n    metrics.increment_counter("bioetl_unregistered_total", 1)\n',
        encoding="utf-8",
    )
    first = subject.collect_metric_inventory(tmp_path)
    assert first["declared_metrics"] == ["bioetl_example_total"]
    assert first["runtime_without_registry"] == ["bioetl_unregistered_total"]
    assert first["unused_declared_metrics"] == ["bioetl_example_total"]
    assert first["declared_risky_label_review_required"] == ["bioetl_example_total"]
    source.write_text(
        'def execute(metrics):\n    metrics.increment_counter("bioetl_newly_introduced_total", 1)\n',
        encoding="utf-8",
    )
    second = subject.collect_metric_inventory(tmp_path)
    assert second["runtime_without_registry"] == ["bioetl_newly_introduced_total"]
    assert "bioetl_unregistered_total" not in second["runtime_emitters"]
