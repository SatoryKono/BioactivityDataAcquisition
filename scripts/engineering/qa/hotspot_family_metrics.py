#!/usr/bin/env python3
"""Shared hotspot-family metrics helpers for RF-06 governance and reporting."""

from __future__ import annotations

import ast
import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypeGuard

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
SRC_ROOT = PROJECT_ROOT / "src" / "bioetl"
TYPE_CHECKING_NAME = "TYPE_CHECKING"


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
    hotspot_policy = source.get("hotspot_family_ratchets", {})
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
    tracked_files = _tracked_family_python_files(path_prefixes=path_prefixes)
    if tracked_files is not None:
        return tracked_files

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


def _tracked_family_python_files(*, path_prefixes: list[str]) -> list[Path] | None:
    """Return tracked Python files for the family, or None if git is unavailable."""
    normalized_prefixes = sorted(
        {
            prefix.strip()
            for prefix in path_prefixes
            if isinstance(prefix, str) and prefix.strip()
        }
    )
    if not normalized_prefixes:
        return []

    result = subprocess.run(
        ["git", "ls-files", "--", *normalized_prefixes],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None

    seen: set[Path] = set()
    tracked_files: list[Path] = []
    for raw_path in result.stdout.splitlines():
        path = PROJECT_ROOT / raw_path.strip()
        if path.suffix != ".py" or not path.exists() or path in seen:
            continue
        seen.add(path)
        tracked_files.append(path)
    if not tracked_files and any(
        (PROJECT_ROOT / prefix).exists() for prefix in normalized_prefixes
    ):
        return None
    return sorted(tracked_files)


def count_total_loc(*, files: list[Path]) -> int:
    """Count total LOC across a file set."""
    return sum(len(path.read_text(encoding="utf-8").splitlines()) for path in files)


def _is_type_checking_guard(test: ast.AST) -> bool:
    """Return whether an AST test is ``if TYPE_CHECKING``."""
    return (isinstance(test, ast.Name) and test.id == TYPE_CHECKING_NAME) or (
        isinstance(test, ast.Attribute) and test.attr == TYPE_CHECKING_NAME
    )


def _is_all_assignment(node: ast.AST) -> bool:
    """Return whether node is a top-level ``__all__`` declaration."""
    if isinstance(node, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == "__all__"
    return False


def _is_facade_side_effect_node(node: ast.AST) -> bool:
    """Return whether node is a lightweight facade guard statement."""
    return isinstance(node, (ast.Assert, ast.Raise, ast.Pass))


def _is_type_checking_if_facade(node: ast.If) -> bool:
    if not node.orelse:
        return all(
            _is_facade_only_statement(child) and not isinstance(child, ast.If)
            for child in node.body
        )
    return all(_is_facade_only_statement(child) for child in node.body) and all(
        _is_facade_only_statement(child) for child in node.orelse
    )


def _is_plain_if_facade(node: ast.If) -> bool:
    body_ok = all(
        _is_facade_only_statement(child) or _is_facade_side_effect_node(child)
        for child in node.body
    )
    if not body_ok:
        return False
    if not node.orelse:
        return True
    return all(
        _is_facade_only_statement(child) or _is_facade_side_effect_node(child)
        for child in node.orelse
    )


def _is_facade_only_statement(node: ast.AST) -> bool:
    """Return whether a top-level node belongs to facade-only structure."""
    if _is_all_assignment(node):
        return True
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return True
    if _is_facade_side_effect_node(node):
        return True
    if isinstance(node, ast.If) and _is_type_checking_guard(node.test):
        return _is_type_checking_if_facade(node)
    if isinstance(node, ast.If):
        return _is_plain_if_facade(node)
    return False


def _facade_node_import_delta(node: ast.AST) -> int | None:
    """Return import count delta for a facade-compatible node, else None."""
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        return 0
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return 1
    if _is_facade_only_statement(node):
        return 1 if isinstance(node, (ast.Import, ast.ImportFrom)) else 0
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None
    if isinstance(node, (ast.For, ast.While, ast.Try, ast.If)):
        return None
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return 0 if _is_all_assignment(node) else None
    return None


def _is_import_facade_file(*, path: Path, source: str | None = None) -> bool:
    """Heuristic classifier for import/re-export facade modules."""
    if path.name.startswith("_"):
        return False
    if path.suffix != ".py":
        return False

    try:
        tree = ast.parse(
            source if source is not None else path.read_text(encoding="utf-8")
        )
    except SyntaxError:
        return False

    import_count = 0
    for node in tree.body:
        delta = _facade_node_import_delta(node)
        if delta is None:
            return False
        import_count += delta

    return import_count >= 1


def _is_schema_or_field_definition_file(
    *, path: Path, source: str | None = None
) -> bool:
    """Heuristic classifier for schema/field definition modules."""
    if path.suffix != ".py":
        return False

    stem = path.stem.lower()
    if any(part == "schemas" for part in path.parts):
        return True
    if "schema" in stem or "field" in stem:
        if source is None:
            try:
                source = path.read_text(encoding="utf-8")
            except OSError:
                return False
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return True
        imported_symbol_modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        return any(
            symbol.split(".")[0] in {"pydantic", "pandera", "pyarrow", "polars"}
            for symbol in imported_symbol_modules
        )
    return False


def _is_loccap_excluded(*, path: Path, source: str | None = None) -> bool:
    """Return whether the module is excluded from 250 LOC family-growth checks."""
    return _is_import_facade_file(
        path=path, source=source
    ) or _is_schema_or_field_definition_file(
        path=path,
        source=source,
    )


def count_files_ge_loc(*, files: list[Path], min_lines: int) -> int:
    """Count files meeting the minimum LOC threshold."""
    return sum(
        1
        for path in files
        if len(path.read_text(encoding="utf-8").splitlines()) >= min_lines
        and not _is_loccap_excluded(path=path)
    )


def _parse_python_ast(path: Path) -> ast.AST | None:
    """Parse Python file into AST, returning None on syntax errors."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _is_counted_function(
    node: ast.AST,
) -> TypeGuard[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return whether the AST node counts as a user-defined function."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    return not (node.name.startswith("__") and node.name.endswith("__"))


def _function_count_delta(tree: ast.AST) -> tuple[int, int]:
    """Return total/helper function increments for one AST."""
    total_functions = 0
    helper_functions = 0
    for node in ast.walk(tree):
        if not _is_counted_function(node):
            continue
        total_functions += 1
        if node.name.startswith("_"):
            helper_functions += 1
    return total_functions, helper_functions


def helper_function_ratio(*, files: list[Path]) -> float:
    """Return the ratio of underscore-prefixed helper functions in the family."""
    total_functions = 0
    helper_functions = 0
    for path in files:
        tree = _parse_python_ast(path)
        if tree is None:
            continue
        total_delta, helper_delta = _function_count_delta(tree)
        total_functions += total_delta
        helper_functions += helper_delta
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
    if isinstance(node, ast.Import):
        return _import_targets(node, family_modules=family_modules)
    return _import_from_targets(
        node,
        source_module=source_module,
        family_modules=family_modules,
    )


def _import_targets(
    node: ast.Import,
    *,
    family_modules: set[str],
) -> tuple[str, ...]:
    """Resolve direct import targets that stay inside the hotspot family."""
    return tuple(alias.name for alias in node.names if alias.name in family_modules)


def _import_from_base_module(
    node: ast.ImportFrom,
    *,
    source_module: str,
) -> str | None:
    """Resolve the base module for an ImportFrom node."""
    if node.level == 0:
        return node.module or None
    base_parts = resolve_relative_import_base(source_module, node.level)
    if not base_parts:
        return None
    return ".".join([*base_parts, node.module]) if node.module else ".".join(base_parts)


def _import_from_targets(
    node: ast.ImportFrom,
    *,
    source_module: str,
    family_modules: set[str],
) -> tuple[str, ...]:
    """Resolve import-from targets that remain inside the hotspot family."""
    base_module = _import_from_base_module(node, source_module=source_module)
    if base_module is None:
        return ()

    targets: list[str] = []
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


def _is_type_checking_guard(test: ast.AST) -> bool:
    """Return whether an ``if`` test guards type-only imports."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _iter_runtime_import_nodes(
    node: ast.AST,
) -> tuple[ast.Import | ast.ImportFrom, ...]:
    """Return import nodes that execute at runtime, ignoring TYPE_CHECKING blocks."""
    imports: list[ast.Import | ast.ImportFrom] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and _is_type_checking_guard(child.test):
            for else_child in child.orelse:
                imports.extend(_iter_runtime_import_nodes(else_child))
            continue
        if isinstance(child, (ast.Import, ast.ImportFrom)):
            imports.append(child)
            continue
        imports.extend(_iter_runtime_import_nodes(child))
    return tuple(imports)


def _seen_internal_targets_for_module(
    tree: ast.AST,
    *,
    source_module: str,
    family_modules: set[str],
) -> set[str]:
    """Collect unique runtime internal import targets referenced by one module."""
    seen_targets: set[str] = set()
    for node in _iter_runtime_import_nodes(tree):
        seen_targets.update(
            resolve_internal_import_targets(
                node,
                source_module=source_module,
                family_modules=family_modules,
            )
        )
    return seen_targets


def _update_fan_in_counter(
    fan_in_counter: Counter[str],
    *,
    source_module: str,
    seen_targets: set[str],
) -> None:
    """Apply one module's unique internal dependencies to the fan-in counter."""
    for target in seen_targets:
        if target == source_module:
            continue
        fan_in_counter[target] += 1


def count_internal_fan_in(*, files: list[Path]) -> tuple[int, str | None]:
    """Count the maximum family-internal fan-in across the file set."""
    module_map = {module_name_from_path(path): path for path in files}
    family_modules = set(module_map)
    fan_in_counter: Counter[str] = Counter()

    for source_module, path in module_map.items():
        tree = _parse_python_ast(path)
        if tree is None:
            continue

        seen_targets = _seen_internal_targets_for_module(
            tree,
            source_module=source_module,
            family_modules=family_modules,
        )
        _update_fan_in_counter(
            fan_in_counter,
            source_module=source_module,
            seen_targets=seen_targets,
        )

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


def _duplication_baseline_path(
    *,
    source: dict[str, object],
    duplication_baseline_path: Path | None,
) -> Path | None:
    """Resolve duplication baseline path from explicit arg or scorecard policy."""
    if duplication_baseline_path is not None:
        return duplication_baseline_path
    artifact_policy = source.get("hotspot_family_ratchets", {})
    if not isinstance(artifact_policy, dict):
        return None
    baseline_artifact = artifact_policy.get("artifact_policy", {})
    if not isinstance(baseline_artifact, dict):
        return None
    baseline_path = baseline_artifact.get("baseline_artifact")
    if isinstance(baseline_path, str):
        return PROJECT_ROOT / baseline_path
    return None


def _bounded_growth_budgets(family: dict[str, object]) -> dict[str, int]:
    """Return normalized bounded growth budgets mapping."""
    bounded_growth_budgets = family.get("bounded_growth_budgets", {})
    if not isinstance(bounded_growth_budgets, dict):
        return {}
    return {
        str(key): int(value)
        for key, value in bounded_growth_budgets.items()
        if isinstance(key, str) and isinstance(value, int)
    }


def _path_prefixes(family: dict[str, object]) -> tuple[str, ...]:
    """Return normalized hotspot family path prefixes."""
    raw_prefixes = family.get("path_prefixes", [])
    if not isinstance(raw_prefixes, list):
        return ()
    return tuple(prefix for prefix in raw_prefixes if isinstance(prefix, str))


def _hotspot_family_metric(
    *,
    family: dict[str, object],
    duplication_rows: dict[str, int],
) -> HotspotFamilyMetrics:
    """Build current metrics for one hotspot family row."""
    path_prefixes = _path_prefixes(family)
    files = iter_family_python_files(path_prefixes=list(path_prefixes))
    max_fan_in, max_fan_in_module = count_internal_fan_in(files=files)
    return HotspotFamilyMetrics(
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
        bounded_growth_budgets=_bounded_growth_budgets(family),
    )


def collect_hotspot_family_metrics(
    *,
    scorecard: dict[str, object] | None = None,
    active_only: bool = True,
    duplication_baseline_path: Path | None = None,
) -> list[HotspotFamilyMetrics]:
    """Collect current metrics for configured hotspot families."""
    source = scorecard if scorecard is not None else load_scorecard()
    duplication_baseline_path = _duplication_baseline_path(
        source=source,
        duplication_baseline_path=duplication_baseline_path,
    )
    duplication_rows = _load_duplication_baseline(duplication_baseline_path)
    return [
        _hotspot_family_metric(
            family=family,
            duplication_rows=duplication_rows,
        )
        for family in iter_hotspot_families(scorecard=source, active_only=active_only)
    ]
