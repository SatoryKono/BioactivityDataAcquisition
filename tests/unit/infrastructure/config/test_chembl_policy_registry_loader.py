"""Unit tests for ChemblPolicyRegistryLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.chembl_policy_registry_loader import (
    ChemblPolicyRegistryLoader,
)


pytestmark = pytest.mark.unit

class TestChemblPolicyRegistryLoader:
    """Tests for config-backed ChEMBL semantic-policy loading."""

    def test_loads_controlled_and_ontology_policies(self, tmp_path: Path) -> None:
        vocab_dir = tmp_path / "vocab"
        vocab_dir.mkdir()
        (vocab_dir / "chembl_controlled.yaml").write_text(
            "\n".join(
                [
                    "strict_boolean_families:",
                    "  bool_like:",
                    "    invalid_value_mode: coerce_common_boolean_lexemes",
                    "    fields:",
                    "      - chembl_publication.is_oa",
                    "strict_flag_families:",
                    "  binary_flags:",
                    "    invalid_value_mode: coerce_common_flag_lexemes",
                    "    fields:",
                    "      - chembl_activity.standard_flag",
                    "controlled_vocabularies:",
                    "  units:",
                    "    invalid_value_mode: preserve_unknown_lexeme",
                    "    fields:",
                    "      - chembl_activity.units",
                ]
            ),
            encoding="utf-8",
        )
        (vocab_dir / "chembl_ontology.yaml").write_text(
            "\n".join(
                [
                    "families:",
                    "  clo:",
                    "    fields:",
                    "      - chembl_cell_line.clo_id",
                    "    companion_fields:",
                    "      iri:",
                    "        - chembl_cell_line.clo_iri",
                    "      mapping_status:",
                    "        - chembl_cell_line.clo_mapping_status",
                    "      version:",
                    "        - chembl_cell_line.clo_ontology_version",
                    "    code_label_fields:",
                    "      - chembl_assay.bao_label",
                ]
            ),
            encoding="utf-8",
        )

        data = ChemblPolicyRegistryLoader(tmp_path).load()

        assert data.strict_boolean_families[0].family_name == "bool_like"
        assert data.strict_boolean_families[0].fields == ("chembl_publication.is_oa",)
        assert data.strict_flag_families[0].family_name == "binary_flags"
        assert data.strict_flag_families[0].fields == ("chembl_activity.standard_flag",)
        assert data.controlled_vocabularies[0].family_name == "units"
        assert data.controlled_vocabularies[0].fields == ("chembl_activity.units",)
        assert data.ontology_families[0].family_name == "clo"
        assert data.ontology_families[0].code_label_fields == (
            "chembl_assay.bao_label",
        )
        assert data.ontology_families[0].iri_fields == ("chembl_cell_line.clo_iri",)
        assert data.ontology_families[0].mapping_status_fields == (
            "chembl_cell_line.clo_mapping_status",
        )
        assert data.ontology_families[0].version_fields == (
            "chembl_cell_line.clo_ontology_version",
        )
        assert data.publication_classification_fields == (
            "publication_type_unified",
            "publication_subclass",
            "publication_class",
        )

    def test_merges_unit_companion_policies_into_ontology_families(
        self,
        tmp_path: Path,
    ) -> None:
        vocab_dir = tmp_path / "vocab"
        vocab_dir.mkdir()
        (vocab_dir / "chembl_controlled.yaml").write_text(
            "controlled_vocabularies: {}\n",
            encoding="utf-8",
        )
        (vocab_dir / "chembl_ontology.yaml").write_text(
            "\n".join(
                [
                    "families:",
                    "  uo:",
                    "    fields:",
                    "      - chembl_activity.uo_units",
                    "    companion_fields:",
                    "      iri:",
                    "        - chembl_activity.uo_unit_iri",
                    "      mapping_status:",
                    "        - chembl_activity.uo_unit_mapping_status",
                    "      version:",
                    "        - chembl_activity.uo_ontology_version",
                    "  qudt:",
                    "    fields:",
                    "      - chembl_activity.qudt_units",
                    "    companion_fields:",
                    "      iri:",
                    "        - chembl_activity.qudt_unit_iri",
                    "      mapping_status:",
                    "        - chembl_activity.qudt_unit_mapping_status",
                    "      version:",
                    "        - chembl_activity.qudt_ontology_version",
                    "unit_companion_policies:",
                    "  chembl_assay_parameters:",
                    "    fields:",
                    "      - chembl_assay_parameters.uo_units",
                    "      - chembl_assay_parameters.qudt_units",
                    "    ontology_families:",
                    "      - uo",
                    "      - qudt",
                ]
            ),
            encoding="utf-8",
        )
        (vocab_dir / "chembl_reference_identifiers.yaml").write_text(
            "reference_identifier_families: {}\n",
            encoding="utf-8",
        )

        data = ChemblPolicyRegistryLoader(tmp_path).load()

        uo_family = next(
            family for family in data.ontology_families if family.family_name == "uo"
        )
        assert uo_family.fields == (
            "chembl_activity.uo_units",
            "chembl_assay_parameters.uo_units",
        )
        assert uo_family.iri_fields == (
            "chembl_activity.uo_unit_iri",
            "chembl_assay_parameters.uo_unit_iri",
        )
        assert uo_family.mapping_status_fields == (
            "chembl_activity.uo_unit_mapping_status",
            "chembl_assay_parameters.uo_unit_mapping_status",
        )
        assert uo_family.version_fields == (
            "chembl_activity.uo_ontology_version",
            "chembl_assay_parameters.uo_ontology_version",
        )

        qudt_family = next(
            family for family in data.ontology_families if family.family_name == "qudt"
        )
        assert qudt_family.fields == (
            "chembl_activity.qudt_units",
            "chembl_assay_parameters.qudt_units",
        )
        assert qudt_family.iri_fields == (
            "chembl_activity.qudt_unit_iri",
            "chembl_assay_parameters.qudt_unit_iri",
        )
        assert qudt_family.mapping_status_fields == (
            "chembl_activity.qudt_unit_mapping_status",
            "chembl_assay_parameters.qudt_unit_mapping_status",
        )
        assert qudt_family.version_fields == (
            "chembl_activity.qudt_ontology_version",
            "chembl_assay_parameters.qudt_ontology_version",
        )

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        loader = ChemblPolicyRegistryLoader(tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load()
