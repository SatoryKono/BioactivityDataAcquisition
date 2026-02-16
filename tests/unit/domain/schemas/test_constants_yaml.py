"""Tests for YAML-based ChEMBL enum constants loading.

Verifies that configs/enums/chembl.yaml is the single source of truth
and that constants.py loads values correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="module")
def chembl_yaml() -> dict:
    """Load raw YAML for independent comparison."""
    yaml_path = Path("configs/enums/chembl.yaml")
    with yaml_path.open() as f:
        return yaml.safe_load(f)


class TestYamlFileExists:
    """Ensure the YAML enum config exists and is valid."""

    def test_chembl_yaml_exists(self) -> None:
        assert Path("configs/enums/chembl.yaml").exists()

    def test_chembl_yaml_has_version(self, chembl_yaml: dict) -> None:
        assert "version" in chembl_yaml

    def test_chembl_yaml_has_all_sections(self, chembl_yaml: dict) -> None:
        expected_sections = {"activity", "assay", "molecule", "target", "publication"}
        assert expected_sections <= set(chembl_yaml.keys())


class TestConstantsMatchYaml:
    """Verify Python constants match YAML values exactly."""

    def test_standard_relations(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import STANDARD_RELATIONS

        assert STANDARD_RELATIONS == frozenset(chembl_yaml["activity"]["standard_relations"])

    def test_activity_standard_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import ACTIVITY_STANDARD_TYPES

        assert ACTIVITY_STANDARD_TYPES == frozenset(chembl_yaml["activity"]["standard_types"])

    def test_data_validity_comments(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import DATA_VALIDITY_COMMENTS

        assert DATA_VALIDITY_COMMENTS == frozenset(
            chembl_yaml["activity"]["data_validity_comments"]
        )

    def test_assay_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import ASSAY_TYPES

        assert ASSAY_TYPES == frozenset(chembl_yaml["assay"]["types"])

    def test_assay_test_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import ASSAY_TEST_TYPES

        assert ASSAY_TEST_TYPES == frozenset(chembl_yaml["assay"]["test_types"])

    def test_assay_categories(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import ASSAY_CATEGORIES

        assert ASSAY_CATEGORIES == frozenset(chembl_yaml["assay"]["categories"])

    def test_relationship_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import RELATIONSHIP_TYPES

        assert RELATIONSHIP_TYPES == frozenset(chembl_yaml["assay"]["relationship_types"])

    def test_molecule_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import MOLECULE_TYPES

        assert MOLECULE_TYPES == frozenset(chembl_yaml["molecule"]["types"])

    def test_structure_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import STRUCTURE_TYPES

        assert STRUCTURE_TYPES == frozenset(chembl_yaml["molecule"]["structure_types"])

    def test_max_phase_values(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import MAX_PHASE_VALUES

        expected = tuple(float(v) for v in chembl_yaml["molecule"]["max_phase_values"])
        assert MAX_PHASE_VALUES == expected

    def test_target_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import TARGET_TYPES

        assert TARGET_TYPES == frozenset(chembl_yaml["target"]["types"])

    def test_target_component_relationships(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import TARGET_COMPONENT_RELATIONSHIPS

        assert TARGET_COMPONENT_RELATIONSHIPS == frozenset(
            chembl_yaml["target"]["component_relationships"]
        )

    def test_publication_types(self, chembl_yaml: dict) -> None:
        from bioetl.domain.schemas.constants import PUBLICATION_TYPES

        assert PUBLICATION_TYPES == frozenset(chembl_yaml["publication"]["types"])


class TestAssayParameterSuperset:
    """ASSAY_PARAMETER_STANDARD_TYPES must be a superset of ACTIVITY_STANDARD_TYPES."""

    def test_superset_relationship(self) -> None:
        from bioetl.domain.schemas.constants import (
            ACTIVITY_STANDARD_TYPES,
            ASSAY_PARAMETER_STANDARD_TYPES,
        )

        assert ACTIVITY_STANDARD_TYPES <= ASSAY_PARAMETER_STANDARD_TYPES

    def test_contains_parameter_specific_types(self) -> None:
        from bioetl.domain.schemas.constants import ASSAY_PARAMETER_STANDARD_TYPES

        parameter_only = {"CONC", "PH", "TEMP", "TIME", "DOSE"}
        assert parameter_only <= ASSAY_PARAMETER_STANDARD_TYPES


class TestConstantTypes:
    """Verify that constants have the correct Python types."""

    def test_frozenset_types(self) -> None:
        from bioetl.domain.schemas.constants import (
            ACTIVITY_STANDARD_TYPES,
            ASSAY_CATEGORIES,
            ASSAY_TYPES,
            MOLECULE_TYPES,
            STANDARD_RELATIONS,
            TARGET_TYPES,
        )

        for const in [
            STANDARD_RELATIONS,
            ACTIVITY_STANDARD_TYPES,
            ASSAY_TYPES,
            ASSAY_CATEGORIES,
            MOLECULE_TYPES,
            TARGET_TYPES,
        ]:
            assert isinstance(const, frozenset), f"{const!r} should be frozenset"

    def test_max_phase_is_tuple(self) -> None:
        from bioetl.domain.schemas.constants import MAX_PHASE_VALUES

        assert isinstance(MAX_PHASE_VALUES, tuple)
        assert all(isinstance(v, float) for v in MAX_PHASE_VALUES)

    def test_constants_are_nonempty(self) -> None:
        from bioetl.domain.schemas.constants import (
            ACTIVITY_STANDARD_TYPES,
            ASSAY_TYPES,
            MAX_PHASE_VALUES,
            MOLECULE_TYPES,
            PUBLICATION_TYPES,
            STANDARD_RELATIONS,
            TARGET_TYPES,
        )

        for const in [
            STANDARD_RELATIONS,
            ACTIVITY_STANDARD_TYPES,
            ASSAY_TYPES,
            MOLECULE_TYPES,
            TARGET_TYPES,
            PUBLICATION_TYPES,
            MAX_PHASE_VALUES,
        ]:
            assert len(const) > 0
