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
"""Property-based invariants for identifier/normalization helpers (TEST-SYS-08 / #7030)."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.normalization.profiles import (
    _profile_governed_value_normalizers as normalizers,
)
from bioetl.domain.normalization.rules import normalize_case
from bioetl.domain.normalization.text import normalize_string

pytestmark = [pytest.mark.hypothesis, pytest.mark.unit]

_ALLOWED = frozenset({"active", "inactive", "unknown"})
_TEXT = st.text(
    min_size=0,
    max_size=24,
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters=" -_\t",
    ),
)


@settings(
    deadline=None,
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
)
@given(value=_TEXT)
def test_mapping_status_idempotent_on_canonical_outputs(value: str) -> None:
    first = normalizers.normalize_profile_mapping_status(value, allowed_values=_ALLOWED)
    if first is None:
        return
    second = normalizers.normalize_profile_mapping_status(
        first, allowed_values=_ALLOWED
    )
    assert second == first
    assert isinstance(second, str)
    assert second == second.casefold()


@settings(
    deadline=None,
    max_examples=40,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
)
@given(
    value=st.one_of(st.none(), st.integers(), st.booleans(), st.floats(allow_nan=False))
)
def test_mapping_status_rejects_non_strings(value: object) -> None:
    assert (
        normalizers.normalize_profile_mapping_status(value, allowed_values=_ALLOWED)
        is None
    )


@settings(
    deadline=None,
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
)
@given(value=_TEXT)
def test_normalize_string_then_case_is_stable_for_allowed(value: str) -> None:
    cleaned = normalize_string(value)
    if cleaned is None:
        return
    allowed = frozenset({cleaned.upper(), cleaned.casefold(), cleaned})
    # normalize_case against a set containing the cleaned form should be deterministic.
    once = normalize_case(cleaned, allowed)
    twice = normalize_case(str(once) if once is not None else cleaned, allowed)
    assert once == twice
