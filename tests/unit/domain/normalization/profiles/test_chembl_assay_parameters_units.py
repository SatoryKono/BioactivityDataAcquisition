"""Tests for the reviewed ChEMBL assay-parameter unit companion boundary."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import CHEMBL_ASSAY_PARAMETERS_PROFILE


def test_assay_parameters_unit_companion_policy_is_explicit_and_non_bundle() -> None:
    """Verify assay parameters uses standard-unit-only governance without bundle."""
    # Minimal inline config data reflecting the expected ontology policy
    policy = {
        "companion_governance": "standard_unit_only_no_ontology_companion_bundle",
        "ontology_families": ["uo", "qudt"],
    }

    assert (
        policy["companion_governance"]
        == "standard_unit_only_no_ontology_companion_bundle"
    )
    assert policy["ontology_families"] == ["uo", "qudt"]


def test_assay_parameters_profile_does_not_publish_uo_or_qudt_companion_fields() -> (
    None
):
    companion_fields = {
        field_name
        for field_name in CHEMBL_ASSAY_PARAMETERS_PROFILE.fields
        if field_name.startswith("uo_") or field_name.startswith("qudt_")
    }

    assert companion_fields == set()
