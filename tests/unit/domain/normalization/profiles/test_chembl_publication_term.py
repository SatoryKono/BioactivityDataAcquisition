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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for ChEMBL publication term normalization profile."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles import CHEMBL_PUBLICATION_TERM_PROFILE
from bioetl.domain.schemas.constants import PUBLICATION_TERM_TYPES


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("MESH_HEADING", "MESH_HEADING"),
        ("mesh_qualifier", "MESH_QUALIFIER"),
        (" keyword ", "KEYWORD"),
    ],
)
def test_publication_term_type_profile_canonicalizes_allowed_values(
    raw_value: str, expected: str
) -> None:
    rule = CHEMBL_PUBLICATION_TERM_PROFILE.field_rules["term_type"]

    assert rule.normalizer(raw_value) == expected


def test_publication_term_type_profile_rejects_unknown_values() -> None:
    rule = CHEMBL_PUBLICATION_TERM_PROFILE.field_rules["term_type"]

    assert rule.normalizer("AUTHOR") is None
    assert rule.normalizer("INSTITUTION") is None
    assert rule.normalizer("not-a-term-type") is None


def test_publication_term_type_uses_shared_schema_enum_source() -> None:
    rule = CHEMBL_PUBLICATION_TERM_PROFILE.field_rules["term_type"]

    assert PUBLICATION_TERM_TYPES == frozenset(
        {"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD"}
    )
    assert "enum" in (rule.notes or "").lower()
