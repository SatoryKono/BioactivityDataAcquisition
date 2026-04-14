#!/usr/bin/env python3
"""Shared hotspot-family metrics helpers for RF-06 governance and reporting."""

from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
SRC_ROOT = PROJECT_ROOT / "src" / "bioetl"


@dataclass(frozen=True)
class HotspotFamilyMetrics:
    """Measured metrics for one hotspot family."""

    name: str
    owner: str
    linked_rf: str
    ratchet_stage: str
    ratchet_scope: str
    path_prefixes: tuple[str, ...]
    duplication_clusters: int | None
    files: int
    total_loc: int
    files_ge_250_loc: int
    helper_function_ratio: float
    max_internal_fan_in: int
    max_internal_fan_in_module: str | None
    bounded_growth_budgets: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly mapping."""
        return asdict(self)


def load_scorecard(path: Path = SCORECARD_PATH) -> dict[str, object]:
    """Load the quality debt scorecard."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def iter_hotspot_families(
    *,
    scorecard: dict[str, object] | None = None,
    active_only: bool = False,
) -> list[dict[str, object]]:
    """Return hotspot-family rows from the scorecard."""
    source = scorecard if scorecard is not None else load_scorecard()
    hotspot_policy = source.get("report_only_hotspot_families", {})
    assert isinstance(hotspot_policy, dict)
    families = hotspot_policy.get("families", [])
    assert isinstance(families, list)
    rows = [family for family in families if isinstance(family, dict)]
    if active_only:
        rows = [family for family in rows if family.get("ratchet_stage") == "active"]
    return rows


def module_name_from_path(path: Path, *, src_root: Path = SRC_ROOT) -> str:
    """Convert a file path to its ``bioetl.*`` module name."""
    rel = path.relative_to(src_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = Path(parts[-1]).stem
    return ".".join(["bioetl", *parts]) if parts else "bioetl"


def iter_family_python_files(*, path_prefixes: list[str]) -> list[Path]:
    """Return unique Python files under the given path prefixes."""
    seen: set[Path] = set()
    files: list[Path] = []
    for prefix in path_prefixes:
        root = PROJECT_ROOT / prefix
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if path in seen:
                continue
            seen.add(path)
            files.append(path)
    return files


def count_total_loc(*, files: list[Path]) -> int:
    """Count total LOC across a file set."""
    return sum(len(path.read_text(encoding="utf-8").splitlines()) for path in files)


def count_files_ge_loc(*, files: list[Path], min_lines: int) -> int:
    """Count files meeting the minimum LOC threshold."""
    return sum(
        1
        for path in files
        if len(path.read_text(encoding="utf-8").splitlines()) >= min_lines
    )


def helper_function_ratio(*, files: list[Path]) -> float:
    """Return the ratio of underscore-prefixed helper functions in the family."""
    total_functions = 0
    helper_functions = 0
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("__") and node.name.endswith("__"):
                continue
            total_functions += 1
            if node.name.startswith("_"):
                helper_functions += 1
    if total_functions == 0:
        return 0.0
    return round(helper_functions / total_functions, 3)


def resolve_relative_import_base(source_module: str, level: int) -> list[str]:
    """Resolve a relative import base for ``ast.ImportFrom`` nodes."""
    package_parts = source_module.split(".")[:-1]
    depth = max(level - 1, 0)
    if depth > len(package_parts):
        return []
    if depth == 0:
        return package_parts
    return package_parts[:-depth]


def resolve_internal_import_targets(
    node: ast.Import | ast.ImportFrom,
    *,
    source_module: str,
    family_modules: set[str],
) -> tuple[str, ...]:
    """Resolve import targets that remain inside the same hotspot family."""
    targets: list[str] = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name in family_modules:
                targets.append(alias.name)
        return tuple(targets)

    if node.level == 0:
        if not node.module:
            return ()
        base_module = node.module
    else:
        base_parts = resolve_relative_import_base(source_module, node.level)
        if not base_parts:
            return ()
        base_module = ".".join([*base_parts, node.module]) if node.module else ".".join(
            base_parts
        )

    for alias in node.names:
        if alias.name == "*":
            continue
        candidate = f"{base_module}.{alias.name}"
        if candidate in family_modules:
            targets.append(candidate)
            continue
        if base_module in family_modules:
            targets.append(base_module)

    if not targets and base_module in family_modules:
        targets.append(base_module)
    return tuple(targets)


def count_internal_fan_in(*, files: list[Path]) -> tuple[int, str | None]:
    """Count the maximum family-internal fan-in across the file set."""
    module_map = {module_name_from_path(path): path for path in files}
    family_modules = set(module_map)
    fan_in_counter: Counter[str] = Counter()

    for source_module, path in module_map.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        seen_targets: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            seen_targets.update(
                resolve_internal_import_targets(
                    node,
                    source_module=source_module,
                    family_modules=family_modules,
                )
            )

        for target in seen_targets:
            if target == source_module:
                continue
            fan_in_counter[target] += 1

    if not fan_in_counter:
        return 0, None

    max_module, max_fan_in = max(
        fan_in_counter.items(),
        key=lambda item: (item[1], item[0]),
    )
    return max_fan_in, max_module


def _load_duplication_baseline(path: Path | None) -> dict[str, int]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    targets = payload.get("targets", [])
    if not isinstance(targets, list):
        return {}
    result: dict[str, int] = {}
    for row in targets:
        if not isinstance(row, dict):
            continue
        target = row.get("target")
        duplicate_count = row.get("duplicate_count")
        if isinstance(target, str) and isinstance(duplicate_count, int):
            result[target.rstrip("/")] = duplicate_count
    return result


def _duplication_count_for_family(
    *,
    path_prefixes: tuple[str, ...],
    duplication_rows: dict[str, int],
) -> int | None:
    if not duplication_rows:
        return None
    for prefix in path_prefixes:
        normalized = prefix.rstrip("/")
        if normalized in duplication_rows:
            return duplication_rows[normalized]
    return None


def collect_hotspot_family_metrics(
    *,
    scorecard: dict[str, object] | None = None,
    active_only: bool = True,
    duplication_baseline_path: Path | None = None,
) -> list[HotspotFamilyMetrics]:
    """Collect current metrics for configured hotspot families."""
    source = scorecard if scorecard is not None else load_scorecard()
    artifact_policy = source.get("report_only_hotspot_families", {})
    if duplication_baseline_path is None and isinstance(artifact_policy, dict):
        baseline_artifact = artifact_policy.get("artifact_policy", {})
        if isinstance(baseline_artifact, dict):
            baseline_path = baseline_artifact.get("baseline_artifact")
            if isinstance(baseline_path, str):
                duplication_baseline_path = PROJECT_ROOT / baseline_path

    duplication_rows = _load_duplication_baseline(duplication_baseline_path)
    metrics: list[HotspotFamilyMetrics] = []
    for family in iter_hotspot_families(scorecard=source, active_only=active_only):
        raw_prefixes = family.get("path_prefixes", [])
        path_prefixes = tuple(prefix for prefix in raw_prefixes if isinstance(prefix, str))
        files = iter_family_python_files(path_prefixes=list(path_prefixes))
        max_fan_in, max_fan_in_module = count_internal_fan_in(files=files)
        bounded_growth_budgets = family.get("bounded_growth_budgets", {})
        metrics.append(
            HotspotFamilyMetrics(
                name=str(family.get("name", "")),
                owner=str(family.get("owner", "")),
                linked_rf=str(family.get("linked_rf", "")),
                ratchet_stage=str(family.get("ratchet_stage", "")),
                ratchet_scope=str(family.get("ratchet_scope", "")),
                path_prefixes=path_prefixes,
                duplication_clusters=_duplication_count_for_family(
                    path_prefixes=path_prefixes,
                    duplication_rows=duplication_rows,
                ),
                files=len(files),
                total_loc=count_total_loc(files=files),
                files_ge_250_loc=count_files_ge_loc(files=files, min_lines=250),
                helper_function_ratio=helper_function_ratio(files=files),
                max_internal_fan_in=max_fan_in,
                max_internal_fan_in_module=max_fan_in_module,
                bounded_growth_budgets=(
                    {
                        str(key): int(value)
                        for key, value in bounded_growth_budgets.items()
                        if isinstance(key, str) and isinstance(value, int)
                    }
                    if isinstance(bounded_growth_budgets, dict)
                    else {}
                ),
            )
        )
    return metrics
