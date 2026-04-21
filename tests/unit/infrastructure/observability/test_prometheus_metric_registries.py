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
    # This ratchet intentionally changes only when we add/remove public metrics.
    assert len(REGISTERED_PROMETHEUS_METRIC_NAMES) == 106


@pytest.mark.unit
def test_removed_dead_metric_families_are_no_longer_registered() -> None:
    assert "bioetl_archive_duration_seconds" not in REGISTERED_PROMETHEUS_METRIC_NAMES
    assert "bioetl_archive_files_total" not in REGISTERED_PROMETHEUS_METRIC_NAMES
    assert "bioetl_preflight_medallion_policy_valid" not in (
        REGISTERED_PROMETHEUS_METRIC_NAMES
    )
    assert "bioetl_preflight_config_errors_total" not in (
        REGISTERED_PROMETHEUS_METRIC_NAMES
    )
    assert "bioetl_vacuum_duration_seconds" not in REGISTERED_PROMETHEUS_METRIC_NAMES


@pytest.mark.unit
def test_bronze_runtime_write_metrics_are_registered() -> None:
    assert "bioetl_bronze_write_attempts_total" in COUNTERS
    assert "bioetl_bronze_write_total_duration_seconds" in HISTOGRAMS
    assert "bioetl_bronze_files_removed_total" in COUNTERS
    assert "bioetl_bronze_bytes_freed_total" in COUNTERS
    assert "bioetl_audit_write_events_total" in COUNTERS
    assert "bioetl_audit_query_events_total" in COUNTERS
    assert "bioetl_audit_write_duration_seconds" in HISTOGRAMS
    assert "bioetl_audit_query_duration_seconds" in HISTOGRAMS


@pytest.mark.unit
def test_control_plane_and_lineage_metrics_are_registered() -> None:
    assert "bioetl_health_check_degraded_total" in COUNTERS
    assert "bioetl_control_plane_manifest_writes_total" in COUNTERS
    assert "bioetl_control_plane_ledger_appends_total" in COUNTERS
    assert "bioetl_control_plane_reads_total" in COUNTERS
    assert "bioetl_traced_runs_total" in COUNTERS
    assert "bioetl_checkpoint_compatibility_events_total" in COUNTERS
    assert "bioetl_checkpoint_load_events_total" in COUNTERS
    assert "bioetl_structural_policy_events_total" in COUNTERS
    assert "bioetl_structural_policy_shadow_comparisons_total" in COUNTERS
    assert "bioetl_control_plane_read_duration_seconds" in HISTOGRAMS
    assert "bioetl_lineage_fragments_emitted_total" in COUNTERS
    assert "bioetl_lineage_refs_missing_total" in COUNTERS
    assert "bioetl_composite_source_selection_total" in COUNTERS
    assert "bioetl_http_retry_budget_exhausted_total" in COUNTERS


@pytest.mark.unit
def test_dq_and_circuit_breaker_diagnostic_metrics_use_bounded_labels() -> None:
    expected_counter_labels = {
        "bioetl_dq_check_failures_total": {
            "pipeline",
            "stage",
            "check_type",
            "severity",
        },
        "bioetl_circuit_breaker_open_total": {"adapter"},
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)


@pytest.mark.unit
def test_control_plane_and_lineage_metrics_avoid_high_cardinality_labels() -> None:
    expected_labels = {
        "bioetl_control_plane_manifest_writes_total": {
            "pipeline",
            "run_type",
            "status",
        },
        "bioetl_control_plane_ledger_appends_total": {
            "pipeline",
            "event_type",
            "status",
        },
        "bioetl_checkpoint_compatibility_events_total": {
            "pipeline",
            "disposition",
        },
        "bioetl_checkpoint_load_events_total": {"pipeline", "status"},
        "bioetl_lineage_fragments_emitted_total": {"pipeline", "layer", "status"},
        "bioetl_lineage_refs_missing_total": {"pipeline", "layer", "ref_type"},
        "bioetl_composite_source_selection_total": {
            "pipeline",
            "decision_type",
            "selected_source",
        },
    }

    for metric_name, labels in expected_labels.items():
        metric = COUNTERS[metric_name]
        actual_labels = set(metric._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels), (
            f"{metric_name} must not use forbidden high-cardinality labels: "
            f"{sorted(_FORBIDDEN_LABELS.intersection(actual_labels))}"
        )


@pytest.mark.unit
def test_audit_metrics_use_bounded_labels() -> None:
    expected_counter_labels = {
        "bioetl_audit_write_events_total": {"layer", "operation", "status"},
        "bioetl_audit_query_events_total": {"layer_filter", "status"},
    }
    expected_histogram_labels = {
        "bioetl_audit_write_duration_seconds": {"layer", "operation", "status"},
        "bioetl_audit_query_duration_seconds": {"layer_filter", "status"},
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    for metric_name, labels in expected_histogram_labels.items():
        actual_labels = set(HISTOGRAMS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)
