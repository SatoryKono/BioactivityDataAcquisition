"""Generate architecture-debt task payloads from the exemptions registry."""

from __future__ import annotations

import ast
from ast import AsyncFunctionDef, ClassDef, FunctionDef
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, cast

from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry

TASK_SCHEMA_VERSION: Final[str] = "1.0"
REGISTRY_NAMES: Final[tuple[str, ...]] = (
    "file_size_limits",
    "function_complexity",
    "function_length",
    "class_size",
    "class_method_count",
    "god_object",
    "domain_complexity",
)
COMMON_ACCEPTANCE_CRITERIA: Final[tuple[str, ...]] = (
    "Поведение не изменено",
    "Публичные интерфейсы не изменены",
    "Докстринги не удалены; изменения соответствуют стандартам проекта",
)
COMMON_ALLOWED_PATHS: Final[tuple[str, ...]] = ("src/bioetl/**", "tests/**")
COMMON_FORBIDDEN_PATHS: Final[tuple[str, ...]] = (
    "configs/**",
    "docs/**",
    ".github/**",
)
COMMON_CHECKS: Final[tuple[str, ...]] = (
    "python -m pytest -q "
    "tests/architecture/test_quality_debt_scorecard.py "
    "tests/architecture/test_quality_exemptions_registry.py",
    "python -m scripts.engineering.qa check-exemptions --mode auto --growth-mode auto --trend-report off",
)


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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_output_path(
    *,
    project_root: Path,
    generated_at: datetime,
) -> Path:
    file_name = (
        "tasks_architecture_metric_exemptions_"
        f"{generated_at.strftime('%Y-%m-%d-%H-%M')}.json"
    )
    return project_root / file_name


def _build_checks(registry_name: str) -> list[str]:
    per_registry = {
        "file_size_limits": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFileSizeLimits",
            "python -m pytest -q "
            "tests/architecture/test_quality_burndown_priorities.py::"
            "test_file_size_limit_registry_has_no_stale_entries",
        ],
        "function_length": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionLength",
            "python -m pytest -q "
            "tests/architecture/test_quality_burndown_priorities.py::"
            "test_function_length_registry_has_no_stale_entries",
        ],
        "function_complexity": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity",
        ],
        "domain_complexity": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestFunctionComplexity",
        ],
        "class_size": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize",
            "python -m pytest -q "
            "tests/architecture/test_quality_burndown_priorities.py::"
            "test_class_size_registry_has_no_stale_entries",
        ],
        "class_method_count": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestClassSize",
        ],
        "god_object": [
            "python -m pytest -q tests/architecture/test_code_metrics.py::TestGodObjectDetection",
        ],
    }
    return [*per_registry[registry_name], *COMMON_CHECKS]


def _build_goal(registry_name: str, *, limit_value: object) -> str:
    if registry_name == "file_size_limits":
        return f"Снизить LOC файла до {limit_value} или ниже без изменения поведения."
    if registry_name == "function_length":
        return f"Сократить длину функции до {limit_value} строк или ниже."
    if registry_name in {"function_complexity", "domain_complexity"}:
        return (
            f"Снизить cyclomatic complexity до {limit_value} или ниже через "
            "extract method, ранние выходы и упрощение branching."
        )
    if registry_name == "class_size":
        return (
            f"Снизить размер класса до {limit_value} LOC или ниже через "
            "декомпозицию ответственности."
        )
    if registry_name == "class_method_count":
        return (
            f"Снизить число методов класса до {limit_value} или ниже через "
            "extraction/move method."
        )
    return (
        "Уменьшить признаки god object через выделение collaborators и "
        "delegation patterns без изменения публичного интерфейса."
    )


def _relative_target(path: Path, *, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _parse_limit_value(entry: dict[str, object]) -> int | str | None:
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


def _safe_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _iter_source_modules(project_root: Path) -> list[Path]:
    src_root = project_root / "src" / "bioetl"
    if not src_root.exists():
        return []
    return sorted(
        path
        for path in src_root.rglob("*.py")
        if path.is_file() and not path.name.startswith("__")
    )


def _fallback_complexity(function_node: FunctionDef | AsyncFunctionDef) -> int:
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


def _function_complexities(source: str) -> dict[str, int]:
    try:
        from radon.complexity import cc_visit  # type: ignore[import-not-found]
    except ImportError:
        tree = ast.parse(source)
        return {
            node.name: _fallback_complexity(node)
            for node in ast.walk(tree)
            if isinstance(node, FunctionDef | AsyncFunctionDef)
        }

    results = cc_visit(source)
    return {item.name: int(item.complexity) for item in results}


def _build_symbol_index(project_root: Path) -> dict[str, list[SymbolMetricLocation]]:
    symbol_index: dict[str, list[SymbolMetricLocation]] = {}
    for module_path in _iter_source_modules(project_root):
        source = _safe_text(module_path)
        if source is None:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        complexities = _function_complexities(source)
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


def _select_symbol_location(
    *,
    key: str,
    registry_name: str,
    project_root: Path,
    symbol_index: dict[str, list[SymbolMetricLocation]],
) -> tuple[SymbolMetricLocation | None, str | None, str | None, str | None]:
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
                _relative_target(candidate.path, project_root=project_root)
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
        _relative_target(selected.path, project_root=project_root),
        key,
        note_text,
    )


def _task_status(
    *,
    registry_name: str,
    current_value: int | None,
    limit_value: int | str | None,
    target_file: str | None,
) -> str:
    if target_file is None:
        return "target_not_found"
    if registry_name == "god_object":
        return "not_measurable"
    if current_value is None or not isinstance(limit_value, int):
        return "not_measurable"
    if current_value > limit_value:
        return "needs_refactor"
    return "within_limit"


def _measure_task(
    *,
    registry_name: str,
    key: str,
    project_root: Path,
    symbol_index: dict[str, list[SymbolMetricLocation]],
) -> tuple[str | None, str | None, int | None, str | None]:
    if registry_name == "file_size_limits":
        target_path = project_root / key
        if not target_path.exists():
            return None, None, None, None
        source = _safe_text(target_path)
        if source is None:
            return (
                _relative_target(target_path, project_root=project_root),
                None,
                None,
                "Could not read file for LOC measurement.",
            )
        return (
            _relative_target(target_path, project_root=project_root),
            None,
            len(source.splitlines()),
            None,
        )

    location, target_file, symbol_name, note_text = _select_symbol_location(
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


def _require_generated_at(generated_at: datetime | None) -> datetime:
    if generated_at is None:
        raise ValueError("generated_at must be provided by the caller")
    return generated_at


def _resolve_registry_entries(
    *,
    registries: dict[str, object],
    registry_name: str,
) -> dict[str, object]:
    """Return normalized registry entries for one exemption family."""
    entries_raw = registries.get(registry_name, {})
    return cast(dict[str, object], entries_raw if isinstance(entries_raw, dict) else {})


def _build_debt_task(
    *,
    registry_name: str,
    ordinal: int,
    key: str,
    entry: dict[str, object],
    project_root: Path,
    symbol_index: dict[str, list[SymbolMetricLocation]],
) -> dict[str, object]:
    """Build one machine-readable debt task from a registry entry."""
    limit_value = _parse_limit_value(entry)
    target_file, symbol_name, current_value, metric_notes = _measure_task(
        registry_name=registry_name,
        key=key,
        project_root=project_root,
        symbol_index=symbol_index,
    )
    status = _task_status(
        registry_name=registry_name,
        current_value=current_value,
        limit_value=limit_value,
        target_file=target_file,
    )
    delta_to_limit = (
        current_value - limit_value
        if isinstance(current_value, int) and isinstance(limit_value, int)
        else None
    )
    return {
        "id": f"AME-{registry_name.upper()}-{ordinal:03d}",
        "registry": registry_name,
        "registry_key": key,
        "owner": entry.get("owner"),
        "reason": entry.get("reason"),
        "expires_on": entry.get("expires_on"),
        "removal_step": entry.get("removal_step"),
        "limit_value": limit_value,
        "current_value": current_value,
        "delta_to_limit": delta_to_limit,
        "status": status,
        "target_file": target_file,
        "symbol_name": symbol_name,
        "goal": _build_goal(registry_name, limit_value=limit_value),
        "acceptance_criteria": list(COMMON_ACCEPTANCE_CRITERIA),
        "allowed_paths": list(COMMON_ALLOWED_PATHS),
        "forbidden_paths": list(COMMON_FORBIDDEN_PATHS),
        "checks": _build_checks(registry_name),
        "notes": metric_notes,
    }


def generate_architecture_debt_tasks_payload(
    *,
    registry_path: Path | str | None = None,
    project_root: Path | str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Build a refactoring task payload from the exemptions registry."""
    resolved_project_root = (
        Path(project_root) if project_root is not None else _project_root()
    )
    registry = load_exemptions_registry(registry_path)
    registries_raw = registry.get("registries", {})
    registries = cast(
        dict[str, object],
        registries_raw if isinstance(registries_raw, dict) else {},
    )
    timestamp = _require_generated_at(generated_at)
    symbol_index = _build_symbol_index(resolved_project_root)

    tasks: list[dict[str, object]] = []
    registry_summary: dict[str, int] = {}

    for registry_name in REGISTRY_NAMES:
        entries = _resolve_registry_entries(
            registries=registries,
            registry_name=registry_name,
        )
        registry_summary[registry_name] = len(entries)

        for ordinal, (key, entry_raw) in enumerate(sorted(entries.items()), start=1):
            entry = cast(
                dict[str, object],
                entry_raw if isinstance(entry_raw, dict) else {},
            )
            tasks.append(
                _build_debt_task(
                    registry_name=registry_name,
                    ordinal=ordinal,
                    key=key,
                    entry=entry,
                    project_root=resolved_project_root,
                    symbol_index=symbol_index,
                )
            )

    registry_summary["total_tasks"] = len(tasks)
    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "source_registry_file": (
            Path(registry_path).as_posix()
            if registry_path is not None
            else "configs/quality/architecture_metric_exemptions.yaml"
        ),
        "generated_at": timestamp.isoformat(),
        "defaults": {
            "behavior_change_allowed": False,
            "public_interface_change_allowed": False,
            "docstrings_rule": (
                "Докстринги: не удалять. Разрешено только изменять с соблюдением "
                "стандартов докстрингов проекта."
            ),
        },
        "registry_summary": registry_summary,
        "tasks": tasks,
    }


__all__ = [
    "COMMON_ACCEPTANCE_CRITERIA",
    "COMMON_ALLOWED_PATHS",
    "COMMON_CHECKS",
    "COMMON_FORBIDDEN_PATHS",
    "REGISTRY_NAMES",
    "TASK_SCHEMA_VERSION",
    "SymbolMetricLocation",
    "_default_output_path",
    "generate_architecture_debt_tasks_payload",
]
