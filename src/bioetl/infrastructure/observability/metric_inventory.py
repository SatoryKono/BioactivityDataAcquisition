"""Live inventory orchestration shared by diagnostics and engineering consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from bioetl.domain.observability_contract import (
    get_runtime_observability_publication_contract,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _allowlisted_metric_diff,
    _canonical_runtime_sets,
    _cardinality_review_fields,
    _collect_observability_event_inventory,
    _combine_metric_emitters,
    _filter_declared_label_contract_metrics,
    _risky_label_review_fields,
    _scan_docs_and_rules_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_events import (
    _load_runtime_cardinality_thresholds,
    _observed_runtime_series_counts,
)
from bioetl.infrastructure.observability.metric_inventory_policy import (
    _load_drift_allowlist,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _installed_registered_metric_names,
    _load_declared_metric_definitions,
    _scan_runtime_metric_calls,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _DEFAULT_DRIFT_ALLOWLIST,
    MetricInventoryReport,
    _ObservabilityEventInventory,
    _reset_inventory_caches,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)


@dataclass(frozen=True, slots=True)
class _InventoryInputs:
    registered: set[str]
    declared: set[str]
    label_contracts: set[str]
    runtime: dict[str, list[str]]
    helpers: dict[str, list[str]]
    aliases: dict[str, list[str]]
    label_violations: list[str]
    label_unresolved: list[str]
    docs: dict[str, list[str]]
    rules: dict[str, list[str]]
    events: _ObservabilityEventInventory
    observed: dict[str, int]
    thresholds: dict[str, int]
    allowed: dict[str, set[str]]
    labels: dict[str, frozenset[str]]


def _read_inventory_inputs(
    repo_root: Path,
    sources: dict[
        str, Any
    ],  # Any: heterogeneous legacy callback overrides and registry values.
) -> _InventoryInputs:
    definitions = sources["_load_declared_metric_definitions"](repo_root)
    registered = set(sources["REGISTERED_PROMETHEUS_METRIC_NAMES"])
    declared = (
        registered
        | definitions["recording_rule_metrics"]
        | definitions["policy_alias_metrics"]
    )
    runtime, helpers, aliases, violations, unresolved = sources[
        "_scan_runtime_metric_calls"
    ](repo_root)
    docs, rules = sources["_scan_docs_and_rules_mentions"](
        repo_root, declared_set=declared
    )
    return _InventoryInputs(
        registered=registered,
        declared=declared,
        label_contracts=definitions["declared_label_contract_metrics"],
        runtime=runtime,
        helpers=helpers,
        aliases=aliases,
        label_violations=violations,
        label_unresolved=_filter_declared_label_contract_metrics(
            unresolved, definitions["declared_label_contract_metrics"]
        ),
        docs=docs,
        rules=rules,
        events=sources["_collect_observability_event_inventory"](repo_root),
        observed=sources["_observed_runtime_series_counts"](),
        thresholds=sources["_load_runtime_cardinality_thresholds"](repo_root),
        allowed=sources["_load_drift_allowlist"](repo_root / _DEFAULT_DRIFT_ALLOWLIST),
        labels=sources["REGISTERED_PROMETHEUS_METRIC_LABELS"],
    )


@dataclass(frozen=True, slots=True)
class _InventorySets:
    runtime: set[str]
    counter_bases: set[str]
    canonical: set[str]
    direct: set[str]
    helpers: set[str]
    docs: set[str]
    rules: set[str]


def _inventory_sets(inputs: _InventoryInputs) -> _InventorySets:
    runtime, bases, canonical, direct, helpers = _canonical_runtime_sets(
        direct_runtime_set=set(inputs.runtime),
        helper_runtime_set=set(inputs.helpers),
        runtime_registered_set=inputs.registered,
    )
    return _InventorySets(
        runtime, bases, canonical, direct, helpers, set(inputs.docs), set(inputs.rules)
    )


def _signal_report(i: _InventoryInputs, s: _InventorySets) -> MetricInventoryReport:
    registry_only = _allowlisted_metric_diff(
        i.registered - s.canonical, i.allowed.get("unused_declared_metrics", set())
    )
    without_registry = _allowlisted_metric_diff(
        s.runtime - i.declared - s.counter_bases,
        i.allowed.get("runtime_without_registry", set()),
    )
    documented = _allowlisted_metric_diff(
        (s.docs & i.registered) - s.canonical,
        i.allowed.get("dashboarded_without_emission", set()),
    )
    ruled = _allowlisted_metric_diff(
        (s.rules & i.registered) - s.canonical,
        i.allowed.get("alerted_without_emission", set()),
    )
    return {
        "declared_metrics": sorted(i.declared),
        "emitted_metrics": sorted(i.declared & s.canonical),
        "dashboarded_metrics": sorted(s.docs & i.declared),
        "alerted_metrics": sorted(s.rules & i.declared),
        "unused_declared_metrics": sorted(registry_only),
        "emitted_without_declaration": sorted(without_registry),
        "dashboarded_without_declaration": sorted(s.docs - i.declared),
        "alerted_without_declaration": sorted(s.rules - i.declared),
        "dashboarded_without_emission": documented,
        "alerted_without_emission": ruled,
        "registered_metrics": sorted(i.declared),
        "live_metrics": sorted(i.declared & s.canonical),
        "direct_live_metrics": sorted(i.declared & s.direct),
        "helper_backed_live_metrics": sorted(i.declared & s.helpers),
        "registered_without_runtime": sorted(registry_only),
        "runtime_without_registry": sorted(without_registry),
        "registry_only_metrics": sorted(registry_only),
        "dead_metrics": sorted((i.registered - s.canonical) - s.docs - s.rules),
        "documented_without_registry": sorted(s.docs - i.declared),
        "rules_without_registry": sorted(s.rules - i.declared),
        "documented_without_runtime": documented,
        "documented_only_metrics": documented,
        "ruled_without_runtime": ruled,
        "compatibility_alias_candidates": sorted(i.aliases),
        "runtime_emitters": i.runtime,
        "helper_backed_emitters": i.helpers,
        "docs_mentions": i.docs,
        "rules_mentions": i.rules,
        "alias_emitters": i.aliases,
        "canonical_runtime_observability_emitters": sorted(
            get_runtime_observability_publication_contract().canonical_emitters
        ),
    }


def _event_report(i: _InventoryInputs) -> MetricInventoryReport:
    e = i.events
    return {
        "declared_observability_events": e["declared_observability_events"],
        "emitted_observability_events": e["emitted_observability_events"],
        "unused_declared_observability_events": _allowlisted_metric_diff(
            set(e["raw_unused_declared_observability_events"]),
            i.allowed.get("unused_declared_observability_events", set()),
        ),
        "retired_declared_observability_events": e[
            "retired_declared_observability_events"
        ],
        "retired_declared_observability_events_emitted": e[
            "retired_declared_observability_events_emitted"
        ],
        "emitted_observability_events_without_contract": e[
            "emitted_observability_events_without_contract"
        ],
        "observability_event_emitters": e["observability_event_emitters"],
        "domain_event_emitters": e["domain_event_emitters"],
    }


def _review_report(i: _InventoryInputs) -> MetricInventoryReport:
    c = _cardinality_review_fields(
        combined_emitters=_combine_metric_emitters(i.runtime, i.helpers),
        drift_allowlist=i.allowed,
        cardinality_thresholds=i.thresholds,
        observed_series_counts=i.observed,
    )
    r = _risky_label_review_fields(
        declared_set=i.declared,
        declared_label_contract_metrics=i.label_contracts,
        drift_allowlist=i.allowed,
        registered_labels=i.labels,
    )
    return {
        "runtime_cardinality_review_candidates": c["runtime_cardinality_candidates"],
        "runtime_cardinality_reviewed": c["runtime_cardinality_reviewed"],
        "runtime_cardinality_review_required": c["runtime_cardinality_review_required"],
        "runtime_cardinality_evidence": c["runtime_cardinality_evidence"],
        "runtime_cardinality_observed_series": {
            name: [f"observed_series_count={count}"]
            for name, count in sorted(i.observed.items())
        },
        "runtime_cardinality_threshold_violations": c[
            "runtime_cardinality_threshold_violations"
        ],
        "declared_risky_label_review_candidates": r["declared_risky_label_candidates"],
        "declared_risky_label_contract_reviewed": sorted(
            r["contract_bounded_risky_labels"]
        ),
        "declared_risky_label_reviewed": r["declared_risky_label_reviewed"],
        "declared_risky_label_review_required": r[
            "declared_risky_label_review_required"
        ],
        "declared_label_contract_metrics": sorted(i.label_contracts),
        "runtime_label_contract_violations": i.label_violations,
        "runtime_label_contract_unresolved": i.label_unresolved,
    }


def _collect_metric_inventory_impl(
    repo_root: Path,
    *,
    sources: dict[
        str, Any
    ],  # Any: heterogeneous legacy callback overrides and registry values.
) -> MetricInventoryReport:
    inputs = _read_inventory_inputs(repo_root.resolve(), sources)
    return {
        **_signal_report(inputs, _inventory_sets(inputs)),
        **_event_report(inputs),
        **_review_report(inputs),
    }


_COLLECTION_LOCK = RLock()


def collect_metric_inventory(repo_root: Path) -> MetricInventoryReport:
    """Scan current inputs; invocation-scoped caches never hide newly introduced drift."""
    from bioetl.infrastructure.observability import metric_inventory_ast as metric_ast
    from bioetl.infrastructure.observability import metric_inventory_events as events
    from bioetl.infrastructure.observability import metric_inventory_scan as scan

    with _COLLECTION_LOCK:
        _reset_inventory_caches()
        labels = {
            name: frozenset(metric._labelnames)
            for registry in (COUNTERS, GAUGES, HISTOGRAMS)
            for name, metric in registry.items()
        }
        scan.REGISTERED_PROMETHEUS_METRIC_LABELS = labels
        metric_ast.REGISTERED_PROMETHEUS_METRIC_LABELS = labels
        events.REGISTERED_PROMETHEUS_METRIC_LABELS = labels
        sources = {
            "_load_declared_metric_definitions": _load_declared_metric_definitions,
            "_scan_runtime_metric_calls": _scan_runtime_metric_calls,
            "_scan_docs_and_rules_mentions": _scan_docs_and_rules_mentions,
            "_collect_observability_event_inventory": _collect_observability_event_inventory,
            "_observed_runtime_series_counts": _observed_runtime_series_counts,
            "_load_runtime_cardinality_thresholds": _load_runtime_cardinality_thresholds,
            "_load_drift_allowlist": _load_drift_allowlist,
            "REGISTERED_PROMETHEUS_METRIC_NAMES": _installed_registered_metric_names(),
            "REGISTERED_PROMETHEUS_METRIC_LABELS": labels,
        }
        return _collect_metric_inventory_impl(repo_root, sources=sources)
