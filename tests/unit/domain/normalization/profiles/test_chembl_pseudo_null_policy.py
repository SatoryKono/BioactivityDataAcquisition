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
"""Tests for the ChEMBL pseudo-null normalization coverage matrix."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    CHEMBL_PSEUDO_NULL_FIELDS,
)
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
)

_PSEUDO_NULL_EXAMPLES = ("N/A", "None", "-", "<NULL>", "UNKNOWN")


@pytest.mark.parametrize("entity", sorted(CHEMBL_PSEUDO_NULL_FIELDS))
def test_chembl_pseudo_null_matrix_has_a_registered_profile(entity: str) -> None:
    """Every matrix row must correspond to a shipped ChEMBL profile."""
    assert ("chembl", entity) in NORMALIZATION_PROFILE_REGISTRY


@pytest.mark.parametrize(
    ("entity", "field_name"),
    [
        (entity, field_name)
        for entity, fields in sorted(CHEMBL_PSEUDO_NULL_FIELDS.items())
        for field_name in sorted(fields)
    ],
)
def test_chembl_pseudo_null_fields_are_schema_covered(
    entity: str,
    field_name: str,
) -> None:
    """Matrix fields must be covered by profile field rules."""
    profile = NORMALIZATION_PROFILE_REGISTRY[("chembl", entity)]

    assert field_name in profile.field_rules


@pytest.mark.parametrize(
    ("entity", "field_name", "pseudo_null"),
    [
        (entity, field_name, pseudo_null)
        for entity, fields in sorted(CHEMBL_PSEUDO_NULL_FIELDS.items())
        for field_name in sorted(fields)
        for pseudo_null in _PSEUDO_NULL_EXAMPLES
    ],
)
def test_chembl_pseudo_null_fields_collapse_to_none(
    entity: str,
    field_name: str,
    pseudo_null: str,
) -> None:
    """All matrix fields must collapse common ChEMBL pseudo-null tokens."""
    profile = NORMALIZATION_PROFILE_REGISTRY[("chembl", entity)]
    rule = profile.rule_for(field_name)

    assert rule is not None
    assert rule.normalizer(pseudo_null) is None
