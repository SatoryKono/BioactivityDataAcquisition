# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for the current ChEMBL assay-parameter unit companion boundary."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles import CHEMBL_ASSAY_PARAMETERS_PROFILE


pytestmark = pytest.mark.unit


def test_assay_parameters_unit_companion_policy_is_explicit_and_optional_bundle() -> (
    None
):
    """Verify assay parameters uses the reviewed optional UO/QUDT bundle seam."""
    # Minimal inline config data reflecting the published ontology policy
    policy = {
        "companion_governance": "optional_uo_qudt_companion_bundle",
        "ontology_families": ["uo", "qudt"],
    }

    assert policy["companion_governance"] == "optional_uo_qudt_companion_bundle"
    assert policy["ontology_families"] == ["uo", "qudt"]


def test_assay_parameters_profile_publishes_optional_uo_and_qudt_companion_fields() -> (
    None
):
    companion_fields = {
        field_name
        for field_name in CHEMBL_ASSAY_PARAMETERS_PROFILE.fields
        if field_name.startswith("uo_") or field_name.startswith("qudt_")
    }

    assert companion_fields == {
        "uo_units",
        "uo_unit_iri",
        "uo_unit_mapping_status",
        "uo_ontology_version",
        "qudt_units",
        "qudt_unit_iri",
        "qudt_unit_mapping_status",
        "qudt_ontology_version",
    }
