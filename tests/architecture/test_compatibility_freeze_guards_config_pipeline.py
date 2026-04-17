"""Compatibility-freeze guardrails for config and pipeline compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architecture.test_compatibility_freeze_guards import (
    ALLOWED_CONFIG_LOADER_SRC_FILES,
    ALLOWED_CONFIG_LOADER_TEST_FILES,
    ALLOWED_CONFIG_LOAD_API_SRC_FILES,
    ALLOWED_CONFIG_LOAD_API_TEST_FILES,
    ALLOWED_INFRASTRUCTURE_CONFIG_LOADER_SYMBOL_SRC_FILES,
    ALLOWED_METADATA_BUILDER_COMPAT_TEST_FILES,
    ALLOWED_PIPELINE_CONFIG_RESOLUTION_SRC_FILES,
    ALLOWED_PIPELINE_CONFIG_RESOLUTION_TEST_FILES,
    ALLOWED_PIPELINE_RUNNER_SERVICE_MODEL_IMPORT_SRC_FILES,
    CONFIG_LOADER_MODULE,
    CONFIG_LOADER_MODULE_PATH,
    CONFIG_LOAD_API_MODULE,
    CONFIG_LOAD_API_MODULE_PATH,
    INFRASTRUCTURE_CONFIG_PUBLIC_MODULE,
    METADATA_BUILDER_COMPAT_MODULE,
    METADATA_BUILDER_COMPAT_MODULE_PATH,
    PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE,
    PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE_PATH,
    PIPELINE_CONFIGS_COMPAT_MODULE,
    PIPELINE_CONFIGS_COMPAT_MODULE_PATH,
    PIPELINE_RUNNER_SERVICE_MODULE,
    SERVICES_CREATION_API_COMPAT_MODULE,
    SERVICES_CREATION_API_COMPAT_MODULE_PATH,
    _iter_imported_symbol_violations,
    _iter_module_import_violations,
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
def test_config_load_api_compat_shim_file_has_been_removed() -> None:
    """Historical config_load_api bridge should remain deleted."""
    assert not CONFIG_LOAD_API_MODULE_PATH.exists(), (
        "Legacy config_load_api compatibility shim must stay removed: "
        "src/bioetl/infrastructure/config_load_api.py"
    )


@pytest.mark.architecture
def test_config_load_api_module_is_absent_from_first_party_src_imports(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical config modules, not config_load_api."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=CONFIG_LOAD_API_MODULE,
        allowed_files=ALLOWED_CONFIG_LOAD_API_SRC_FILES,
    )
    assert not violations, (
        "config_load_api compatibility module leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_config_load_api_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed config_load_api shim."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=CONFIG_LOAD_API_MODULE,
        allowed_files=ALLOWED_CONFIG_LOAD_API_TEST_FILES,
    )
    assert not violations, (
        "config_load_api compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    "symbol",
    ("load_pipeline_config", "load_composite_config", "load_source_config"),
)
def test_infrastructure_config_loader_symbols_are_confined_to_canonical_owner_imports_in_src(
    symbol: str,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import config loader symbols from canonical owner modules."""
    violations = _iter_imported_symbol_violations(
        source_ast_cache,
        module_names=frozenset({INFRASTRUCTURE_CONFIG_PUBLIC_MODULE}),
        symbol=symbol,
        allowed_files=ALLOWED_INFRASTRUCTURE_CONFIG_LOADER_SYMBOL_SRC_FILES,
    )
    assert not violations, (
        "infrastructure.config loader re-export surface leaked into first-party "
        "src imports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_services_creation_api_compat_shim_file_has_been_removed() -> None:
    """Deprecated services.creation_api shim should stay deleted."""
    assert not SERVICES_CREATION_API_COMPAT_MODULE_PATH.exists(), (
        "Legacy services.creation_api compatibility shim must stay removed: "
        "src/bioetl/composition/factories/services/creation_api.py"
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
def test_pipeline_config_resolution_compat_shim_file_has_been_removed() -> None:
    """Deprecated config_resolution shim should stay deleted."""
    assert not PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE_PATH.exists(), (
        "Legacy pipeline.config_resolution compatibility shim must stay removed: "
        "src/bioetl/composition/factories/pipeline/config_resolution.py"
    )


@pytest.mark.architecture
def test_pipeline_config_resolution_compat_module_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must keep the removed config_resolution shim absent."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE,
        allowed_files=ALLOWED_PIPELINE_CONFIG_RESOLUTION_SRC_FILES,
    )
    assert not violations, (
        "pipeline.config_resolution compatibility shim leaked into first-party src "
        "imports:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_pipeline_config_resolution_compat_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must keep the removed config_resolution shim absent."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=PIPELINE_CONFIG_RESOLUTION_COMPAT_MODULE,
        allowed_files=ALLOWED_PIPELINE_CONFIG_RESOLUTION_TEST_FILES,
    )
    assert not violations, (
        "pipeline.config_resolution compatibility shim must stay removed from "
        "tests:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_pipeline_configs_compat_shim_file_has_been_removed() -> None:
    """Deprecated pipeline.configs shim should stay deleted."""
    assert not PIPELINE_CONFIGS_COMPAT_MODULE_PATH.exists(), (
        "Legacy pipeline.configs compatibility shim must stay removed: "
        "src/bioetl/composition/factories/pipeline/configs.py"
    )


@pytest.mark.architecture
def test_pipeline_configs_compat_module_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import the canonical pipeline registry manifest."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name=PIPELINE_CONFIGS_COMPAT_MODULE,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "pipeline.configs compatibility shim leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_pipeline_configs_compat_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must keep the removed pipeline.configs shim absent."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=PIPELINE_CONFIGS_COMPAT_MODULE,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "pipeline.configs compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_services_creation_api_compat_module_is_confined_to_dedicated_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must keep the removed services.creation_api shim absent."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name=SERVICES_CREATION_API_COMPAT_MODULE,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "services.creation_api compatibility shim must stay removed from tests:\n"
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
def test_metadata_builder_module_file_has_been_removed() -> None:
    """Legacy storage metadata builder module should stay deleted."""
    metadata_builder_path = Path(
        "src/bioetl/infrastructure/storage/metadata_builder.py"
    )
    assert not metadata_builder_path.exists(), (
        "Legacy storage metadata builder must stay removed: "
        "src/bioetl/infrastructure/storage/metadata_builder.py"
    )


@pytest.mark.architecture
def test_metadata_builder_module_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must not import the removed metadata_builder module."""
    violations = _iter_module_import_violations(
        source_ast_cache,
        module_name="bioetl.infrastructure.storage.metadata_builder",
        allowed_files=frozenset(),
    )
    assert not violations, (
        "metadata_builder leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_metadata_builder_module_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed metadata_builder module."""
    violations = _iter_module_import_violations(
        test_ast_cache,
        module_name="bioetl.infrastructure.storage.metadata_builder",
        allowed_files=frozenset(),
    )
    assert not violations, (
        "metadata_builder leaked into tests after coordinator-only hardening:\n"
        + "\n".join(violations)
    )
