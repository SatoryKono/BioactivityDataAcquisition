"""Tests for non-ChEMBL composite normalization boundary policy."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: str) -> dict[str, object]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def test_uniprot_reviewed_gold_filter_uses_boolean_value() -> None:
    config = _load_yaml("configs/entities/uniprot/protein.yaml")

    assert config["filters"]["gold_filters"]["columns"]["reviewed"] == [True]


def test_non_chembl_publication_configs_use_canonical_identifier_names() -> None:
    provider_paths = (
        "configs/entities/crossref/publication.yaml",
        "configs/entities/openalex/publication.yaml",
        "configs/entities/semanticscholar/publication.yaml",
    )

    for path in provider_paths:
        config = _load_yaml(path)
        identifiers = next(
            group
            for group in config["schema"]["column_groups"]
            if group["name"] == "identifiers"
        )

        assert "publication_doi" not in identifiers["fields"]
        assert "publication_pmid" not in identifiers["fields"]
        assert "doi" in identifiers["fields"]


def test_composite_publication_promotes_harmonized_classification() -> None:
    config = _load_yaml("configs/composites/publication.yaml")
    merge = config["composite"]["merge"]
    doc_type = next(
        group for group in merge["column_groups"] if group["name"] == "doc_type"
    )

    for field_name in (
        "publication_type_unified",
        "publication_subclass",
        "publication_class",
    ):
        assert field_name in doc_type["fields"]
        assert field_name in merge["field_priorities"]
        assert f"chembl.publication.{field_name}" not in merge["exclude_fields"]


def test_publication_composite_documents_normalized_identifier_and_title_fallback() -> (
    None
):
    config = _load_yaml("configs/composites/publication.yaml")
    policy = config["composite"]["normalized_join_key_policy"]["publication_identity"]

    assert policy["primary_join_keys"] == ["doi", "pmid"]
    assert policy["fallback_join_keys"] == ["title"]


def test_publication_field_groups_keep_publication_doi_as_chembl_legacy_only() -> None:
    config = _load_yaml("configs/composites/field_groups/publication.yaml")
    id_group = next(
        group for group in config["groups"] if group["id"] == "id_and_status"
    )
    publication_doi = next(
        field for field in id_group["fields"] if field["base_name"] == "publication_doi"
    )

    assert publication_doi["columns"] == ["chembl.publication.publication_doi"]


def test_molecule_composite_exposes_pubchem_normalized_structure_anchors() -> None:
    config = _load_yaml("configs/composites/molecule.yaml")
    column_groups = config["composite"]["merge"]["column_groups"]
    identifiers = next(
        group for group in column_groups if group["name"] == "identifiers"
    )

    assert "standardized_inchi_key" in identifiers["fields"]
    assert "structure_parent_key" in identifiers["fields"]


def test_molecule_composite_documents_pubchem_anchor_boundary() -> None:
    config = _load_yaml("configs/composites/molecule.yaml")
    policy = config["composite"]["normalized_anchor_policy"]["pubchem_compound"][
        "join_boundary"
    ]
    pubchem_enricher = next(
        enricher
        for enricher in config["composite"]["enrichers"]
        if enricher["pipeline"] == "pubchem_compound"
    )

    assert policy["active_join_keys"] == ["inchi_key", "canonical_smiles"]
    assert pubchem_enricher["join_keys"] == policy["active_join_keys"]
    assert set(policy["retained_validation_anchors"]) == {
        "standardized_inchi_key",
        "structure_parent_key",
    }
    assert not set(policy["retained_validation_anchors"]) & set(
        pubchem_enricher["join_keys"]
    )


def test_target_composite_documents_uniprot_idmapping_anchor_boundary() -> None:
    config = _load_yaml("configs/composites/target.yaml")
    policy = config["composite"]["normalized_anchor_policy"]["uniprot_idmapping"][
        "join_boundary"
    ]
    uniprot_protein = next(
        dependency
        for dependency in config["composite"]["dependencies"]
        if dependency["pipeline"] == "uniprot_protein"
    )

    assert policy["source_anchor"] == "target_id"
    assert policy["normalized_output_anchor"] == "uniprot_accession"
    assert policy["required_status"] == "found"
    assert uniprot_protein["join_keys"] == [policy["normalized_output_anchor"]]
    assert uniprot_protein["key_source"] == "uniprot_idmapping"
    assert uniprot_protein["key_filter"] == "mapping_status = 'found'"


def test_target_composite_references_canonical_uniprot_protein_fields() -> None:
    config = _load_yaml("configs/composites/target.yaml")
    exclude_fields = set(config["composite"]["merge"]["exclude_fields"])

    assert "uniprot.protein.features_json" in exclude_fields
    assert "uniprot.protein.features" not in exclude_fields
    assert "uniprot.protein.organism_id" not in exclude_fields


def test_semanticscholar_dq_conditions_use_derived_publication_taxonomy() -> None:
    config = _load_yaml("configs/entities/semanticscholar/publication.yaml")
    conditional_rules = config["quality"]["entity_conditional_validations"]
    journal_article_rule = next(
        rule
        for rule in conditional_rules
        if rule["name"] == "journal_article_requires_title"
    )

    assert journal_article_rule["condition_field"] == "publication_type_unified"
    assert journal_article_rule["condition_value"] == "Journal Article"
