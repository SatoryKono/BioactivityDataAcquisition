"""Source discovery and AST scanners for observability metric inventory."""

from __future__ import annotations

import ast

from bioetl.infrastructure.observability.metric_inventory_bindings import (
    _call_method_name,
    _call_nodes,
    _resolve_metric_name_expr,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _DIRECT_COLLECTOR_TERMINAL_METHODS,
    _NON_METRIC_ALIAS_PREFIXES,
    _PROMETHEUS_ALIAS_SUFFIXES,
    _PROMETHEUS_METRIC_NAME_RE,
    _RUNTIME_METRIC_METHODS,
    _RUNTIME_METRIC_NAME_KEYWORDS,
)

REGISTERED_PROMETHEUS_METRIC_LABELS: dict[str, frozenset[str]] = {}


def _helper_metric_candidates(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
    call_method_name: str | None,
) -> set[str]:
    candidates: set[str] = set()
    if call_method_name == "emit_metric":
        for arg in node.args:
            metric_name = _resolve_metric_name_expr(
                arg,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
                metric_bindings=metric_bindings,
            )
            if metric_name is not None:
                candidates.add(metric_name)
    for keyword in node.keywords:
        metric_name = _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if metric_name is None:
            continue
        if keyword.arg in _RUNTIME_METRIC_NAME_KEYWORDS or metric_name.startswith(
            "bioetl_"
        ):
            candidates.add(metric_name)
    return candidates


def _scan_metric_names_in_tree(
    tree: ast.AST,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> tuple[set[str], set[str], set[str]]:
    direct_metric_names: set[str] = set()
    helper_metric_names: set[str] = set()
    alias_metric_names: set[str] = set()

    for call_node in _call_nodes(tree):
        direct_metric_name, helper_candidates = _metric_names_for_call(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if direct_metric_name is not None:
            direct_metric_names.add(direct_metric_name)
            continue
        _partition_helper_metric_candidates(
            helper_candidates,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )

    return direct_metric_names, helper_metric_names, alias_metric_names


def _metric_names_for_call(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> tuple[str | None, set[str]]:
    """Return direct runtime metric name or helper candidates for one call."""
    method_name = _call_method_name(node)
    if method_name in _RUNTIME_METRIC_METHODS:
        return (
            _direct_metric_name(
                node,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
                metric_bindings=metric_bindings,
            ),
            set(),
        )
    collector_metric_name = _direct_collector_metric_name(
        node,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )
    if collector_metric_name is not None:
        return (collector_metric_name, set())
    return (
        None,
        _helper_metric_candidates(
            node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
            call_method_name=method_name,
        ),
    )


def _direct_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    """Resolve the direct runtime metric name from a runtime metrics call."""
    if node.args:
        return _resolve_metric_name_expr(
            node.args[0],
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    for keyword in node.keywords:
        if keyword.arg != "name" or keyword.value is None:
            continue
        return _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
    return None


def _collector_base_metric_expr(node: ast.Call) -> ast.expr | None:
    func = node.func
    if (
        not isinstance(func, ast.Attribute)
        or func.attr not in _DIRECT_COLLECTOR_TERMINAL_METHODS
    ):
        return None
    if isinstance(func.value, ast.Call):
        labels_call = func.value
        labels_func = labels_call.func
        if isinstance(labels_func, ast.Attribute) and labels_func.attr == "labels":
            return labels_func.value
        return None
    return func.value


def _direct_collector_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> str | None:
    metric_expr = _collector_base_metric_expr(node)
    if metric_expr is None:
        return None
    return _resolve_metric_name_expr(
        metric_expr,
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
        metric_bindings=metric_bindings,
    )


def _dict_literal_string_keys(node: ast.expr) -> frozenset[str] | None:
    """Return literal string keys when *node* is a dict literal."""
    if not isinstance(node, ast.Dict):
        return None
    keys: set[str] = set()
    for key_node in node.keys:
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            return None
        keys.add(key_node.value)
    return frozenset(keys)


def _direct_metric_label_keys(node: ast.Call) -> frozenset[str] | None:
    """Resolve statically declared label keys from one direct metric call."""
    for keyword in node.keywords:
        if keyword.arg == "labels" and keyword.value is not None:
            return _dict_literal_string_keys(keyword.value)
    if len(node.args) >= 3:
        return _dict_literal_string_keys(node.args[2])
    return frozenset()


def _scan_direct_metric_label_shapes(
    tree: ast.AST,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
    metric_bindings: dict[str, str],
) -> list[tuple[str, frozenset[str] | None, int]]:
    """Return direct metric label shapes resolved from literal label dictionaries."""
    shapes: list[tuple[str, frozenset[str] | None, int]] = []
    for call_node in _call_nodes(tree):
        if _call_method_name(call_node) not in _RUNTIME_METRIC_METHODS:
            continue
        metric_name = _direct_metric_name(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
            metric_bindings=metric_bindings,
        )
        if metric_name is None or not metric_name.startswith("bioetl_"):
            continue
        shapes.append(
            (
                metric_name,
                _direct_metric_label_keys(call_node),
                getattr(call_node, "lineno", 0),
            )
        )
    return shapes


def _record_label_contract_violations(
    *,
    label_contract_violations: list[str],
    label_contract_unresolved: list[str],
    relative_path: str,
    label_shapes: list[tuple[str, frozenset[str] | None, int]],
) -> None:
    """Compare direct emitter label keys against declared registry contracts."""
    for metric_name, emitted_labels, lineno in label_shapes:
        declared_labels = REGISTERED_PROMETHEUS_METRIC_LABELS.get(metric_name)
        if declared_labels is None:
            continue
        location = f"{relative_path}:{lineno}"
        if emitted_labels is None:
            label_contract_unresolved.append(f"{metric_name} @ {location}")
            continue
        missing = sorted(declared_labels - emitted_labels)
        extra = sorted(emitted_labels - declared_labels)
        if missing or extra:
            emitted = sorted(emitted_labels)
            declared = sorted(declared_labels)
            label_contract_violations.append(
                f"{metric_name} @ {location} missing={missing} extra={extra} "
                f"emitted={emitted} declared={declared}"
            )


def _partition_helper_metric_candidates(
    metric_names: set[str],
    *,
    helper_metric_names: set[str],
    alias_metric_names: set[str],
) -> None:
    """Partition helper candidate names into canonical and alias buckets."""
    for metric_name in metric_names:
        if metric_name.startswith("bioetl_"):
            helper_metric_names.add(metric_name)
        elif _is_metric_like_alias_name(metric_name):
            alias_metric_names.add(metric_name)


def _is_metric_like_alias_name(metric_name: str) -> bool:
    """Return True only for plausible Prometheus-style alias metric names."""
    normalized = metric_name.strip()
    if not normalized:
        return False
    if not _PROMETHEUS_METRIC_NAME_RE.fullmatch(normalized):
        return False
    if "_" not in normalized:
        return False
    if normalized.startswith(_NON_METRIC_ALIAS_PREFIXES):
        return False
    return normalized.endswith(tuple(_PROMETHEUS_ALIAS_SUFFIXES))


def _record_runtime_mentions(
    *,
    canonical_mentions: dict[str, list[str]],
    helper_backed_mentions: dict[str, list[str]],
    alias_mentions: dict[str, list[str]],
    relative_path: str,
    direct_metric_names: set[str],
    helper_metric_names: set[str],
    alias_metric_names: set[str],
) -> None:
    for metric_name in sorted(direct_metric_names):
        if metric_name.startswith("bioetl_"):
            canonical_mentions[metric_name].append(relative_path)
            continue
        if _is_metric_like_alias_name(metric_name):
            alias_mentions[metric_name].append(relative_path)
    for metric_name in sorted(helper_metric_names - direct_metric_names):
        helper_backed_mentions[metric_name].append(relative_path)
    for metric_name in sorted(alias_metric_names):
        alias_mentions[metric_name].append(relative_path)
