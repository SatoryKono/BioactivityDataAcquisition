"""Architecture tests for provider/entity ownership in the test matrix."""

from __future__ import annotations

import pytest

from tests.architecture._test_matrix_policy_support import (
    MATRIX_PATH,
    ROOT,
    TESTS_DIR,
    golden_master_registry_pipelines,
    iter_entity_configs,
    load_matrix,
    ownership_paths,
    provider_suite_index,
    represented_golden_master_entities,
    required_provider_names,
)


@pytest.mark.architecture
class TestEntityOwnershipCoverage:
    """Validate provider/entity test ownership ratchets."""

    def test_each_active_provider_entity_has_test_ownership_entry(self) -> None:
        matrix = load_matrix()
        ownership = matrix.get("entity_test_ownership", {})

        for provider, entity, _config_path in iter_entity_configs():
            entity_key = f"{provider}.{entity}"
            assert entity_key in ownership, (
                f"Missing entity_test_ownership entry for '{entity_key}' in "
                f"{MATRIX_PATH.relative_to(ROOT)}"
            )

    def test_owned_test_paths_exist_for_declared_entities(self) -> None:
        matrix = load_matrix()

        for provider, entity, _config_path in iter_entity_configs():
            entity_key = f"{provider}.{entity}"
            owned_paths = ownership_paths(matrix, entity_key)

            assert owned_paths, (
                f"entity '{entity_key}' must declare at least one test path"
            )
            for owned_path in owned_paths:
                assert owned_path.exists(), (
                    f"Declared ownership path for '{entity_key}' is missing: "
                    f"{owned_path.relative_to(ROOT)}"
                )

    def test_must_contract_providers_have_owned_contract_or_provider_regression_suite(
        self,
    ) -> None:
        matrix = load_matrix()
        provider_suites = matrix.get("provider_regression_suites", {})
        contract_dir = TESTS_DIR / "contract"
        suite_index = provider_suite_index(provider_suites)

        for provider in required_provider_names(matrix, "contract_tests"):
            contract_path = contract_dir / f"test_{provider}_contract.py"
            assert contract_path.exists() or provider in suite_index, (
                f"provider '{provider}' requires contract coverage but has neither "
                f"{contract_path.relative_to(ROOT)} nor a canonical provider regression suite"
            )

    def test_golden_master_representative_set_matches_matrix_policy(self) -> None:
        matrix = load_matrix()
        represented = represented_golden_master_entities()
        registry = golden_master_registry_pipelines(matrix)

        for provider, pipelines in registry.items():
            expected_entities = {
                pipeline.split("_", maxsplit=1)[1] for pipeline in pipelines
            }
            assert represented.get(provider, set()) == expected_entities, (
                f"provider '{provider}' golden-master registry mismatch: "
                f"expected entities {sorted(expected_entities)}, "
                f"represented {sorted(represented.get(provider, set()))}"
            )

    def test_provider_matrix_only_references_existing_entity_configs(self) -> None:
        matrix = load_matrix()
        existing = {(provider, entity) for provider, entity, _ in iter_entity_configs()}

        for provider, config in matrix["providers"].items():
            for entity in config.get("entities", []):
                assert (provider, entity) in existing, (
                    f"matrix references missing entity config '{provider}.{entity}'"
                )
