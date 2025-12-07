from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

import pytest

SOURCE_ROOT = Path("src")
PACKAGE_ROOT = SOURCE_ROOT / "bioetl"
ALLOWED_LAYERS = {"domain", "application", "infrastructure", "interfaces"}


def _iter_python_files(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*.py") if "/__pycache__/" not in path.as_posix())


def _collect_import_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if base:
                modules.append(base)
    return modules


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
        elif isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
            names.add(base.value.id)
    return names


@pytest.fixture()
def domain_python_files() -> list[Path]:
    return sorted(_iter_python_files(PACKAGE_ROOT / "domain"))


@pytest.fixture()
def infrastructure_python_files() -> list[Path]:
    return sorted(_iter_python_files(PACKAGE_ROOT / "infrastructure"))


def test_sources_reside_in_layers() -> None:
    """Verify that modules live under the four canonical layers."""

    violations: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT):
        relative = path.relative_to(PACKAGE_ROOT)
        if len(relative.parts) == 1:
            # Root package files like __init__.py and __main__.py are allowed.
            continue

        layer = relative.parts[0]
        if layer not in ALLOWED_LAYERS:
            violations.append(relative.as_posix())

    if violations:
        pytest.fail(
            "Files detected outside allowed layers:\n" + "\n".join(sorted(violations))
        )


def test_domain_isolation_has_no_forbidden_imports(domain_python_files: list[Path]) -> None:
    """Ensure domain code avoids infrastructure, application and heavy I/O deps."""

    forbidden_prefixes = ("bioetl.infrastructure", "bioetl.application")
    forbidden_modules = {
        "requests",
        "httpx",
        "aiohttp",
        "sqlalchemy",
        "boto3",
    }

    violations: list[str] = []
    for path in domain_python_files:
        for module in _collect_import_modules(path):
            if module.startswith(forbidden_prefixes) or module in forbidden_modules:
                violations.append(f"{path.as_posix()}: forbidden import {module}")

    if violations:
        pytest.fail(
            "Domain must stay isolated; forbidden imports found:\n"
            + "\n".join(sorted(violations))
        )


def test_abc_impl_pairs_align(
    domain_python_files: list[Path], infrastructure_python_files: list[Path]
) -> None:
    """Check that *Impl classes align with their domain ABC/Protocol counterparts."""

    domain_abcs: dict[str, str] = {}
    for path in domain_python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith(("ABC", "Protocol")):
                domain_abcs[node.name] = path.as_posix()

    impls: dict[str, tuple[str, set[str]]] = {}
    for path in infrastructure_python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Impl"):
                impls[node.name] = (path.as_posix(), _base_names(node))

    violations: list[str] = []
    for abc_name, abc_path in domain_abcs.items():
        impl_name = abc_name.replace("ABC", "Impl").replace("Protocol", "Impl")
        impl_info = impls.get(impl_name)
        if impl_info is None:
            # No implementation yet; the rule is enforced only when a matching Impl exists.
            continue

        impl_path, bases = impl_info
        if abc_name not in bases:
            violations.append(
                f"{impl_path}: {impl_name} must inherit from {abc_name} (defined in {abc_path})"
            )

    if violations:
        pytest.fail("ABC/Impl alignment violations:\n" + "\n".join(sorted(violations)))


def test_pipeline_stage_layout_respects_convention() -> None:
    """Ensure pipeline folders (if present) contain the expected ETL stage modules."""

    pipelines_root = PACKAGE_ROOT / "application" / "pipelines"
    provider_dirs = [
        path for path in pipelines_root.iterdir() if path.is_dir() and path.name != "__pycache__"
    ]

    entity_dirs: list[Path] = []
    for provider_dir in provider_dirs:
        for candidate in provider_dir.iterdir():
            if candidate.is_dir() and candidate.name != "__pycache__":
                entity_dirs.append(candidate)

    if not entity_dirs:
        pytest.skip("No provider/entity pipeline directories to validate.")

    required_files = {"extract.py", "transform.py", "validate.py", "export.py"}
    violations: list[str] = []

    for entity_dir in entity_dirs:
        present = {path.name for path in entity_dir.iterdir() if path.is_file()}
        missing = sorted(required_files - present)
        if missing:
            violations.append(
                f"{entity_dir.as_posix()}: missing stage files {', '.join(missing)}"
            )

    if violations:
        pytest.fail("Pipeline layout violations:\n" + "\n".join(sorted(violations)))


def test_duplicate_class_names_are_allowlisted() -> None:
    """Detect duplicate class names and require an explicit allowlist entry."""

    duplicates_allowlist = {
        "ProviderRegistryError",
        "ConfigError",
        "ConfigValidationError",
        "BaseProviderConfig",
        "NormalizationServiceImpl",
        "NormalizationConfig",
        "Config",
    }

    class_map: dict[str, list[Path]] = {}
    for path in _iter_python_files(PACKAGE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_map.setdefault(node.name, []).append(path)

    unexpected_duplicates: dict[str, list[str]] = {}
    for name, paths in class_map.items():
        if len(paths) > 1 and name not in duplicates_allowlist:
            unexpected_duplicates[name] = [p.as_posix() for p in paths]

    if unexpected_duplicates:
        formatted = "; ".join(
            f"{name}: {', '.join(locations)}" for name, locations in sorted(unexpected_duplicates.items())
        )
        pytest.fail(f"Unexpected duplicate class names detected: {formatted}")
