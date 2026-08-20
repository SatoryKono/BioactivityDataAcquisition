#!/usr/bin/env python3
"""Report registry/runtime/docs drift for public observability metric families.

Usage:
    python -m scripts.engineering.qa report-observability-metric-inventory [--json]

The report is intentionally static and repo-local. It reconciles:
- registered public metric families
- runtime metric emitters in ``src/bioetl``
- documentation/dashboard references
- Prometheus rule references
- non-canonical alias candidates used in metric API calls
"""

from __future__ import annotations

import sys

# `python -m scripts.engineering.qa.report_observability_metric_inventory` loads
# this file as ``__main__``. The scan helper imports the same module by package
# name; alias the in-flight module so that import does not start a second copy
# and trip the circular import with observability_metric_inventory_scan.
if __name__ == "__main__":
    sys.modules.setdefault(
        "scripts.engineering.qa.report_observability_metric_inventory",
        sys.modules[__name__],
    )

import argparse
import ast
import json
import os
import re
import subprocess
import types
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final, Protocol, TypedDict, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.engineering.qa.observability_metric_inventory_shared import (
    _REPO_ROOT,
    _SRC_ROOT,
    _StartupInfoLike,
    _CANONICAL_METRIC_RE,
    _PROMETHEUS_METRIC_NAME_RE,
    _RUNTIME_SCAN_ROOT,
    _INFRASTRUCTURE_PATH_PREFIX,
    _REGISTERED_SCAN_ROOT,
    _DOC_SCAN_ROOTS,
    _RULE_SCAN_ROOT,
    _DEFAULT_DRIFT_ALLOWLIST,
    _DEFAULT_DECLARED_METRIC_DEFINITIONS,
    _DEFAULT_OBSERVABILITY_GOVERNANCE,
    _POLICY_ALIAS_CATALOG,
    _PANEL_CONTRACT_INVENTORY,
    _RUNTIME_EXCLUDE_PARTS,
    _TEXT_SUFFIXES,
    MetricInventoryReport,
    _ObservabilityEventInventory,
    _CardinalityReviewFields,
    _RiskyLabelReviewFields,
    _TEXT_FILE_DISCOVERY_CACHE,
    _METRIC_INVENTORY_CACHE,
    _SOURCE_TEXT_CACHE,
    _RUNTIME_CANDIDATE_TEXT_CACHE,
    _RUNTIME_CANDIDATE_PATH_CACHE,
    _RUNTIME_EVENT_CANDIDATE_PATH_CACHE,
    _TEXT_DISCOVERY_TIMEOUT_SECONDS,
    _METRIC_MENTION_GREP_TIMEOUT_SECONDS,
    _METRIC_MENTION_GREP_CHUNK_SIZE,
    _PROMETHEUS_QUERY_TIMEOUT_SECONDS,
    _PROMETHEUS_BASE_URL_ENV_VAR,
    _PROMETHEUS_BEARER_TOKEN_ENV_VAR,
    _RUNTIME_METRIC_METHODS,
    _RUNTIME_METRIC_NAME_KEYWORDS,
    _RUNTIME_SCAN_MARKERS,
    _STATIC_RUNTIME_EMITTERS,
    _PROMETHEUS_FAMILY_SUFFIXES,
    _PROMETHEUS_ALIAS_SUFFIXES,
    _RUNTIME_EVENT_SCAN_MARKERS,
    _NON_METRIC_ALIAS_PREFIXES,
    _IGNORED_DOC_METRIC_NAMES,
    _CHECK_DRIFT_KEYS,
    _ALLOWLIST_METADATA_REQUIRED_KEYS,
    _CARDINALITY_RISK_LABEL_NAMES,
    _DIRECT_COLLECTOR_TERMINAL_METHODS,
    _METRIC_OBJECT_NAME_BY_ID,
    _EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS,
)

from bioetl.domain.runtime_observability_publication_contract import (
    get_runtime_observability_publication_contract,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)

if __name__ == "__main__":
    sys.modules.setdefault(
        "scripts.engineering.qa.report_observability_metric_inventory",
        sys.modules[__name__],
    )

from scripts.engineering.qa import observability_metric_inventory_scan as _metric_scan
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_text_files_with_rg,
    _run_text_discovery_command,
    _WindowsSubprocessKwargs,
    _hidden_windows_subprocess_kwargs,
    _repo_relative_pathspec,
    _as_repo_relative,
    _scan_canonical_metric_mentions,
    _scan_canonical_metric_mentions_via_direct_reads,
    _repo_relative_paths_for_scan,
    _append_metric_mentions_from_grep_line,
    _run_metric_mention_grep,
    _scan_metric_mentions_via_command_chunks,
    _scan_canonical_metric_mentions_with_git_grep,
    _scan_canonical_metric_mentions_with_rg,
    _normalize_mapping_lists,
    _read_cached_text,
    _read_runtime_candidate_text,
    _read_runtime_event_candidate_text,
    _iter_runtime_candidate_paths,
    _candidate_paths_from_stdout,
    _iter_candidate_paths_with_git_grep,
    _iter_candidate_paths_with_rg,
    _iter_runtime_candidate_paths_with_rg,
    _iter_runtime_event_candidate_paths,
    _iter_runtime_event_candidate_paths_with_rg,
    _collect_runtime_candidate_texts,
    _module_path_from_import,
    _collect_module_string_bindings,
    _iter_string_assignments,
    _resolve_imported_string_bindings,
    _collect_class_attribute_bindings,
    _collect_repo_class_attribute_bindings,
    _resolve_metric_name_expr,
    _collect_local_string_bindings,
    _call_method_name,
    _helper_metric_candidates,
    _scan_metric_names_in_tree,
    _import_from_nodes,
    _looks_like_imported_string_constant_name,
    _imported_string_constant_aliases,
    _module_string_bindings,
    _merge_imported_string_aliases,
    _class_nodes,
    _class_attribute_string_bindings,
    _call_nodes,
    _metric_names_for_call,
    _direct_metric_name,
    _collector_base_metric_expr,
    _direct_collector_metric_name,
    _dict_literal_string_keys,
    _direct_metric_label_keys,
    _scan_direct_metric_label_shapes,
    _record_label_contract_violations,
    _partition_helper_metric_candidates,
    _is_metric_like_alias_name,
    _record_runtime_mentions,
    _scan_runtime_metric_file,
    _scan_runtime_metric_calls,
    _record_static_runtime_emitters,
    _scan_registered_metric_names,
    _load_declared_metric_definitions,
    _resolve_imported_metric_bindings,
)

_iter_text_files_impl = _metric_scan._iter_text_files
_iter_text_files_with_git_ls_files_impl = (
    _metric_scan._iter_text_files_with_git_ls_files
)


def _sync_metric_scan_compatibility_seams() -> None:
    """Propagate historical module overrides into the scanner seam."""
    _metric_scan._iter_text_files_with_git_ls_files = _iter_text_files_with_git_ls_files
    _metric_scan._run_text_discovery_command = _run_text_discovery_command
    _metric_scan._module_string_bindings = _module_string_bindings
    _metric_scan._DEFAULT_DECLARED_METRIC_DEFINITIONS = (
        _DEFAULT_DECLARED_METRIC_DEFINITIONS
    )
    _metric_scan.REGISTERED_PROMETHEUS_METRIC_LABELS = (
        REGISTERED_PROMETHEUS_METRIC_LABELS
        if "REGISTERED_PROMETHEUS_METRIC_LABELS" in globals()
        else {}
    )


def _iter_text_files(root: Path) -> list[Path]:
    """Compatibility wrapper for the historical scanner patch surface."""
    _sync_metric_scan_compatibility_seams()
    return _iter_text_files_impl(root)


def _iter_text_files_with_git_ls_files(root: Path) -> list[Path] | None:
    """Compatibility wrapper for bounded git-backed discovery."""
    _metric_scan._run_text_discovery_command = _run_text_discovery_command
    return _iter_text_files_with_git_ls_files_impl(root)


from scripts.engineering.qa.observability_metric_inventory_report import (
    _coerce_int,
    _iter_dashboard_panels,
    _field_config_link_candidates,
    _runbook_urls_from_link_candidates,
    _panel_runbook_urls,
    _target_kind,
    _canonical_datasource_type,
    _target_query_tokens,
    _panel_contract,
    _catalog_policy_aliases,
    _panel_contract_document,
    _panel_contract_drift,
    write_panel_contract_inventory,
    _datasource_type_text,
    _consume_prometheus_rule,
    _scan_typed_prometheus_rules,
    _http_target_row,
    _consume_dashboard_target,
    _scan_typed_dashboard_targets,
    _scan_documented_metrics_from_docs,
    _typed_target_sort_key,
    _http_target_sort_key,
    _http_semantics_violations,
    _build_typed_inventory_report,
    collect_typed_observability_inventory,
    _filter_declared_label_contract_metrics,
    _looks_like_metric_family_name,
    _is_generated_prometheus_series,
    _filter_documented_metric_mentions,
    _scan_rule_metric_mentions,
    _extract_rule_metric_names,
    _drift_allowlist_token,
)

REGISTERED_PROMETHEUS_METRIC_NAMES = _scan_registered_metric_names(_REPO_ROOT)
REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {
    name: frozenset(metric._labelnames)
    for registry in (COUNTERS, GAUGES, HISTOGRAMS)
    for name, metric in registry.items()
}
_metric_scan.REGISTERED_PROMETHEUS_METRIC_LABELS = REGISTERED_PROMETHEUS_METRIC_LABELS

from scripts.engineering.qa import (
    observability_metric_inventory_runtime as _metric_runtime,
)
from scripts.engineering.qa.observability_metric_inventory_runtime import (
    RuntimeCardinalityReviewSummary,
)
from scripts.engineering.qa.observability_metric_inventory_runtime import (
    _declared_pipeline_event_names,
    _load_retired_observability_event_names,
    _resolve_observability_event_expr,
    _scan_domain_mapping_observability_events,
    _collect_emit_event_names,
    _scan_path_for_runtime_event_calls,
    _scan_runtime_observability_event_calls,
    _load_runtime_cardinality_thresholds,
    _sample_matches_metric,
    _observed_labelsets_for_metric,
    _observed_runtime_series_counts,
    _runtime_cardinality_evidence_rows,
    _runtime_cardinality_threshold_violations,
    _resolve_prometheus_base_url,
    _prometheus_metric_family_matcher,
    _prometheus_cardinality_query,
    _prometheus_query_request,
    _load_prometheus_query_payload,
    _scalar_from_prometheus_data,
    _label_values_from_prometheus_result,
    _git_source_provenance,
    _parse_observed_series_count_rows,
    _local_observed_series_counts,
    _sorted_string_rows,
    _threshold_violation_rows,
    _initial_cardinality_review_summary,
    _apply_local_cardinality_fallback,
    _query_live_cardinality_metrics,
    _finalize_live_cardinality_review,
)

_query_prometheus_scalar_impl = _metric_runtime._query_prometheus_scalar
_query_prometheus_label_values_impl = _metric_runtime._query_prometheus_label_values
_build_runtime_cardinality_review_summary_impl = (
    _metric_runtime._build_runtime_cardinality_review_summary
)
_metric_runtime.REGISTERED_PROMETHEUS_METRIC_LABELS = REGISTERED_PROMETHEUS_METRIC_LABELS


def _query_prometheus_scalar(
    *,
    prometheus_base_url: str,
    query: str,
    bearer_token: str,
) -> int:
    """Compatibility wrapper preserving module-level ``urlopen`` patching."""
    _metric_runtime.urlopen = urlopen
    return _query_prometheus_scalar_impl(
        prometheus_base_url=prometheus_base_url,
        query=query,
        bearer_token=bearer_token,
    )


def _query_prometheus_label_values(
    *,
    prometheus_base_url: str,
    metric_name: str,
    label_names: frozenset[str],
    bearer_token: str,
) -> dict[str, list[str]]:
    """Compatibility wrapper preserving module-level ``urlopen`` patching."""
    _metric_runtime.urlopen = urlopen
    return _query_prometheus_label_values_impl(
        prometheus_base_url=prometheus_base_url,
        metric_name=metric_name,
        label_names=label_names,
        bearer_token=bearer_token,
    )


def _build_runtime_cardinality_review_summary(
    report: MetricInventoryReport,
    *,
    repo_root: Path,
    prometheus_base_url: str | None,
    allow_local_cardinality_fallback: bool = False,
) -> RuntimeCardinalityReviewSummary:
    """Compatibility wrapper preserving the historical test/extension seam."""
    _metric_runtime._load_runtime_cardinality_thresholds = (
        _load_runtime_cardinality_thresholds
    )
    _metric_runtime.REGISTERED_PROMETHEUS_METRIC_LABELS = (
        REGISTERED_PROMETHEUS_METRIC_LABELS
    )
    _metric_runtime._query_prometheus_scalar = _query_prometheus_scalar
    _metric_runtime._query_prometheus_label_values = _query_prometheus_label_values
    return _build_runtime_cardinality_review_summary_impl(
        report,
        repo_root=repo_root,
        prometheus_base_url=prometheus_base_url,
        allow_local_cardinality_fallback=allow_local_cardinality_fallback,
    )


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
) -> _RiskyLabelReviewFields:
    declared_risky_label_candidates = sorted(
        metric_name
        for metric_name, label_names in REGISTERED_PROMETHEUS_METRIC_LABELS.items()
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


def _collect_metric_inventory_impl(
    repo_root: Path,
) -> MetricInventoryReport:
    repo_root = repo_root.resolve()
    cache_key = repo_root.as_posix()
    cached = _METRIC_INVENTORY_CACHE.get(cache_key)
    if cached is not None:
        return cached
    declared_metric_definitions = _load_declared_metric_definitions(repo_root)
    declared_rule_metrics = declared_metric_definitions["recording_rule_metrics"]
    declared_policy_aliases = declared_metric_definitions["policy_alias_metrics"]
    declared_label_contract_metrics = declared_metric_definitions[
        "declared_label_contract_metrics"
    ]
    runtime_registered_set = set(REGISTERED_PROMETHEUS_METRIC_NAMES)
    declared_set = (
        runtime_registered_set | declared_rule_metrics | declared_policy_aliases
    )
    registered = sorted(declared_set)
    (
        runtime_mentions,
        helper_backed_mentions,
        alias_mentions,
        label_contract_violations,
        label_contract_unresolved,
    ) = _scan_runtime_metric_calls(repo_root)
    label_contract_unresolved = _filter_declared_label_contract_metrics(
        label_contract_unresolved,
        declared_label_contract_metrics,
    )
    docs_mentions, rules_mentions = _scan_docs_and_rules_mentions(
        repo_root, declared_set=declared_set
    )
    event_inventory = _collect_observability_event_inventory(repo_root)
    runtime_observability_contract = get_runtime_observability_publication_contract()

    registered_set = set(registered)
    (
        runtime_set,
        runtime_counter_bases,
        canonical_runtime_set,
        canonical_direct_runtime_set,
        canonical_helper_runtime_set,
    ) = _canonical_runtime_sets(
        direct_runtime_set=set(runtime_mentions),
        helper_runtime_set=set(helper_backed_mentions),
        runtime_registered_set=runtime_registered_set,
    )
    docs_set = set(docs_mentions)
    rules_set = set(rules_mentions)
    registry_only_metric_set = runtime_registered_set - canonical_runtime_set
    runtime_without_registry_set = runtime_set - registered_set - runtime_counter_bases
    dead_metrics = registry_only_metric_set - docs_set - rules_set
    ruled_without_runtime_set = (
        rules_set & runtime_registered_set
    ) - canonical_runtime_set
    combined_emitters = _combine_metric_emitters(
        runtime_mentions, helper_backed_mentions
    )
    observed_series_counts = _observed_runtime_series_counts()
    cardinality_thresholds = _load_runtime_cardinality_thresholds(repo_root)
    drift_allowlist = _load_drift_allowlist(repo_root / _DEFAULT_DRIFT_ALLOWLIST)
    documented_without_runtime = _allowlisted_metric_diff(
        (docs_set & runtime_registered_set) - canonical_runtime_set,
        drift_allowlist.get("dashboarded_without_emission", set()),
    )
    registry_only_metrics = _allowlisted_metric_diff(
        registry_only_metric_set,
        drift_allowlist.get("unused_declared_metrics", set()),
    )
    runtime_without_registry = _allowlisted_metric_diff(
        runtime_without_registry_set,
        drift_allowlist.get("runtime_without_registry", set()),
    )
    unused_declared_observability_events = _allowlisted_metric_diff(
        set(event_inventory["raw_unused_declared_observability_events"]),
        drift_allowlist.get("unused_declared_observability_events", set()),
    )
    ruled_without_runtime = _allowlisted_metric_diff(
        ruled_without_runtime_set,
        drift_allowlist.get("alerted_without_emission", set()),
    )
    cardinality_fields = _cardinality_review_fields(
        combined_emitters=combined_emitters,
        drift_allowlist=drift_allowlist,
        cardinality_thresholds=cardinality_thresholds,
        observed_series_counts=observed_series_counts,
    )
    risky_label_fields = _risky_label_review_fields(
        declared_set=declared_set,
        declared_label_contract_metrics=declared_label_contract_metrics,
        drift_allowlist=drift_allowlist,
    )

    report: MetricInventoryReport = {
        "declared_metrics": registered,
        "emitted_metrics": sorted(registered_set & canonical_runtime_set),
        "declared_observability_events": event_inventory[
            "declared_observability_events"
        ],
        "emitted_observability_events": event_inventory["emitted_observability_events"],
        "unused_declared_observability_events": unused_declared_observability_events,
        "retired_declared_observability_events": event_inventory[
            "retired_declared_observability_events"
        ],
        "retired_declared_observability_events_emitted": event_inventory[
            "retired_declared_observability_events_emitted"
        ],
        "emitted_observability_events_without_contract": event_inventory[
            "emitted_observability_events_without_contract"
        ],
        "dashboarded_metrics": sorted(docs_set & registered_set),
        "alerted_metrics": sorted(rules_set & registered_set),
        "unused_declared_metrics": sorted(registry_only_metrics),
        "emitted_without_declaration": sorted(runtime_without_registry),
        "dashboarded_without_declaration": sorted(docs_set - registered_set),
        "alerted_without_declaration": sorted(rules_set - registered_set),
        "dashboarded_without_emission": sorted(documented_without_runtime),
        "alerted_without_emission": sorted(ruled_without_runtime),
        "runtime_cardinality_review_candidates": cardinality_fields[
            "runtime_cardinality_candidates"
        ],
        "runtime_cardinality_reviewed": cardinality_fields[
            "runtime_cardinality_reviewed"
        ],
        "runtime_cardinality_review_required": cardinality_fields[
            "runtime_cardinality_review_required"
        ],
        "runtime_cardinality_evidence": cardinality_fields[
            "runtime_cardinality_evidence"
        ],
        "runtime_cardinality_observed_series": {
            metric_name: [f"observed_series_count={count}"]
            for metric_name, count in sorted(observed_series_counts.items())
        },
        "runtime_cardinality_threshold_violations": cardinality_fields[
            "runtime_cardinality_threshold_violations"
        ],
        "declared_risky_label_review_candidates": risky_label_fields[
            "declared_risky_label_candidates"
        ],
        "declared_risky_label_contract_reviewed": sorted(
            risky_label_fields["contract_bounded_risky_labels"]
        ),
        "declared_risky_label_reviewed": risky_label_fields[
            "declared_risky_label_reviewed"
        ],
        "declared_risky_label_review_required": risky_label_fields[
            "declared_risky_label_review_required"
        ],
        "declared_label_contract_metrics": sorted(declared_label_contract_metrics),
        "runtime_label_contract_violations": label_contract_violations,
        "runtime_label_contract_unresolved": label_contract_unresolved,
        "registered_metrics": registered,
        "live_metrics": sorted(registered_set & canonical_runtime_set),
        "direct_live_metrics": sorted(registered_set & canonical_direct_runtime_set),
        "helper_backed_live_metrics": sorted(
            registered_set & canonical_helper_runtime_set
        ),
        "registered_without_runtime": sorted(registry_only_metrics),
        "runtime_without_registry": sorted(runtime_without_registry),
        "registry_only_metrics": sorted(registry_only_metrics),
        "dead_metrics": sorted(dead_metrics),
        "documented_without_registry": sorted(docs_set - registered_set),
        "rules_without_registry": sorted(rules_set - registered_set),
        "documented_without_runtime": sorted(documented_without_runtime),
        "documented_only_metrics": sorted(documented_without_runtime),
        "ruled_without_runtime": sorted(ruled_without_runtime),
        "compatibility_alias_candidates": sorted(alias_mentions),
        "runtime_emitters": runtime_mentions,
        "helper_backed_emitters": helper_backed_mentions,
        "observability_event_emitters": event_inventory["observability_event_emitters"],
        "domain_event_emitters": event_inventory["domain_event_emitters"],
        "canonical_runtime_observability_emitters": sorted(
            runtime_observability_contract.canonical_emitters
        ),
        "docs_mentions": docs_mentions,
        "rules_mentions": rules_mentions,
        "alias_emitters": alias_mentions,
    }
    _METRIC_INVENTORY_CACHE[cache_key] = report
    return report


def _combine_metric_emitters(
    runtime_emitters: dict[str, list[str]],
    helper_backed_emitters: dict[str, list[str]],
) -> dict[str, list[str]]:
    combined: dict[str, list[str]] = defaultdict(list)
    for source in (runtime_emitters, helper_backed_emitters):
        for metric_name, emitter_paths in source.items():
            combined[metric_name].extend(emitter_paths)
    return dict(combined)


def collect_metric_inventory(repo_root: Path) -> MetricInventoryReport:
    """Collect the inventory after syncing compatibility overrides."""
    _sync_metric_scan_compatibility_seams()
    return _collect_metric_inventory_impl(repo_root)


from scripts.engineering.qa import observability_metric_inventory_cli as _metric_cli
from scripts.engineering.qa.observability_metric_inventory_cli import (
    _build_parser,
    _parse_allowlist_metric_name,
    _validate_allowlist_review_date,
    _load_drift_allowlist,
    validate_metric_inventory as validate_metric_inventory,
    _render_text,
    _write_evidence_report,
    _resolved_allowlist_path,
    _metric_inventory_violations,
    _emit_json_report,
    _emit_text_report,
    _write_runtime_cardinality_review_summary,
    _render_runtime_cardinality_review_summary,
    _append_runtime_cardinality_review_summary,
    _typed_inventory_violations,
)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI while preserving the historical module patch surface."""
    _metric_cli.collect_metric_inventory = collect_metric_inventory
    _metric_cli.collect_typed_observability_inventory = (
        collect_typed_observability_inventory
    )
    _metric_cli.write_panel_contract_inventory = write_panel_contract_inventory
    _metric_cli._build_runtime_cardinality_review_summary = (
        _build_runtime_cardinality_review_summary
    )
    return _metric_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
