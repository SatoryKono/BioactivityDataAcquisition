"""Cross-pipeline case and ontology consistency contracts for ChEMBL profiles."""

from __future__ import annotations

import pytest

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    build_field_matrix_rows,
)
from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_TARGET_COMPONENT_PROFILE,
    CHEMBL_TARGET_PROFILE,
    CHEMBL_TISSUE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    CHEMBL_ONTOLOGY_POLICY_CONFIG,
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def _matrix_row(pipeline_name: str, field_name: str) -> dict[str, str]:
    return next(
        row
        for row in build_field_matrix_rows()
        if row["pipeline_name"] == pipeline_name and row["field_name"] == field_name
    )


@pytest.mark.parametrize(
    ("profile", "field_name", "raw_value", "expected"),
    [
        (CHEMBL_ACTIVITY_PROFILE, "assay_type", " b ", "B"),
        (CHEMBL_ASSAY_PROFILE, "assay_type", " b ", "B"),
        (CHEMBL_ASSAY_PROFILE, "relationship_type", " d ", "D"),
        (CHEMBL_ACTIVITY_PROFILE, "standard_relation", " ≤ ", "<="),
        (CHEMBL_ASSAY_PARAMETERS_PROFILE, "standard_relation", " ≤ ", "<="),
        (CHEMBL_ACTIVITY_PROFILE, "standard_units", " nanomolar ", "nM"),
        (CHEMBL_ASSAY_PARAMETERS_PROFILE, "standard_units", " nanomolar ", "nM"),
        (CHEMBL_MOLECULE_PROFILE, "ro3_pass", " y ", "Y"),
        (CHEMBL_TARGET_PROFILE, "target_type", " single protein ", "SINGLE PROTEIN"),
        (
            CHEMBL_TARGET_COMPONENT_PROFILE,
            "component_type",
            " protein ",
            "PROTEIN",
        ),
    ],
)
def test_chembl_shared_case_families_canonicalize_consistently(
    profile: object,
    field_name: str,
    raw_value: str,
    expected: str,
) -> None:
    """Equivalent ChEMBL field families should collapse to one canonical form."""
    rule = profile.rule_for(field_name)

    assert rule is not None
    assert rule.normalizer(raw_value) == expected


@pytest.mark.parametrize(
    ("profile", "pipeline_name", "field_name", "raw_value", "expected"),
    [
        (
            CHEMBL_ASSAY_PROFILE,
            "chembl_assay",
            "bao_format",
            "bao:0000190",
            "BAO_0000190",
        ),
        (
            CHEMBL_CELL_LINE_PROFILE,
            "chembl_cell_line",
            "clo_id",
            "clo:0000045",
            "CLO_0000045",
        ),
        (
            CHEMBL_CELL_LINE_PROFILE,
            "chembl_cell_line",
            "efo_id",
            "efo:0000319",
            "EFO_0000319",
        ),
        (
            CHEMBL_TISSUE_PROFILE,
            "chembl_tissue",
            "bto_id",
            "bto:0000089",
            "BTO_0000089",
        ),
        (
            CHEMBL_TISSUE_PROFILE,
            "chembl_tissue",
            "efo_id",
            "efo:0000319",
            "EFO_0000319",
        ),
        (
            CHEMBL_TISSUE_PROFILE,
            "chembl_tissue",
            "uberon_id",
            "uberon:0002107",
            "UBERON_0002107",
        ),
    ],
)
def test_chembl_ontology_identifier_families_are_profile_and_matrix_aligned(
    profile: object,
    pipeline_name: str,
    field_name: str,
    raw_value: str,
    expected: str,
) -> None:
    """Ontology-backed ChEMBL IDs should share one canonicalization contract."""
    rule = profile.rule_for(field_name)
    row = _matrix_row(pipeline_name, field_name)

    assert rule is not None
    assert rule.normalizer(raw_value) == expected
    assert row["semantic_category"] == "ontology_reference_identifier"
    assert row["controlled_vocabulary_source"] == CHEMBL_ONTOLOGY_POLICY_CONFIG


def test_chembl_target_has_no_ontology_identifier_family_by_design() -> None:
    """Target remains reference-identifier governed and does not publish ontology IDs."""
    target_ontology_fields = sorted(
        field_ref
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.ontology_families
        for field_ref in family.fields
        if field_ref.startswith("chembl_target.")
    )

    assert target_ontology_fields == []
    taxonomy_row = _matrix_row("chembl_target", "taxonomy_id")
    assert taxonomy_row["semantic_category"] == "reference_identifier"
    assert taxonomy_row["strictness"] == "canonical_identifier"
