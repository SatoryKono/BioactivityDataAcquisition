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

# Tooling must also bootstrap from a source root without an installed package.
from scripts.engineering.qa.observability_metric_inventory_shared import (
    _SRC_ROOT as _SRC_ROOT,
)


from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _scan_docs_and_rules_mentions as _scan_docs_and_rules_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _collect_observability_event_inventory as _collect_observability_event_inventory,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _counter_total_aliases as _counter_total_aliases,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _canonical_runtime_sets as _canonical_runtime_sets,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _allowlisted_metric_diff as _allowlisted_metric_diff,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _cardinality_review_fields as _cardinality_review_fields,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _risky_label_review_fields as _risky_label_review_fields,
)
from bioetl.infrastructure.observability.metric_inventory import (
    _collect_metric_inventory_impl as _collect_metric_inventory_impl,
)
from bioetl.infrastructure.observability.metric_inventory_assembly import (
    _combine_metric_emitters as _combine_metric_emitters,
)


import sys
from contextlib import contextmanager
from collections.abc import Iterator

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

from bioetl.infrastructure.observability import metric_inventory_scan as _metric_scan
from scripts.engineering.qa import (
    observability_metric_inventory_scan as _metric_discovery,
)
from bioetl.infrastructure.observability import metric_inventory_ast as _metric_ast
from bioetl.infrastructure.observability import (
    metric_inventory_bindings as _metric_bindings,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_text_files_with_rg,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _run_text_discovery_command,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _WindowsSubprocessKwargs,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _hidden_windows_subprocess_kwargs,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _repo_relative_pathspec,
)
from scripts.engineering.qa.observability_metric_inventory_scan import _as_repo_relative
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _scan_canonical_metric_mentions,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _scan_canonical_metric_mentions_via_direct_reads,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _repo_relative_paths_for_scan,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _append_metric_mentions_from_grep_line,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _run_metric_mention_grep,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _scan_metric_mentions_via_command_chunks,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _scan_canonical_metric_mentions_with_git_grep,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _scan_canonical_metric_mentions_with_rg,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _normalize_mapping_lists,
)
from scripts.engineering.qa.observability_metric_inventory_scan import _read_cached_text
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _read_runtime_candidate_text,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _read_runtime_event_candidate_text,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_runtime_candidate_paths,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _candidate_paths_from_stdout,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_candidate_paths_with_git_grep,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_candidate_paths_with_rg,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_runtime_candidate_paths_with_rg,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_runtime_event_candidate_paths,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _iter_runtime_event_candidate_paths_with_rg,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _collect_runtime_candidate_texts,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _module_path_from_import,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_module_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _iter_string_assignments,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _resolve_imported_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_class_attribute_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_repo_class_attribute_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _resolve_metric_name_expr,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_local_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _call_method_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _helper_metric_candidates,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _scan_metric_names_in_tree,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _import_from_nodes,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _looks_like_imported_string_constant_name,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _imported_string_constant_aliases,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _module_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _merge_imported_string_aliases,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import _class_nodes
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _class_attribute_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import _call_nodes
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _metric_names_for_call,
)
from bioetl.infrastructure.observability.metric_inventory_ast import _direct_metric_name
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _collector_base_metric_expr,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _direct_collector_metric_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _dict_literal_string_keys,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _direct_metric_label_keys,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _scan_direct_metric_label_shapes,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _record_label_contract_violations,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _partition_helper_metric_candidates,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _is_metric_like_alias_name,
)
from bioetl.infrastructure.observability.metric_inventory_ast import (
    _record_runtime_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _scan_runtime_metric_file,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _scan_runtime_metric_calls,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _record_static_runtime_emitters,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _scan_registered_metric_names,
)
from bioetl.infrastructure.observability.metric_inventory_scan import (
    _load_declared_metric_definitions,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _resolve_imported_metric_bindings,
)

_iter_text_files_impl = _metric_discovery._iter_text_files
_iter_text_files_with_git_ls_files_impl = (
    _metric_discovery._iter_text_files_with_git_ls_files
)


def _sync_metric_scan_compatibility_seams() -> None:
    """Propagate historical module overrides into the scanner seam."""
    _metric_discovery._iter_text_files_with_git_ls_files = (
        _iter_text_files_with_git_ls_files
    )
    _metric_discovery._run_text_discovery_command = _run_text_discovery_command
    _metric_bindings._module_string_bindings = _module_string_bindings
    _metric_scan._DEFAULT_DECLARED_METRIC_DEFINITIONS = (
        _DEFAULT_DECLARED_METRIC_DEFINITIONS
    )
    _metric_ast.REGISTERED_PROMETHEUS_METRIC_LABELS = (
        REGISTERED_PROMETHEUS_METRIC_LABELS
        if "REGISTERED_PROMETHEUS_METRIC_LABELS" in globals()
        else {}
    )


@contextmanager
def _inventory_compatibility_seams(repo_root: Path | None = None) -> Iterator[None]:
    from bioetl.infrastructure.observability import metric_inventory_events as events
    from bioetl.infrastructure.observability import (
        metric_inventory_assembly as assembly,
    )
    from bioetl.infrastructure.observability import (
        metric_inventory_candidates as candidates,
    )
    from bioetl.infrastructure.observability import metric_inventory_report as report

    targets = (
        (_metric_discovery, "_REPO_ROOT"),
        (_metric_discovery, "_iter_text_files_with_git_ls_files"),
        (_metric_discovery, "_run_text_discovery_command"),
        (_metric_bindings, "_module_string_bindings"),
        (_metric_ast, "REGISTERED_PROMETHEUS_METRIC_LABELS"),
        (_metric_scan, "_DEFAULT_DECLARED_METRIC_DEFINITIONS"),
        (events, "REGISTERED_PROMETHEUS_METRIC_LABELS"),
        (assembly, "_iter_text_files"),
        (candidates, "_iter_text_files"),
        (report, "_iter_text_files"),
        (assembly, "_scan_canonical_metric_mentions"),
        (report, "_scan_canonical_metric_mentions"),
    )
    previous = [(module, name, getattr(module, name)) for module, name in targets]
    try:
        _sync_metric_scan_compatibility_seams()
        if repo_root is not None:
            _metric_discovery._REPO_ROOT = repo_root.resolve()
        for module in (assembly, candidates, report):
            module._iter_text_files = _iter_text_files_impl
        for module in (assembly, report):
            module._scan_canonical_metric_mentions = (
                _metric_discovery._scan_canonical_metric_mentions
            )
        events.REGISTERED_PROMETHEUS_METRIC_LABELS = REGISTERED_PROMETHEUS_METRIC_LABELS
        yield
    finally:
        for module, name, value in previous:
            setattr(module, name, value)


def _iter_text_files(root: Path) -> list[Path]:
    """Use engineering overrides without leaking them into installed-runtime logic."""
    with _inventory_compatibility_seams():
        return _iter_text_files_impl(root)


def _iter_text_files_with_git_ls_files(root: Path) -> list[Path] | None:
    """Use bounded discovery with the historical engineering command seam."""
    previous = _metric_discovery._run_text_discovery_command
    try:
        _metric_discovery._run_text_discovery_command = _run_text_discovery_command
        return _iter_text_files_with_git_ls_files_impl(root)
    finally:
        _metric_discovery._run_text_discovery_command = previous


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
_metric_runtime.REGISTERED_PROMETHEUS_METRIC_LABELS = (
    REGISTERED_PROMETHEUS_METRIC_LABELS
)


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


def collect_metric_inventory(repo_root: Path) -> MetricInventoryReport:
    """Collect using the shared implementation and historical engineering overrides."""
    from bioetl.infrastructure.observability.metric_inventory import _COLLECTION_LOCK
    from bioetl.infrastructure.observability.metric_inventory_shared import (
        _reset_inventory_caches,
    )

    with _COLLECTION_LOCK, _inventory_compatibility_seams(repo_root):
        _reset_inventory_caches()
        return _collect_metric_inventory_impl(
            repo_root,
            sources={
                "_load_declared_metric_definitions": _load_declared_metric_definitions,
                "_scan_runtime_metric_calls": _scan_runtime_metric_calls,
                "_scan_docs_and_rules_mentions": _scan_docs_and_rules_mentions,
                "_collect_observability_event_inventory": _collect_observability_event_inventory,
                "_observed_runtime_series_counts": _observed_runtime_series_counts,
                "_load_runtime_cardinality_thresholds": _load_runtime_cardinality_thresholds,
                "_load_drift_allowlist": _load_drift_allowlist,
                "REGISTERED_PROMETHEUS_METRIC_NAMES": REGISTERED_PROMETHEUS_METRIC_NAMES,
                "REGISTERED_PROMETHEUS_METRIC_LABELS": REGISTERED_PROMETHEUS_METRIC_LABELS,
            },
        )


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
