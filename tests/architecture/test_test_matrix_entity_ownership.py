# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
            if entity_key == "composite.assay":
                pipeline_name = "composite_assay"
                assert any(pipeline_name in path.as_posix() for path in owned_paths), (
                    "composite.assay owner must name composite_assay, not chembl_assay"
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

    def test_composite_assay_owner_executes_composite_assay_not_chembl_assay(
        self,
    ) -> None:
        """Owned paths for composite.assay must run composite_assay, not chembl_assay."""
        matrix = load_matrix()
        composite_paths = ownership_paths(matrix, "composite.assay")
        chembl_paths = {
            path.resolve() for path in ownership_paths(matrix, "chembl.assay")
        }

        assert composite_paths, "composite.assay must declare an owned test path"
        for owned in composite_paths:
            relative = owned.relative_to(ROOT).as_posix()
            assert relative != "tests/e2e/test_chembl_assay_e2e.py", (
                "composite.assay owner must not be the chembl_assay e2e lane"
            )
            assert owned.resolve() not in chembl_paths, (
                f"{relative} is shared with chembl.assay and cannot distinguish "
                "composite_assay from chembl_assay"
            )
            source = owned.read_text(encoding="utf-8")
            assert (
                'config.name == "composite_assay"' in source
                or 'pipeline_name"] == "composite_assay"' in source
                or 'pipeline_name == "composite_assay"' in source
            ), f"{relative} must execute composite_assay"
            assert 'create_deterministic_test_context("chembl_assay"' not in source
