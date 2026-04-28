"""Unit tests for ChemblPolicyRegistryLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.chembl_policy_registry_loader import (
    ChemblPolicyRegistryLoader,
)


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
        assert data.strict_boolean_families[0].fields == (
            "chembl_publication.is_oa",
        )
        assert data.strict_flag_families[0].family_name == "binary_flags"
        assert data.strict_flag_families[0].fields == (
            "chembl_activity.standard_flag",
        )
        assert data.controlled_vocabularies[0].family_name == "units"
        assert data.controlled_vocabularies[0].fields == ("chembl_activity.units",)
        assert data.ontology_families[0].family_name == "clo"
        assert data.ontology_families[0].code_label_fields == (
            "chembl_assay.bao_label",
        )
        assert data.ontology_families[0].iri_fields == ("chembl_cell_line.clo_iri",)
        assert data.ontology_families[0].version_fields == (
            "chembl_cell_line.clo_ontology_version",
        )
        assert data.publication_classification_fields == (
            "publication_type_unified",
            "publication_subclass",
            "publication_class",
        )

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        loader = ChemblPolicyRegistryLoader(tmp_path)
        with pytest.raises(FileNotFoundError):
            loader.load()
