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
"""Regression tests for pseudo-null handling in the ChEMBL assay profile."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles import CHEMBL_ASSAY_PROFILE

pytestmark = pytest.mark.unit

_PSEUDO_NULLS = ("N/A", "None", "-", ".", "<NULL>", "UNKNOWN")
_DIRECT_NULL_FIELDS = (
    "assay_type_description",
    "relationship_description",
    "assay_pref_name",
    "assay_cell_type",
    "assay_tissue",
    "assay_strain",
)
_SPECIAL_RULE_NULL_FIELDS = (
    "confidence_description",
    "assay_organism",
)


@pytest.mark.parametrize("field_name", _DIRECT_NULL_FIELDS + _SPECIAL_RULE_NULL_FIELDS)
@pytest.mark.parametrize("pseudo_null", _PSEUDO_NULLS)
def test_chembl_assay_pseudo_null_fields_collapse_common_tokens_to_none(
    field_name: str,
    pseudo_null: str,
) -> None:
    rule = CHEMBL_ASSAY_PROFILE.rule_for(field_name)

    assert rule is not None
    assert rule.normalizer(pseudo_null) is None
    assert "pseudo-null" in (rule.notes or "").lower()


def test_chembl_assay_confidence_description_keeps_controlled_vocab_behavior_after_null_guard() -> (
    None
):
    rule = CHEMBL_ASSAY_PROFILE.rule_for("confidence_description")

    assert rule is not None
    assert (
        rule.normalizer(" direct single protein target assigned ")
        == "Direct single protein target assigned"
    )
    assert rule.normalizer("mystery confidence") is None


def test_chembl_assay_organism_keeps_curated_normalization_after_null_guard() -> None:
    rule = CHEMBL_ASSAY_PROFILE.rule_for("assay_organism")

    assert rule is not None
    assert rule.normalizer("  homo   sapiens ") == "Homo sapiens"
    assert rule.normalizer("e. coli") == "Escherichia coli"
