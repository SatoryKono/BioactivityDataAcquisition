"""Sync tests: verify domain/schemas/constants.py matches configs/enums/chembl.yaml.

The YAML file is the single source of truth (ADR-035).
These tests catch drift between the YAML config and Python constants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture(scope="module")
def chembl_yaml() -> dict[str, Any]:
    """Load YAML enum config for comparison."""
    yaml_path = Path("configs/enums/chembl.yaml")
    with yaml_path.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def uniprot_yaml() -> dict[str, Any]:
    """Load UniProt enum config for comparison."""
    yaml_path = Path("configs/enums/uniprot.yaml")
    with yaml_path.open() as f:
        return yaml.safe_load(f)


class TestYamlFileIntegrity:
    """Ensure the YAML enum config exists and is well-formed."""

    def test_chembl_yaml_exists(self) -> None:
        assert Path("configs/enums/chembl.yaml").exists()

    def test_chembl_yaml_has_version(self, chembl_yaml: dict[str, Any]) -> None:
        assert "version" in chembl_yaml

    def test_chembl_yaml_has_all_sections(self, chembl_yaml: dict[str, Any]) -> None:
        expected = {"activity", "assay", "molecule", "target", "publication"}
        assert expected <= set(chembl_yaml.keys())

    def test_uniprot_yaml_exists(self) -> None:
        assert Path("configs/enums/uniprot.yaml").exists()

    def test_uniprot_yaml_has_version(self, uniprot_yaml: dict[str, Any]) -> None:
        assert "version" in uniprot_yaml


class TestActivitySync:
    """Activity enum constants must match YAML."""

    def test_standard_relations(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import STANDARD_RELATIONS

        assert STANDARD_RELATIONS == frozenset(
            chembl_yaml["activity"]["standard_relations"]
        )

    def test_activity_standard_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ACTIVITY_STANDARD_TYPES

        assert ACTIVITY_STANDARD_TYPES == frozenset(
            chembl_yaml["activity"]["standard_types"]
        )

    def test_data_validity_comments(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import DATA_VALIDITY_COMMENTS

        assert DATA_VALIDITY_COMMENTS == frozenset(
            chembl_yaml["activity"]["data_validity_comments"]
        )


class TestAssaySync:
    """Assay enum constants must match YAML."""

    def test_assay_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ASSAY_TYPES

        assert ASSAY_TYPES == frozenset(chembl_yaml["assay"]["types"])

    def test_assay_test_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ASSAY_TEST_TYPES

        assert ASSAY_TEST_TYPES == frozenset(chembl_yaml["assay"]["test_types"])

    def test_assay_categories(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ASSAY_CATEGORIES

        assert ASSAY_CATEGORIES == frozenset(chembl_yaml["assay"]["categories"])

    def test_relationship_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import RELATIONSHIP_TYPES

        assert RELATIONSHIP_TYPES == frozenset(
            chembl_yaml["assay"]["relationship_types"]
        )

    def test_assay_groups(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ASSAY_GROUPS

        assert ASSAY_GROUPS == frozenset(chembl_yaml["assay"]["assay_groups"])

    def test_confidence_descriptions(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import CONFIDENCE_DESCRIPTIONS

        assert CONFIDENCE_DESCRIPTIONS == frozenset(
            chembl_yaml["assay"]["confidence_descriptions"]
        )

    def test_assay_parameter_standard_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ASSAY_PARAMETER_STANDARD_TYPES

        expected = frozenset(chembl_yaml["activity"]["standard_types"]) | frozenset(
            chembl_yaml["assay"]["parameter_standard_types"]
        )
        assert ASSAY_PARAMETER_STANDARD_TYPES == expected


class TestMoleculeSync:
    """Molecule enum constants must match YAML."""

    def test_molecule_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import MOLECULE_TYPES

        assert MOLECULE_TYPES == frozenset(chembl_yaml["molecule"]["types"])

    def test_structure_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import STRUCTURE_TYPES

        assert STRUCTURE_TYPES == frozenset(chembl_yaml["molecule"]["structure_types"])

    def test_max_phase_values(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import MAX_PHASE_VALUES

        expected = tuple(float(v) for v in chembl_yaml["molecule"]["max_phase_values"])
        assert MAX_PHASE_VALUES == expected


class TestTargetSync:
    """Target enum constants must match YAML."""

    def test_target_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import TARGET_TYPES

        assert TARGET_TYPES == frozenset(chembl_yaml["target"]["types"])

    def test_target_component_relationships(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import TARGET_COMPONENT_RELATIONSHIPS

        assert TARGET_COMPONENT_RELATIONSHIPS == frozenset(
            chembl_yaml["target"]["component_relationships"]
        )


class TestPublicationSync:
    """Publication enum constants must match YAML."""

    def test_publication_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import PUBLICATION_TYPES

        assert PUBLICATION_TYPES == frozenset(chembl_yaml["publication"]["types"])


class TestUniProtSync:
    """UniProt enum constants must match YAML."""

    def test_uniprot_protein_enums(self, uniprot_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.uniprot._core import (
            ENTRY_TYPES,
            PROTEIN_EXISTENCE_LEVELS,
            PROTEIN_FLAGS,
        )

        assert ENTRY_TYPES == uniprot_yaml["protein"]["entry_types"]
        assert PROTEIN_FLAGS == uniprot_yaml["protein"]["protein_flags"]
        assert (
            PROTEIN_EXISTENCE_LEVELS
            == uniprot_yaml["protein"]["protein_existence_levels"]
        )


class TestConstantInvariants:
    """Structural invariants that must hold regardless of values."""

    def test_assay_parameter_superset_of_activity(self) -> None:
        from bioetl.domain.schemas.constants import (
            ACTIVITY_STANDARD_TYPES,
            ASSAY_PARAMETER_STANDARD_TYPES,
        )

        assert ACTIVITY_STANDARD_TYPES <= ASSAY_PARAMETER_STANDARD_TYPES

    def test_all_frozensets_are_nonempty(self) -> None:
        from bioetl.domain.schemas.constants import (
            ACTIVITY_STANDARD_TYPES,
            ASSAY_CATEGORIES,
            ASSAY_TYPES,
            MOLECULE_TYPES,
            PUBLICATION_TYPES,
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
            PUBLICATION_TYPES,
        ]:
            assert len(const) > 0
