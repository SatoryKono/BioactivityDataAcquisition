"""Pure metric filtering and static rule scanning shared with diagnostics."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _as_repo_relative,
    _iter_text_files,
    _scan_canonical_metric_mentions,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _CANONICAL_METRIC_RE,
    _IGNORED_DOC_METRIC_NAMES,
    _PROMETHEUS_FAMILY_SUFFIXES,
    _RULE_SCAN_ROOT,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _normalize_mapping_lists,
)


def _looks_like_metric_family_name(name: str) -> bool:
    return any(name.endswith(suffix) for suffix in _PROMETHEUS_FAMILY_SUFFIXES)


def _is_generated_prometheus_series(
    metric_name: str,
    registered_metrics: frozenset[str] | set[str],
) -> bool:
    histogram_suffixes = ("_bucket", "_sum", "_count")
    for suffix in histogram_suffixes:
        if metric_name.endswith(suffix):
            return metric_name[: -len(suffix)] in registered_metrics
    if metric_name.endswith("_created"):
        base = metric_name.removesuffix("_created")
        return base in registered_metrics or f"{base}_total" in registered_metrics
    return False


def _filter_documented_metric_mentions(
    mentions: dict[str, list[str]],
    *,
    registered_metrics: frozenset[str] | set[str],
) -> dict[str, list[str]]:
    filtered: dict[str, list[str]] = {}
    for metric_name, paths in mentions.items():
        if metric_name in _IGNORED_DOC_METRIC_NAMES:
            continue
        if metric_name.endswith("_"):
            continue
        if _is_generated_prometheus_series(metric_name, registered_metrics):
            continue
        if metric_name not in registered_metrics and not _looks_like_metric_family_name(
            metric_name
        ):
            continue
        filtered[metric_name] = paths
    return _normalize_mapping_lists(filtered)


def _scan_rule_metric_mentions(repo_root: Path) -> dict[str, list[str]]:
    try:
        import yaml
    except ImportError:
        return _scan_canonical_metric_mentions(
            _iter_text_files(repo_root / _RULE_SCAN_ROOT),
            repo_root,
        )

    mentions: dict[str, list[str]] = defaultdict(list)
    for path in _iter_text_files(repo_root / _RULE_SCAN_ROOT):
        try:
            payload = yaml.safe_load(
                path.read_text(encoding="utf-8")
            )  # NOSONAR - path confined
        except (UnicodeDecodeError, yaml.YAMLError):
            continue
        if not isinstance(payload, dict):
            continue
        rel_path = _as_repo_relative(path, repo_root)
        groups = payload.get("groups", [])
        if not isinstance(groups, list):
            continue
        for metric_name in _extract_rule_metric_names(groups):
            mentions[metric_name].append(rel_path)
    return _normalize_mapping_lists(mentions)


def _extract_rule_metric_names(groups: list[object]) -> list[str]:
    metric_names: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        rules = group.get("rules", [])
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            expr = rule.get("expr")
            if isinstance(expr, str):
                metric_names.update(_CANONICAL_METRIC_RE.findall(expr))
    return sorted(metric_names)


def _drift_allowlist_token(key: str, value: str) -> str:
    """Normalize drift rows for allowlist comparison."""
    if key == "runtime_label_contract_unresolved":
        return value.split(" @ ", 1)[0]
    return value
