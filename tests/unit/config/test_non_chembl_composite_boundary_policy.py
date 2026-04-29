"""Tests for non-ChEMBL composite normalization boundary policy."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: str) -> dict[str, object]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def test_uniprot_reviewed_gold_filter_uses_stringified_boolean_value() -> None:
    config = _load_yaml("configs/entities/uniprot/protein.yaml")

    assert config["filters"]["gold_filters"]["columns"]["reviewed"] == ["True"]


def test_molecule_composite_exposes_pubchem_normalized_structure_anchors() -> None:
    config = _load_yaml("configs/composites/molecule.yaml")
    column_groups = config["composite"]["merge"]["column_groups"]
    identifiers = next(group for group in column_groups if group["name"] == "identifiers")

    assert "standardized_inchi_key" in identifiers["fields"]
    assert "structure_parent_key" in identifiers["fields"]


def test_semanticscholar_dq_conditions_use_derived_publication_taxonomy() -> None:
    config = _load_yaml("configs/entities/semanticscholar/publication.yaml")
    conditional_rules = config["quality"]["entity_conditional_validations"]
    journal_article_rule = next(
        rule for rule in conditional_rules if rule["name"] == "journal_article_requires_title"
    )

    assert journal_article_rule["condition_field"] == "publication_type_unified"
    assert journal_article_rule["condition_value"] == "Journal Article"
