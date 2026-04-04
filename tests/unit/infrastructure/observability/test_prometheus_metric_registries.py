"""Contract tests for grouped Prometheus metric registries."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.observability.metrics_definitions import __all__ as defs_all
from bioetl.infrastructure.observability.metrics_export_names import (
    METRICS_DEFINITION_EXPORT_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
    METRIC_REGISTRY_FAMILIES,
    METRIC_REGISTRY_INVENTORY,
    REGISTERED_PROMETHEUS_METRIC_NAMES,
)

_FORBIDDEN_LABELS = frozenset(
    {"run_id", "manifest_id", "path", "file_path", "dataset_hash", "source_batch_id"}
)


@pytest.mark.unit
def test_metric_registry_family_inventory_has_expected_families() -> None:
    assert tuple(METRIC_REGISTRY_INVENTORY) == (
        "pipeline_runtime",
        "storage_medallion",
        "http_adapters",
        "dq_validation",
        "system_process",
    )


@pytest.mark.unit
def test_metric_registry_family_keys_are_disjoint() -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for family in METRIC_REGISTRY_FAMILIES:
        family_names = (
            set(family.counters) | set(family.gauges) | set(family.histograms)
        )
        duplicates.update(seen & family_names)
        seen.update(family_names)

    assert not duplicates, (
        "Metric registry families must not overlap; duplicates found: "
        + ", ".join(sorted(duplicates))
    )


@pytest.mark.unit
def test_metric_registry_inventory_matches_public_registries() -> None:
    inventory_names = {
        name
        for family_inventory in METRIC_REGISTRY_INVENTORY.values()
        for registry_names in family_inventory.values()
        for name in registry_names
    }

    assert inventory_names == REGISTERED_PROMETHEUS_METRIC_NAMES
    assert inventory_names == set(COUNTERS) | set(GAUGES) | set(HISTOGRAMS)


@pytest.mark.unit
def test_metric_definition_exports_remain_stable() -> None:
    assert set(defs_all) == set(METRICS_DEFINITION_EXPORT_NAMES)


@pytest.mark.unit
def test_grouped_registry_inventory_preserves_expected_size() -> None:
    assert len(REGISTERED_PROMETHEUS_METRIC_NAMES) == 84


@pytest.mark.unit
def test_control_plane_and_lineage_metrics_are_registered() -> None:
    assert "health_check_degraded_total" in COUNTERS
    assert "control_plane_manifest_writes_total" in COUNTERS
    assert "control_plane_ledger_appends_total" in COUNTERS
    assert "control_plane_reads_total" in COUNTERS
    assert "traced_runs_total" in COUNTERS
    assert "checkpoint_compatibility_events_total" in COUNTERS
    assert "structural_policy_events_total" in COUNTERS
    assert "structural_policy_shadow_comparisons_total" in COUNTERS
    assert "control_plane_read_duration_seconds" in HISTOGRAMS
    assert "lineage_fragments_emitted_total" in COUNTERS
    assert "lineage_refs_missing_total" in COUNTERS
    assert "composite_source_selection_total" in COUNTERS


@pytest.mark.unit
def test_control_plane_and_lineage_metric_labels_avoid_forbidden_identity_fields() -> None:
    metric_names = (
        "control_plane_manifest_writes_total",
        "control_plane_ledger_appends_total",
        "checkpoint_compatibility_events_total",
        "lineage_fragments_emitted_total",
        "lineage_refs_missing_total",
        "composite_source_selection_total",
    )

    for metric_name in metric_names:
        metric = COUNTERS[metric_name]
        assert _FORBIDDEN_LABELS.isdisjoint(metric._labelnames), (
            f"{metric_name} exposes forbidden labels: "
            f"{sorted(_FORBIDDEN_LABELS.intersection(metric._labelnames))}"
        )
