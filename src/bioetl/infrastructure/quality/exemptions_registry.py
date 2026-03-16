"""Registry loader/validator for architecture metric exemptions.

Exemptions are stored in a YAML registry with mandatory metadata:
- owner
- reason
- classification
- linked_rf
- due date (`expires_on` or `due_on`)
- removal_step
"""

from __future__ import annotations

__all__ = [
    "EXEMPTION_REGISTRIES_ALLOW_EMPTY",
    "REQUIRED_EXEMPTION_REGISTRIES",
    "build_module_path_key",
    "get_registry_values",
    "load_exemptions_registry",
    "resolve_registry_value",
    "validate_exemption_key_normalization",
    "validate_exemption_target_references",
    "validate_exemptions_registry",
]

import ast
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    _SRC_ROOT_PREFIX,
    build_module_path_key,
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
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    resolve_registry_path as _resolve_registry_path,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    get_policy_required_fields as _get_policy_required_fields,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    validate_exemption_entry as _validate_exemption_entry,
)

REQUIRED_EXEMPTION_REGISTRIES = (
    "file_size_limits",
    "function_complexity",
    "function_length",
    "class_size",
    "class_method_count",
    "god_object",
    "domain_complexity",
)
EXEMPTION_REGISTRIES_ALLOW_EMPTY = frozenset(
    {
        "file_size_limits",
        "function_length",
        "class_size",
        "class_method_count",
        "god_object",
        "function_complexity",
        "domain_complexity",
    }
)
_CLASS_SYMBOL_REGISTRIES = frozenset(
    {
        "class_method_count",
        "class_size",
        "god_object",
    }
)
_FUNCTION_SYMBOL_REGISTRIES = frozenset(
    {
        "domain_complexity",
        "function_complexity",
        "function_length",
    }
)


def load_exemptions_registry(
    path: Path | str | None = None,
) -> JsonDict:  # Any: DQ check values vary by check type
    """Load YAML exemptions registry as dictionary.

    Returns:
        Dictionary with the parsed registry YAML content.
    """
    registry_path = _resolve_registry_path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Exemptions registry not found: {registry_path}")

    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Exemptions registry must be a mapping: {registry_path}")
    return raw


def get_registry_values(
    registry_name: str,
    path: Path | str | None = None,
) -> JsonDict:  # Any: DQ check values vary by check type
    """Return value-only mapping for a concrete registry section.

    Returns:
        Dictionary mapping exemption names to their 'value' fields for the given registry section.
    """
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("Invalid exemptions registry: 'registries' must be a mapping")

    entries = registries.get(registry_name, {})
    if not isinstance(entries, dict):
        raise ValueError(f"Invalid registry '{registry_name}': expected mapping")

    values: JsonDict = {}  # Any: DQ check values vary by check type
    for name, entry in entries.items():
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(
                f"Invalid entry for registry '{registry_name}' key '{name}': missing 'value'"
            )
        values[name] = entry["value"]
    return values


def resolve_registry_value(
    values: JsonDict,  # Any: check-specific thresholds vary by registry
    *,
    module_path: Path | str,
    symbol_name: str | None = None,
    legacy_name: str | None = None,
) -> Any | None:  # Any: dynamic payload or structural mixin boundary
    """Resolve exemption value using canonical path key with dual-read fallback.

    Lookup priority:
    1) ``src/bioetl/.../module.py::symbol`` (when ``symbol_name`` is provided)
    2) ``src/bioetl/.../module.py``
    3) legacy symbol key (``symbol_name``)
    4) explicit ``legacy_name`` (typically basename)
    5) basename of ``module_path``

    This keeps one-release compatibility during key migration from basename/symbol
    to path-aware identifiers.

    Returns:
        Exemption value from the registry if found using any candidate key, None otherwise.
    """
    module_key = build_module_path_key(module_path)
    candidates: list[str] = []
    if symbol_name:
        candidates.append(f"{module_key}::{symbol_name}")
    candidates.append(module_key)
    if symbol_name:
        candidates.append(symbol_name)
    if legacy_name:
        candidates.append(legacy_name)
    candidates.append(Path(module_key).name)

    for candidate in candidates:
        if candidate in values:
            return values[candidate]
    return None


def validate_exemption_key_normalization(
    path: Path | str | None = None,
) -> list[str]:
    """Validate that file-size exemptions use canonical path keys.

    During transition, other registries may still use symbol-only keys. This
    validator focuses on collision-prone ``file_size_limits`` entries.

    Returns:
        List of error message strings describing normalization violations, empty if all valid.
    """
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        return ["registries: expected mapping"]

    file_size = registries.get("file_size_limits", {})
    if not isinstance(file_size, dict):
        return ["registries.file_size_limits: expected mapping"]

    errors: list[str] = []
    src_root = _project_root() / "src"

    for key in sorted(file_size):
        if not isinstance(key, str) or not key.strip():
            errors.append("file_size_limits: key must be non-empty string")
            continue

        normalized = _normalize_path_text(key)
        if not _is_module_path_key(normalized):
            errors.append(
                f"file_size_limits.{key}: expected canonical path key "
                f"'{_SRC_ROOT_PREFIX}.../*.py'"
            )
            continue

        module_path = _project_root() / normalized
        if not module_path.exists():
            errors.append(f"file_size_limits.{key}: target file does not exist")
            continue
        if not module_path.is_relative_to(src_root):
            errors.append(
                f"file_size_limits.{key}: target path must be inside src/ tree"
            )

    return errors


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



def _check_registry_symbols(
    registry_name: str,
    entries: dict[str, Any],
    classes_by_module: dict[str, set[str]],
    class_counts: Counter[str],
    functions_by_module: dict[str, set[str]],
    function_counts: Counter[str],
    errors: list[str],
) -> None:
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
        _check_registry_symbols(registry_name, entries, classes_by_module, class_counts, functions_by_module, function_counts, errors)

    return errors


def _validate_required_registries(
    registries: dict[str, object],
    errors: list[str],
) -> None:
    """Check that all required registries exist and have valid types."""
    missing = sorted(set(REQUIRED_EXEMPTION_REGISTRIES) - set(registries))
    if missing:
        errors.append("Missing required exemption registries: " + ", ".join(missing))

    for name in REQUIRED_EXEMPTION_REGISTRIES:
        if name in missing:
            continue
        entries = registries.get(name)
        if not isinstance(entries, dict):
            errors.append(f"{name}: expected mapping of exemptions, got {type(entries).__name__}")
            continue
        if not entries and name not in EXEMPTION_REGISTRIES_ALLOW_EMPTY:
            errors.append(f"{name}: registry must not be empty")


def validate_exemptions_registry(
    path: Path | str | None = None,
    *,
    today: date | None = None,
) -> tuple[list[str], list[str]]:
    """Validate registry metadata and return (metadata_errors, expired_entries).

    Returns:
        Tuple of (metadata_errors list, expired_entries list) with issue descriptions.
    """
    raw = load_exemptions_registry(path)
    now = today or date.today()
    metadata_errors: list[str] = []
    expired_entries: list[str] = []
    required_fields = _get_policy_required_fields(raw, metadata_errors)

    registries = raw.get("registries")
    if not isinstance(registries, dict):
        return (["Missing or invalid top-level 'registries' mapping"], [])

    _validate_required_registries(registries, metadata_errors)

    for registry_name, entries in sorted(registries.items()):
        if not isinstance(entries, dict):
            metadata_errors.append(
                f"{registry_name}: expected mapping of exemptions, got {type(entries).__name__}"
            )
            continue
        for exemption_name, entry in sorted(entries.items()):
            _validate_exemption_entry(
                registry_name, exemption_name, entry,
                required_fields, now, metadata_errors, expired_entries,
            )

    metadata_errors.extend(validate_exemption_key_normalization(path))
    metadata_errors.extend(validate_exemption_target_references(path))
    return metadata_errors, expired_entries
