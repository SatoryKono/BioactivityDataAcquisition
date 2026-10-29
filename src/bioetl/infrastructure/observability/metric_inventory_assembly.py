"""Shared inventory helpers with a single runtime owner."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _iter_text_files,
    _scan_canonical_metric_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_events import (
    _declared_pipeline_event_names,
    _load_retired_observability_event_names,
    _runtime_cardinality_evidence_rows,
    _runtime_cardinality_threshold_violations,
    _scan_domain_mapping_observability_events,
    _scan_runtime_observability_event_calls,
)
from bioetl.infrastructure.observability.metric_inventory_report import (
    _drift_allowlist_token,
    _filter_documented_metric_mentions,
    _scan_rule_metric_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _CARDINALITY_RISK_LABEL_NAMES,
    _DOC_SCAN_ROOTS,
    _CardinalityReviewFields,
    _ObservabilityEventInventory,
    _RiskyLabelReviewFields,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {}


def _scan_docs_and_rules_mentions(
    repo_root: Path, *, declared_set: set[str]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    doc_paths: list[Path] = []
    for root in _DOC_SCAN_ROOTS:
        doc_paths.extend(_iter_text_files(repo_root / root))
    docs_mentions = _filter_documented_metric_mentions(
        _scan_canonical_metric_mentions(doc_paths, repo_root),
        registered_metrics=declared_set,
    )
    rules_mentions = _filter_documented_metric_mentions(
        _scan_rule_metric_mentions(repo_root),
        registered_metrics=declared_set,
    )
    return docs_mentions, rules_mentions


def _collect_observability_event_inventory(
    repo_root: Path,
) -> _ObservabilityEventInventory:
    declared_pipeline_events = _declared_pipeline_event_names()
    mapped_observability_events, mapped_event_emitters = (
        _scan_domain_mapping_observability_events(repo_root)
    )
    direct_observability_event_emitters, domain_event_emitters = (
        _scan_runtime_observability_event_calls(repo_root)
    )
    raw_declared_observability_events = (
        declared_pipeline_events | mapped_observability_events
    )
    retired_declared_observability_events = sorted(
        raw_declared_observability_events
        & _load_retired_observability_event_names(repo_root)
    )
    declared_observability_events = sorted(
        raw_declared_observability_events - set(retired_declared_observability_events)
    )
    emitted_observability_events = sorted(
        set(direct_observability_event_emitters) | mapped_observability_events
    )
    return {
        "declared_observability_events": declared_observability_events,
        "emitted_observability_events": emitted_observability_events,
        "retired_declared_observability_events": retired_declared_observability_events,
        "retired_declared_observability_events_emitted": sorted(
            set(retired_declared_observability_events)
            & set(emitted_observability_events)
        ),
        "raw_unused_declared_observability_events": sorted(
            set(declared_observability_events) - set(emitted_observability_events)
        ),
        "emitted_observability_events_without_contract": sorted(
            set(emitted_observability_events) - set(declared_observability_events)
        ),
        "observability_event_emitters": _combine_metric_emitters(
            direct_observability_event_emitters,
            mapped_event_emitters,
        ),
        "domain_event_emitters": domain_event_emitters,
    }


def _counter_total_aliases(
    metric_names: set[str], runtime_registered_set: set[str]
) -> set[str]:
    return {
        f"{metric_name}_total"
        for metric_name in metric_names
        if f"{metric_name}_total" in runtime_registered_set
    }


def _canonical_runtime_sets(
    *,
    direct_runtime_set: set[str],
    helper_runtime_set: set[str],
    runtime_registered_set: set[str],
) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    # Prometheus client counters expose a base metric name at runtime while
    # the registry stores the canonical ``_total`` sample name.  Treat only
    # registered, exact suffix pairs as equivalent; do not generalize this to
    # arbitrary names because that would hide genuine registry drift.
    runtime_set = direct_runtime_set | helper_runtime_set
    runtime_counter_bases = {
        metric_name
        for metric_name in runtime_set
        if f"{metric_name}_total" in runtime_registered_set
    }
    canonical_runtime_set = runtime_set | {
        f"{metric_name}_total" for metric_name in runtime_counter_bases
    }
    canonical_direct_runtime_set = direct_runtime_set | _counter_total_aliases(
        direct_runtime_set, runtime_registered_set
    )
    canonical_helper_runtime_set = helper_runtime_set | _counter_total_aliases(
        helper_runtime_set, runtime_registered_set
    )
    return (
        runtime_set,
        runtime_counter_bases,
        canonical_runtime_set,
        canonical_direct_runtime_set,
        canonical_helper_runtime_set,
    )


def _allowlisted_metric_diff(raw_set: set[str], allowlist: set[str]) -> list[str]:
    return sorted(raw_set - allowlist)


def _cardinality_review_fields(
    *,
    combined_emitters: dict[str, list[str]],
    drift_allowlist: dict[str, set[str]],
    cardinality_thresholds: dict[str, int],
    observed_series_counts: dict[str, int],
) -> _CardinalityReviewFields:
    reviewed_runtime_cardinality = drift_allowlist.get(
        "runtime_cardinality_review_required", set()
    ) | set(cardinality_thresholds)
    runtime_cardinality_candidates = sorted(
        metric_name
        for metric_name, emitter_paths in combined_emitters.items()
        if len(set(emitter_paths)) >= 3
    )
    runtime_cardinality_reviewed = sorted(
        set(runtime_cardinality_candidates) & reviewed_runtime_cardinality
    )
    runtime_cardinality_review_required = [
        metric_name
        for metric_name in runtime_cardinality_candidates
        if metric_name not in reviewed_runtime_cardinality
    ]
    return {
        "runtime_cardinality_candidates": runtime_cardinality_candidates,
        "runtime_cardinality_reviewed": runtime_cardinality_reviewed,
        "runtime_cardinality_review_required": runtime_cardinality_review_required,
        "runtime_cardinality_evidence": _runtime_cardinality_evidence_rows(
            metric_names=runtime_cardinality_candidates,
            combined_emitters=combined_emitters,
            observed_series_counts=observed_series_counts,
            thresholds=cardinality_thresholds,
        ),
        "runtime_cardinality_threshold_violations": (
            _runtime_cardinality_threshold_violations(
                observed_series_counts=observed_series_counts,
                thresholds=cardinality_thresholds,
            )
        ),
    }


def _risky_label_review_fields(
    *,
    declared_set: set[str],
    declared_label_contract_metrics: set[str],
    drift_allowlist: dict[str, set[str]],
    registered_labels: dict[str, frozenset[str]],
) -> _RiskyLabelReviewFields:
    declared_risky_label_candidates = sorted(
        metric_name
        for metric_name, label_names in registered_labels.items()
        if metric_name in declared_set
        and bool(set(label_names) & _CARDINALITY_RISK_LABEL_NAMES)
    )
    contract_bounded_risky_labels = (
        set(declared_risky_label_candidates) & declared_label_contract_metrics
    )
    reviewed_risky_labels = drift_allowlist.get(
        "declared_risky_label_review_required",
        set(),
    )
    declared_risky_label_reviewed = sorted(
        (set(declared_risky_label_candidates) & reviewed_risky_labels)
        | contract_bounded_risky_labels
    )
    declared_risky_label_review_required = [
        metric_name
        for metric_name in declared_risky_label_candidates
        if metric_name not in reviewed_risky_labels
        and metric_name not in contract_bounded_risky_labels
    ]
    return {
        "declared_risky_label_candidates": declared_risky_label_candidates,
        "contract_bounded_risky_labels": contract_bounded_risky_labels,
        "declared_risky_label_reviewed": declared_risky_label_reviewed,
        "declared_risky_label_review_required": declared_risky_label_review_required,
    }


def _filter_declared_label_contract_metrics(
    unresolved_rows: list[str], declared_metric_names: set[str]
) -> list[str]:
    return [
        row
        for row in unresolved_rows
        if _drift_allowlist_token("runtime_label_contract_unresolved", row)
        not in declared_metric_names
    ]


def _combine_metric_emitters(
    runtime_emitters: dict[str, list[str]],
    helper_backed_emitters: dict[str, list[str]],
) -> dict[str, list[str]]:
    combined: dict[str, list[str]] = defaultdict(list)
    for source in (runtime_emitters, helper_backed_emitters):
        for metric_name, emitter_paths in source.items():
            combined[metric_name].extend(emitter_paths)
    return dict(combined)
