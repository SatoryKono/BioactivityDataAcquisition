"""Compatibility-freeze guardrails for shim imports and symbols."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
LEGACY_DATASOURCE_FACTORY_MODULE = "bioetl.composition.factories.datasource.factory"
INTERNAL_COMPOSITION_ENTRYPOINT_MODULES = (
    "bioetl.composition._pipeline_execution",
    "bioetl.composition._resource_management",
    "bioetl.composition._services",
)
CLI_REGISTRY_HELPER_MODULE = "bioetl.interfaces.cli.registry_helpers"
CONFIG_LOADER_MODULE = "bioetl.infrastructure.config_loader"
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
        / "mmd-diagrams"
        / "class-diagrams"
        / "16-factories-bootstrap.mmd",
        ROOT
        / "docs"
        / "02-architecture"
        / "mmd-diagrams"
        / "architecture"
        / "12a-bootstrap-factories.mmd",
        ROOT
        / "docs"
        / "02-architecture"
        / "mmd-diagrams"
        / "architecture"
        / "12-bootstrap-di-container.mmd",
        ROOT / "docs" / "02-architecture" / "mmd-diagrams" / "diagram-descriptions.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "mmd-diagrams"
        / "diagram-descriptions"
        / "class-diagrams-descriptions.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "mmd-diagrams"
        / "class-diagrams-with-descriptions.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "mmd-diagrams"
        / "architecture-diagrams-with-descriptions.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagram-descriptions"
        / "mmd-diagrams"
        / "architecture"
        / "12a-bootstrap-factories.md",
        ROOT
        / "docs"
        / "02-architecture"
        / "diagram-descriptions"
        / "mmd-diagrams"
        / "class-diagrams"
        / "16-factories-bootstrap.md",
    }
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES: frozenset[Path] = frozenset()
LEGACY_DATASOURCE_FACTORY_MODULE_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "factories" / "datasource" / "factory.py"
)
ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES: frozenset[Path] = frozenset()
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
    }
)
ALLOWED_COMPOSITION_DEFAULT_REGISTRY_SRC_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "types.py",
        ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "cli" / "config.py",
        ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "cli" / "storage.py",
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "pipeline"
        / "registry.py",
    }
)
ALLOWED_CONFIG_LOADER_PRIVATE_HELPER_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "config"
        / "test_pipeline_config_legacy_normalization.py",
    }
)
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


def _normalized_allowed_rel_paths(allowed_files: frozenset[Path]) -> frozenset[str]:
    """Normalize allowlist paths to project-relative POSIX strings."""
    return frozenset(
        path.resolve().relative_to(ROOT).as_posix() for path in allowed_files
    )


def _iter_module_import_violations(
    search_root: Path,
    *,
    module_name: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file in search_root.rglob("*.py"):
        rel_path = py_file.resolve().relative_to(ROOT).as_posix()
        if rel_path in allowed_rel_paths or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
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
    search_root: Path,
    *,
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file in search_root.rglob("*.py"):
        rel_path = py_file.resolve().relative_to(ROOT).as_posix()
        if rel_path in allowed_rel_paths or "__pycache__" in py_file.parts:
            continue
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), 1
        ):
            if symbol in line:
                violations.append(f"{rel_path}:{lineno} mentions {symbol}")
    return violations


def _iter_string_mentions(
    search_root: Path,
    *,
    needle: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file in search_root.rglob("*.py"):
        rel_path = py_file.resolve().relative_to(ROOT).as_posix()
        if rel_path in allowed_rel_paths or "__pycache__" in py_file.parts:
            continue
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), 1
        ):
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
        rel_path = file_path.resolve().relative_to(ROOT).as_posix()
        for lineno, line in enumerate(
            file_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if symbol in line:
                violations.append(f"{rel_path}:{lineno} mentions {symbol}")
    return violations


def _iter_imported_symbol_violations(
    search_root: Path,
    *,
    module_names: frozenset[str],
    symbol: str,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file in search_root.rglob("*.py"):
        rel_path = py_file.resolve().relative_to(ROOT).as_posix()
        if rel_path in allowed_rel_paths or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
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
    search_root: Path,
    *,
    call_name: str,
    keyword_names: frozenset[str],
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    allowed_rel_paths = _normalized_allowed_rel_paths(allowed_files)
    for py_file in search_root.rglob("*.py"):
        rel_path = py_file.resolve().relative_to(ROOT).as_posix()
        if rel_path in allowed_rel_paths or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
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
def test_transformer_dependency_compat_shim_is_not_used_in_src() -> None:
    """First-party src must use canonical base-transformer dependency types directly."""
    violations = _iter_module_import_violations(
        SRC_ROOT,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "base_transformer dependency compatibility shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_transformer_dependency_compat_shim_is_not_used_in_tests() -> None:
    """Tests must not keep importing the removed dependency shim."""
    violations = _iter_module_import_violations(
        TESTS_ROOT,
        module_name=TRANSFORMER_DEPENDENCY_SHIM,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "base_transformer dependency compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_cli_registry_helper_module_is_confined_to_cli_src_entrypoints() -> None:
    """Compatibility CLI registry helper must not leak outside the CLI perimeter."""
    violations = _iter_module_import_violations(
        SRC_ROOT,
        module_name=CLI_REGISTRY_HELPER_MODULE,
        allowed_files=ALLOWED_CLI_REGISTRY_HELPER_SRC_FILES,
    )
    assert not violations, (
        "CLI registry helper compatibility seam leaked beyond the known CLI src "
        "entrypoints:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_default_registry_import_is_confined_to_known_src_compatibility_seams() -> None:
    """Shared default-registry access must stay frozen to the current src seams."""
    violations = _iter_imported_symbol_violations(
        SRC_ROOT,
        module_names=frozenset({"bioetl.composition.registry"}),
        symbol="get_default_registry",
        allowed_files=ALLOWED_COMPOSITION_DEFAULT_REGISTRY_SRC_FILES,
    )
    assert not violations, (
        "composition.registry.get_default_registry leaked into new src call sites:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    "symbol",
    ("read_pipeline_config_payload", "normalize_pipeline_config_payload"),
)
def test_config_loader_private_compat_helpers_are_confined(
    symbol: str,
) -> None:
    """Private config-loader compatibility helpers should not become general APIs."""
    src_violations = _iter_imported_symbol_violations(
        SRC_ROOT,
        module_names=frozenset({CONFIG_LOADER_MODULE}),
        symbol=symbol,
        allowed_files=frozenset(),
    )
    assert not src_violations, (
        f"{symbol} must stay out of first-party src imports:\n"
        + "\n".join(src_violations)
    )

    test_violations = _iter_imported_symbol_violations(
        TESTS_ROOT,
        module_names=frozenset({CONFIG_LOADER_MODULE}),
        symbol=symbol,
        allowed_files=ALLOWED_CONFIG_LOADER_PRIVATE_HELPER_TEST_FILES,
    )
    assert not test_violations, (
        f"{symbol} leaked beyond dedicated config compatibility coverage:\n"
        + "\n".join(test_violations)
    )


@pytest.mark.architecture
def test_merge_service_legacy_keyword_wiring_does_not_expand_in_src() -> None:
    """Legacy MergeService keyword wiring must stay confined to the owning module."""
    violations = _iter_call_keyword_violations(
        SRC_ROOT,
        call_name="MergeService",
        keyword_names=LEGACY_MERGE_SERVICE_KEYWORDS,
        allowed_files=ALLOWED_MERGE_SERVICE_SRC_FILES,
    )
    assert not violations, (
        "MergeService legacy collaborator keyword wiring leaked into new src call sites:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_datasource_registry_symbol_is_confined_to_compat_exports_in_src() -> None:
    """New first-party src must use canonical datasource paths, not DataSourceRegistry."""
    violations = _iter_symbol_mentions(
        SRC_ROOT,
        symbol="DataSourceRegistry",
        allowed_files=ALLOWED_DATASOURCE_REGISTRY_SRC_FILES,
    )
    assert not violations, (
        "DataSourceRegistry compatibility surface leaked into first-party src/ beyond "
        "explicit compatibility exports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_datasource_registry_symbol_is_confined_to_compat_tests() -> None:
    """Ordinary tests must not treat DataSourceRegistry as a normal factory API."""
    violations = _iter_imported_symbol_violations(
        TESTS_ROOT,
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
def test_register_all_providers_symbol_is_confined_to_provider_loading_modules() -> (
    None
):
    """Canonical provider lifecycle must use ensure_providers_loaded outside loaders."""
    violations = _iter_symbol_mentions(
        SRC_ROOT,
        symbol="register_all_providers",
        allowed_files=ALLOWED_REGISTER_ALL_PROVIDERS_SRC_FILES,
    )
    assert not violations, (
        "register_all_providers leaked beyond provider loading internals:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_registration_biblio_module_is_confined_to_provider_registration() -> None:
    """Private provider registration builders must not become ordinary src imports."""
    violations = _iter_module_import_violations(
        SRC_ROOT,
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
def test_legacy_datasource_factory_module_is_not_used_in_src() -> None:
    """First-party src must use canonical datasource module paths."""
    violations = _iter_module_import_violations(
        SRC_ROOT,
        module_name=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES,
    )
    assert not violations, (
        "Legacy datasource.factory module must stay removed from src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_is_only_used_by_compat_tests() -> None:
    """Tests must not keep importing the removed legacy datasource module."""
    violations = _iter_module_import_violations(
        TESTS_ROOT,
        module_name=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES,
    )
    assert not violations, (
        "Legacy datasource.factory module must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_legacy_datasource_factory_module_string_mentions_are_confined_to_compat_tests() -> (
    None
):
    """Tests must not reintroduce string patch targets for removed datasource module."""
    violations = _iter_string_mentions(
        TESTS_ROOT,
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
) -> None:
    """Unit tests must patch public composition.entrypoints instead of internals."""
    violations = _iter_module_import_violations(
        TESTS_ROOT / "unit",
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
) -> None:
    """Unit tests must not reintroduce string patch targets for internal entrypoints."""
    violations = _iter_string_mentions(
        TESTS_ROOT / "unit",
        needle=module_name,
        allowed_files=ALLOWED_INTERNAL_ENTRYPOINT_TEST_FILES_BY_MODULE[module_name],
    )
    assert not violations, (
        "Internal composition entrypoint module gained new string references in unit tests:\n"
        + "\n".join(violations)
    )
