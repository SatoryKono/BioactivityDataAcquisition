"""Runtime-event and cardinality review logic for observability inventory."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen as urlopen

from prometheus_client.registry import Collector

from bioetl.domain.observability_contract import (
    ORDINARY_PIPELINE_STAGE_NAMES,
    PipelineEvent,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _call_method_name,
    _call_nodes,
)
from bioetl.infrastructure.observability.metric_inventory_candidates import (
    _iter_runtime_event_candidate_paths,
)
from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _as_repo_relative,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _DEFAULT_DRIFT_ALLOWLIST,
    _DEFAULT_OBSERVABILITY_GOVERNANCE,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _normalize_mapping_lists,
    _read_runtime_event_candidate_text,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {
    name: frozenset(metric._labelnames)
    for registry in (COUNTERS, GAUGES, HISTOGRAMS)
    for name, metric in registry.items()
}


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
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return _resolve_stage_event_call(node, node.func)
    return set()


def _resolve_stage_event_call(node: ast.Call, function: ast.Attribute) -> set[str]:
    if not (
        isinstance(function.value, ast.Name) and function.value.id == "PipelineEvent"
    ):
        return set()
    if function.attr not in {"phase_started", "phase_completed"}:
        return set()
    resolver = (
        PipelineEvent.phase_started
        if function.attr == "phase_started"
        else PipelineEvent.phase_completed
    )
    if (
        node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return {resolver(node.args[0].value)}
    return {resolver(stage_name) for stage_name in ORDINARY_PIPELINE_STAGE_NAMES}


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
    metric: Collector, metric_name: str
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
