"""Source discovery and AST scanners for observability metric inventory."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_ast import (
    _record_label_contract_violations,
    _record_runtime_mentions,
    _scan_direct_metric_label_shapes,
    _scan_metric_names_in_tree,
)
from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _collect_class_attribute_bindings,
    _collect_local_string_bindings,
    _collect_repo_class_attribute_bindings,
    _resolve_imported_metric_bindings,
    _resolve_imported_string_bindings,
)
from bioetl.infrastructure.observability.metric_inventory_candidates import (
    _collect_runtime_candidate_texts,
)
from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _as_repo_relative,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _CANONICAL_METRIC_RE,
    _DEFAULT_DECLARED_METRIC_DEFINITIONS,
    _REGISTERED_SCAN_ROOT,
    _STATIC_RUNTIME_EMITTERS,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _normalize_mapping_lists,
    _read_runtime_candidate_text,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {}


def _scan_runtime_metric_file(
    path: Path,
    *,
    repo_root: Path,
    import_binding_cache: dict[Path, dict[str, str]],
    repo_attribute_bindings: dict[str, str] | None = None,
    preloaded_text: str | None = None,
) -> (
    tuple[
        str,
        set[str],
        set[str],
        set[str],
        list[tuple[str, frozenset[str] | None, int]],
    ]
    | None
):
    text = (
        preloaded_text
        if preloaded_text is not None
        else _read_runtime_candidate_text(path)
    )
    if text is None:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    string_bindings = _resolve_imported_string_bindings(
        tree,
        repo_root=repo_root,
        cache=import_binding_cache,
    )
    string_bindings.update(_collect_local_string_bindings(tree))
    metric_bindings = _resolve_imported_metric_bindings(tree)
    attribute_bindings = dict(repo_attribute_bindings or {})
    attribute_bindings.update(_collect_class_attribute_bindings(tree))
    direct_metric_names, helper_metric_names, alias_metric_names = (
        _scan_metric_names_in_tree(
            tree,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    )
    label_shapes = _scan_direct_metric_label_shapes(
        tree,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )
    return (
        _as_repo_relative(path, repo_root),
        direct_metric_names,
        helper_metric_names,
        alias_metric_names,
        label_shapes,
    )


def _scan_runtime_metric_calls(
    repo_root: Path,
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
    dict[str, list[str]],
    list[str],
    list[str],
]:
    canonical_mentions: dict[str, list[str]] = defaultdict(list)
    helper_backed_mentions: dict[str, list[str]] = defaultdict(list)
    alias_mentions: dict[str, list[str]] = defaultdict(list)
    label_contract_violations: list[str] = []
    label_contract_unresolved: list[str] = []
    import_binding_cache: dict[Path, dict[str, str]] = {}
    candidate_files = _collect_runtime_candidate_texts(repo_root)
    repo_attribute_bindings = _collect_repo_class_attribute_bindings(candidate_files)
    for path, preloaded_text in candidate_files:
        scan_result = _scan_runtime_metric_file(
            path,
            repo_root=repo_root,
            import_binding_cache=import_binding_cache,
            repo_attribute_bindings=repo_attribute_bindings,
            preloaded_text=preloaded_text,
        )
        if scan_result is None:
            continue
        (
            relative_path,
            direct_metric_names,
            helper_metric_names,
            alias_metric_names,
            label_shapes,
        ) = scan_result
        _record_runtime_mentions(
            canonical_mentions=canonical_mentions,
            helper_backed_mentions=helper_backed_mentions,
            alias_mentions=alias_mentions,
            relative_path=relative_path,
            direct_metric_names=direct_metric_names,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )
        _record_label_contract_violations(
            label_contract_violations=label_contract_violations,
            label_contract_unresolved=label_contract_unresolved,
            relative_path=relative_path,
            label_shapes=label_shapes,
        )
    _record_static_runtime_emitters(repo_root, canonical_mentions)
    return (
        _normalize_mapping_lists(canonical_mentions),
        _normalize_mapping_lists(helper_backed_mentions),
        _normalize_mapping_lists(alias_mentions),
        sorted(label_contract_violations),
        sorted(label_contract_unresolved),
    )


def _record_static_runtime_emitters(
    repo_root: Path,
    canonical_mentions: dict[str, list[str]],
) -> None:
    """Record runtime emitters that use direct Prometheus collectors."""
    for metric_name, relative_paths in _STATIC_RUNTIME_EMITTERS.items():
        for relative_path in relative_paths:
            if (repo_root / relative_path).exists():
                canonical_mentions[metric_name].append(relative_path)


def _scan_registered_metric_names(repo_root: Path) -> frozenset[str]:
    metric_names: set[str] = set()
    for path in sorted((repo_root / _REGISTERED_SCAN_ROOT).glob("_metrics_defs_*.py")):
        try:
            text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
        except UnicodeDecodeError:
            continue
        metric_names.update(_CANONICAL_METRIC_RE.findall(text))
    return frozenset(metric_names)


def _installed_registered_metric_names() -> frozenset[str]:
    """Read registry declarations from this installed distribution's own sources."""
    metric_names: set[str] = set()
    for path in sorted(Path(__file__).parent.glob("_metrics_defs_*.py")):
        metric_names.update(
            _CANONICAL_METRIC_RE.findall(path.read_text(encoding="utf-8"))
        )
    return frozenset(metric_names)


def _load_declared_metric_definitions(repo_root: Path) -> dict[str, set[str]]:
    path = repo_root / _DEFAULT_DECLARED_METRIC_DEFINITIONS
    if not path.exists():
        return {
            "recording_rule_metrics": set(),
            "policy_alias_metrics": set(),
            "declared_label_contract_metrics": set(),
        }
    try:
        import yaml
    except ImportError:
        return {
            "recording_rule_metrics": set(),
            "policy_alias_metrics": set(),
            "declared_label_contract_metrics": set(),
        }
    payload = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )  # NOSONAR - path confined
    if not isinstance(payload, dict):
        return {
            "recording_rule_metrics": set(),
            "policy_alias_metrics": set(),
            "declared_label_contract_metrics": set(),
        }

    definitions: dict[str, set[str]] = {}
    for field in (
        "recording_rule_metrics",
        "policy_alias_metrics",
        "declared_label_contract_metrics",
    ):
        raw_metrics = payload.get(field, [])
        if not isinstance(raw_metrics, list):
            definitions[field] = set()
            continue
        definitions[field] = {
            value
            for value in raw_metrics
            if isinstance(value, str) and value.startswith("bioetl_")
        }
    return definitions
