"""Compatibility-freeze guardrails for provider and datasource compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architecture.test_compatibility_freeze_guards import (
    ALLOWED_CLI_GET_DEFAULT_REGISTRY_TEST_FILES,
    ALLOWED_DATASOURCE_REGISTRY_SRC_FILES,
    ALLOWED_DATASOURCE_REGISTRY_TEST_FILES,
    ALLOWED_DEFAULT_PROVIDER_REGISTRATION_SRC_FILES,
    ALLOWED_INTERNAL_ENTRYPOINT_TEST_FILES_BY_MODULE,
    ALLOWED_LEGACY_DATASOURCE_FACTORY_SRC_FILES,
    ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES,
    ALLOWED_MERGE_SERVICE_SRC_FILES,
    ALLOWED_REGISTER_ALL_PROVIDERS_SRC_FILES,
    ALLOWED_REGISTRATION_BIBLIO_SRC_FILES,
    CANONICAL_DATASOURCE_DOC_FILES,
    CANONICAL_PROVIDER_SURFACE_DOC_FILES,
    INTERNAL_COMPOSITION_ENTRYPOINT_MODULES,
    LEGACY_BATCH_TRANSFORMER_ORCHESTRATION_MODULE_PATH,
    LEGACY_DATASOURCE_FACTORY_MODULE,
    LEGACY_DATASOURCE_FACTORY_MODULE_PATH,
    LEGACY_MERGE_SERVICE_KEYWORDS,
    ROOT,
    SANCTIONED_DEAD_CODE_EXCLUSION_MODULE_PATHS,
    _iter_call_keyword_violations,
    _iter_imported_symbol_violations,
    _iter_module_import_violations,
    _iter_string_mentions,
    _iter_symbol_mentions,
    _iter_text_symbol_mentions,
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
def test_register_default_provider_config_symbol_is_confined_to_provider_compat_seams(
    source_content_cache: dict[Path, str],
) -> None:
    """Default-registry provider writes must remain confined to compat seams."""
    violations = _iter_symbol_mentions(
        source_content_cache,
        symbol="register_default_provider_config",
        allowed_files=ALLOWED_DEFAULT_PROVIDER_REGISTRATION_SRC_FILES,
    )
    assert not violations, (
        "register_default_provider_config leaked beyond provider compat seams:\n"
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
def test_legacy_batch_transformer_orchestration_module_file_has_been_removed() -> None:
    """Legacy batch-transformer orchestration duplicate should stay removed."""
    assert not LEGACY_BATCH_TRANSFORMER_ORCHESTRATION_MODULE_PATH.exists(), (
        "Legacy batch_transformer_orchestration duplicate must stay removed: "
        "src/bioetl/application/core/batch_transformer_orchestration.py"
    )


@pytest.mark.architecture
def test_sanctioned_dead_code_exclusion_modules_remain_present() -> None:
    """Sanctioned aggregate/wrapper seams must not be dropped by generic cleanup."""
    missing = [
        str(path.relative_to(ROOT))
        for path in sorted(SANCTIONED_DEAD_CODE_EXCLUSION_MODULE_PATHS)
        if not path.exists()
    ]
    assert not missing, (
        "Sanctioned compatibility/aggregate seams must stay present unless a "
        "dedicated migration removes their public obligations:\n"
        + "\n".join(f"  - {item}" for item in missing)
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
    violations = _iter_string_mentions(
        test_content_cache,
        needle=LEGACY_DATASOURCE_FACTORY_MODULE,
        allowed_files=ALLOWED_LEGACY_DATASOURCE_FACTORY_TEST_FILES
        | frozenset(
            {
                Path(__file__).resolve(),
                ROOT / "tests" / "architecture" / "test_compatibility_freeze_guards.py",
            }
        ),
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
