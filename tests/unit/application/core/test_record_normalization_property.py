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
"""Hypothesis properties for pure identity/hash normalization (T-11 / #6606)."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.application.composite._coalesce_policy_support import (
    extract_field_from_qualified,
)
from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.normalization.identifiers import normalize_doi

pytestmark = [pytest.mark.unit, pytest.mark.hypothesis]

_TEXT = st.text(
    min_size=1,
    max_size=16,
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_",
    ),
)
_SCALAR = st.one_of(
    st.booleans(),
    st.integers(min_value=-10_000, max_value=10_000),
    _TEXT,
)
_PROPERTY_SETTINGS = settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@_PROPERTY_SETTINGS
@given(
    provider=_TEXT,
    payload=st.dictionaries(keys=_TEXT, values=_SCALAR, min_size=1, max_size=6),
)
def test_identity_content_hash_is_deterministic(
    provider: str,
    payload: dict[str, object],
) -> None:
    service = EntityIdentityGenerator()
    first = service.compute_content_hash(provider, dict(payload))
    second = service.compute_content_hash(provider, dict(payload))
    assert first == second
    assert len(str(first)) == 64


@_PROPERTY_SETTINGS
@given(raw=_TEXT)
def test_normalize_doi_is_idempotent_for_plain_tokens(raw: str) -> None:
    once = normalize_doi(raw)
    twice = normalize_doi(once) if once is not None else None
    assert once == twice


@_PROPERTY_SETTINGS
@given(
    a=_TEXT,
    b=_TEXT,
    c=_TEXT,
)
def test_extract_field_from_qualified_is_deterministic(a: str, b: str, c: str) -> None:
    """Pure coalesce helper: qualified x.y.z extracts z; other shapes are stable."""
    qualified = f"{a}.{b}.{c}"
    assert extract_field_from_qualified(qualified) == c
    plain = f"{a}_{b}"
    assert extract_field_from_qualified(plain) == plain
