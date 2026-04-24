"""Support helpers for architecture debt task generation."""

from __future__ import annotations

import ast
from ast import AsyncFunctionDef, ClassDef, FunctionDef
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SymbolMetricLocation:
    """Resolved symbol location and structural metrics."""

    name: str
    path: Path
    kind: str
    lineno: int
    end_lineno: int
    size: int
    method_count: int | None = None
    complexity: int | None = None


def parse_limit_value(entry: dict[str, object]) -> int | str | None:
    """Parse one registry threshold into a normalized scalar value."""
    raw = entry.get("value")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    if isinstance(raw, str) and raw.strip():
        stripped = raw.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return None


def relative_target(path: Path, *, project_root: Path) -> str:
    """Return one repo-relative POSIX path."""
    return path.relative_to(project_root).as_posix()


def safe_text(path: Path) -> str | None:
    """Read one UTF-8 source file, returning None on inaccessible input."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def iter_source_modules(project_root: Path) -> list[Path]:
    """Return canonical project source modules eligible for symbol analysis."""
    src_root = project_root / "src" / "bioetl"
    if not src_root.exists():
        return []
    return sorted(
        path
        for path in src_root.rglob("*.py")
        if path.is_file() and not path.name.startswith("__")
    )


def fallback_complexity(function_node: FunctionDef | AsyncFunctionDef) -> int:
    """Estimate cyclomatic complexity when radon is unavailable."""
    decision_nodes = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.IfExp,
        ast.Match,
    )
    complexity = 1
    for child in ast.walk(function_node):
        if isinstance(child, decision_nodes):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += max(len(child.values) - 1, 1)
        elif isinstance(child, ast.comprehension):
            complexity += 1
    return complexity


def function_complexities(source: str) -> dict[str, int]:
    """Build a function-name to complexity map for one source module."""
    try:
        from radon.complexity import cc_visit  # type: ignore[import-untyped]
    except ImportError:
        tree = ast.parse(source)
        return {
            node.name: fallback_complexity(node)
            for node in ast.walk(tree)
            if isinstance(node, FunctionDef | AsyncFunctionDef)
        }

    results = cc_visit(source)
    return {item.name: int(item.complexity) for item in results}


def build_symbol_index(project_root: Path) -> dict[str, list[SymbolMetricLocation]]:
    """Index functions and classes across the source tree with basic metrics."""
    symbol_index: dict[str, list[SymbolMetricLocation]] = {}
    for module_path in iter_source_modules(project_root):
        source = safe_text(module_path)
        if source is None:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        complexities = function_complexities(source)
        for node in ast.walk(tree):
            if isinstance(node, FunctionDef | AsyncFunctionDef):
                start = node.lineno
                end = node.end_lineno or start
                location = SymbolMetricLocation(
                    name=node.name,
                    path=module_path,
                    kind="function",
                    lineno=start,
                    end_lineno=end,
                    size=end - start + 1,
                    complexity=complexities.get(node.name),
                )
                symbol_index.setdefault(node.name, []).append(location)
            elif isinstance(node, ClassDef):
                start = node.lineno
                end = node.end_lineno or start
                method_count = sum(
                    1
                    for child in node.body
                    if isinstance(child, FunctionDef | AsyncFunctionDef)
                )
                location = SymbolMetricLocation(
                    name=node.name,
                    path=module_path,
                    kind="class",
                    lineno=start,
                    end_lineno=end,
                    size=end - start + 1,
                    method_count=method_count,
                )
                symbol_index.setdefault(node.name, []).append(location)
    return symbol_index


def select_symbol_location(
    *,
    key: str,
    registry_name: str,
    project_root: Path,
    symbol_index: dict[str, list[SymbolMetricLocation]],
) -> tuple[SymbolMetricLocation | None, str | None, str | None, str | None]:
    """Resolve one registry key to the best symbol location candidate."""
    notes: list[str] = []
    if "::" in key:
        raw_path, symbol_name = key.split("::", 1)
        target_path = project_root / raw_path
        candidates = [
            location
            for location in symbol_index.get(symbol_name, [])
            if location.path == target_path
        ]
        if not candidates:
            return None, raw_path, symbol_name, None
        selected = max(candidates, key=lambda item: item.size)
        return selected, raw_path, symbol_name, None

    if key.endswith(".py"):
        return None, key, None, None

    expected_kind = (
        "class"
        if registry_name in {"class_size", "class_method_count", "god_object"}
        else "function"
    )
    candidates = [
        location
        for location in symbol_index.get(key, [])
        if location.kind == expected_kind
    ]
    if not candidates:
        return None, None, key, None

    selected = max(candidates, key=lambda item: item.size)
    if len(candidates) > 1:
        alt_paths = ", ".join(
            sorted(
                relative_target(candidate.path, project_root=project_root)
                for candidate in candidates
                if candidate != selected
            )
        )
        if alt_paths:
            notes.append(
                "Multiple symbol matches; selected largest definition. "
                f"Other candidates: {alt_paths}."
            )
    note_text = " ".join(notes) if notes else None
    return (
        selected,
        relative_target(selected.path, project_root=project_root),
        key,
        note_text,
    )


def task_status(
    *,
    registry_name: str,
    current_value: int | None,
    limit_value: int | str | None,
    target_file: str | None,
) -> str:
    """Classify the actionable state of one generated debt task."""
    if target_file is None:
        return "target_not_found"
    if registry_name == "god_object":
        return "not_measurable"
    if current_value is None or not isinstance(limit_value, int):
        return "not_measurable"
    if current_value > limit_value:
        return "needs_refactor"
    return "within_limit"


def measure_task(
    *,
    registry_name: str,
    key: str,
    project_root: Path,
    symbol_index: dict[str, list[SymbolMetricLocation]],
) -> tuple[str | None, str | None, int | None, str | None]:
    """Measure the current value for one registry entry."""
    if registry_name == "file_size_limits":
        target_path = project_root / key
        if not target_path.exists():
            return None, None, None, None
        source = safe_text(target_path)
        if source is None:
            return (
                relative_target(target_path, project_root=project_root),
                None,
                None,
                "Could not read file for LOC measurement.",
            )
        return (
            relative_target(target_path, project_root=project_root),
            None,
            len(source.splitlines()),
            None,
        )

    location, target_file, symbol_name, note_text = select_symbol_location(
        key=key,
        registry_name=registry_name,
        project_root=project_root,
        symbol_index=symbol_index,
    )
    if location is None:
        return target_file, symbol_name, None, note_text

    if registry_name == "function_length":
        return target_file, location.name, location.size, note_text
    if registry_name in {"function_complexity", "domain_complexity"}:
        return target_file, location.name, location.complexity, note_text
    if registry_name == "class_size":
        return target_file, location.name, location.size, note_text
    if registry_name == "class_method_count":
        return target_file, location.name, location.method_count, note_text
    return target_file, location.name, None, note_text
