"""Live target reference validation for architecture metric exemptions."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

from bioetl.infrastructure.quality.exemptions_registry_access import (
    load_exemptions_registry,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    is_module_path_key as _is_module_path_key,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    normalize_path_text as _normalize_path_text,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    project_root as _project_root,
)

_CLASS_SYMBOL_REGISTRIES = frozenset({"class_method_count", "class_size", "god_object"})
_FUNCTION_SYMBOL_REGISTRIES = frozenset(
    {"domain_complexity", "function_complexity", "function_length"}
)


def _iter_source_modules(src_root: Path) -> list[Path]:
    """Return all source modules that participate in exemption lookups."""
    return sorted(
        path
        for path in src_root.rglob("*.py")
        if path.is_file() and not path.name.startswith("__")
    )


def _build_symbol_index(
    src_root: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]], Counter[str], Counter[str]]:
    """Build per-module and global class/function symbol indexes."""
    project_root = _project_root()
    classes_by_module: dict[str, set[str]] = {}
    functions_by_module: dict[str, set[str]] = {}
    class_counts: Counter[str] = Counter()
    function_counts: Counter[str] = Counter()

    for module_path in _iter_source_modules(src_root):
        try:
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        module_key = module_path.relative_to(project_root).as_posix()
        classes: set[str] = set()
        functions: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                functions.add(node.name)

        classes_by_module[module_key] = classes
        functions_by_module[module_key] = functions
        class_counts.update(classes)
        function_counts.update(functions)

    return classes_by_module, functions_by_module, class_counts, function_counts


def _validate_symbol_key_reference(
    *,
    registry_name: str,
    key: str,
    symbol_kind: str,
    symbols_by_module: dict[str, set[str]],
    global_counts: Counter[str],
    errors: list[str],
) -> None:
    """Validate a class/function exemption key points at a live symbol."""
    normalized_key = _normalize_path_text(key)
    prefix = f"{registry_name}.{key}"

    if "::" in normalized_key:
        module_key, symbol_name = normalized_key.split("::", 1)
        if not symbol_name.strip():
            errors.append(f"{prefix}: symbol name after '::' must be non-empty")
            return
        if not _is_module_path_key(module_key):
            errors.append(
                f"{prefix}: path-qualified symbol key must use canonical module path"
            )
            return

        module_path = _project_root() / module_key
        if not module_path.exists():
            errors.append(f"{prefix}: target module does not exist")
            return

        module_symbols = symbols_by_module.get(module_key, set())
        if symbol_name not in module_symbols:
            errors.append(
                f"{prefix}: target {symbol_kind} '{symbol_name}' not found in {module_key}"
            )
        return

    symbol_name = normalized_key.strip()
    matches = int(global_counts.get(symbol_name, 0))
    if matches == 0:
        errors.append(f"{prefix}: target {symbol_kind} '{symbol_name}' not found")
        return
    if matches > 1:
        errors.append(
            f"{prefix}: bare symbol key is ambiguous for {symbol_kind} "
            f"'{symbol_name}' ({matches} matches); use src/.../module.py::{symbol_name}"
        )


def validate_exemption_target_references(
    path: Path | str | None = None,
) -> list[str]:
    """Validate that path/symbol-based exemption keys point to live code targets."""
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        return ["registries: expected mapping"]

    src_root = _project_root() / "src" / "bioetl"
    if not src_root.exists():
        return ["src/bioetl: source root not found"]

    classes_by_module, functions_by_module, class_counts, function_counts = (
        _build_symbol_index(src_root)
    )
    errors: list[str] = []

    for registry_name, entries in sorted(registries.items()):
        if not isinstance(entries, dict):
            continue
        if registry_name in _CLASS_SYMBOL_REGISTRIES:
            for key in sorted(entries):
                if isinstance(key, str):
                    _validate_symbol_key_reference(
                        registry_name=registry_name,
                        key=key,
                        symbol_kind="class",
                        symbols_by_module=classes_by_module,
                        global_counts=class_counts,
                        errors=errors,
                    )
        elif registry_name in _FUNCTION_SYMBOL_REGISTRIES:
            for key in sorted(entries):
                if isinstance(key, str):
                    _validate_symbol_key_reference(
                        registry_name=registry_name,
                        key=key,
                        symbol_kind="function",
                        symbols_by_module=functions_by_module,
                        global_counts=function_counts,
                        errors=errors,
                    )

    return errors


__all__ = ["validate_exemption_target_references"]
