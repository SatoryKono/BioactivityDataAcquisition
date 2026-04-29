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

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Final

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

_CANONICAL_METRIC_RE = re.compile(r"\bbioetl_[a-z0-9_]+\b")

_RUNTIME_SCAN_ROOT = Path("src/bioetl")
_REGISTERED_SCAN_ROOT = Path("src/bioetl/infrastructure/observability")
_DOC_SCAN_ROOTS = (
    Path("docs/02-architecture"),
    Path("docs/03-guides"),
    Path("docs/04-reference"),
    Path("docs/05-operations"),
    Path("grafana/dashboards"),
    Path("grafana/README.md"),
)
_RULE_SCAN_ROOT = Path("grafana/prometheus-rules")
_DEFAULT_DRIFT_ALLOWLIST = Path(
    "configs/quality/observability_metric_inventory_allowlist.yaml"
)
_RUNTIME_EXCLUDE_PARTS = (
    "src/bioetl/infrastructure/observability",
    "src/bioetl/domain",
)
_TEXT_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml"}
_RUNTIME_METRIC_METHODS = frozenset(
    {"increment_counter", "observe_histogram", "set_gauge"}
)
_RUNTIME_METRIC_NAME_KEYWORDS = frozenset(
    {"metric_name", "state_metric_name", "trip_metric_name"}
)
_RUNTIME_SCAN_MARKERS: Final[tuple[str, ...]] = (
    "bioetl_",
    "increment_counter",
    "observe_histogram",
    "set_gauge",
    "metric_name",
    "state_metric_name",
    "trip_metric_name",
)
_PROMETHEUS_FAMILY_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        "_bytes",
        "_count",
        "_enabled",
        "_ms",
        "_passed",
        "_rate",
        "_records",
        "_score",
        "_seconds",
        "_size",
        "_state",
        "_status",
        "_total",
        "_validated",
    }
)
_IGNORED_DOC_METRIC_NAMES: Final[frozenset[str]] = frozenset(
    {
        "bioetl_alerts",
        "bioetl_observability",
        "bioetl_pipeline",
    }
)
_CHECK_DRIFT_KEYS: Final[tuple[str, ...]] = (
    "registered_without_runtime",
    "runtime_without_registry",
    "dead_metrics",
    "documented_without_registry",
    "rules_without_registry",
)


def _iter_text_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root] if root.suffix in _TEXT_SUFFIXES else []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in _TEXT_SUFFIXES
    )


def _as_repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_canonical_metric_mentions(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]]:
    mentions: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(text))):
            mentions[metric_name].append(_as_repo_relative(path, repo_root))
    return dict(mentions)


def _read_runtime_candidate_text(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    if not any(marker in text for marker in _RUNTIME_SCAN_MARKERS):
        return None
    return text


def _module_path_from_import(module_name: str, repo_root: Path) -> Path | None:
    if not module_name.startswith("bioetl."):
        return None
    module_rel = module_name.replace(".", "/")
    module_path = repo_root / "src" / f"{module_rel}.py"
    if module_path.exists():
        return module_path
    package_init = repo_root / "src" / module_rel / "__init__.py"
    if package_init.exists():
        return package_init
    return None


def _collect_module_string_bindings(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    bindings: dict[str, str] = {}
    for node in tree.body:
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value_node.value
    return bindings


def _iter_string_assignments(tree: ast.AST) -> list[tuple[list[ast.expr], str]]:
    assignments: list[tuple[list[ast.expr], str]] = []
    for node in ast.walk(tree):
        value_node: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value_node = node.value
            targets = [node.target]
        if (
            value_node is None
            or not isinstance(value_node, ast.Constant)
            or not isinstance(value_node.value, str)
        ):
            continue
        assignments.append((targets, value_node.value))
    return assignments


def _resolve_imported_string_bindings(
    tree: ast.AST,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]] | None = None,
) -> dict[str, str]:
    resolved_cache = cache if cache is not None else {}
    bindings: dict[str, str] = {}
    for node in _import_from_nodes(tree):
        module_bindings = _module_string_bindings(
            node.module,
            repo_root=repo_root,
            cache=resolved_cache,
        )
        if module_bindings is None:
            continue
        _merge_imported_string_aliases(bindings, module_bindings, node.names)
    return bindings


def _collect_class_attribute_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for class_node in _class_nodes(tree):
        bindings.update(_class_attribute_string_bindings(class_node))
    return bindings


def _resolve_metric_name_expr(
    node: ast.expr,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return string_bindings.get(node.id)
    if isinstance(node, ast.Attribute):
        return attribute_bindings.get(node.attr)
    return None


def _collect_local_string_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for targets, value in _iter_string_assignments(tree):
        for target in targets:
            if isinstance(target, ast.Name):
                bindings[target.id] = value
    return bindings


def _call_method_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _helper_metric_candidates(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
) -> set[str]:
    candidates: set[str] = set()
    for arg in node.args:
        metric_name = _resolve_metric_name_expr(
            arg,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
        )
        if metric_name is not None:
            candidates.add(metric_name)
    for keyword in node.keywords:
        if keyword.value is None:
            continue
        metric_name = _resolve_metric_name_expr(
            keyword.value,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
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
) -> tuple[set[str], set[str], set[str]]:
    direct_metric_names: set[str] = set()
    helper_metric_names: set[str] = set()
    alias_metric_names: set[str] = set()

    for call_node in _call_nodes(tree):
        direct_metric_name, helper_candidates = _metric_names_for_call(
            call_node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
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


def _import_from_nodes(tree: ast.AST) -> list[ast.ImportFrom]:
    """Return import-from nodes with concrete module names."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]


def _module_string_bindings(
    module_name: str | None,
    *,
    repo_root: Path,
    cache: dict[Path, dict[str, str]],
) -> dict[str, str] | None:
    """Load cached string bindings for one imported module."""
    if module_name is None:
        return None
    module_path = _module_path_from_import(module_name, repo_root)
    if module_path is None:
        return None
    if module_path not in cache:
        try:
            cache[module_path] = _collect_module_string_bindings(module_path)
        except UnicodeDecodeError:
            cache[module_path] = {}
    return cache[module_path]


def _merge_imported_string_aliases(
    bindings: dict[str, str],
    module_bindings: dict[str, str],
    aliases: list[ast.alias],
) -> None:
    """Merge imported string constants into the local binding map."""
    for alias in aliases:
        if alias.name == "*":
            continue
        resolved = module_bindings.get(alias.name)
        if resolved is not None:
            bindings[alias.asname or alias.name] = resolved


def _class_nodes(tree: ast.AST) -> list[ast.ClassDef]:
    """Return all class definitions in the tree."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _class_attribute_string_bindings(class_node: ast.ClassDef) -> dict[str, str]:
    """Collect string-valued class attribute bindings for one class."""
    bindings: dict[str, str] = {}
    for body_node in class_node.body:
        for targets, value in _iter_string_assignments(body_node):
            for target in targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = value
    return bindings


def _call_nodes(tree: ast.AST) -> list[ast.Call]:
    """Return all call nodes from the AST."""
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def _metric_names_for_call(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
) -> tuple[str | None, set[str]]:
    """Return direct runtime metric name or helper candidates for one call."""
    method_name = _call_method_name(node)
    if method_name in _RUNTIME_METRIC_METHODS:
        return (
            _direct_metric_name(
                node,
                string_bindings=string_bindings,
                attribute_bindings=attribute_bindings,
            ),
            set(),
        )
    return (
        None,
        _helper_metric_candidates(
            node,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
        ),
    )


def _direct_metric_name(
    node: ast.Call,
    *,
    string_bindings: dict[str, str],
    attribute_bindings: dict[str, str],
) -> str | None:
    """Resolve the direct runtime metric name from a runtime metrics call."""
    if not node.args:
        return None
    return _resolve_metric_name_expr(
        node.args[0],
        string_bindings=string_bindings,
        attribute_bindings=attribute_bindings,
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
        else:
            alias_metric_names.add(metric_name)


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
        target = (
            canonical_mentions if metric_name.startswith("bioetl_") else alias_mentions
        )
        target[metric_name].append(relative_path)
    for metric_name in sorted(helper_metric_names - direct_metric_names):
        helper_backed_mentions[metric_name].append(relative_path)
    for metric_name in sorted(alias_metric_names):
        alias_mentions[metric_name].append(relative_path)


def _scan_runtime_metric_file(
    path: Path,
    *,
    repo_root: Path,
    import_binding_cache: dict[Path, dict[str, str]],
    preloaded_text: str | None = None,
) -> tuple[str, set[str], set[str], set[str]] | None:
    text = preloaded_text if preloaded_text is not None else _read_runtime_candidate_text(path)
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
    attribute_bindings = _collect_class_attribute_bindings(tree)
    direct_metric_names, helper_metric_names, alias_metric_names = (
        _scan_metric_names_in_tree(
            tree,
            string_bindings=string_bindings,
            attribute_bindings=attribute_bindings,
        )
    )
    return (
        _as_repo_relative(path, repo_root),
        direct_metric_names,
        helper_metric_names,
        alias_metric_names,
    )


def _scan_runtime_metric_calls(
    repo_root: Path,
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    canonical_mentions: dict[str, list[str]] = defaultdict(list)
    helper_backed_mentions: dict[str, list[str]] = defaultdict(list)
    alias_mentions: dict[str, list[str]] = defaultdict(list)
    import_binding_cache: dict[Path, dict[str, str]] = {}
    for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT):
        path_str = path.as_posix()
        if any(excluded in path_str for excluded in _RUNTIME_EXCLUDE_PARTS):
            continue
        scan_result = _scan_runtime_metric_file(
            path,
            repo_root=repo_root,
            import_binding_cache=import_binding_cache,
        )
        if scan_result is None:
            continue
        relative_path, direct_metric_names, helper_metric_names, alias_metric_names = (
            scan_result
        )
        _record_runtime_mentions(
            canonical_mentions=canonical_mentions,
            helper_backed_mentions=helper_backed_mentions,
            alias_mentions=alias_mentions,
            relative_path=relative_path,
            direct_metric_names=direct_metric_names,
            helper_metric_names=helper_metric_names,
            alias_metric_names=alias_metric_names,
        )
    return (
        dict(canonical_mentions),
        dict(helper_backed_mentions),
        dict(alias_mentions),
    )


def _scan_registered_metric_names(repo_root: Path) -> frozenset[str]:
    metric_names: set[str] = set()
    for path in sorted((repo_root / _REGISTERED_SCAN_ROOT).glob("_metrics_defs_*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        metric_names.update(_CANONICAL_METRIC_RE.findall(text))
    return frozenset(metric_names)


REGISTERED_PROMETHEUS_METRIC_NAMES = _scan_registered_metric_names(_REPO_ROOT)


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
    return filtered


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
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
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
    return dict(mentions)


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


def collect_metric_inventory(
    repo_root: Path,
) -> dict[str, list[str] | dict[str, list[str]]]:
    registered = sorted(REGISTERED_PROMETHEUS_METRIC_NAMES)
    runtime_mentions, helper_backed_mentions, alias_mentions = (
        _scan_runtime_metric_calls(repo_root)
    )

    doc_paths: list[Path] = []
    for root in _DOC_SCAN_ROOTS:
        doc_paths.extend(_iter_text_files(repo_root / root))
    docs_mentions = _filter_documented_metric_mentions(
        _scan_canonical_metric_mentions(doc_paths, repo_root),
        registered_metrics=REGISTERED_PROMETHEUS_METRIC_NAMES,
    )
    rules_mentions = _filter_documented_metric_mentions(
        _scan_rule_metric_mentions(repo_root),
        registered_metrics=REGISTERED_PROMETHEUS_METRIC_NAMES,
    )

    registered_set = set(registered)
    direct_runtime_set = set(runtime_mentions)
    helper_runtime_set = set(helper_backed_mentions)
    runtime_set = direct_runtime_set | helper_runtime_set
    docs_set = set(docs_mentions)
    rules_set = set(rules_mentions)
    registry_only_metrics = registered_set - runtime_set
    runtime_without_registry = runtime_set - registered_set
    dead_metrics = registry_only_metrics - docs_set - rules_set
    documented_without_runtime = (docs_set & registered_set) - runtime_set
    ruled_without_runtime = (rules_set & registered_set) - runtime_set

    report: dict[str, list[str] | dict[str, list[str]]] = {
        "registered_metrics": registered,
        "live_metrics": sorted(registered_set & runtime_set),
        "direct_live_metrics": sorted(registered_set & direct_runtime_set),
        "helper_backed_live_metrics": sorted(registered_set & helper_runtime_set),
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
        "docs_mentions": docs_mentions,
        "rules_mentions": rules_mentions,
        "alias_emitters": alias_mentions,
    }
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when metric registry/runtime/docs drift exceeds the allowlist",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=_DEFAULT_DRIFT_ALLOWLIST,
        help="YAML file with allowed drift entries for --check",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to scan",
    )
    return parser


def _load_drift_allowlist(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    raw_allowed = payload.get("allowed", payload)
    if not isinstance(raw_allowed, dict):
        return {}
    allowlist: dict[str, set[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = raw_allowed.get(key, [])
        if not isinstance(values, list):
            continue
        allowlist[key] = {str(value) for value in values}
    return allowlist


def validate_metric_inventory(
    report: dict[str, list[str] | dict[str, list[str]]],
    *,
    allowlist: dict[str, set[str]] | None = None,
) -> dict[str, list[str]]:
    """Return unallowed metric drift grouped by deterministic check category."""
    allowed = allowlist or {}
    violations: dict[str, list[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = report.get(key, [])
        if not isinstance(values, list):
            continue
        unallowed = sorted(set(values) - allowed.get(key, set()))
        if unallowed:
            violations[key] = unallowed
    return violations


def _render_text(report: dict[str, list[str] | dict[str, list[str]]]) -> str:
    lines = ["Observability metric inventory"]
    for key in (
        "live_metrics",
        "direct_live_metrics",
        "helper_backed_live_metrics",
        "registered_without_runtime",
        "runtime_without_registry",
        "dead_metrics",
        "documented_without_registry",
        "rules_without_registry",
        "documented_without_runtime",
        "ruled_without_runtime",
        "compatibility_alias_candidates",
    ):
        values = report[key]
        assert isinstance(values, list)
        lines.append(f"\n{key} ({len(values)}):")
        if not values:
            lines.append("  - <none>")
            continue
        lines.extend(f"  - {value}" for value in values)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = collect_metric_inventory(args.repo_root)
    allowlist_path = args.allowlist
    if not allowlist_path.is_absolute():
        allowlist_path = args.repo_root / allowlist_path
    violations = (
        validate_metric_inventory(
            report,
            allowlist=_load_drift_allowlist(allowlist_path),
        )
        if args.check
        else {}
    )
    if args.json:
        if args.check:
            report["check_violations"] = violations
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        if violations:
            return 1
        return 0
    print(_render_text(report))
    if violations:
        print("\nMetric inventory drift check failed:", file=sys.stderr)
        for key, values in violations.items():
            print(f"{key} ({len(values)}):", file=sys.stderr)
            for value in values:
                print(f"  - {value}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
