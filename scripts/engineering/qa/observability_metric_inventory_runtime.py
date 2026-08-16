"""Runtime-event and cardinality review logic for observability inventory."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen as urlopen

from bioetl.domain.events import (
    ORDINARY_PIPELINE_STAGE_NAMES,
    PipelineEvent,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)
from scripts.engineering.qa.observability_metric_inventory_scan import (
    _as_repo_relative,
    _call_method_name,
    _call_nodes,
    _iter_runtime_event_candidate_paths,
    _normalize_mapping_lists,
    _read_runtime_event_candidate_text,
)
from scripts.engineering.qa.report_observability_metric_inventory import (
    REGISTERED_PROMETHEUS_METRIC_LABELS as REGISTERED_PROMETHEUS_METRIC_LABELS,
    MetricInventoryReport,
    _CANONICAL_METRIC_RE,
    _DEFAULT_DRIFT_ALLOWLIST,
    _DEFAULT_OBSERVABILITY_GOVERNANCE,
    _PROMETHEUS_BASE_URL_ENV_VAR,
    _PROMETHEUS_BEARER_TOKEN_ENV_VAR,
    _PROMETHEUS_QUERY_TIMEOUT_SECONDS,
)


def _declared_pipeline_event_names() -> set[str]:
    declared: set[str] = set()
    for attribute_name in dir(PipelineEvent):
        if not attribute_name.isupper():
            continue
        value = getattr(PipelineEvent, attribute_name, None)
        if isinstance(value, str):
            declared.add(value)
    for stage_name in ORDINARY_PIPELINE_STAGE_NAMES:
        declared.add(PipelineEvent.phase_started(stage_name))
        declared.add(PipelineEvent.phase_completed(stage_name))
    return declared


def _load_retired_observability_event_names(repo_root: Path) -> set[str]:
    path = repo_root / _DEFAULT_OBSERVABILITY_GOVERNANCE
    if not path.exists():
        return set()
    try:
        import yaml
    except ImportError:
        return set()
    payload = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )  # NOSONAR - path confined
    if not isinstance(payload, dict):
        return set()
    event_governance = payload.get("event_signal_governance", {})
    if not isinstance(event_governance, dict):
        return set()
    retired_entries = event_governance.get("retired_declared_events", [])
    if not isinstance(retired_entries, list):
        return set()
    retired: set[str] = set()
    for entry in retired_entries:
        if not isinstance(entry, dict):
            continue
        event_name = entry.get("event_name")
        action = entry.get("action")
        if isinstance(event_name, str) and action == "retire":
            retired.add(event_name)
    return retired


def _resolve_observability_event_expr(node: ast.expr) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "PipelineEvent"
    ):
        resolved = getattr(PipelineEvent, node.attr, None)
        return {resolved} if isinstance(resolved, str) else set()
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "PipelineEvent"
        and node.func.attr in {"phase_started", "phase_completed"}
    ):
        resolver = (
            PipelineEvent.phase_started
            if node.func.attr == "phase_started"
            else PipelineEvent.phase_completed
        )
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return {resolver(node.args[0].value)}
        return {resolver(stage_name) for stage_name in ORDINARY_PIPELINE_STAGE_NAMES}
    return set()


def _scan_domain_mapping_observability_events(
    repo_root: Path,
) -> tuple[set[str], dict[str, list[str]]]:
    mapping_path = repo_root / "src/bioetl/domain/observability_event_mapping.py"
    try:
        tree = ast.parse(
            mapping_path.read_text(encoding="utf-8")
        )  # NOSONAR - path confined
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set(), {}

    event_names: set[str] = set()
    emitters: dict[str, list[str]] = defaultdict(list)
    relative_path = _as_repo_relative(mapping_path, repo_root)
    for node in _call_nodes(tree):
        if not isinstance(node.func, ast.Name) or node.func.id != "_build_envelope":
            continue
        for keyword in node.keywords:
            if keyword.arg != "event_name" or keyword.value is None:
                continue
            for event_name in _resolve_observability_event_expr(keyword.value):
                event_names.add(event_name)
                emitters[event_name].append(relative_path)
    return event_names, _normalize_mapping_lists(emitters)


def _collect_emit_event_names(
    node: ast.Call, *, relative_path: str, direct_emitters: dict[str, list[str]]
) -> None:
    if not node.args:
        return
    for event_name in _resolve_observability_event_expr(node.args[0]):
        direct_emitters[event_name].append(relative_path)


def _scan_path_for_runtime_event_calls(
    path: Path,
    *,
    repo_root: Path,
    direct_emitters: dict[str, list[str]],
    domain_event_emitters: list[str],
) -> None:
    relative_path = _as_repo_relative(path, repo_root)
    text = _read_runtime_event_candidate_text(path)
    if text is None:
        return
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    for node in _call_nodes(tree):
        method_name = _call_method_name(node)
        if method_name == "emit_event":
            _collect_emit_event_names(
                node, relative_path=relative_path, direct_emitters=direct_emitters
            )
        if method_name == "emit_domain_event":
            domain_event_emitters.append(relative_path)


def _scan_runtime_observability_event_calls(
    repo_root: Path,
) -> tuple[dict[str, list[str]], list[str]]:
    direct_emitters: dict[str, list[str]] = defaultdict(list)
    domain_event_emitters: list[str] = []
    for path in _iter_runtime_event_candidate_paths(repo_root):
        _scan_path_for_runtime_event_calls(
            path,
            repo_root=repo_root,
            direct_emitters=direct_emitters,
            domain_event_emitters=domain_event_emitters,
        )
    return _normalize_mapping_lists(direct_emitters), sorted(set(domain_event_emitters))


def _load_runtime_cardinality_thresholds(repo_root: Path) -> dict[str, int]:
    """Load approved runtime-cardinality thresholds from governed allowlist."""
    allowlist_path = repo_root / _DEFAULT_DRIFT_ALLOWLIST
    if not allowlist_path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    payload = yaml.safe_load(
        allowlist_path.read_text(encoding="utf-8")
    )  # NOSONAR - path confined
    if not isinstance(payload, dict):
        return {}
    allowed = payload.get("allowed", {})
    if not isinstance(allowed, dict):
        return {}
    thresholds: dict[str, int] = {}
    for entry in allowed.get("runtime_cardinality_review_required", []):
        if not isinstance(entry, dict):
            continue
        metric = entry.get("metric")
        approved_max = entry.get("approved_max_series")
        if isinstance(metric, str) and isinstance(approved_max, int):
            thresholds[metric] = approved_max
    return thresholds


def _sample_matches_metric(sample_name: str, metric_name: str) -> bool:
    return sample_name == metric_name or sample_name.startswith(f"{metric_name}_")


def _observed_labelsets_for_metric(
    metric: Any, metric_name: str
) -> set[tuple[tuple[str, str], ...]]:
    observed_labelsets: set[tuple[tuple[str, str], ...]] = set()
    for family in metric.collect():
        for sample in family.samples:
            if not _sample_matches_metric(str(sample.name), metric_name):
                continue
            observed_labelsets.add(
                tuple(sorted((str(k), str(v)) for k, v in sample.labels.items()))
            )
    return observed_labelsets


def _observed_runtime_series_counts() -> dict[str, int]:
    """Return current-process observed series counts from registered collectors."""
    counts: dict[str, int] = {}
    for registry in (COUNTERS, GAUGES, HISTOGRAMS):
        for metric_name, metric in registry.items():
            counts[metric_name] = len(
                _observed_labelsets_for_metric(metric, metric_name)
            )
    return counts


def _runtime_cardinality_evidence_rows(
    *,
    metric_names: list[str],
    combined_emitters: dict[str, list[str]],
    observed_series_counts: dict[str, int],
    thresholds: dict[str, int],
) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}
    for metric_name in metric_names:
        labels = sorted(REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name, ()))
        rows = [
            f"observed_series_count={observed_series_counts.get(metric_name, 0)}",
            f"approved_max_series={thresholds.get(metric_name, 0)}",
            f"runtime_emitter_count={len(set(combined_emitters.get(metric_name, [])))}",
            "label_keys=" + ",".join(labels),
        ]
        evidence[metric_name] = rows
    return evidence


def _runtime_cardinality_threshold_violations(
    *,
    observed_series_counts: dict[str, int],
    thresholds: dict[str, int],
) -> list[str]:
    violations: list[str] = []
    for metric_name, approved_max in sorted(thresholds.items()):
        observed = observed_series_counts.get(metric_name, 0)
        if observed > approved_max:
            violations.append(
                f"{metric_name} observed_series_count={observed} approved_max_series={approved_max}"
            )
    return violations


def _resolve_prometheus_base_url(
    explicit_base_url: str | None,
) -> tuple[str | None, str]:
    if explicit_base_url and explicit_base_url.strip():
        return explicit_base_url.strip().rstrip("/"), "cli"
    env_base_url = os.getenv(_PROMETHEUS_BASE_URL_ENV_VAR, "").strip()
    if env_base_url:
        return env_base_url.rstrip("/"), "env"
    return None, "unconfigured"


def _prometheus_metric_family_matcher(metric_name: str) -> str:
    escaped = re.escape(metric_name)
    return f"^{escaped}(?:_bucket|_sum|_count|_created)?$"


def _prometheus_cardinality_query(
    metric_name: str,
    *,
    label_names: frozenset[str],
    allow_absent_zero: bool = False,
) -> str:
    selector = (
        "{__name__=~" + json.dumps(_prometheus_metric_family_matcher(metric_name)) + "}"
    )
    if label_names:
        labels_expr = ", ".join(sorted(label_names))
        query = f"count(count by ({labels_expr}) ({selector}))"
        return f"{query} or vector(0)" if allow_absent_zero else query

    ignored_labels = ["__name__"]
    if metric_name in HISTOGRAMS:
        ignored_labels.append("le")
    ignored_expr = ", ".join(sorted(ignored_labels))
    query = f"count(count without ({ignored_expr}) ({selector}))"
    return f"{query} or vector(0)" if allow_absent_zero else query


def _prometheus_query_request(
    *,
    prometheus_base_url: str,
    query: str,
    bearer_token: str,
) -> Request:
    request = Request(
        url=prometheus_base_url.rstrip("/")
        + "/api/v1/query?"
        + urlencode({"query": query}),
        headers={"Accept": "application/json"},
    )
    if bearer_token:
        request.add_header("Authorization", f"Bearer {bearer_token}")
    return request


def _load_prometheus_query_payload(
    *,
    prometheus_base_url: str,
    query: str,
    bearer_token: str,
    error_prefix: str,
) -> dict[str, object]:
    request = _prometheus_query_request(
        prometheus_base_url=prometheus_base_url,
        query=query,
        bearer_token=bearer_token,
    )
    try:
        with urlopen(request, timeout=_PROMETHEUS_QUERY_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as exc:  # pragma: no cover - exercised via mocked failure paths
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except URLError as exc:  # pragma: no cover - exercised via mocked failure paths
        raise RuntimeError(str(exc.reason)) from exc

    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RuntimeError(error_prefix)
    return payload


def _scalar_from_prometheus_data(data: object) -> int:
    if not isinstance(data, dict):
        raise RuntimeError("missing Prometheus API data payload")
    result_type = data.get("resultType")
    result = data.get("result")
    if result_type == "scalar" and isinstance(result, list) and len(result) == 2:
        return int(float(result[1]))
    if result_type == "vector" and isinstance(result, list) and len(result) == 1:
        vector_item = result[0]
        if isinstance(vector_item, dict):
            value = vector_item.get("value")
            if isinstance(value, list) and len(value) == 2:
                return int(float(value[1]))
    raise RuntimeError("Prometheus query did not return a single scalar result")


def _query_prometheus_scalar(
    *,
    prometheus_base_url: str,
    query: str,
    bearer_token: str,
) -> int:
    payload = _load_prometheus_query_payload(
        prometheus_base_url=prometheus_base_url,
        query=query,
        bearer_token=bearer_token,
        error_prefix="unexpected Prometheus API response",
    )
    return _scalar_from_prometheus_data(payload.get("data"))


def _label_values_from_prometheus_result(
    result: list[object], label_names: frozenset[str]
) -> dict[str, list[str]]:
    observed: dict[str, set[str]] = {label_name: set() for label_name in label_names}
    for sample in result:
        if not isinstance(sample, dict) or not isinstance(sample.get("metric"), dict):
            continue
        labelset = sample["metric"]
        for label_name in label_names:
            value = labelset.get(label_name)
            if isinstance(value, str):
                observed[label_name].add(value)
    return {
        label_name: sorted(values) for label_name, values in sorted(observed.items())
    }


def _query_prometheus_label_values(
    *,
    prometheus_base_url: str,
    metric_name: str,
    label_names: frozenset[str],
    bearer_token: str,
) -> dict[str, list[str]]:
    """Return bounded observed label values for one watched metric family."""
    selector = (
        "{__name__=~" + json.dumps(_prometheus_metric_family_matcher(metric_name)) + "}"
    )
    payload = _load_prometheus_query_payload(
        prometheus_base_url=prometheus_base_url,
        query=selector,
        bearer_token=bearer_token,
        error_prefix="unexpected Prometheus query API response",
    )
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("result"), list):
        raise RuntimeError("missing Prometheus query API data payload")
    return _label_values_from_prometheus_result(data["result"], label_names)


def _git_source_provenance(repo_root: Path) -> dict[str, object]:
    """Capture revision and dirty state without coupling the two git probes."""

    def run_git(*args: str) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    revision_result = run_git("rev-parse", "HEAD")
    revision = (
        revision_result.stdout.strip()
        if revision_result is not None and revision_result.returncode == 0
        else None
    )

    tracked_result = run_git("diff-index", "--quiet", "HEAD", "--")
    untracked_result = run_git("ls-files", "--others", "--exclude-standard")
    dirty: bool | None = None
    if tracked_result is not None and tracked_result.returncode in {0, 1}:
        dirty = tracked_result.returncode == 1
    if untracked_result is not None and untracked_result.returncode == 0:
        dirty = bool(untracked_result.stdout.strip()) or bool(dirty)
    return {
        "source_revision": revision,
        "source_worktree_dirty": dirty,
    }


RuntimeCardinalityReviewSummary = dict[str, object]


def _parse_observed_series_count_rows(
    raw_value: Sequence[object],
) -> int | None:
    prefix = "observed_series_count="
    for row in raw_value:
        if not isinstance(row, str) or not row.startswith(prefix):
            continue
        try:
            return int(row.removeprefix(prefix))
        except ValueError:
            return None
    return None


def _local_observed_series_counts(report: MetricInventoryReport) -> dict[str, int]:
    raw_local_observed_series = report.get("runtime_cardinality_observed_series", {})
    if not isinstance(raw_local_observed_series, dict):
        return {}
    counts: dict[str, int] = {}
    for metric_name, raw_value in raw_local_observed_series.items():
        if not isinstance(metric_name, str):
            continue
        if isinstance(raw_value, int):
            counts[metric_name] = raw_value
            continue
        if not isinstance(raw_value, list):
            continue
        parsed = _parse_observed_series_count_rows(raw_value)
        if parsed is not None:
            counts[metric_name] = parsed
    return counts


def _sorted_string_rows(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return sorted(str(item) for item in raw if isinstance(item, str))


def _threshold_violation_rows(
    *,
    metric_names: list[str],
    observed_series: dict[str, int],
    thresholds: dict[str, int],
) -> list[str]:
    violations: list[str] = []
    for metric_name in metric_names:
        if metric_name not in observed_series or metric_name not in thresholds:
            continue
        observed_series_count = observed_series[metric_name]
        approved_max_series = thresholds[metric_name]
        if observed_series_count > approved_max_series:
            violations.append(
                f"{metric_name} observed_series_count={observed_series_count} "
                f"approved_max_series={approved_max_series}"
            )
    return violations


def _initial_cardinality_review_summary(
    *,
    repo_root: Path,
    reviewed_metrics: list[str],
    review_required: list[str],
    static_threshold_violations: list[str],
    thresholds: dict[str, int],
    prometheus: tuple[str | None, str],
    allow_local_cardinality_fallback: bool,
    local_series: tuple[dict[str, int], list[str]],
    live_series: tuple[
        dict[str, int],
        list[str],
        list[str],
        dict[str, str],
        dict[str, dict[str, list[str]]],
    ],
) -> RuntimeCardinalityReviewSummary:
    """Build the initial cardinality review summary.

    Packed groups keep this helper under the Sonar S107 parameter budget:
    - ``prometheus``: ``(resolved_base_url, url_source)``
    - ``local_series``: ``(local_observed_series, local_threshold_violations)``
    - ``live_series``: ``(query_results, live_threshold_violations,
      degraded_reasons, query_errors, observed_label_values)``
    """
    resolved_base_url, url_source = prometheus
    local_observed_series, local_threshold_violations = local_series
    (
        query_results,
        live_threshold_violations,
        degraded_reasons,
        query_errors,
        observed_label_values,
    ) = live_series
    return {
        "generated_at": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source_command": (
            "python -m scripts.engineering.qa.report_observability_metric_inventory "
            "--check --write-evidence reports/observability/runtime_cardinality_inventory.json "
            "--review-json-out reports/observability/runtime_cardinality_review.json "
            '--summary-out "$GITHUB_STEP_SUMMARY" '
            "--fail-on-degraded-live-review"
        ),
        "status": "passed",
        "mode": "static_only",
        "prometheus_base_url": resolved_base_url,
        "prometheus_base_url_source": url_source,
        "prometheus_url_env_var": _PROMETHEUS_BASE_URL_ENV_VAR,
        "prometheus_token_env_var": _PROMETHEUS_BEARER_TOKEN_ENV_VAR,
        "local_cardinality_fallback_allowed": allow_local_cardinality_fallback,
        "reviewed_metrics": reviewed_metrics,
        "review_required_metrics": review_required,
        "static_threshold_violations": static_threshold_violations,
        "approved_thresholds": {
            metric_name: thresholds[metric_name]
            for metric_name in reviewed_metrics
            if metric_name in thresholds
        },
        "local_observed_series": {
            metric_name: local_observed_series[metric_name]
            for metric_name in reviewed_metrics
            if metric_name in local_observed_series
        },
        "local_threshold_violations": local_threshold_violations,
        "live_observed_series": query_results,
        "live_threshold_violations": live_threshold_violations,
        "degraded_reasons": degraded_reasons,
        "query_errors": query_errors,
        "label_keys": {
            metric_name: sorted(
                REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name, frozenset())
            )
            for metric_name in reviewed_metrics
        },
        "observed_label_values": observed_label_values,
        **_git_source_provenance(repo_root),
    }


def _apply_local_cardinality_fallback(
    summary: RuntimeCardinalityReviewSummary,
    *,
    reviewed_metrics: list[str],
    thresholds: dict[str, int],
    local_observed_series: dict[str, int],
    local_threshold_violations: list[str],
    static_threshold_violations: list[str],
    degraded_reasons: list[str],
    missing_thresholds: list[str],
    allow_local_cardinality_fallback: bool,
) -> None:
    """Apply local fallback when Prometheus URL is missing."""
    if allow_local_cardinality_fallback and not missing_thresholds:
        missing_local_observations = [
            metric_name
            for metric_name in reviewed_metrics
            if metric_name not in local_observed_series
        ]
        if not missing_local_observations:
            summary["mode"] = "local_cardinality_fallback"
            local_threshold_violations.extend(
                _threshold_violation_rows(
                    metric_names=reviewed_metrics,
                    observed_series=local_observed_series,
                    thresholds=thresholds,
                )
            )
            if local_threshold_violations or static_threshold_violations:
                summary["status"] = "failed"
            return
        degraded_reasons.append(
            "missing local cardinality observations for reviewed metrics: "
            + ", ".join(missing_local_observations)
        )
    summary["status"] = "degraded"
    degraded_reasons.append(
        f"missing {_PROMETHEUS_BASE_URL_ENV_VAR}; falling back to static cardinality evidence only"
    )


def _query_live_cardinality_metrics(
    *,
    reviewed_metrics: list[str],
    resolved_base_url: str,
    query_results: dict[str, int],
    query_errors: dict[str, str],
    observed_label_values: dict[str, dict[str, list[str]]],
) -> None:
    bearer_token = os.getenv(_PROMETHEUS_BEARER_TOKEN_ENV_VAR, "").strip()
    for metric_name in reviewed_metrics:
        label_names = REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name, frozenset())
        query = _prometheus_cardinality_query(
            metric_name,
            label_names=label_names,
            allow_absent_zero=True,
        )
        try:
            query_results[metric_name] = _query_prometheus_scalar(
                prometheus_base_url=resolved_base_url,
                query=query,
                bearer_token=bearer_token,
            )
            observed_label_values[metric_name] = _query_prometheus_label_values(
                prometheus_base_url=resolved_base_url,
                metric_name=metric_name,
                label_names=label_names,
                bearer_token=bearer_token,
            )
        except RuntimeError as exc:
            query_errors[metric_name] = str(exc)


def _finalize_live_cardinality_review(
    summary: RuntimeCardinalityReviewSummary,
    *,
    thresholds: dict[str, int],
    query_results: dict[str, int],
    query_errors: dict[str, str],
    degraded_reasons: list[str],
    live_threshold_violations: list[str],
) -> RuntimeCardinalityReviewSummary:
    if query_errors or degraded_reasons:
        summary["status"] = "degraded"
        summary["mode"] = "live_review_unavailable"
        if query_errors:
            degraded_reasons.append(
                "live Prometheus review failed for: " + ", ".join(sorted(query_errors))
            )
        return summary

    summary["mode"] = "live_review"
    live_threshold_violations.extend(
        _threshold_violation_rows(
            metric_names=sorted(thresholds),
            observed_series=query_results,
            thresholds=thresholds,
        )
    )
    if live_threshold_violations:
        summary["status"] = "failed"
    return summary


def _build_runtime_cardinality_review_summary(
    report: MetricInventoryReport,
    *,
    repo_root: Path,
    prometheus_base_url: str | None,
    allow_local_cardinality_fallback: bool = False,
) -> RuntimeCardinalityReviewSummary:
    reviewed_metrics = _sorted_string_rows(
        report.get("runtime_cardinality_reviewed", [])
    )
    review_required = _sorted_string_rows(
        report.get("runtime_cardinality_review_required", [])
    )
    static_threshold_violations = _sorted_string_rows(
        report.get("runtime_cardinality_threshold_violations", [])
    )
    thresholds = _load_runtime_cardinality_thresholds(repo_root)
    resolved_base_url, url_source = _resolve_prometheus_base_url(prometheus_base_url)
    query_results: dict[str, int] = {}
    query_errors: dict[str, str] = {}
    observed_label_values: dict[str, dict[str, list[str]]] = {}
    degraded_reasons: list[str] = []
    live_threshold_violations: list[str] = []
    local_observed_series = _local_observed_series_counts(report)
    local_threshold_violations: list[str] = []

    summary = _initial_cardinality_review_summary(
        repo_root=repo_root,
        reviewed_metrics=reviewed_metrics,
        review_required=review_required,
        static_threshold_violations=static_threshold_violations,
        thresholds=thresholds,
        prometheus=(resolved_base_url, url_source),
        allow_local_cardinality_fallback=allow_local_cardinality_fallback,
        local_series=(local_observed_series, local_threshold_violations),
        live_series=(
            query_results,
            live_threshold_violations,
            degraded_reasons,
            query_errors,
            observed_label_values,
        ),
    )
    if not reviewed_metrics:
        summary["mode"] = "no_reviewed_metrics"
        degraded_reasons.append(
            "no reviewed runtime-cardinality metrics require live evidence"
        )
        return summary

    missing_thresholds = [
        metric_name for metric_name in reviewed_metrics if metric_name not in thresholds
    ]
    if missing_thresholds:
        degraded_reasons.append(
            "missing approved_max_series for reviewed metrics: "
            + ", ".join(missing_thresholds)
        )

    if resolved_base_url is None:
        _apply_local_cardinality_fallback(
            summary,
            reviewed_metrics=reviewed_metrics,
            thresholds=thresholds,
            local_observed_series=local_observed_series,
            local_threshold_violations=local_threshold_violations,
            static_threshold_violations=static_threshold_violations,
            degraded_reasons=degraded_reasons,
            missing_thresholds=missing_thresholds,
            allow_local_cardinality_fallback=allow_local_cardinality_fallback,
        )
        return summary

    _query_live_cardinality_metrics(
        reviewed_metrics=reviewed_metrics,
        resolved_base_url=resolved_base_url,
        query_results=query_results,
        query_errors=query_errors,
        observed_label_values=observed_label_values,
    )
    return _finalize_live_cardinality_review(
        summary,
        thresholds=thresholds,
        query_results=query_results,
        query_errors=query_errors,
        degraded_reasons=degraded_reasons,
        live_threshold_violations=live_threshold_violations,
    )
