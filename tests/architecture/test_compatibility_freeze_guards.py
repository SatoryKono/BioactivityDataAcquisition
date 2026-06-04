"""Compatibility-freeze guardrails for shim imports and symbols."""

from __future__ import annotations

import ast
from datetime import date
from importlib import import_module
from pathlib import Path
import subprocess

import pytest

from scripts.engineering.qa.file_discovery import discover_files

ROOT = Path(__file__).resolve().parents[2]
SUNSET_DATE = date(2026, 6, 30)
POLICY_REVIEW_DATE = date(2026, 5, 15)
LEGACY_DATASOURCE_FACTORY_MODULE = "bioetl.composition.factories.datasource.factory"
INTERNAL_COMPOSITION_ENTRYPOINT_MODULES = (
    "bioetl.composition._pipeline_execution",
    "bioetl.composition._resource_management",
    "bioetl.composition._services",
)
COMPOSITION_BOOTSTRAP_FACADE_MODULE = "bioetl.composition.bootstrap"
COMPOSITION_SERVICES_API_MODULE = "bioetl.composition.services_api"
SERVICE_BOOTSTRAPS_COMPAT_MODULE = "bioetl.composition._service_bootstraps"
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
REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE = (
    "bioetl.application.services.checkpoint_compatibility_service_v2"
)
REMOVED_CHECKPOINT_COMPATIBILITY_V2_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "checkpoint_compatibility_service_v2.py"
)
BASE_PIPELINE_CONFIG = ROOT / "configs" / "base" / "pipeline.yaml"
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
MAINTENANCE_COMMAND_INTERNAL_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "domains"
    / "maintenance"
    / "command.py"
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
TEST_FACING_QUARANTINE_HELPER_SEAM_MODULES = frozenset()
TEST_FACING_HEALTH_HELPER_SEAM_MODULES = frozenset()
TEST_FACING_SHARED_CLI_POLICY_SEAM_MODULES: frozenset[str] = frozenset()
APPLICATION_SERVICES_PACKAGE_ROOT_MODULE = "bioetl.application.services"
APPLICATION_SERVICES_PACKAGE_ROOT_PATH = (
    ROOT / "src" / "bioetl" / "application" / "services" / "__init__.py"
)
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
BIOETL_PACKAGE_INIT_PATH = ROOT / "src" / "bioetl" / "__init__.py"
COMPOSITION_PACKAGE_INIT_PATH = ROOT / "src" / "bioetl" / "composition" / "__init__.py"
COMPOSITION_BOOTSTRAP_INIT_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "__init__.py"
)
SERVICE_BOOTSTRAPS_COMPAT_MODULE_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "_service_bootstraps.py"
)
CLI_RUN_COMMAND_PATH = (
    ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run.py"
)
CLI_RUN_SERVICE_ACCESS_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "domains"
    / "run"
    / "service_access.py"
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
REMOVED_COMPAT_MODULES: dict[str, Path] = {
    "application services cli_run_orchestration_service facade": Path(
        "src/bioetl/application/services/cli_run_orchestration_service.py"
    ),
    "application services cli_run_orchestration_contracts facade": Path(
        "src/bioetl/application/services/cli_run_orchestration_contracts.py"
    ),
    "application services cli_run_orchestration_models facade": Path(
        "src/bioetl/application/services/cli_run_orchestration_models.py"
    ),
    "application services lineage_inspection_service facade": Path(
        "src/bioetl/application/services/lineage_inspection_service.py"
    ),
    "application services metadata_coordinator facade": Path(
        "src/bioetl/application/services/metadata_coordinator.py"
    ),
    "application services run_ledger_service facade": Path(
        "src/bioetl/application/services/run_ledger_service.py"
    ),
    "application services run_manifest_inspection_service facade": Path(
        "src/bioetl/application/services/run_manifest_inspection_service.py"
    ),
    "application services pipeline_run_context_service facade": Path(
        "src/bioetl/application/services/pipeline_run_context_service.py"
    ),
    "application services pipeline_run_execution_service facade": Path(
        "src/bioetl/application/services/pipeline_run_execution_service.py"
    ),
    "application services pipeline_run_lifecycle_service facade": Path(
        "src/bioetl/application/services/pipeline_run_lifecycle_service.py"
    ),
    "application services pipeline_runner_models facade": Path(
        "src/bioetl/application/services/pipeline_runner_models.py"
    ),
    "application services pipeline_runner_service facade": Path(
        "src/bioetl/application/services/pipeline_runner_service.py"
    ),
    "application services checkpoint_compatibility_runtime facade": Path(
        "src/bioetl/application/services/checkpoint_compatibility_runtime.py"
    ),
    "application services run_manifest_diagnostics facade": Path(
        "src/bioetl/application/services/run_manifest_diagnostics.py"
    ),
    "application services effective_config_service facade": Path(
        "src/bioetl/application/services/effective_config_service.py"
    ),
    "application services run_manifest_service facade": Path(
        "src/bioetl/application/services/run_manifest_service.py"
    ),
    "cli inspection_output compat wrapper": Path(
        "src/bioetl/interfaces/cli/commands/inspection_output.py"
    ),
    "cli run_manifest_output compat wrapper": Path(
        "src/bioetl/interfaces/cli/commands/run_manifest_output.py"
    ),
    "cli maintenance plan facade": Path("src/bioetl/interfaces/cli/commands/plan.py"),
    "aggregate_port.py (StoragePort)": Path(
        "src/bioetl/domain/ports/storage/aggregate_port.py"
    ),
    "domain normalization_authors compat wrapper": Path(
        "src/bioetl/domain/normalization_authors.py"
    ),
    "domain normalization_pages compat wrapper": Path(
        "src/bioetl/domain/normalization_pages.py"
    ),
    "domain normalization_dates compat wrapper": Path(
        "src/bioetl/domain/normalization_dates.py"
    ),
    "domain normalization_chembl compat wrapper": Path(
        "src/bioetl/domain/normalization_chembl.py"
    ),
    "domain publication_field_groups facade": Path(
        "src/bioetl/domain/value_objects/publication_field_groups.py"
    ),
    "domain services doi_normalization compat wrapper": Path(
        "src/bioetl/domain/services/doi_normalization.py"
    ),
    "domain services pmid_normalization compat wrapper": Path(
        "src/bioetl/domain/services/pmid_normalization.py"
    ),
    "domain services date_normalization compat wrapper": Path(
        "src/bioetl/domain/services/date_normalization.py"
    ),
    "domain services text_normalization compat wrapper": Path(
        "src/bioetl/domain/services/text_normalization.py"
    ),
    "domain services _date_helpers compat wrapper": Path(
        "src/bioetl/domain/services/_date_helpers.py"
    ),
    "application checkpoint legacy wrapper": Path(
        "src/bioetl/application/core/lifecycle/_checkpoint_legacy.py"
    ),
    "cli run-all internal command wrapper": Path(
        "src/bioetl/interfaces/cli/commands/domains/run_all/command.py"
    ),
    "application core batch execution lifecycle flat facade": Path(
        "src/bioetl/application/core/batch_execution_lifecycle.py"
    ),
    "application core batch execution run service flat facade": Path(
        "src/bioetl/application/core/batch_execution_run_service.py"
    ),
    "application core pipeline registry wiring flat facade": Path(
        "src/bioetl/application/core/pipeline_registry_wiring_api.py"
    ),
    "application core runtime wiring flat facade": Path(
        "src/bioetl/application/core/runtime_wiring_api.py"
    ),
    "application core transformer wiring flat facade": Path(
        "src/bioetl/application/core/transformer_wiring_api.py"
    ),
}


def _find_candidate_importer_files(
    root: Path, module_name: str, leaf_name: str
) -> list[Path]:
    try:
        root_spec = root.relative_to(ROOT).as_posix()
    except ValueError:
        return []
    command = [
        "git",
        "-C",
        ROOT.as_posix(),
        "grep",
        "-I",
        "-l",
        "-F",
        "--no-color",
        "-e",
        module_name,
        "-e",
        leaf_name,
        "--",
        root_spec,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return [
            root / relative_path
            for relative_path in discover_files(str(root.resolve()), ".py")
        ]
    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        return [
            root / relative_path
            for relative_path in discover_files(str(root.resolve()), ".py")
        ]
    return [
        ROOT / line
        for line in completed.stdout.splitlines()
        if line.strip() and Path(line).suffix == ".py"
    ]


def _find_importers(root: Path, module_name: str) -> list[str]:
    violations: list[str] = []
    parent_module, _, leaf_name = module_name.rpartition(".")
    for path in _find_candidate_importer_files(root, module_name, leaf_name):
        text = path.read_text(encoding="utf-8")
        if module_name not in text and leaf_name not in text:
            continue
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
                if module_name in names:
                    violations.append(path.relative_to(ROOT).as_posix())
                    break
            if isinstance(node, ast.ImportFrom):
                imported_names = {alias.name for alias in node.names}
                if node.module == module_name or (
                    node.module == parent_module and leaf_name in imported_names
                ):
                    violations.append(path.relative_to(ROOT).as_posix())
                    break
    return violations


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
    }
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_PIPELINE_RUNNER_SERVICE_MODEL_IMPORT_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "application" / "services" / "__init__.py",
    }
)
ALLOWED_INTERNAL_ENTRYPOINT_TEST_FILES_BY_MODULE = {
    "bioetl.composition._pipeline_execution": frozenset(
        {
            ROOT / "tests" / "unit" / "composition" / "test_entrypoints.py",
            ROOT / "tests" / "unit" / "composition" / "test_execution_api_contract.py",
            ROOT
            / "tests"
            / "unit"
            / "composition"
            / "test_maintenance_api_contract.py",
            ROOT / "tests" / "unit" / "composition" / "test_resources_api_contract.py",
        }
    ),
    "bioetl.composition._resource_management": frozenset(
        {
            ROOT / "tests" / "unit" / "composition" / "test_resource_management.py",
            ROOT / "tests" / "unit" / "composition" / "test_health_api_contract.py",
            ROOT
            / "tests"
            / "unit"
            / "composition"
            / "test_maintenance_api_contract.py",
            ROOT / "tests" / "unit" / "composition" / "test_resources_api_contract.py",
        }
    ),
    "bioetl.composition._services": frozenset(
        {
            ROOT / "tests" / "unit" / "composition" / "test_services_entrypoints.py",
            ROOT / "tests" / "unit" / "composition" / "test_observability_api.py",
            ROOT
            / "tests"
            / "unit"
            / "composition"
            / "test_maintenance_api_contract.py",
            ROOT / "tests" / "unit" / "composition" / "test_resources_api_contract.py",
        }
    ),
}
ALLOWED_RUN_COMMAND_INTERNAL_SRC_FILES: frozenset[Path] = frozenset()
ALLOWED_RUN_COMMAND_INTERNAL_STRING_SRC_FILES: frozenset[Path] = frozenset()
ALLOWED_RUN_ALL_COMMAND_INTERNAL_SRC_FILES = frozenset()
ALLOWED_RUN_ALL_COMMAND_INTERNAL_STRING_SRC_FILES = frozenset()
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
        ROOT / "src" / "bioetl" / "composition" / "registry_api.py",
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


def _iter_matching_import_nodes(
    tree: ast.Module,
    *,
    py_file: Path,
    module_names: frozenset[str],
) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            matched_module = _matching_imported_module(
                py_file=py_file,
                node=node,
                module_names=module_names,
            )
            if matched_module is not None:
                matches.append((node.lineno, matched_module))
            continue
        if isinstance(node, ast.Import):
            matches.extend(
                (node.lineno, alias.name)
                for alias in node.names
                if alias.name in module_names
            )
    return matches


def _iter_imported_symbol_matches(
    tree: ast.Module,
    *,
    module_names: frozenset[str],
    symbol: str,
) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module not in module_names:
            continue
        if any(alias.name == symbol for alias in node.names):
            matches.append((node.lineno, node.module))
    return matches


def _iter_module_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    module_name: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    return _iter_module_import_violations_for_modules(
        ast_cache,
        module_names=frozenset({module_name}),
        allowed_files=allowed_files,
    )


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
        for lineno, matched_module in _iter_matching_import_nodes(
            tree,
            py_file=py_file,
            module_names=module_names,
        ):
            violations.append(f"{rel_path}:{lineno} imports {matched_module}")
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
        render_message=lambda rel_path, lineno, _line: (
            f"{rel_path}:{lineno} mentions {symbol}"
        ),
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
        render_message=lambda rel_path, lineno, _line: (
            f"{rel_path}:{lineno} mentions {needle}"
        ),
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
        for lineno, module_name in _iter_imported_symbol_matches(
            tree,
            module_names=module_names,
            symbol=symbol,
        ):
            violations.append(
                f"{rel_path}:{lineno} imports {symbol} from {module_name}"
            )
    return violations


def _call_target_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _matched_call_keywords(
    node: ast.Call,
    *,
    call_name: str,
    keyword_names: frozenset[str],
) -> list[str]:
    if _call_target_name(node) != call_name:
        return []
    used_keywords = {
        keyword.arg for keyword in node.keywords if keyword.arg is not None
    }
    return sorted(used_keywords.intersection(keyword_names))


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
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            matched_keywords = _matched_call_keywords(
                node,
                call_name=call_name,
                keyword_names=keyword_names,
            )
            if matched_keywords:
                violations.append(
                    f"{rel_path}:{node.lineno} uses {call_name} legacy keywords "
                    f"{matched_keywords}"
                )
    return violations


def _assert_no_violations(violations: list[str], failure_message: str) -> None:
    """Assert violation lists with one consistent failure rendering."""
    assert not violations, failure_message + "\n" + "\n".join(violations)


def _assignment_target_names(node: ast.Assign) -> frozenset[str]:
    return frozenset(
        target.id for target in node.targets if isinstance(target, ast.Name)
    )


def _ann_assignment_matches(node: ast.AnnAssign, assignment_name: str) -> bool:
    return isinstance(node.target, ast.Name) and node.target.id == assignment_name


def _literal_assignment_value(node: ast.stmt, assignment_name: str) -> ast.expr | None:
    if isinstance(node, ast.Assign):
        if assignment_name in _assignment_target_names(node):
            return node.value
        return None
    if isinstance(node, ast.AnnAssign) and _ann_assignment_matches(
        node, assignment_name
    ):
        return node.value
    return None


def _literal_names_from_value(value: ast.expr) -> frozenset[str]:
    if isinstance(value, ast.Dict):
        return frozenset(
            key.value
            for key in value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        )
    if isinstance(value, ast.List | ast.Tuple | ast.Set):
        return frozenset(
            item.value
            for item in value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        )
    if isinstance(value, ast.Call):
        # Handle frozenset({...}) and similar calls
        if len(value.args) == 1:
            return _literal_names_from_value(value.args[0])
    return frozenset()


def _literal_assignment_names(path: Path, assignment_name: str) -> frozenset[str]:
    """Return string keys/items assigned to a module-level literal."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        value = _literal_assignment_value(node, assignment_name)
        if value is None:
            continue
        return _literal_names_from_value(value)
    raise AssertionError(f"{path} missing module-level {assignment_name}")


def _resolve_cache_fixture(
    request: pytest.FixtureRequest,
    cache_fixture_name: str,
) -> dict[Path, ast.Module]:
    """Resolve one AST cache fixture by name for parametrized seam checks."""
    return request.getfixturevalue(cache_fixture_name)


_MODULE_IMPORT_SCOPE_CASES = (
    pytest.param(
        "src",
        "source_ast_cache",
        TRANSFORMER_DEPENDENCY_SHIM,
        frozenset(),
        "base_transformer dependency compatibility shim is still imported from src/:",
        id="transformer-shim-src",
    ),
    pytest.param(
        "tests",
        "test_ast_cache",
        TRANSFORMER_DEPENDENCY_SHIM,
        frozenset(),
        "base_transformer dependency compatibility shim must stay removed from tests:",
        id="transformer-shim-tests",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        CLI_REGISTRY_HELPER_MODULE,
        ALLOWED_CLI_REGISTRY_HELPER_SRC_FILES,
        "CLI registry helper compatibility seam leaked beyond the known CLI src entrypoints:",
        id="cli-registry-helper-src",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        RUN_COMMAND_INTERNAL_MODULE,
        ALLOWED_RUN_COMMAND_INTERNAL_SRC_FILES,
        "Internal run command module leaked into first-party src imports:",
        id="run",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        RUN_ALL_COMMAND_INTERNAL_MODULE,
        ALLOWED_RUN_ALL_COMMAND_INTERNAL_SRC_FILES,
        "Internal run-all command module leaked into first-party src imports:",
        id="run-all",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        RUN_COMPOSITE_COMMAND_INTERNAL_MODULE,
        ALLOWED_RUN_COMPOSITE_COMMAND_INTERNAL_SRC_FILES,
        "Internal run-composite command module leaked into first-party src imports:",
        id="run-composite",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        HEALTH_COMMAND_INTERNAL_MODULE,
        ALLOWED_HEALTH_COMMAND_INTERNAL_SRC_FILES,
        "Internal health command module leaked into first-party src imports:",
        id="health",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        QUARANTINE_COMMAND_INTERNAL_MODULE,
        ALLOWED_QUARANTINE_COMMAND_INTERNAL_SRC_FILES,
        "Internal quarantine command module leaked into first-party src imports:",
        id="quarantine",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        MAINTENANCE_COMMAND_INTERNAL_MODULE,
        ALLOWED_MAINTENANCE_COMMAND_INTERNAL_SRC_FILES,
        "Internal maintenance command module leaked into first-party src imports:",
        id="maintenance",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        ARCHIVE_COMMAND_INTERNAL_MODULE,
        ALLOWED_ARCHIVE_COMMAND_INTERNAL_SRC_FILES,
        "Internal archive command module leaked into first-party src imports:",
        id="archive",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        CLEANUP_COMMAND_INTERNAL_MODULE,
        ALLOWED_CLEANUP_COMMAND_INTERNAL_SRC_FILES,
        "Internal cleanup command module leaked into first-party src imports:",
        id="cleanup",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        VACUUM_COMMAND_INTERNAL_MODULE,
        ALLOWED_VACUUM_COMMAND_INTERNAL_SRC_FILES,
        "Internal vacuum command module leaked into first-party src imports:",
        id="vacuum",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        APPLICATION_SERVICES_PACKAGE_ROOT_MODULE,
        frozenset({APPLICATION_SERVICES_PACKAGE_ROOT_PATH}),
        (
            "First-party src must import application services from semantic "
            "subpackages or concrete owner modules instead of the package-root "
            "lazy compatibility facade:"
        ),
        id="application-services-package-root-src",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        "bioetl.composition.registry",
        ALLOWED_COMPOSITION_REGISTRY_MODULE_SRC_FILES,
        (
            "Direct src imports of bioetl.composition.registry leaked beyond the "
            "canonical package-root and compatibility seams:"
        ),
        id="registry-module-src",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        COMPOSITION_BOOTSTRAP_FACADE_MODULE,
        frozenset(),
        (
            "First-party src must import canonical bootstrap owners "
            "(`bootstrap.runtime`, `bootstrap.cli`, or `bootstrap.assembly`) "
            "instead of the package-level bootstrap facade:"
        ),
        id="composition-bootstrap-facade-src",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        COMPOSITION_SERVICES_API_MODULE,
        frozenset(),
        (
            "First-party src must use narrow composition APIs or internal "
            "composition owners instead of the compatibility services_api facade:"
        ),
        id="composition-services-api-src",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        SERVICE_BOOTSTRAPS_COMPAT_MODULE,
        frozenset(),
        "_service_bootstraps compatibility wrapper imports must stay removed from src:",
        id="service-bootstraps-src",
    ),
    pytest.param(
        "tests",
        "test_ast_cache",
        SERVICE_BOOTSTRAPS_COMPAT_MODULE,
        frozenset(),
        "_service_bootstraps compatibility wrapper imports must stay removed from tests:",
        id="service-bootstraps-tests",
    ),
    pytest.param(
        "tests",
        "test_ast_cache",
        "bioetl.composition.registry",
        ALLOWED_COMPOSITION_REGISTRY_MODULE_TEST_FILES,
        (
            "Direct test imports of bioetl.composition.registry leaked beyond "
            "dedicated registry compatibility coverage:"
        ),
        id="registry-module-tests",
    ),
)

_INTERNAL_CLI_MODULE_STRING_CASES = (
    pytest.param(
        RUN_COMMAND_INTERNAL_MODULE,
        ALLOWED_RUN_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal run command module string references leaked into first-party src:",
        id="run",
    ),
    pytest.param(
        RUN_ALL_COMMAND_INTERNAL_MODULE,
        ALLOWED_RUN_ALL_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal run-all command module string references leaked into first-party src:",
        id="run-all",
    ),
    pytest.param(
        RUN_COMPOSITE_COMMAND_INTERNAL_MODULE,
        ALLOWED_RUN_COMPOSITE_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal run-composite command module string references leaked into first-party src:",
        id="run-composite",
    ),
    pytest.param(
        HEALTH_COMMAND_INTERNAL_MODULE,
        ALLOWED_HEALTH_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal health command module string references leaked into first-party src:",
        id="health",
    ),
    pytest.param(
        QUARANTINE_COMMAND_INTERNAL_MODULE,
        ALLOWED_QUARANTINE_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal quarantine command module string references leaked into first-party src:",
        id="quarantine",
    ),
    pytest.param(
        MAINTENANCE_COMMAND_INTERNAL_MODULE,
        ALLOWED_MAINTENANCE_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal maintenance command module string references leaked into first-party src:",
        id="maintenance",
    ),
    pytest.param(
        ARCHIVE_COMMAND_INTERNAL_MODULE,
        ALLOWED_ARCHIVE_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal archive command module string references leaked into first-party src:",
        id="archive",
    ),
    pytest.param(
        CLEANUP_COMMAND_INTERNAL_MODULE,
        ALLOWED_CLEANUP_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal cleanup command module string references leaked into first-party src:",
        id="cleanup",
    ),
    pytest.param(
        VACUUM_COMMAND_INTERNAL_MODULE,
        ALLOWED_VACUUM_COMMAND_INTERNAL_STRING_SRC_FILES,
        "Internal vacuum command module string references leaked into first-party src:",
        id="vacuum",
    ),
)

_TEST_FACING_HELPER_SEAM_CASES = (
    pytest.param(
        TEST_FACING_RUN_HELPER_SEAM_MODULES,
        "Test-facing run helper seams leaked into first-party src imports:",
        id="run",
    ),
    pytest.param(
        TEST_FACING_RUN_ALL_HELPER_SEAM_MODULES,
        "Test-facing run-all helper seams leaked into first-party src imports:",
        id="run-all",
    ),
    pytest.param(
        TEST_FACING_RUN_COMPOSITE_HELPER_SEAM_MODULES,
        "Test-facing run-composite helper seams leaked into first-party src imports:",
        id="run-composite",
    ),
    pytest.param(
        TEST_FACING_QUARANTINE_HELPER_SEAM_MODULES,
        "Test-facing quarantine helper seams leaked into first-party src imports:",
        id="quarantine",
    ),
    pytest.param(
        TEST_FACING_HEALTH_HELPER_SEAM_MODULES,
        "Test-facing health helper seams leaked into first-party src imports:",
        id="health",
    ),
    pytest.param(
        TEST_FACING_SHARED_CLI_POLICY_SEAM_MODULES,
        "Test-facing shared CLI policy seams leaked into first-party src imports:",
        id="shared-cli-policy",
    ),
)

_IMPORTED_SYMBOL_SCOPE_CASES = (
    pytest.param(
        "src",
        "source_ast_cache",
        frozenset({CLI_REGISTRY_HELPER_MODULE}),
        "get_default_registry",
        frozenset(),
        "CLI src still imports registry_helpers.get_default_registry directly:",
        id="cli-registry-helper-src",
    ),
    pytest.param(
        "tests",
        "test_ast_cache",
        frozenset({CLI_REGISTRY_HELPER_MODULE}),
        "get_default_registry",
        frozenset(),
        "Tests still import registry_helpers.get_default_registry directly:",
        id="cli-registry-helper-tests",
    ),
    pytest.param(
        "src",
        "source_ast_cache",
        frozenset({"bioetl.composition.registry"}),
        "get_default_registry",
        ALLOWED_COMPOSITION_DEFAULT_REGISTRY_SRC_FILES,
        ("composition.registry.get_default_registry leaked into new src call sites:"),
        id="default-registry-src",
    ),
    pytest.param(
        "tests",
        "test_ast_cache",
        frozenset({"bioetl.composition.registry"}),
        "get_default_registry",
        ALLOWED_COMPOSITION_DEFAULT_REGISTRY_TEST_FILES,
        ("composition.registry.get_default_registry leaked into new test call sites:"),
        id="default-registry-tests",
    ),
)


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_file_has_been_removed() -> None:
    """Legacy base-transformer dependency shim should no longer exist."""
    assert not TRANSFORMER_DEPENDENCY_SHIM_PATH.exists(), (
        "Legacy base-transformer dependency shim must stay removed: "
        "src/bioetl/application/core/base_transformer/dependencies.py"
    )


@pytest.mark.architecture
def test_cli_run_orchestration_singleton_stays_private_compat_owner() -> None:
    """The CLI run singleton may exist only as a retained compatibility accessor."""
    allowed_path = CLI_RUN_SERVICE_ACCESS_PATH
    offenders: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        if path != allowed_path and any(
            isinstance(node, ast.Name) and node.id == "_cli_run_orchestration_service"
            for node in ast.walk(tree)
        ):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert not offenders, (
        "CLI run orchestration singleton leaked outside private service_access.py:\n"
        + "\n".join(offenders)
    )

    run_source = CLI_RUN_COMMAND_PATH.read_text(encoding="utf-8")
    assert "service = create_cli_run_orchestration_service()" in run_source, (
        "Runtime CLI run command must build a fresh orchestration service."
    )
    assert "service = get_cli_run_orchestration_service()" not in run_source, (
        "Runtime CLI run command must not use the retained compatibility singleton."
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    (
        "scope_label",
        "cache_fixture_name",
        "module_name",
        "allowed_files",
        "failure_message",
    ),
    _MODULE_IMPORT_SCOPE_CASES,
)
def test_module_import_seams_are_confined(
    request: pytest.FixtureRequest,
    scope_label: str,
    cache_fixture_name: str,
    module_name: str,
    allowed_files: frozenset[Path],
    failure_message: str,
) -> None:
    """Module import seams must stay frozen to the known src and test call sites."""
    del scope_label
    ast_cache = _resolve_cache_fixture(request, cache_fixture_name)
    violations = _iter_module_import_violations(
        ast_cache,
        module_name=module_name,
        allowed_files=allowed_files,
    )
    _assert_no_violations(violations, failure_message)


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("module_name", "allowed_files", "failure_message"),
    _INTERNAL_CLI_MODULE_STRING_CASES,
)
def test_internal_cli_command_strings_are_confined_to_known_src_seams(
    source_content_cache: dict[Path, str],
    module_name: str,
    allowed_files: frozenset[Path],
    failure_message: str,
) -> None:
    """Internal CLI command-owner strings should stay inside retained src seams."""
    violations = _iter_string_mentions(
        source_content_cache,
        needle=f'"{module_name}"',
        allowed_files=allowed_files,
    )
    assert not violations, failure_message + "\n" + "\n".join(violations)


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("module_names", "failure_message"),
    _TEST_FACING_HELPER_SEAM_CASES,
)
def test_test_facing_helper_seams_are_not_imported_in_first_party_src(
    source_ast_cache: dict[Path, ast.Module],
    module_names: frozenset[str],
    failure_message: str,
) -> None:
    """First-party src should not accumulate imports of test-facing helper seams."""
    violations = _iter_module_import_violations_for_modules(
        source_ast_cache,
        module_names=module_names,
        allowed_files=frozenset(),
    )
    assert not violations, failure_message + "\n" + "\n".join(sorted(violations))


@pytest.mark.architecture
@pytest.mark.parametrize(
    (
        "scope_label",
        "cache_fixture_name",
        "module_names",
        "symbol",
        "allowed_files",
        "failure_message",
    ),
    _IMPORTED_SYMBOL_SCOPE_CASES,
)
def test_imported_symbol_seams_are_confined(
    request: pytest.FixtureRequest,
    scope_label: str,
    cache_fixture_name: str,
    module_names: frozenset[str],
    symbol: str,
    allowed_files: frozenset[Path],
    failure_message: str,
) -> None:
    """Imported symbol seams must stay frozen to the known src and test sites."""
    del scope_label
    ast_cache = _resolve_cache_fixture(request, cache_fixture_name)
    violations = _iter_imported_symbol_violations(
        ast_cache,
        module_names=module_names,
        symbol=symbol,
        allowed_files=allowed_files,
    )
    _assert_no_violations(violations, failure_message)


@pytest.mark.architecture
def test_package_level_lazy_proxy_surfaces_stay_frozen() -> None:
    """Package-level proxy exports must not grow without an explicit policy change."""
    bioetl_text = BIOETL_PACKAGE_INIT_PATH.read_text(encoding="utf-8")
    assert "__getattr__" not in bioetl_text
    assert _literal_assignment_names(BIOETL_PACKAGE_INIT_PATH, "__all__") == {
        "__version__"
    }

    assert _literal_assignment_names(
        COMPOSITION_PACKAGE_INIT_PATH, "_LAZY_MODULE_EXPORTS"
    ) == {
        "composite_api",
        "control_plane_api",
        "entrypoints",
        "execution_api",
        "health_api",
        "maintenance_api",
        "observability_api",
        "registry_api",
        "resources_api",
        "types",
    }
    assert _literal_assignment_names(
        COMPOSITION_PACKAGE_INIT_PATH, "_LAZY_ATTR_EXPORTS"
    ) == {
        "PipelineDefinition",
        "PipelineRegistry",
        "create_registry",
        "get_default_registry",
    }

    expected_bootstrap_exports = {
        "bootstrap_composite_runner",
        "bootstrap_dq_monitor",
        "bootstrap_logger",
        "bootstrap_metrics",
        "bootstrap_observability_bundle",
        "bootstrap_pipeline_runner",
        "bootstrap_tracer",
        "load_composite_config",
        "load_pipeline_config",
        "maybe_start_metrics_server",
    }
    assert (
        _literal_assignment_names(COMPOSITION_BOOTSTRAP_INIT_PATH, "__all__")
        == expected_bootstrap_exports
    )
    assert (
        _literal_assignment_names(COMPOSITION_BOOTSTRAP_INIT_PATH, "_PUBLIC_EXPORTS")
        == expected_bootstrap_exports
    )


@pytest.mark.architecture
def test_service_bootstraps_compat_wrapper_file_stays_removed() -> None:
    """The retired `_service_bootstraps` wrapper module must not be reintroduced."""
    assert not SERVICE_BOOTSTRAPS_COMPAT_MODULE_PATH.exists()


@pytest.mark.architecture
def test_retired_run_command_wrapper_and_placeholder_package_stay_absent() -> None:
    """Collapsed run-command seams and retired placeholder packages must not return."""
    retired_paths = (
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "run"
        / "command.py",
        ROOT / "src" / "bioetl" / "interfaces" / "orchestration",
    )
    assert not [path for path in retired_paths if path.exists()], (
        "Retired run-command wrapper or placeholder orchestration package returned:\n"
        + "\n".join(
            sorted(
                path.relative_to(ROOT).as_posix()
                for path in retired_paths
                if path.exists()
            )
        )
    )


@pytest.mark.architecture
def test_selected_public_runtime_facades_do_not_mutate_module_globals() -> None:
    """Retained public runtime facades must not cache exports via globals mutation."""
    targets = (
        ROOT / "src" / "bioetl" / "composition" / "entrypoints.py",
        ROOT / "src" / "bioetl" / "composition" / "execution_api.py",
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "__init__.py",
    )
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in targets
        if "globals()[name] =" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        "Mutable compatibility export caching must stay retired from public runtime "
        "facades:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize(
    "name,path",
    REMOVED_COMPAT_MODULES.items(),
    ids=REMOVED_COMPAT_MODULES.keys(),
)
def test_removed_compatibility_modules_stay_removed(name: str, path: Path) -> None:
    """Removed compatibility modules must not silently return."""
    assert not (ROOT / path).exists(), (
        f"Removed compatibility module {name} exists again at {path}. "
        "Use the canonical narrow-port or normalization surface instead."
    )


@pytest.mark.architecture
def test_checkpoint_compatibility_v2_surface_stays_removed_and_unimportable() -> None:
    """Removed checkpoint compatibility V2 surface must stay absent everywhere."""
    assert not REMOVED_CHECKPOINT_COMPATIBILITY_V2_PATH.exists()
    with pytest.raises(ModuleNotFoundError):
        import_module(REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE)
    assert not _find_importers(ROOT / "src", REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE)
    assert not _find_importers(
        ROOT / "tests", REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE
    )


@pytest.mark.architecture
def test_removed_maintenance_command_wrapper_stays_absent_and_unimportable() -> None:
    """Retired maintenance wrapper must stay absent everywhere."""
    assert not MAINTENANCE_COMMAND_INTERNAL_PATH.exists()
    with pytest.raises(ModuleNotFoundError):
        import_module(MAINTENANCE_COMMAND_INTERNAL_MODULE)


@pytest.mark.architecture
def test_removed_pipeline_base_yaml_fallback_surface_stays_absent() -> None:
    """Historical pipeline base fallback path must not silently return."""
    assert POLICY_REVIEW_DATE <= SUNSET_DATE
    text = BASE_PIPELINE_CONFIG.read_text(encoding="utf-8")
    assert "configs/pipelines/_base.yaml" not in text
    assert not (ROOT / "configs" / "pipelines").exists()
