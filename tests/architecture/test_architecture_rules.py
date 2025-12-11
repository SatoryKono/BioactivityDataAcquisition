from __future__ import annotations

import ast
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
    "DefaultNormalizationTransformerImpl",
    "NormalizationConfig",
    "Config",
    "BaseProviderConfig",
    # Temporary: bounded context configs migration (will be consolidated)
    "CsvInputConfig",
    "DataSourceConfig",
    "DataSinkConfig",
    "OutputOptionsConfig",
    # Forward declaration for type hints (application_context.py)
    "UseCaseFactory",
}
ALLOWED_ABCS_WITHOUT_IMPL = {
    "CLICommandABC",
    "ErrorPolicyABC",
    "PaginatorABC",
    "PipelineContainerABC",
    "PipelineHookABC",
    "ProviderRegistryABC",
    "RequestBuilderABC",
    "ResponseParserABC",
    "SchemaProviderABC",
    "SecretProviderABC",
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

    # Files with deprecated lazy imports for backward compatibility
    # These files exist only to redirect imports and will be removed
    deprecated_files = {
        # domain/schemas/generator.py - deprecated, redirects to infrastructure
        "generator.py",
    }

    violations: list[str] = []

    for file_path in sorted((BIOETL_ROOT / "domain").rglob("*.py")):
        # Skip deprecated files that exist only for backward compatibility
        if file_path.name in deprecated_files:
            continue

        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for module in forbidden_modules:
                        if alias.name.startswith(module):
                            violations.append(
                                f"{file_path}:{node.lineno}: import {alias.name}"
                            )
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
    registry_path = (
        BIOETL_ROOT / "infrastructure" / "clients" / "base" / "abc_registry.yaml"
    )
    return yaml.safe_load(registry_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def abc_impls() -> dict[str, dict]:
    impls_path = BIOETL_ROOT / "infrastructure" / "clients" / "base" / "abc_impls.yaml"
    return yaml.safe_load(impls_path.read_text(encoding="utf-8"))


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
            "Implementations are missing for ABCs: "
            + ", ".join(sorted(set(missing_impl)))
        )

    if missing_files:
        pytest.fail(
            "Referenced modules are absent: " + ", ".join(sorted(set(missing_files)))
        )


def test_pipeline_docs_and_stage_structure() -> None:
    violations: list[str] = []
    # Directories that are not providers (shared utilities, etc.)
    NON_PROVIDER_DIRS = {"stages"}

    for provider_dir in sorted(PIPELINES_ROOT.iterdir()):
        if (
            not provider_dir.is_dir()
            or provider_dir.name.startswith("__")
            or provider_dir.name in NON_PROVIDER_DIRS
        ):
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

        entity_dirs = [
            d
            for d in provider_dir.iterdir()
            if d.is_dir() and not d.name.startswith("__")
        ]
        if not entity_dirs:
            continue

        for entity_dir in entity_dirs:
            stage_files = {
                child.name for child in entity_dir.iterdir() if child.is_file()
            }
            missing = [name for name in STAGE_FILES if name not in stage_files]
            if missing:
                violations.append(
                    f"{entity_dir.as_posix()} is missing stage files: "
                    f"{', '.join(sorted(missing))}"
                )

    if violations:
        pytest.fail(
            "Pipeline structure violations:\n" + "\n".join(sorted(set(violations)))
        )


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
        formatted = [
            f"{name}: {sorted(paths)}" for name, paths in sorted(duplicates.items())
        ]
        pytest.fail("Potential duplicate classes detected:\n" + "\n".join(formatted))


def test_infrastructure_abc_impls_has_no_application_references() -> None:
    """Verify infrastructure abc_impls.yaml doesn't reference application layer.

    Application-layer implementations should be defined in interfaces layer
    (interfaces/abc_impls_application.yaml) to maintain proper layer boundaries.
    Infrastructure layer must not know about application layer.
    """
    impls_path = BIOETL_ROOT / "infrastructure" / "clients" / "base" / "abc_impls.yaml"
    data = yaml.safe_load(impls_path.read_text(encoding="utf-8"))

    violations: list[str] = []
    for role, config in data.items():
        if not isinstance(config, dict):
            continue

        default_factory = config.get("default_factory", "")
        if "bioetl.application" in default_factory:
            violations.append(f"{role}.default_factory -> {default_factory}")

        for impl_name, impl_path in config.get("implementations", {}).items():
            if "bioetl.application" in impl_path:
                violations.append(f"{role}.implementations.{impl_name} -> {impl_path}")

    if violations:
        pytest.fail(
            "Infrastructure abc_impls.yaml must not reference application layer.\n"
            "Application implementations should be in "
            "interfaces/abc_impls_application.yaml.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


# =============================================================================
# Phase 8: Strengthened Architectural Tests
# =============================================================================


def _collect_imports_with_context(path: Path) -> list[tuple[str, int, bool]]:
    """Collect import modules with line numbers and TYPE_CHECKING context.

    Returns:
        List of tuples: (module_name, line_number, is_type_checking_only)
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[tuple[str, int, bool]] = []

    # Find TYPE_CHECKING blocks
    type_checking_ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check if this is `if TYPE_CHECKING:`
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                # Get the range of lines in the if block
                start_line = node.lineno
                # Find the last line in the body
                end_line = start_line
                for item in node.body:
                    if hasattr(item, "end_lineno") and item.end_lineno:
                        end_line = max(end_line, item.end_lineno)
                    elif hasattr(item, "lineno"):
                        end_line = max(end_line, item.lineno)
                type_checking_ranges.append((start_line, end_line))

    def is_in_type_checking(lineno: int) -> bool:
        return any(start <= lineno <= end for start, end in type_checking_ranges)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    (
                        alias.name,
                        node.lineno,
                        is_in_type_checking(node.lineno),
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(
                    (node.module, node.lineno, is_in_type_checking(node.lineno))
                )

    return imports


def test_application_has_no_runtime_infrastructure_imports() -> None:
    """Ensure application layer has no runtime imports from infrastructure.

    TYPE_CHECKING imports are allowed for type hints only.
    Allowed exceptions are tracked and should be minimized over time.
    """
    application_root = BIOETL_ROOT / "application"
    # Known allowed exceptions (should be empty after full refactoring)
    allowed_exceptions: set[str] = {
        # Lazy import in orchestrator for backward compatibility
        "bioetl.application.orchestrator:bioetl.infrastructure.provider_registry",
    }

    violations: list[str] = []
    for path in sorted(_iter_python_files(application_root)):
        for module, lineno, is_type_checking in _collect_imports_with_context(path):
            if module.startswith("bioetl.infrastructure"):
                if is_type_checking:
                    continue  # Type hints are OK
                rel_path = path.relative_to(SRC_ROOT).as_posix()
                module_path = rel_path.replace("/", ".").replace(".py", "")
                exception_key = f"{module_path}:{module}"
                if exception_key not in allowed_exceptions:
                    violations.append(f"{path}:{lineno}: import {module}")

    if violations:
        pytest.fail(
            "Application layer must not have runtime imports from infrastructure.\n"
            "Use dependency injection or move import to TYPE_CHECKING block.\n"
            "Violations:\n" + "\n".join(sorted(set(violations)))
        )


def test_application_has_no_pandas_imports() -> None:
    """Ensure application layer does not directly depend on pandas.

    Application should use TabularData protocol for dataframe operations.
    TYPE_CHECKING imports for type hints are allowed.

    Note: Some legacy files still have pandas imports and are tracked for
    gradual migration. These are listed in ALLOWED_PANDAS_FILES.
    """
    application_root = BIOETL_ROOT / "application"
    forbidden_modules = {"pandas", "pd"}

    # Legacy files that still use pandas directly (tracked for migration)
    # TODO: Migrate these to use TabularData protocol
    allowed_pandas_files = {
        "executor.py",
        "csv_record_source.py",
        "base.py",  # pipelines/base.py and chembl/base.py
        "transformer.py",
        "stage_runtime_manager.py",
        "stage_processor.py",
        "extract.py",
        "pandas_batch_adapter.py",
    }

    violations: list[str] = []
    for path in sorted(_iter_python_files(application_root)):
        # Skip allowed legacy files
        if path.name in allowed_pandas_files:
            continue

        for module, lineno, is_type_checking in _collect_imports_with_context(path):
            if module in forbidden_modules or module.startswith("pandas."):
                if is_type_checking:
                    continue  # Type hints are OK
                violations.append(f"{path}:{lineno}: import {module}")

    if violations:
        pytest.fail(
            "Application layer must not directly depend on pandas.\n"
            "Use TabularData protocol from domain.data for dataframe operations.\n"
            "Violations:\n" + "\n".join(sorted(set(violations)))
        )


def test_interfaces_has_controlled_infrastructure_imports() -> None:
    """Ensure interfaces layer has controlled infrastructure imports.

    Interfaces layer (composition root) is allowed to import infrastructure
    for wiring, but should do so in a controlled manner.
    This test tracks and limits the number of infrastructure imports.

    Note: Some files are allowed to have infrastructure imports because
    they are part of the composition/wiring layer. These files are
    explicitly listed and should not grow without discussion.
    """
    interfaces_root = BIOETL_ROOT / "interfaces"

    # Files that are allowed to have infrastructure imports (composition/wiring)
    # These files are responsible for wiring infrastructure to the application
    allowed_files = {
        # Core composition
        "composition_root.py",
        "application_context.py",
        "bootstrap_factory.py",
        "use_case_factory.py",
        # Factories (by design, wire infrastructure)
        "factories/__init__.py",
        "factories/infrastructure.py",
        "factories/observability.py",
        "factories/provider_registry.py",
        # CLI entry points (composition happens here)
        "cli/app.py",
        "cli/__init__.py",
        # Monitoring (needs infrastructure observability)
        "monitoring/__init__.py",
    }

    violations: list[str] = []
    for path in sorted(_iter_python_files(interfaces_root)):
        relative_path = path.relative_to(interfaces_root).as_posix()
        if relative_path in allowed_files:
            continue  # Allowed files can import infrastructure

        for module, lineno, is_type_checking in _collect_imports_with_context(path):
            if module.startswith("bioetl.infrastructure"):
                if is_type_checking:
                    continue
                violations.append(f"{path}:{lineno}: import {module}")

    if violations:
        pytest.fail(
            "Interfaces layer has uncontrolled infrastructure imports.\n"
            "Only composition/wiring files should import infrastructure directly.\n"
            "Other files should use ports and adapters.\n"
            "Violations:\n" + "\n".join(sorted(set(violations)))
        )


def test_no_cross_module_private_attribute_access() -> None:
    """Detect access to private attributes of other modules.

    This test finds patterns like `other_module._private` which violate
    encapsulation principles. Private attributes should only be accessed
    within their own module.
    """
    # Pattern: accessing _attr on something other than self
    violations: list[str] = []

    for path in sorted(_iter_python_files(BIOETL_ROOT)):
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                attr_name = node.attr
                # Skip dunder methods and non-private attributes
                if not attr_name.startswith("_") or attr_name.startswith("__"):
                    continue

                # Check if it's accessing on something other than self
                if isinstance(node.value, ast.Name):
                    if node.value.id != "self":
                        # Accessing _private on a variable (not self)
                        violations.append(
                            f"{path}:{node.lineno}: {node.value.id}.{attr_name}"
                        )
                elif isinstance(node.value, ast.Attribute):
                    # Chain access like obj.sub._private
                    violations.append(f"{path}:{node.lineno}: ....{attr_name}")

    # Filter to keep only likely cross-module violations
    # Some false positives are expected (e.g., testing, internal use)
    allowed_patterns = {
        # Internal testing utilities
        "_mock",
        "_stub",
        "_test",
        "_fixture",
        # Common Python internals
        "_name",
        "_module",
        "_asdict",
        "_replace",
        "_fields",
        # Pydantic/dataclass internals
        "_validate",
        "_validators",
        # Common framework patterns
        "_registry",
        "_instance",
        "_cache",
        "_lock",
    }

    filtered_violations = [
        v for v in violations if not any(pattern in v for pattern in allowed_patterns)
    ]

    # Report as warning, not failure (informational)
    if filtered_violations and len(filtered_violations) > 50:
        pytest.fail(
            f"Found {len(filtered_violations)} potential cross-module "
            "private attribute accesses.\n"
            "Consider using proper public APIs instead of private attributes.\n"
            "First 20 violations:\n" + "\n".join(filtered_violations[:20])
        )
