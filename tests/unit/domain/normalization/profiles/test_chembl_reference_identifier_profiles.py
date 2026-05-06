"""Shared ChEMBL reference-identifier profile regression coverage."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_PUBLICATION_TERM_PROFILE,
    CHEMBL_TARGET_COMPONENT_PROFILE,
    CHEMBL_TARGET_PROFILE,
)


def test_chembl_activity_profile_uses_shared_reference_identifier_rules() -> None:
    assay_id_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("assay_id")
    taxonomy_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("target_taxonomy_id")
    doi_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("publication_doi")
    pmid_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("publication_pmid")

    assert assay_id_rule is not None
    assert assay_id_rule.apply(" chembl25 ") == "CHEMBL25"

    assert taxonomy_rule is not None
    assert taxonomy_rule.apply(" 9606 ") == 9606

    assert doi_rule is not None
    assert doi_rule.apply(" HTTPS://doi.org/10.1000/ABC123 ") == "10.1000/abc123"

    assert pmid_rule is not None
    assert pmid_rule.apply(" PMID:0012345 ") == "12345"


def test_chembl_target_profiles_use_shared_reference_identifier_rules() -> None:
    component_accessions_rule = CHEMBL_TARGET_PROFILE.rule_for("component_accessions")
    accession_rule = CHEMBL_TARGET_COMPONENT_PROFILE.rule_for("accession")
    taxonomy_rule = CHEMBL_TARGET_COMPONENT_PROFILE.rule_for("taxonomy_id")

    assert component_accessions_rule is not None
    assert (
        component_accessions_rule.apply('[" q9y243 ","P12345"]')
        == '["Q9Y243","P12345"]'
    )

    assert accession_rule is not None
    assert accession_rule.apply(" q9y243 ") == "Q9Y243"

    assert taxonomy_rule is not None
    assert taxonomy_rule.apply(" 10090 ") == 10090


def test_chembl_publication_profiles_use_shared_reference_identifier_rules() -> None:
    doi_rule = CHEMBL_PUBLICATION_PROFILE.rule_for("doi")
    pmid_rule = CHEMBL_PUBLICATION_PROFILE.rule_for("pmid")
    pmc_id_rule = CHEMBL_PUBLICATION_PROFILE.rule_for("pmc_id")
    mesh_rule = CHEMBL_PUBLICATION_TERM_PROFILE.rule_for("mesh_id")
    cell_taxonomy_rule = CHEMBL_CELL_LINE_PROFILE.rule_for("cell_source_taxonomy_id")

    assert doi_rule is not None
    assert doi_rule.apply("doi:10.2000/XYZ") == "10.2000/xyz"

    assert pmid_rule is not None
    assert pmid_rule.apply(12345) == "12345"

    assert pmc_id_rule is not None
    assert pmc_id_rule.apply(" pmc12345 ") == "PMC12345"

    assert mesh_rule is not None
    assert mesh_rule.apply(" d001241 ") == "D001241"

    assert cell_taxonomy_rule is not None
    assert cell_taxonomy_rule.apply(" 9606 ") == 9606
