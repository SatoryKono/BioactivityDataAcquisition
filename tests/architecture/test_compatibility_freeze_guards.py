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
SERVICES_CREATION_API_COMPAT_MODULE = (
    "bioetl.composition.factories.services.creation_api"
)
PIPELINE_RUNNER_SERVICE_MODULE = (
    "bioetl.application.services.pipeline_runner_service"
)
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
ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES: frozenset[Path] = frozenset()
ALLOWED_SERVICES_CREATION_API_TEST_FILES = frozenset(
    {
        ROOT / "tests" / "unit" / "composition" / "test_canonical_module_paths.py",
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
ALLOWED_CLI_REGISTRY_HELPER_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "__init__.py",
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "main.py",
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run_helpers.py",
        ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "run_all.py",
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


def _iter_module_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    module_name: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file, tree in sorted(ast_cache.items()):
        rel_path = _relative_to_root(py_file)
        if rel_path in allowed_rel_paths:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                is_absolute_match = node.module == module_name
                is_relative_match = False
                if node.level > 0:
                    module_parts = list(py_file.relative_to(ROOT).with_suffix("").parts)
                    current_package_parts = (
                        module_parts
                        if py_file.stem == "__init__"
                        else module_parts[:-1]
                    )
                    anchor_length = len(current_package_parts) - (node.level - 1)
                    if anchor_length > 0:
                        absolute_module = ".".join(
                            [
                                *current_package_parts[:anchor_length],
                                *node.module.split("."),
                            ]
                        )
                        is_relative_match = absolute_module == module_name
                if is_absolute_match or is_relative_match:
                    violations.append(f"{rel_path}:{node.lineno} imports {module_name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module_name:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {module_name}"
                        )
    return violations


def _iter_symbol_mentions(
    content_cache: dict[Path, str],
    *,
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file, content in sorted(content_cache.items()):
        rel_path = _relative_to_root(py_file)
        if rel_path in allowed_rel_paths:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if symbol in line:
                violations.append(f"{rel_path}:{lineno} mentions {symbol}")
    return violations


def _iter_string_mentions(
    content_cache: dict[Path, str],
    *,
    needle: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file, content in sorted(content_cache.items()):
        rel_path = _relative_to_root(py_file)
        if rel_path in allowed_rel_paths:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if needle in line:
                violations.append(f"{rel_path}:{lineno} mentions {needle}")
    return violations


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
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file, tree in sorted(ast_cache.items()):
        rel_path = _relative_to_root(py_file)
        if rel_path in allowed_rel_paths:
            continue
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
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file, tree in sorted(ast_cache.items()):
        rel_path = _relative_to_root(py_file)
        if rel_path in allowed_rel_paths:
            continue
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


@pytest.mark.architecture
def test_config_loader_compat_shim_file_has_been_removed() -> None:
    """Historical config_loader shim should remain deleted."""
    assert not CONFIG_LOADER_MODULE_PATH.exists(), (
        "Legacy config_loader compatibility shim must stay removed: "
        "src/bioetl/infrastructure/config_loader.py"
    )


@pytest.mark.architecture
def test_config_loader_module_is_absent_from_first_party_src_imports(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """New first-party src imports must use canonical config modules, not config_loader."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=CONFIG_LOADER_MODULE,
        allowed_files=ALLOWED_CONFIG_LOADER_SRC_FILES,
    )
    assert not violations, (
        "config_loader compatibility module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_config_loader_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed config_loader shim."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=CONFIG_LOADER_MODULE,
        allowed_files=ALLOWED_CONFIG_LOADER_TEST_FILES,
    )
    assert not violations, (
        "config_loader compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_services_creation_api_compat_module_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical pipeline creation symbols directly."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=SERVICES_CREATION_API_COMPAT_MODULE,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "services.creation_api compatibility shim leaked into first-party src "
        "imports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_services_creation_api_compat_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must treat services.creation_api as a dedicated compatibility seam."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=SERVICES_CREATION_API_COMPAT_MODULE,
        allowed_files=ALLOWED_SERVICES_CREATION_API_TEST_FILES,
    )
    assert not violations, (
        "services.creation_api compatibility shim leaked beyond dedicated tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    "symbol",
    ("RunOptions", "RunResult", "PipelineRunResult", "PipelineNotFoundError"),
)
def test_pipeline_runner_service_model_symbols_are_confined_to_package_re_exports_in_src(
    symbol: str,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import runner models from their canonical owner module."""
    violations = _iter_imported_symbol_violations(
        source_ast_cache,
        module_names=frozenset({PIPELINE_RUNNER_SERVICE_MODULE}),
        symbol=symbol,
        allowed_files=ALLOWED_PIPELINE_RUNNER_SERVICE_MODEL_IMPORT_SRC_FILES,
    )
    assert not violations, (
        "pipeline_runner_service model compatibility surface leaked into first-party "
        "src imports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_metadata_builder_compat_module_file_has_been_removed() -> None:
    """Historical storage metadata compat wrapper should remain deleted."""
    assert not METADATA_BUILDER_COMPAT_MODULE_PATH.exists(), (
        "Legacy storage metadata compat wrapper must stay removed: "
        "src/bioetl/infrastructure/storage/metadata_builder_composite_helpers.py"
    )


@pytest.mark.architecture
def test_metadata_builder_compat_module_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import composite metadata helpers from the domain seam."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=METADATA_BUILDER_COMPAT_MODULE,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "metadata_builder_composite_helpers leaked into first-party src/ imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_metadata_builder_compat_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed storage metadata compat wrapper."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=METADATA_BUILDER_COMPAT_MODULE,
        allowed_files=ALLOWED_METADATA_BUILDER_COMPAT_TEST_FILES,
    )
    assert not violations, (
        "metadata_builder_composite_helpers leaked beyond dedicated compatibility "
        "coverage:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_merge_service_legacy_keyword_wiring_does_not_expand_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Legacy MergeService keyword wiring must stay confined to the owning module."""
    violations = _iter_call_keyword_violations(
        source_ast_cache,
        call_name="MergeService",
        keyword_names=LEGACY_MERGE_SERVICE_KEYWORDS,
        allowed_files=ALLOWED_MERGE_SERVICE_SRC_FILES,
    )
    assert not violations, (
        "MergeService legacy collaborator keyword wiring leaked into new src call sites:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_datasource_registry_symbol_is_confined_to_compat_exports_in_src(
    source_content_cache: dict[Path, str],
) -> None:
    """New first-party src must use canonical datasource paths, not DataSourceRegistry."""
    violations = _iter_symbol_mentions(
        source_content_cache,
        symbol="DataSourceRegistry",
        allowed_files=ALLOWED_DATASOURCE_REGISTRY_SRC_FILES,
    )
    assert not violations, (
        "DataSourceRegistry compatibility surface leaked into first-party src/ beyond "
        "explicit compatibility exports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_datasource_registry_symbol_is_confined_to_compat_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Ordinary tests must not treat DataSourceRegistry as a normal factory API."""
    violations = _iter_imported_symbol_violations(
        test_ast_cache,
        module_names=frozenset(
            {
                "bioetl.composition.factories",
                "bioetl.composition.factories.datasource",
                "bioetl.composition.factories.datasource.data_source_factory",
            }
        ),
        symbol="DataSourceRegistry",
        allowed_files=ALLOWED_DATASOURCE_REGISTRY_TEST_FILES,
    )
    assert not violations, (
        "DataSourceRegistry compatibility surface leaked into ordinary tests beyond "
        "explicit compat/contract coverage:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_datasource_registry_symbol_is_absent_from_canonical_docs_and_diagrams() -> (
    None
):
    """Canonical docs/diagrams must present only the provider-backed datasource path."""
    violations = _iter_text_symbol_mentions(
        files=CANONICAL_DATASOURCE_DOC_FILES,
        symbol="DataSourceRegistry",
    )
    assert not violations, (
        "DataSourceRegistry compatibility surface leaked into canonical docs/diagrams:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_register_all_providers_symbol_is_confined_to_provider_loading_modules(
    source_content_cache: dict[Path, str],
) -> None:
    """Canonical provider lifecycle must use ensure_providers_loaded outside loaders."""
    violations = _iter_symbol_mentions(
        source_content_cache,
        symbol="register_all_providers",
        allowed_files=ALLOWED_REGISTER_ALL_PROVIDERS_SRC_FILES,
    )
    assert not violations, (
        "register_all_providers leaked beyond provider loading internals:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_registration_biblio_module_is_confined_to_provider_registration(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Private provider registration builders must not become ordinary src imports."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name="bioetl.composition.providers.registration_biblio",
        allowed_files=ALLOWED_REGISTRATION_BIBLIO_SRC_FILES,
    )
    assert not violations, (
        "registration_biblio leaked beyond provider registration internals:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_provider_loading_and_pipeline_config_legacy_symbols_are_absent_from_canonical_docs() -> (
    None
):
    """Canonical docs must not present private loading/config seams as normal extension paths."""
    violations = []
    for symbol in (
        "register_all_providers",
        "registration_biblio",
        "pipeline_factories.py",
    ):
        violations.extend(
            _iter_text_symbol_mentions(
                files=CANONICAL_PROVIDER_SURFACE_DOC_FILES,
                symbol=symbol,
            )
        )
    assert not violations, (
        "Private provider/config compatibility surface leaked into canonical docs:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_file_has_been_removed() -> None:
    """Legacy datasource.factory shim should remain deleted."""
    assert not LEGACY_DATASOURCE_FACTORY_MODULE_PATH.exists(), (
        "Legacy datasource factory shim must stay removed: "
        "src/bioetl/composition/factories/datasource/factory.py"
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must use canonical datasource module paths."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES,
    )
    assert not violations, (
        "Legacy datasource.factory module must stay removed from src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_is_only_used_by_compat_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed legacy datasource module."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES,
    )
    assert not violations, (
        "Legacy datasource.factory module must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_string_mentions_are_confined_to_compat_tests(
    test_content_cache: dict[Path, str],
) -> None:
    """Tests must not reintroduce string patch targets for removed datasource module."""
    # Note: this test needs fresh content_cache including self-file; use test_content_cache
    violations = _iter_string_mentions(
        test_content_cache,
        needle=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES
        | frozenset({Path(__file__).resolve()}),
    )
    assert not violations, (
        "Legacy datasource.factory module must stay removed from string references:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize("module_name", INTERNAL_COMPOSITION_ENTRYPOINT_MODULES)
def test_internal_composition_entrypoint_modules_are_not_imported_in_unit_tests(
    module_name: str,
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Unit tests must patch public composition.entrypoints instead of internals."""
    unit_root = ROOT / "tests" / "unit"
    unit_ast_cache = {
        p: t for p, t in test_ast_cache.items() if p.is_relative_to(unit_root)
    }
    violations = _iter_module_import_violations(
        unit_ast_cache,
        module_name=module_name,
        allowed_files=ALLOWED_INTERNAL_ENTRYPOINT_TEST_FILES_BY_MODULE[module_name],
    )
    assert not violations, (
        "Internal composition entrypoint module gained new unit-test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize("module_name", INTERNAL_COMPOSITION_ENTRYPOINT_MODULES)
def test_internal_composition_entrypoint_module_strings_are_not_used_in_unit_tests(
    module_name: str,
    test_content_cache: dict[Path, str],
) -> None:
    """Unit tests must not reintroduce string patch targets for internal entrypoints."""
    unit_root = ROOT / "tests" / "unit"
    unit_content_cache = {
        p: c for p, c in test_content_cache.items() if p.is_relative_to(unit_root)
    }
    violations = _iter_string_mentions(
        unit_content_cache,
        needle=module_name,
        allowed_files=ALLOWED_INTERNAL_ENTRYPOINT_TEST_FILES_BY_MODULE[module_name],
    )
    assert not violations, (
        "Internal composition entrypoint module gained new string references in unit tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    "needle",
    (
        "bioetl.interfaces.cli.main.get_default_registry",
        "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
        "bioetl.interfaces.cli.commands.run_all.get_default_registry",
    ),
)
def test_cli_local_get_default_registry_patch_points_remain_removed_from_tests(
    needle: str,
    test_content_cache: dict[Path, str],
) -> None:
    """Tests must not reintroduce removed CLI get_default_registry patch aliases."""
    violations = _iter_string_mentions(
        test_content_cache,
        needle=needle,
        allowed_files=ALLOWED_CLI_GET_DEFAULT_REGISTRY_TEST_FILES
        | frozenset({Path(__file__).resolve()}),
    )
    assert not violations, (
        "Removed CLI get_default_registry patch points reappeared in tests:\n"
        + "\n".join(violations)
    )
