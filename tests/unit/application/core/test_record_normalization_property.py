"""Hypothesis properties for pure identity/hash normalization (T-11 / #6606)."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

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
