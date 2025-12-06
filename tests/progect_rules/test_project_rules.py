from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable

import pytest
import tomllib
import yaml

from bioetl.domain.configs import HashingConfig, NormalizationConfig
from bioetl.infrastructure.config.provider_registry_loader import (
    ProviderRegistryModel,
    ProviderRegistryNotFoundError,
    ProviderRegistryFormatError,
    ProviderNotConfiguredError,
    ensure_provider_known,
)

SRC_ROOT = Path("src")
BIOETL_ROOT = SRC_ROOT / "bioetl"
SCHEMAS_ROOT = BIOETL_ROOT / "domain" / "schemas" / "chembl"
PYPROJECT = Path("pyproject.toml")

MODULE_NAME_PATTERN = re.compile(r"^[a-z0-9_]+\.py$")
CLASS_NAME_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]+$")
FUNCTION_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _iter_python_files(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*.py") if path.is_file())


def test_style_tooling_is_configured(pyproject: dict) -> None:
    tools = pyproject.get("tool", {})
    missing = [name for name in ("black", "isort", "ruff") if name not in tools]
    if missing:
        pytest.fail(f"Missing formatter/linter configuration sections: {', '.join(missing)}")


def test_mypy_strict_options_enabled(pyproject: dict) -> None:
    mypy_cfg = pyproject.get("tool", {}).get("mypy", {})
    required_flags = {
        "disallow_untyped_defs": True,
        "disallow_incomplete_defs": True,
        "check_untyped_defs": True,
        "no_implicit_optional": True,
    }
    missing = [key for key, expected in required_flags.items() if mypy_cfg.get(key) != expected]
    if missing:
        pytest.fail(
            "Mypy strict configuration is incomplete for keys: " + ", ".join(sorted(missing))
        )


def test_abcs_from_registry_have_docstrings() -> None:
    registry_path = BIOETL_ROOT / "infrastructure" / "clients" / "base" / "abc_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    missing: list[str] = []
    for target in registry.values():
        module_path, class_name = target.rsplit(".", 1)
        source_path = SRC_ROOT / Path(*module_path.split(".")).with_suffix(".py")
        if not source_path.exists():
            continue

        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                if ast.get_docstring(node) is None:
                    missing.append(target)
                break

    if missing:
        pytest.fail("Missing docstrings for: " + ", ".join(sorted(missing)))


def test_module_and_function_naming_conventions() -> None:
    violations: list[str] = []

    for path in _iter_python_files(BIOETL_ROOT):
        filename = path.name
        if filename not in {"__init__.py", "__main__.py"} and not MODULE_NAME_PATTERN.match(
            filename
        ):
            violations.append(f"Invalid module name: {filename}")

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                if not CLASS_NAME_PATTERN.match(node.name):
                    violations.append(
                        f"{path}:{node.lineno} class name '{node.name}' violates convention"
                    )
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("_"):
                    continue
                if not FUNCTION_NAME_PATTERN.match(node.name):
                    violations.append(
                        f"{path}:{node.lineno} function name '{node.name}' violates snake_case"
                    )

    if violations:
        pytest.fail("Naming convention violations:\n" + "\n".join(sorted(violations)))


def test_no_builtin_print_calls_in_source() -> None:
    offenders: list[str] = []

    for path in _iter_python_files(BIOETL_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "print":
                    offenders.append(f"{path}:{node.lineno}")

    if offenders:
        pytest.fail("Use logging instead of print():\n" + "\n".join(offenders))


def test_pandera_schemas_defined_for_entities() -> None:
    violations: list[str] = []
    allow_missing = {
        (SCHEMAS_ROOT / "models.py").as_posix(),
        (SCHEMAS_ROOT / "output_views.py").as_posix(),
    }

    for schema_file in sorted(SCHEMAS_ROOT.glob("*.py")):
        if schema_file.name == "__init__.py":
            continue

        tree = ast.parse(schema_file.read_text(encoding="utf-8"))
        schema_classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and (
                node.name.endswith("Schema")
                or any(
                    isinstance(base, ast.Attribute) and base.attr == "DataFrameModel"
                    for base in node.bases
                )
                or any(
                    isinstance(base, ast.Name) and base.id in {"DataFrameModel", "DataFrameSchema"}
                    for base in node.bases
                )
            )
        ]

        if not schema_classes and schema_file.as_posix() not in allow_missing:
            violations.append(schema_file.as_posix())

    if violations:
        pytest.fail("Missing Pandera schemas in files:\n" + "\n".join(violations))


def test_configs_validate_against_models() -> None:
    hashing_data = yaml.safe_load((Path("configs") / "hashing.yaml").read_text(encoding="utf-8"))
    normalization_data = yaml.safe_load(
        (Path("configs") / "normalization.yaml").read_text(encoding="utf-8")
    )
    providers_data = yaml.safe_load((Path("configs") / "providers.yaml").read_text(encoding="utf-8"))

    HashingConfig.model_validate(hashing_data.get("hashing", {}))
    NormalizationConfig.model_validate(normalization_data.get("normalization", {}))
    ProviderRegistryModel.model_validate(providers_data)


def test_provider_registry_fail_fast_on_unknown_provider() -> None:
    registry_path = Path("configs") / "providers.yaml"

    with pytest.raises(ProviderNotConfiguredError):
        ensure_provider_known("nonexistent", registry_path=registry_path)

    with pytest.raises(ProviderRegistryNotFoundError):
        ensure_provider_known("chembl", registry_path=registry_path.parent / "missing.yaml")

    with pytest.raises(ProviderRegistryFormatError):
        bad_path = registry_path.parent / "_invalid_provider.yaml"
        bad_path.write_text("providers: invalid", encoding="utf-8")
        try:
            ensure_provider_known("chembl", registry_path=bad_path)
        finally:
            bad_path.unlink(missing_ok=True)
