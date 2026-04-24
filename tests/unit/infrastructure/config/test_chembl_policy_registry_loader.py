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
                    "    code_label_fields:",
                    "      - chembl_assay.bao_label",
                ]
            ),
            encoding="utf-8",
        )

        data = ChemblPolicyRegistryLoader(tmp_path).load()

        assert data.controlled_vocabularies[0].family_name == "units"
        assert data.controlled_vocabularies[0].fields == ("chembl_activity.units",)
        assert data.ontology_families[0].family_name == "clo"
        assert data.ontology_families[0].code_label_fields == (
            "chembl_assay.bao_label",
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
