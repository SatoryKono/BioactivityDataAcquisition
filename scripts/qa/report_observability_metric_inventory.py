#!/usr/bin/env python3
"""Report registry/runtime/docs drift for public observability metric families.

Usage:
    python -m scripts.qa report-observability-metric-inventory [--json]

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

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

_CANONICAL_METRIC_RE = re.compile(r"\bbioetl_[a-z0-9_]+\b")

_RUNTIME_SCAN_ROOT = Path("src/bioetl")
_REGISTERED_SCAN_ROOT = Path("src/bioetl/infrastructure/observability")
_DOC_SCAN_ROOTS = (Path("docs"), Path("grafana/dashboards"), Path("grafana/README.md"))
_RULE_SCAN_ROOT = Path("grafana/prometheus-rules")
_RUNTIME_EXCLUDE_PARTS = (
    "src/bioetl/infrastructure/observability",
    "src/bioetl/domain",
)
_TEXT_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml"}
_RUNTIME_METRIC_METHODS = frozenset(
    {"increment_counter", "observe_histogram", "set_gauge"}
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


def _scan_runtime_metric_calls(repo_root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    canonical_mentions: dict[str, list[str]] = defaultdict(list)
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
        metric_names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in _RUNTIME_METRIC_METHODS:
                continue
            if not node.args:
                continue
            first_arg = node.args[0]
            metric_name: str | None = None
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                metric_name = first_arg.value
            elif isinstance(first_arg, ast.Name):
                metric_name = string_bindings.get(first_arg.id)
            if metric_name is None:
                continue
            metric_names.add(metric_name)
        for metric_name in sorted(metric_names):
            target = (
                canonical_mentions
                if metric_name.startswith("bioetl_")
                else alias_mentions
            )
            target[metric_name].append(_as_repo_relative(path, repo_root))
    return dict(canonical_mentions), dict(alias_mentions)


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


def collect_metric_inventory(repo_root: Path) -> dict[str, list[str] | dict[str, list[str]]]:
    registered = sorted(REGISTERED_PROMETHEUS_METRIC_NAMES)
    runtime_mentions, alias_mentions = _scan_runtime_metric_calls(repo_root)

    doc_paths: list[Path] = []
    for root in _DOC_SCAN_ROOTS:
        doc_paths.extend(_iter_text_files(repo_root / root))
    docs_mentions = _scan_canonical_metric_mentions(doc_paths, repo_root)
    rules_mentions = _scan_canonical_metric_mentions(
        _iter_text_files(repo_root / _RULE_SCAN_ROOT),
        repo_root,
    )

    registered_set = set(registered)
    runtime_set = set(runtime_mentions)
    docs_set = set(docs_mentions)
    rules_set = set(rules_mentions)

    report: dict[str, list[str] | dict[str, list[str]]] = {
        "registered_metrics": registered,
        "live_metrics": sorted(registered_set & runtime_set),
        "registered_without_runtime": sorted(registered_set - runtime_set),
        "documented_without_registry": sorted(docs_set - registered_set),
        "rules_without_registry": sorted(rules_set - registered_set),
        "documented_without_runtime": sorted((docs_set & registered_set) - runtime_set),
        "ruled_without_runtime": sorted((rules_set & registered_set) - runtime_set),
        "compatibility_alias_candidates": sorted(alias_mentions),
        "runtime_emitters": runtime_mentions,
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
        "registered_without_runtime",
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
