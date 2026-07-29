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
"""Tests for shared ChEMBL normalization-profile vocabularies."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles._chembl_vocab import chembl_enum
from bioetl.domain.schemas.constants import (
    ACTIVITY_STANDARD_TYPES,
    ASSAY_PARAMETER_STANDARD_TYPES,
    ASSAY_TYPES,
    RELATIONSHIP_TYPES,
    RO3_PASS_VALUES,
    STANDARD_RELATIONS,
    TARGET_COMPONENT_TYPES,
)


pytestmark = pytest.mark.unit


def test_chembl_enum_returns_immutable_profile_vocabularies() -> None:
    assert chembl_enum("activity", "standard_type") == ACTIVITY_STANDARD_TYPES
    assert chembl_enum("activity", "assay_type") == ASSAY_TYPES
    assert chembl_enum("assay", "relationship_type") == RELATIONSHIP_TYPES
    assert (
        chembl_enum("assay_parameters", "standard_type")
        == ASSAY_PARAMETER_STANDARD_TYPES
    )
    assert chembl_enum("assay_parameters", "standard_relation") == STANDARD_RELATIONS
    assert chembl_enum("molecule", "ro3_pass") == RO3_PASS_VALUES
    assert chembl_enum("target_component", "component_type") == TARGET_COMPONENT_TYPES
    assert isinstance(chembl_enum("assay", "assay_type"), frozenset)


def test_chembl_enum_fails_for_unknown_vocabularies() -> None:
    with pytest.raises(
        KeyError,
        match=r"Unknown ChEMBL vocabulary activity\.unknown",
    ):
        chembl_enum("activity", "unknown")
