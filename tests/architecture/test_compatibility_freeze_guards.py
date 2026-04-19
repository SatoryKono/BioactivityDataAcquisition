"""Compatibility-freeze guardrails for shim imports and symbols."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGACY_DATASOURCE_FACTORY_MODULE = "bioetl.composition.factories.datasource.factory"
INTERNAL_COMPOSITION_ENTRYPOINT_MODULES = (
    "bioetl.composition._pipeline_execution",
    "bioetl.composition._resource_management",
    "bioetl.composition._services",
)
CLI_REGISTRY_HELPER_MODULE = "bioetl.interfaces.cli.registry_helpers"
METADATA_BUILDER_COMPAT_MODULE = (
    "bioetl.infrastructure.storage.metadata_builder_composite_helpers"
)
METADATA_BUILDER_COMPAT_MODULE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "storage"
    / "metadata_builder_composite_helpers.py"
)
CONFIG_LOADER_MODULE = "bioetl.infrastructure.config_loader"
CONFIG_LOADER_MODULE_PATH = (
    ROOT / "src" / "bioetl" / "infrastructure" / "config_loader.py"
)
CONFIG_LOAD_API_MODULE = "bioetl.infrastructure.config_load_api"
CONFIG_LOAD_API_MODULE_PATH = (
    ROOT / "src" / "bioetl" / "infrastructure" / "config_load_api.py"
)
INFRASTRUCTURE_CONFIG_PUBLIC_MODULE = "bioetl.infrastructure.config"
SERVICES_CREATION_API_COMPAT_MODULE = (
    "bioetl.composition.factories.services.creation_api"
)
SERVICES_CREATION_API_COMPAT_MODULE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "factories"
    / "services"
    / "creation_api.py"
)
PIPELINE_CREATION_API_COMPAT_MODULE = (
    "bioetl.composition.factories.pipeline.creation_api"
)
PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE = (
    "bioetl.composition.factories.pipeline.config_resolution"
)
PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "factories"
    / "pipeline"
    / "config_resolution.py"
)
PIPELINE_CONFIGS_COMPAT_MODULE = "bioetl.composition.factories.pipeline.configs"
PIPELINE_CONFIGS_COMPAT_MODULE_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "factories" / "pipeline" / "configs.py"
)
RUN_COMMAND_INTERNAL_MODULE = "bioetl.interfaces.cli.commands.domains.run.command"
RUN_ALL_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.run_all.command"
)
RUN_COMPOSITE_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.composite.command"
)
HEALTH_COMMAND_INTERNAL_MODULE = "bioetl.interfaces.cli.commands.domains.health.command"
QUARANTINE_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.quarantine.command"
)
MAINTENANCE_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.maintenance.command"
)
ARCHIVE_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.maintenance.archive"
)
CLEANUP_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.maintenance.cleanup"
)
VACUUM_COMMAND_INTERNAL_MODULE = (
    "bioetl.interfaces.cli.commands.domains.maintenance.vacuum"
)
TEST_FACING_RUN_HELPER_SEAM_MODULES = frozenset()
TEST_FACING_RUN_ALL_HELPER_SEAM_MODULES = frozenset()
TEST_FACING_RUN_COMPOSITE_HELPER_SEAM_MODULES = frozenset()
TEST_FACING_QUARANTINE_HELPER_SEAM_MODULES = frozenset(
    {
        "bioetl.interfaces.cli.commands.quarantine_execution",
        "bioetl.interfaces.cli.commands.quarantine_rendering",
        "bioetl.interfaces.cli.commands.quarantine_support",
    }
)
TEST_FACING_HEALTH_HELPER_SEAM_MODULES = frozenset(
    {
        "bioetl.interfaces.cli.commands.health_rendering",
        "bioetl.interfaces.cli.commands.health_server_integration",
        "bioetl.interfaces.cli.commands.metrics_server_integration",
    }
)
TEST_FACING_SHARED_CLI_POLICY_SEAM_MODULES: frozenset[str] = frozenset()
PIPELINE_RUNNER_SERVICE_MODULE = "bioetl.application.services.pipeline_runner_service"
LEGACY_MERGE_SERVICE_KEYWORDS = frozenset(
    {
        "deduplicator",
        "aggregator",
        "renamer",
        "orderer",
        "priority_orderer",
        "coalesce_policy",
        "conflict_resolver",
        "join_planner",
    }
)

TRANSFORMER_DEPENDENCY_SHIM = "bioetl.application.core.base_transformer.dependencies"
TRANSFORMER_DEPENDENCY_SHIM_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "base_transformer"
    / "dependencies.py"
)

ALLOWED_DATASOURCE_REGISTRY_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "factories" / "__init__.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "datasource"
        / "__init__.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "datasource"
        / "data_source_factory.py",
    }
)
ALLOWED_DATASOURCE_REGISTRY_TEST_FILES = frozenset(
    {
        ROOT / "tests" / "architecture" / "test_registry_contracts.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "factories"
        / "datasource"
        / "test_data_source_registry.py",
        ROOT / "tests" / "unit" / "composition" / "test_canonical_module_paths.py",
        ROOT / "tests" / "unit" / "composition" / "test_registry_protocol.py",
    }
)
ALLOWED_REGISTER_ALL_PROVIDERS_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "providers" / "__init__.py",
        ROOT / "src" / "bioetl" / "composition" / "providers" / "_loading.py",
        ROOT / "src" / "bioetl" / "composition" / "providers" / "loader.py",
        ROOT / "src" / "bioetl" / "composition" / "providers" / "registration.py",
    }
)
ALLOWED_DEFAULT_PROVIDER_REGISTRATION_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "providers" / "provider_registry.py",
        ROOT / "src" / "bioetl" / "composition" / "providers" / "decorators.py",
    }
)
ALLOWED_REGISTRATION_BIBLIO_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "providers" / "registration.py",
    }
)
CANONICAL_PROVIDER_SURFACE_DOC_FILES = frozenset(
    {
        ROOT / "docs" / "02-architecture" / "05-composition-layer.md",
        ROOT / "docs" / "03-guides" / "add-new-source.md",
        ROOT / "docs" / "03-guides" / "add-pipeline-existing-source.md",
        ROOT / "docs" / "00-project" / "governance" / "04-extending-bioetl.md",
        ROOT / "docs" / "04-reference" / "providers" / "chembl" / "cell-line.md",
        ROOT / "docs" / "04-reference" / "api" / "composition.md",
    }
)
CANONICAL_DATASOURCE_DOC_FILES = frozenset(
    {
        ROOT / "docs" / "02-architecture" / "03-infrastructure-layer.md",
        ROOT / "docs" / "02-architecture" / "05-composition-layer.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "class-diagrams"
        / "16-factories-bootstrap.mmd",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "architecture"
        / "12a-bootstrap-factories.mmd",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "architecture"
        / "12-bootstrap-di-container.mmd",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "descriptions"
        / "class-summary.md",
        ROOT / "docs" / "02-architecture" / "diagrams" / "bundles" / "class.bundle.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "bundles"
        / "architecture.bundle.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "descriptions"
        / "architecture"
        / "12a-bootstrap-factories.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagrams"
        / "descriptions"
        / "class"
        / "16-factories-bootstrap.md",
    }
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES: frozenset[Path] = frozenset()
LEGACY_DATASOURCE_FACTORY_MODULE_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "factories" / "datasource" / "factory.py"
)
LEGACY_BATCH_TRANSFORMER_ORCHESTRATION_MODULE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "batch_transformer_orchestration.py"
)
SANCTIONED_DEAD_CODE_EXCLUSION_MODULE_PATHS = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "dependency_join_support.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "core"
        / "batch_execution_lifecycle.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "core"
        / "batch_execution_run_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "core"
        / "batch_execution_state_service.py",
    }
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_PIPELINE_CREATION_API_TEST_FILES = frozenset(
    {
        ROOT / "tests" / "unit" / "composition" / "test_canonical_module_paths.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "factories"
        / "test_factory_decoupling_contracts.py",
    }
)
ALLOWED_PIPELINE_RUNNER_SERVICE_MODEL_IMPORT_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "application" / "services" / "__init__.py",
    }
)
ALLOWED_INTERNAL_ENTRYPOINT_TEST_FILES_BY_MODULE = {
    "bioetl.composition._pipeline_execution": frozenset(
        {
            ROOT / "tests" / "unit" / "composition" / "test_entrypoints.py",
        }
    ),
    "bioetl.composition._resource_management": frozenset(
        {
            ROOT / "tests" / "unit" / "composition" / "test_resource_management.py",
        }
    ),
    "bioetl.composition._services": frozenset(
        {
            ROOT / "tests" / "unit" / "composition" / "test_services_entrypoints.py",
        }
    ),
}
ALLOWED_RUN_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run"
        / "__init__.py",
    }
)
ALLOWED_RUN_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run.py",
    }
)
ALLOWED_RUN_ALL_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run_all.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run_all"
        / "__init__.py",
    }
)
ALLOWED_RUN_ALL_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run_all.py",
    }
)
ALLOWED_RUN_COMPOSITE_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "run_composite.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "composite"
        / "__init__.py",
    }
)
ALLOWED_RUN_COMPOSITE_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "run_composite.py",
    }
)
ALLOWED_HEALTH_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "health.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "health"
        / "__init__.py",
    }
)
ALLOWED_HEALTH_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "health.py",
    }
)
ALLOWED_QUARANTINE_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "quarantine.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "quarantine"
        / "__init__.py",
    }
)
ALLOWED_QUARANTINE_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "quarantine.py",
    }
)
ALLOWED_MAINTENANCE_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "maintenance.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "maintenance"
        / "__init__.py",
    }
)
ALLOWED_MAINTENANCE_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "maintenance.py",
    }
)
ALLOWED_ARCHIVE_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "archive.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "maintenance"
        / "command.py",
    }
)
ALLOWED_ARCHIVE_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "archive.py",
    }
)
ALLOWED_CLEANUP_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "cleanup.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "maintenance"
        / "command.py",
    }
)
ALLOWED_CLEANUP_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "cleanup.py",
    }
)
ALLOWED_VACUUM_COMMAND_INTERNAL_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "vacuum.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "maintenance"
        / "command.py",
    }
)
ALLOWED_VACUUM_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "vacuum.py",
    }
)
ALLOWED_CLI_REGISTRY_HELPER_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "__init__.py",
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "main.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run"
        / "support.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run_all"
        / "command.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run"
        / "support.py",
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run_all"
        / "command.py",
    }
)
ALLOWED_CLI_GET_DEFAULT_REGISTRY_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_COMPOSITION_DEFAULT_REGISTRY_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "__init__.py",
    }
)
ALLOWED_COMPOSITION_REGISTRY_MODULE_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "__init__.py",
        ROOT / "src" / "bioetl" / "composition" / "registry_default.py",
    }
)
ALLOWED_COMPOSITION_REGISTRY_MODULE_TEST_FILES = frozenset({})
ALLOWED_COMPOSITION_DEFAULT_REGISTRY_TEST_FILES = frozenset({})
ALLOWED_CONFIG_LOADER_SRC_FILES: frozenset[Path] = frozenset()
ALLOWED_CONFIG_LOADER_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_CONFIG_LOAD_API_SRC_FILES: frozenset[Path] = frozenset()
ALLOWED_CONFIG_LOAD_API_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_INFRASTRUCTURE_CONFIG_LOADER_SYMBOL_SRC_FILES: frozenset[Path] = frozenset()
ALLOWED_PIPELINE_CONFIG_RESOLUTION_SRC_FILES: frozenset[Path] = frozenset()
ALLOWED_PIPELINE_CONFIG_RESOLUTION_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_METADATA_BUILDER_COMPAT_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_MERGE_SERVICE_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "application" / "composite" / "merger.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "composite_support_services_factory.py",
    }
)


def _relative_to_root(path: Path) -> str:
    """Return a stable project-relative POSIX path without eager filesystem resolution."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().relative_to(ROOT).as_posix()


def _normalized_allowed_rel_paths(allowed_files: frozenset[Path]) -> frozenset[str]:
    """Normalize allowlist paths to project-relative POSIX strings."""
    return frozenset(_relative_to_root(path) for path in allowed_files)


def _current_package_parts(py_file: Path) -> list[str]:
    module_parts = list(py_file.relative_to(ROOT).with_suffix("").parts)
    return module_parts if py_file.stem == "__init__" else module_parts[:-1]


def _resolve_relative_import_module(py_file: Path, node: ast.ImportFrom) -> str | None:
    if node.module is None or node.level <= 0:
        return None
    package_parts = _current_package_parts(py_file)
    anchor_length = len(package_parts) - (node.level - 1)
    if anchor_length <= 0:
        return None
    return ".".join([*package_parts[:anchor_length], *node.module.split(".")])


def _matching_imported_module(
    *,
    py_file: Path,
    node: ast.ImportFrom,
    module_names: frozenset[str],
) -> str | None:
    if node.module in module_names:
        return node.module
    resolved = _resolve_relative_import_module(py_file, node)
    if resolved in module_names:
        return resolved
    return None


def _iter_non_allowed_cache_items(
    cache: dict[Path, object],
    *,
    allowed_files: frozenset[Path],
) -> list[tuple[Path, object, str]]:
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    items: list[tuple[Path, object, str]] = []
    for py_file, payload in sorted(cache.items()):
        rel_path = _relative_to_root(py_file)
        if rel_path in allowed_rel_paths:
            continue
        items.append((py_file, payload, rel_path))
    return items


def _iter_text_mentions(
    *,
    content_cache: dict[Path, str],
    allowed_files: frozenset[Path],
    predicate,
    render_message,
) -> list[str]:
    violations: list[str] = []
    for _py_file, content, rel_path in _iter_non_allowed_cache_items(
        content_cache, allowed_files=allowed_files
    ):
        for lineno, line in enumerate(content.splitlines(), 1):
            if predicate(line):
                violations.append(render_message(rel_path, lineno, line))
    return violations


def _iter_module_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    module_name: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree, rel_path in _iter_non_allowed_cache_items(
        ast_cache, allowed_files=allowed_files
    ):
        tree = tree  # narrow object payload back to ast.Module for local use
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                matched_module = _matching_imported_module(
                    py_file=py_file,
                    node=node,
                    module_names=frozenset({module_name}),
                )
                if matched_module == module_name:
                    violations.append(f"{rel_path}:{node.lineno} imports {module_name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module_name:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {module_name}"
                        )
    return violations


def _iter_module_import_violations_for_modules(
    ast_cache: dict[Path, ast.Module],
    *,
    module_names: frozenset[str],
    allowed_files: frozenset[Path],
) -> list[str]:
    """Collect module import violations for several modules in a single AST pass."""
    violations: list[str] = []
    for py_file, tree, rel_path in _iter_non_allowed_cache_items(
        ast_cache, allowed_files=allowed_files
    ):
        tree = tree
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                matched_module = _matching_imported_module(
                    py_file=py_file,
                    node=node,
                    module_names=module_names,
                )
                if matched_module is not None:
                    violations.append(
                        f"{rel_path}:{node.lineno} imports {matched_module}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in module_names:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {alias.name}"
                        )
    return violations


def _iter_symbol_mentions(
    content_cache: dict[Path, str],
    *,
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    return _iter_text_mentions(
        content_cache=content_cache,
        allowed_files=allowed_files,
        predicate=lambda line: symbol in line,
        render_message=lambda rel_path, lineno, _line: f"{rel_path}:{lineno} mentions {symbol}",
    )


def _iter_string_mentions(
    content_cache: dict[Path, str],
    *,
    needle: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    return _iter_text_mentions(
        content_cache=content_cache,
        allowed_files=allowed_files,
        predicate=lambda line: needle in line,
        render_message=lambda rel_path, lineno, _line: f"{rel_path}:{lineno} mentions {needle}",
    )


def _iter_text_symbol_mentions(
    *,
    files: frozenset[Path],
    symbol: str,
) -> list[str]:
    violations: list[str] = []
    for file_path in sorted(files):
        rel_path = _relative_to_root(file_path)
        for lineno, line in enumerate(
            file_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if symbol in line:
                violations.append(f"{rel_path}:{lineno} mentions {symbol}")
    return violations


def _iter_imported_symbol_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    module_names: frozenset[str],
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for _py_file, tree, rel_path in _iter_non_allowed_cache_items(
        ast_cache, allowed_files=allowed_files
    ):
        tree = tree
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module not in module_names:
                continue
            for alias in node.names:
                if alias.name != symbol:
                    continue
                violations.append(
                    f"{rel_path}:{node.lineno} imports {symbol} from {node.module}"
                )
    return violations


def _iter_call_keyword_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    call_name: str,
    keyword_names: frozenset[str],
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for _py_file, tree, rel_path in _iter_non_allowed_cache_items(
        ast_cache, allowed_files=allowed_files
    ):
        tree = tree
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target_name: str | None = None
            if isinstance(node.func, ast.Name):
                target_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                target_name = node.func.attr
            if target_name != call_name:
                continue
            used_keywords = {
                keyword.arg for keyword in node.keywords if keyword.arg is not None
            }
            matched_keywords = sorted(used_keywords.intersection(keyword_names))
            if matched_keywords:
                violations.append(
                    f"{rel_path}:{node.lineno} uses {call_name} legacy keywords "
                    f"{matched_keywords}"
                )
    return violations


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_file_has_been_removed() -> None:
    """Legacy base-transformer dependency shim should no longer exist."""
    assert not TRANSFORMER_DEPENDENCY_SHIM_PATH.exists(), (
        "Legacy base-transformer dependency shim must stay removed: "
        "src/bioetl/application/core/base_transformer/dependencies.py"
    )


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must use canonical base-transformer dependency types directly."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "base_transformer dependency compatibility shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed dependency shim."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "base_transformer dependency compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_cli_registry_helper_module_is_confined_to_cli_src_entrypoints(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Compatibility CLI registry helper must not leak outside the CLI perimeter."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=CLI_REGISTRY_HELPER_MODULE,
        allowed_files=ALLOWED_CLI_REGISTRY_HELPER_SRC_FILES,
    )
    assert not violations, (
        "CLI registry helper compatibility seam leaked beyond the known CLI src "
        "entrypoints:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_run_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should reach the run command through the retained public seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=RUN_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_RUN_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal run command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_run_command_internal_module_string_is_confined_to_retained_run_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal run-owner string references should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{RUN_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_RUN_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal run command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_run_all_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should reach run-all through the retained public seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=RUN_ALL_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_RUN_ALL_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal run-all command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_run_all_command_internal_module_string_is_confined_to_retained_run_all_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal run-all owner string references should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{RUN_ALL_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_RUN_ALL_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal run-all command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_run_composite_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should reach run-composite through the retained public seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=RUN_COMPOSITE_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_RUN_COMPOSITE_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal run-composite command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_run_composite_command_internal_module_string_is_confined_to_retained_run_composite_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal run-composite owner string refs should stay inside retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{RUN_COMPOSITE_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_RUN_COMPOSITE_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal run-composite command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_health_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should reach health through the retained public seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=HEALTH_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_HEALTH_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal health command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_health_command_internal_module_string_is_confined_to_retained_health_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal health owner string references should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{HEALTH_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_HEALTH_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal health command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_quarantine_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should reach quarantine through the retained public seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=QUARANTINE_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_QUARANTINE_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal quarantine command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_quarantine_command_internal_module_string_is_confined_to_retained_quarantine_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal quarantine owner string refs should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{QUARANTINE_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_QUARANTINE_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal quarantine command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_maintenance_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should reach maintenance through the retained public seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=MAINTENANCE_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_MAINTENANCE_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal maintenance command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_maintenance_command_internal_module_string_is_confined_to_retained_maintenance_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal maintenance owner string refs should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{MAINTENANCE_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_MAINTENANCE_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal maintenance command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_archive_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should keep archive-owner imports confined to maintenance internals."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=ARCHIVE_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_ARCHIVE_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal archive command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_archive_command_internal_module_string_is_confined_to_retained_archive_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal archive owner string refs should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{ARCHIVE_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_ARCHIVE_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal archive command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_cleanup_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should keep cleanup-owner imports confined to maintenance internals."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=CLEANUP_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_CLEANUP_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal cleanup command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_cleanup_command_internal_module_string_is_confined_to_retained_cleanup_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal cleanup owner string refs should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{CLEANUP_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_CLEANUP_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal cleanup command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_vacuum_command_internal_module_is_not_imported_in_src_outside_owning_package(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should keep vacuum-owner imports confined to maintenance internals."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=VACUUM_COMMAND_INTERNAL_MODULE,
        allowed_files=ALLOWED_VACUUM_COMMAND_INTERNAL_SRC_FILES,
    )
    assert not violations, (
        "Internal vacuum command module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_vacuum_command_internal_module_string_is_confined_to_retained_vacuum_seam_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """Internal vacuum owner string refs should stay inside the retained seam."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{VACUUM_COMMAND_INTERNAL_MODULE}"',
        allowed_files=ALLOWED_VACUUM_COMMAND_INTERNAL_STRING_SRC_FILES,
    )
    assert not violations, (
        "Internal vacuum command module string references leaked into first-party src:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_test_facing_run_helper_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import canonical domains.run helper modules directly."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=TEST_FACING_RUN_HELPER_SEAM_MODULES,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Test-facing run helper seams leaked into first-party src imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_test_facing_run_all_helper_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import canonical domains.run_all helper modules directly."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=TEST_FACING_RUN_ALL_HELPER_SEAM_MODULES,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Test-facing run-all helper seams leaked into first-party src imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_test_facing_run_composite_helper_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import canonical domains.composite helpers directly."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=TEST_FACING_RUN_COMPOSITE_HELPER_SEAM_MODULES,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Test-facing run-composite helper seams leaked into first-party src imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_test_facing_quarantine_helper_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import canonical domains.quarantine helpers directly."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=TEST_FACING_QUARANTINE_HELPER_SEAM_MODULES,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Test-facing quarantine helper seams leaked into first-party src imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_test_facing_health_helper_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import canonical domains.health helpers directly."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=TEST_FACING_HEALTH_HELPER_SEAM_MODULES,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Test-facing health helper seams leaked into first-party src imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_test_facing_shared_cli_policy_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import canonical shared CLI policy modules directly."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=TEST_FACING_SHARED_CLI_POLICY_SEAM_MODULES,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Test-facing shared CLI policy seams leaked into first-party src imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_cli_registry_helper_get_default_registry_import_is_absent_from_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src should import the canonical builder, not the compat alias."""
    violations = _iter_imported_symbol_violations(
        source_ast_cache,
        module_names=frozenset({CLI_REGISTRY_HELPER_MODULE}),
        symbol="get_default_registry",
        allowed_files=frozenset(),
    )
    assert not violations, (
        "CLI src still imports registry_helpers.get_default_registry directly:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_cli_registry_helper_get_default_registry_import_is_absent_from_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests should patch local CLI compat seams, not import the registry-helper alias."""
    violations = _iter_imported_symbol_violations(
        test_ast_cache,
        module_names=frozenset({CLI_REGISTRY_HELPER_MODULE}),
        symbol="get_default_registry",
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Tests still import registry_helpers.get_default_registry directly:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_default_registry_import_is_confined_to_known_src_compatibility_seams(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Shared default-registry access must stay frozen to the current src seams."""
    violations = _iter_imported_symbol_violations(
        source_ast_cache,
        module_names=frozenset({"bioetl.composition.registry"}),
        symbol="get_default_registry",
        allowed_files=ALLOWED_COMPOSITION_DEFAULT_REGISTRY_SRC_FILES,
    )
    assert not violations, (
        "composition.registry.get_default_registry leaked into new src call sites:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_registry_module_imports_are_confined_to_canonical_and_compat_src_seams(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Direct registry-module imports in src must stay confined to known seams."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name="bioetl.composition.registry",
        allowed_files=ALLOWED_COMPOSITION_REGISTRY_MODULE_SRC_FILES,
    )
    assert not violations, (
        "Direct src imports of bioetl.composition.registry leaked beyond the "
        "canonical package-root and compatibility seams:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_default_registry_import_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Ordinary tests must not accumulate new direct imports of default registry access."""
    violations = _iter_imported_symbol_violations(
        test_ast_cache,
        module_names=frozenset({"bioetl.composition.registry"}),
        symbol="get_default_registry",
        allowed_files=ALLOWED_COMPOSITION_DEFAULT_REGISTRY_TEST_FILES,
    )
    assert not violations, (
        "composition.registry.get_default_registry leaked into new test call sites:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_registry_module_imports_are_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must treat bioetl.composition.registry as a dedicated compat seam."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name="bioetl.composition.registry",
        allowed_files=ALLOWED_COMPOSITION_REGISTRY_MODULE_TEST_FILES,
    )
    assert not violations, (
        "Direct test imports of bioetl.composition.registry leaked beyond dedicated "
        "registry compatibility coverage:\n" + "\n".join(violations)
    )
