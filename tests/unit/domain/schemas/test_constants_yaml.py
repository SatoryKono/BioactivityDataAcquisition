"""Sync tests: verify domain/schemas/constants.py matches configs/enums/chembl.yaml.

The YAML file is the single source of truth (ADR-035).
These tests catch drift between the YAML config and Python constants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def chembl_yaml() -> dict[str, Any]:
    """Load YAML enum config for comparison."""
    yaml_path = Path("configs/enums/chembl.yaml")
    with yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def uniprot_yaml() -> dict[str, Any]:
    """Load UniProt enum config for comparison."""
    yaml_path = Path("configs/enums/uniprot.yaml")
    with yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def pubchem_yaml() -> dict[str, Any]:
    """Load PubChem enum config for comparison."""
    yaml_path = Path("configs/enums/pubchem.yaml")
    with yaml_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestYamlFileIntegrity:
    """Ensure the YAML enum config exists and is well-formed."""

    def test_chembl_yaml_exists(self) -> None:
        assert Path("configs/enums/chembl.yaml").exists()

    def test_chembl_yaml_has_version(self, chembl_yaml: dict[str, Any]) -> None:
        assert "version" in chembl_yaml

    def test_chembl_yaml_has_all_sections(self, chembl_yaml: dict[str, Any]) -> None:
        expected = {
            "activity",
            "assay",
            "molecule",
            "target",
            "publication",
            "publication_term",
        }
        assert expected <= set(chembl_yaml.keys())

    def test_uniprot_yaml_exists(self) -> None:
        assert Path("configs/enums/uniprot.yaml").exists()

    def test_uniprot_yaml_has_version(self, uniprot_yaml: dict[str, Any]) -> None:
        assert "version" in uniprot_yaml

    def test_pubchem_yaml_exists(self) -> None:
        assert Path("configs/enums/pubchem.yaml").exists()

    def test_pubchem_yaml_has_version(self, pubchem_yaml: dict[str, Any]) -> None:
        assert "version" in pubchem_yaml


class TestActivitySync:
    """Activity enum constants must match YAML."""

    def test_activity_action_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ACTIVITY_ACTION_TYPES

        assert ACTIVITY_ACTION_TYPES == frozenset(
            chembl_yaml["activity"]["action_types"]
        )

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

    def test_activity_standard_units(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ACTIVITY_STANDARD_UNITS

        assert ACTIVITY_STANDARD_UNITS == frozenset(
            chembl_yaml["activity"]["standard_units"]
        )

    def test_activity_mapping_statuses(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import ONTOLOGY_MAPPING_STATUSES

        assert ONTOLOGY_MAPPING_STATUSES == frozenset(
            chembl_yaml["activity"]["mapping_statuses"]
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

    def test_ro3_pass_values(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import RO3_PASS_VALUES

        assert RO3_PASS_VALUES == frozenset(chembl_yaml["molecule"]["ro3_pass_values"])

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

    def test_target_component_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import TARGET_COMPONENT_TYPES

        assert TARGET_COMPONENT_TYPES == frozenset(
            chembl_yaml["target"]["component_types"]
        )


class TestPublicationSync:
    """Publication enum constants must match YAML."""

    def test_publication_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import PUBLICATION_TYPES

        assert PUBLICATION_TYPES == frozenset(chembl_yaml["publication"]["types"])

    def test_publication_native_doc_types_are_declared(
        self, chembl_yaml: dict[str, Any]
    ) -> None:
        assert frozenset(chembl_yaml["publication"]["native_doc_types"]) == frozenset(
            {"PUBLICATION", "PATENT", "DATASET", "BOOK"}
        )

    def test_publication_term_types(self, chembl_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import PUBLICATION_TERM_TYPES

        assert PUBLICATION_TERM_TYPES == frozenset(
            chembl_yaml["publication_term"]["term_types"]
        )


class TestUniProtSync:
    """UniProt enum constants must match YAML."""

    def test_uniprot_protein_enums(self, uniprot_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import (
            UNIPROT_ENTRY_TYPES,
            UNIPROT_PROTEIN_EXISTENCE_LEVELS,
            UNIPROT_PROTEIN_FLAGS,
        )

        assert UNIPROT_ENTRY_TYPES == tuple(uniprot_yaml["protein"]["entry_types"])
        assert UNIPROT_PROTEIN_FLAGS == tuple(uniprot_yaml["protein"]["protein_flags"])
        assert UNIPROT_PROTEIN_EXISTENCE_LEVELS == tuple(
            uniprot_yaml["protein"]["protein_existence_levels"]
        )

    def test_uniprot_idmapping_statuses(self, uniprot_yaml: dict[str, Any]) -> None:
        from bioetl.domain.schemas.constants import UNIPROT_MAPPING_STATUSES

        assert UNIPROT_MAPPING_STATUSES == tuple(
            uniprot_yaml["idmapping"]["mapping_statuses"]
        )


class TestPubChemSync:
    """PubChem enum constants must match YAML."""

    def test_pubchem_standardization_statuses(
        self, pubchem_yaml: dict[str, Any]
    ) -> None:
        from bioetl.domain.schemas.constants import (
            PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES,
        )

        assert PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES == tuple(
            pubchem_yaml["compound"]["chemical_standardization_statuses"]
        )

    def test_pubchem_standardization_policy_version(
        self, pubchem_yaml: dict[str, Any]
    ) -> None:
        from bioetl.domain.schemas.constants import (
            PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,
        )

        assert pubchem_yaml["compound"]["chemical_standardization_policy_versions"] == [
            PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION
        ]


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
            ACTIVITY_STANDARD_UNITS,
            ASSAY_CATEGORIES,
            ASSAY_TYPES,
            MOLECULE_TYPES,
            PUBLICATION_TERM_TYPES,
            PUBLICATION_TYPES,
            RO3_PASS_VALUES,
            STANDARD_RELATIONS,
            TARGET_TYPES,
        )

        for const in [
            STANDARD_RELATIONS,
            ACTIVITY_STANDARD_TYPES,
            ACTIVITY_STANDARD_UNITS,
            ASSAY_TYPES,
            ASSAY_CATEGORIES,
            MOLECULE_TYPES,
            RO3_PASS_VALUES,
            TARGET_TYPES,
            PUBLICATION_TYPES,
            PUBLICATION_TERM_TYPES,
        ]:
            assert len(const) > 0
