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


def _resolve_imported_string_bindings(
    tree: ast.AST,
    *,
    repo_root: Path,
) -> dict[str, str]:
    cache: dict[Path, dict[str, str]] = {}
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        module_path = _module_path_from_import(node.module, repo_root)
        if module_path is None:
            continue
        if module_path not in cache:
            try:
                cache[module_path] = _collect_module_string_bindings(module_path)
            except UnicodeDecodeError:
                cache[module_path] = {}
        module_bindings = cache[module_path]
        for alias in node.names:
            if alias.name == "*":
                continue
            resolved = module_bindings.get(alias.name)
            if resolved is not None:
                bindings[alias.asname or alias.name] = resolved
    return bindings


def _collect_class_attribute_bindings(tree: ast.AST) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for body_node in node.body:
            value_node: ast.expr | None = None
            targets: list[ast.expr] = []
            if isinstance(body_node, ast.Assign):
                value_node = body_node.value
                targets = list(body_node.targets)
            elif isinstance(body_node, ast.AnnAssign):
                value_node = body_node.value
                targets = [body_node.target]
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


def _scan_runtime_metric_calls(
    repo_root: Path,
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    canonical_mentions: dict[str, list[str]] = defaultdict(list)
    helper_backed_mentions: dict[str, list[str]] = defaultdict(list)
    alias_mentions: dict[str, list[str]] = defaultdict(list)
    for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT):
        path_str = path.as_posix()
        if any(excluded in path_str for excluded in _RUNTIME_EXCLUDE_PARTS):
            continue
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        string_bindings: dict[str, str] = {}
        string_bindings.update(_resolve_imported_string_bindings(tree, repo_root=repo_root))
        attribute_bindings = _collect_class_attribute_bindings(tree)
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
            for target in targets:
                if isinstance(target, ast.Name):
                    string_bindings[target.id] = value_node.value
        direct_metric_names: set[str] = set()
        helper_metric_names: set[str] = set()
        alias_metric_names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            method_name: str | None = None
            if isinstance(func, ast.Attribute):
                method_name = func.attr
            elif isinstance(func, ast.Name):
                method_name = func.id
            if method_name in _RUNTIME_METRIC_METHODS:
                if not node.args:
                    continue
                metric_name = _resolve_metric_name_expr(
                    node.args[0],
                    string_bindings=string_bindings,
                    attribute_bindings=attribute_bindings,
                )
                if metric_name is None:
                    continue
                direct_metric_names.add(metric_name)
                continue

            helper_candidates: set[str] = set()
            for arg in node.args:
                metric_name = _resolve_metric_name_expr(
                    arg,
                    string_bindings=string_bindings,
                    attribute_bindings=attribute_bindings,
                )
                if metric_name is not None:
                    helper_candidates.add(metric_name)
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
                    helper_candidates.add(metric_name)
            for metric_name in helper_candidates:
                if metric_name.startswith("bioetl_"):
                    helper_metric_names.add(metric_name)
                else:
                    alias_metric_names.add(metric_name)

        relative_path = _as_repo_relative(path, repo_root)
        for metric_name in sorted(direct_metric_names):
            target = (
                canonical_mentions
                if metric_name.startswith("bioetl_")
                else alias_mentions
            )
            target[metric_name].append(relative_path)
        for metric_name in sorted(helper_metric_names - direct_metric_names):
            helper_backed_mentions[metric_name].append(relative_path)
        for metric_name in sorted(alias_metric_names):
            alias_mentions[metric_name].append(relative_path)
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
                if not isinstance(expr, str):
                    continue
                for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(expr))):
                    mentions[metric_name].append(rel_path)
    return dict(mentions)


def collect_metric_inventory(repo_root: Path) -> dict[str, list[str] | dict[str, list[str]]]:
    registered = sorted(REGISTERED_PROMETHEUS_METRIC_NAMES)
    runtime_mentions, helper_backed_mentions, alias_mentions = _scan_runtime_metric_calls(
        repo_root
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
    dead_metrics = registry_only_metrics - docs_set - rules_set
    documented_without_runtime = (docs_set & registered_set) - runtime_set
    ruled_without_runtime = (rules_set & registered_set) - runtime_set

    report: dict[str, list[str] | dict[str, list[str]]] = {
        "registered_metrics": registered,
        "live_metrics": sorted(registered_set & runtime_set),
        "direct_live_metrics": sorted(registered_set & direct_runtime_set),
        "helper_backed_live_metrics": sorted(registered_set & helper_runtime_set),
        "registered_without_runtime": sorted(registry_only_metrics),
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
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to scan",
    )
    return parser


def _render_text(report: dict[str, list[str] | dict[str, list[str]]]) -> str:
    lines = ["Observability metric inventory"]
    for key in (
        "live_metrics",
        "direct_live_metrics",
        "helper_backed_live_metrics",
        "registered_without_runtime",
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
    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    print(_render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
