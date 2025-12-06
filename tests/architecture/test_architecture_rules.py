from __future__ import annotations

import ast
import importlib
import inspect
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import pytest
import yaml

SRC_ROOT = Path("src")
BIOETL_ROOT = SRC_ROOT / "bioetl"
PIPELINES_ROOT = BIOETL_ROOT / "application" / "pipelines"
DOC_PIPELINES_ROOT = Path("docs") / "application" / "pipelines"

ALLOWED_LAYERS = {"domain", "application", "infrastructure", "interfaces"}
STAGE_FILES = {"extract.py", "transform.py", "validate.py", "export.py"}
ALLOWED_DUPLICATE_CLASSES = {
    "ProviderRegistryError",
    "ConfigError",
    "ConfigValidationError",
    "NormalizationServiceImpl",
    "NormalizationConfig",
    "Config",
    "BaseProviderConfig",
}
ALLOWED_ABCS_WITHOUT_IMPL = {
    "CLICommandABC",
    "ErrorPolicyABC",
    "MutableProviderRegistryABC",
    "PaginatorABC",
    "PipelineContainerABC",
    "PipelineHookABC",
    "ProviderRegistryABC",
    "RequestBuilderABC",
    "ResponseParserABC",
    "SchemaProviderABC",
    "SecretProviderABC",
    "SideInputProviderABC",
    "SourceClientABC",
    "StageABC",
    "TracerABC",
}


def _iter_python_files(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*.py") if path.is_file())


def test_source_files_are_within_allowed_layers() -> None:
    violations: list[str] = []

    for path in _iter_python_files(BIOETL_ROOT):
        relative = path.relative_to(BIOETL_ROOT)
        parts = relative.parts
        if len(parts) == 1 and parts[0] in {"__init__.py", "__main__.py"}:
            continue

        if not parts:
            continue

        layer = parts[0]
        if layer not in ALLOWED_LAYERS:
            violations.append(path.as_posix())

    if violations:
        pytest.fail(
            "Found source files outside domain/application/infrastructure/interfaces:\n"
            + "\n".join(sorted(violations))
        )


def test_domain_imports_avoid_infrastructure_and_io_clients() -> None:
    forbidden_modules = {
        "bioetl.infrastructure",
        "requests",
        "httpx",
        "aiohttp",
        "botocore",
        "boto3",
    }

    violations: list[str] = []

    for file_path in sorted((BIOETL_ROOT / "domain").rglob("*.py")):
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for module in forbidden_modules:
                        if alias.name.startswith(module):
                            violations.append(f"{file_path}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                for module in forbidden_modules:
                    if node.module.startswith(module):
                        violations.append(
                            f"{file_path}:{node.lineno}: from {node.module} import ..."
                        )

    if violations:
        pytest.fail(
            "Domain layer must not depend on infrastructure or IO clients:\n"
            + "\n".join(sorted(set(violations)))
        )


@pytest.fixture(scope="module")
def abc_registry() -> dict[str, str]:
    registry_path = BIOETL_ROOT / "infrastructure" / "clients" / "base" / "abc_registry.yaml"
    return yaml.safe_load(registry_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def abc_impls() -> dict[str, dict]:
    impls_path = BIOETL_ROOT / "infrastructure" / "clients" / "base" / "abc_impls.yaml"
    return yaml.safe_load(impls_path.read_text(encoding="utf-8"))


def _load_class(target: str) -> type:
    module_path, class_name = target.rsplit(".", 1)
    module = importlib.import_module(module_path)
    obj = getattr(module, class_name)
    if not inspect.isclass(obj):
        pytest.fail(f"{target} is not a class")
    return obj


def _is_explicit_subclass(candidate: type, expected_base: type) -> bool:
    try:
        return issubclass(candidate, expected_base)
    except TypeError:
        return expected_base in candidate.__mro__


def test_abcs_have_documented_implementations(
    abc_registry: dict[str, str], abc_impls: dict[str, dict]
) -> None:
    missing_impl: list[str] = []
    missing_files: list[str] = []

    for name, target in abc_registry.items():
        module_path, _ = target.rsplit(".", 1)
        source_path = SRC_ROOT / Path(*module_path.split(".")).with_suffix(".py")
        if not source_path.exists():
            missing_files.append(source_path.as_posix())

        impl_entry = abc_impls.get(name)
        if not impl_entry or not impl_entry.get("implementations"):
            if name in ALLOWED_ABCS_WITHOUT_IMPL:
                continue
            missing_impl.append(name)
            continue

        for impl_target in impl_entry["implementations"].values():
            impl_module, _ = impl_target.rsplit(".", 1)
            impl_path = SRC_ROOT / Path(*impl_module.split(".")).with_suffix(".py")
            if not impl_path.exists():
                missing_files.append(impl_path.as_posix())

    if missing_impl:
        pytest.fail(
            "Implementations are missing for ABCs: " + ", ".join(sorted(set(missing_impl)))
        )

    if missing_files:
        pytest.fail(
            "Referenced modules are absent: " + ", ".join(sorted(set(missing_files)))
        )


def test_registered_impls_subclass_their_abcs(
    abc_registry: dict[str, str], abc_impls: dict[str, dict]
) -> None:
    violations: list[str] = []

    for abc_name, abc_target in abc_registry.items():
        impl_entry = abc_impls.get(abc_name)
        implementations = impl_entry.get("implementations") if impl_entry else None
        if not implementations:
            if abc_name in ALLOWED_ABCS_WITHOUT_IMPL:
                continue
            violations.append(f"{abc_name} is missing implementations")
            continue

        abc_cls = _load_class(abc_target)
        for impl_target in implementations.values():
            impl_cls = _load_class(impl_target)
            if not _is_explicit_subclass(impl_cls, abc_cls):
                violations.append(
                    f"{impl_target} must subclass {abc_target} as per ABC/Impl pattern"
                )

    if violations:
        pytest.fail("ABC/Impl contract violations:\n" + "\n".join(sorted(set(violations))))


def test_pipeline_docs_and_stage_structure() -> None:
    violations: list[str] = []

    for provider_dir in sorted(PIPELINES_ROOT.iterdir()):
        if not provider_dir.is_dir() or provider_dir.name.startswith("__"):
            continue

        docs_dir = DOC_PIPELINES_ROOT / provider_dir.name
        if not docs_dir.exists():
            violations.append(
                f"docs for provider '{provider_dir.name}' not found at {docs_dir}"
            )
        elif not (docs_dir / "00-index.md").exists():
            violations.append(
                f"docs/application/pipelines/{provider_dir.name}/00-index.md is missing"
            )

        entity_dirs = [d for d in provider_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        if not entity_dirs:
            continue

        for entity_dir in entity_dirs:
            stage_files = {child.name for child in entity_dir.iterdir() if child.is_file()}
            missing = [name for name in STAGE_FILES if name not in stage_files]
            if missing:
                violations.append(
                    f"{entity_dir.as_posix()} is missing stage files: {', '.join(sorted(missing))}"
                )

    if violations:
        pytest.fail("Pipeline structure violations:\n" + "\n".join(sorted(set(violations))))


def test_no_untracked_duplicate_class_names() -> None:
    class_locations: defaultdict[str, set[Path]] = defaultdict(set)

    for path in _iter_python_files(BIOETL_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_locations[node.name].add(path)

    duplicates = {
        name: {p.as_posix() for p in paths}
        for name, paths in class_locations.items()
        if len(paths) > 1 and name not in ALLOWED_DUPLICATE_CLASSES
    }

    if duplicates:
        formatted = [f"{name}: {sorted(paths)}" for name, paths in sorted(duplicates.items())]
        pytest.fail("Potential duplicate classes detected:\n" + "\n".join(formatted))
