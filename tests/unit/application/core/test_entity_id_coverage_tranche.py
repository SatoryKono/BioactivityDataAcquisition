# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Coverage tranche tests for application-core entity ID helpers (#6480)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.core.entity_id import (
    ENTITY_ID_SCHEME_VERSION,
    compute_publication_term_entity_id,
    compute_subcellular_fraction_entity_id,
)
from bioetl.domain.schemas.constants import (
    PUBLICATION_TERM_TYPES,
    SUBCELLULAR_FRACTIONS,
)


def test_entity_id_scheme_version_is_explicit_v2() -> None:
    """#7777: identity scheme is versioned, not silent."""
    assert ENTITY_ID_SCHEME_VERSION == "v2"


def test_publication_term_entity_id_is_stable_for_known_term_types() -> None:
    term_type = next(iter(PUBLICATION_TERM_TYPES))
    left = compute_publication_term_entity_id("CHEMBL1", term_type, "  Alpha  ")
    right = compute_publication_term_entity_id("CHEMBL1", term_type, "Alpha")
    assert left == right
    assert len(left) == 16


def test_publication_term_entity_id_uppercases_unknown_term_types() -> None:
    """v2: unknown term types are case-folded the same as known types (#7777)."""
    left = compute_publication_term_entity_id("CHEMBL1", "CustomType", "beta")
    right = compute_publication_term_entity_id("CHEMBL1", "customtype", "beta")
    assert left == right
    other = compute_publication_term_entity_id("CHEMBL1", "OtherType", "beta")
    assert left != other


def test_publication_term_entity_id_rejects_empty_normalized_components() -> None:
    """Empty normalized publication-term identity components fail closed."""
    with pytest.raises(ValueError, match="non-empty"):
        compute_publication_term_entity_id("", "TARGET", "Alpha")
    with pytest.raises(ValueError, match="non-empty"):
        compute_publication_term_entity_id("CHEMBL1", "   ", "Alpha")
    with pytest.raises(ValueError, match="non-empty"):
        compute_publication_term_entity_id("CHEMBL1", "TARGET", "   ")


def test_publication_term_entity_id_golden_digest_v2() -> None:
    """Pin the v2 composite digest so identity changes require a scheme bump."""
    digest = compute_publication_term_entity_id("CHEMBL1", "TARGET", "Alpha Kinase")
    assert digest == "3a1a78383545193f"
    assert digest == compute_publication_term_entity_id(
        "CHEMBL1", "target", "Alpha Kinase"
    )
    assert len(digest) == 16
    assert all(ch in "0123456789abcdef" for ch in digest)


def test_subcellular_fraction_entity_id_uses_governed_vocabulary() -> None:
    fraction = next(iter(SUBCELLULAR_FRACTIONS))
    left = compute_subcellular_fraction_entity_id(fraction)
    right = compute_subcellular_fraction_entity_id(fraction.lower())
    assert left == right
    assert len(left) == 16


def test_subcellular_fraction_entity_id_preserves_unknown_values() -> None:
    left = compute_subcellular_fraction_entity_id("unknown-fraction")
    right = compute_subcellular_fraction_entity_id("unknown-fraction")
    assert left == right
    assert left != compute_subcellular_fraction_entity_id("other-fraction")
