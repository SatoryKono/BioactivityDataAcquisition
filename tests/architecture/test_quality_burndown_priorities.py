"""Architecture quality-gate tests for burn-down priority registries.

Ensures exemptions in the top burn-down registries remain "live":
- file_size_limits
- function_length
- class_size
"""

from __future__ import annotations

import ast
from pathlib import Path

from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry

_SRC_ROOT = Path("src")
_BIOETL_ROOT = _SRC_ROOT / "bioetl"

_LAYER_FILE_LIMITS = {
    "domain": 305,
    "application": 500,
    "composition": 350,
    "infrastructure": 650,
    "interfaces": 400,
}
_DEFAULT_FUNCTION_LENGTH_LIMIT = 100
_DEFAULT_CLASS_SIZE_LIMIT = 300


def _iter_source_modules() -> list[Path]:
    return sorted(
        path
        for path in _BIOETL_ROOT.rglob("*.py")
        if not path.name.startswith("__") and path.is_file()
    )


def _collect_max_function_lengths() -> dict[str, int]:
    lengths: dict[str, int] = {}
    for module in _iter_source_modules():
        try:
            tree = ast.parse(module.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                start = node.lineno
                end = node.end_lineno or start
                length = end - start + 1
                current = lengths.get(node.name, 0)
                if length > current:
                    lengths[node.name] = length
    return lengths


def _collect_max_class_sizes() -> dict[str, int]:
    sizes: dict[str, int] = {}
    for module in _iter_source_modules():
        try:
            tree = ast.parse(module.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                start = node.lineno
                end = node.end_lineno or start
                size = end - start + 1
                current = sizes.get(node.name, 0)
                if size > current:
                    sizes[node.name] = size
    return sizes


def test_file_size_limit_registry_has_no_stale_entries() -> None:
    """file_size_limits exemptions must only remain for files above default limits."""
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    file_size = registries.get("file_size_limits", {})

    violations: list[str] = []
    for key in sorted(file_size):
        module_path = Path(key)
        if not module_path.exists():
            continue

        parts = module_path.parts
        if len(parts) < 3 or parts[:2] != ("src", "bioetl"):
            continue
        layer = parts[2]
        default_limit = _LAYER_FILE_LIMITS.get(layer)
        if default_limit is None:
            continue

        loc = len(module_path.read_text(encoding="utf-8").splitlines())
        if loc <= default_limit:
            violations.append(f"{key}: {loc} <= default layer limit {default_limit}")

    assert not violations, (
        "Stale file_size_limits exemptions detected in burn-down priority registry:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )


def test_function_length_registry_has_no_stale_entries() -> None:
    """function_length exemptions must map to symbols still exceeding 100 lines."""
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    function_length = registries.get("function_length", {})
    max_lengths = _collect_max_function_lengths()

    violations: list[str] = []
    for function_key in sorted(function_length):
        symbol_name = _extract_symbol_name(function_key)
        max_len = max_lengths.get(symbol_name, 0)
        if max_len <= _DEFAULT_FUNCTION_LENGTH_LIMIT:
            violations.append(
                f"{function_key}: max_len={max_len} <= {_DEFAULT_FUNCTION_LENGTH_LIMIT}"
            )

    assert not violations, (
        "Stale function_length exemptions detected in burn-down priority registry:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )


def _extract_symbol_name(key: str) -> str:
    """Extract symbol name from registry key (supports path::Symbol format)."""
    if "::" in key:
        return key.split("::", 1)[1]
    return key


def test_class_size_registry_has_no_stale_entries() -> None:
    """class_size exemptions must map to classes still exceeding 300 lines."""
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    class_size = registries.get("class_size", {})
    max_sizes = _collect_max_class_sizes()

    violations: list[str] = []
    for class_key in sorted(class_size):
        symbol = _extract_symbol_name(class_key)
        max_size = max_sizes.get(symbol, 0)
        if max_size <= _DEFAULT_CLASS_SIZE_LIMIT:
            violations.append(
                f"{class_key}: max_size={max_size} <= {_DEFAULT_CLASS_SIZE_LIMIT}"
            )

    assert not violations, (
        "Stale class_size exemptions detected in burn-down priority registry:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )
