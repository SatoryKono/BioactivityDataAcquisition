"""
Property-based tests for normalization.
"""

import pytest

pytest.importorskip("hypothesis")
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from bioetl.domain.transform.impl.normalize import normalize_scalar
from bioetl.domain.transform.impl.serializer import serialize_dict, serialize_list


@settings(suppress_health_check=[], database=None)
@given(st.text())
def test_normalize_scalar_idempotent_default(s):
    """Normalizing twice gives same result (idempotency)."""
    n1 = normalize_scalar(s)
    n2 = normalize_scalar(n1)
    # If n1 is None, n2 is None.
    # If n1 is string (lower), n2 is string (lower) -> same.
    assert n1 == n2


@settings(suppress_health_check=[], database=None)
@given(st.text())
def test_normalize_scalar_idempotent_id(s):
    """Normalizing ID twice gives same result."""
    n1 = normalize_scalar(s, mode="id")
    n2 = normalize_scalar(n1, mode="id")
    assert n1 == n2


@settings(suppress_health_check=[], database=None)
@given(st.lists(st.text()))
def test_serialize_list_determinism(lst):
    """Serialization should be deterministic for same input."""
    s1 = serialize_list(lst)
    s2 = serialize_list(lst)
    assert s1 is s2 or s1 == s2


@settings(suppress_health_check=[], database=None)
@given(st.dictionaries(st.text(), st.text()))
def test_serialize_dict_determinism(d):
    """Dictionary serialization sorts keys, so must be deterministic."""
    s1 = serialize_dict(d)
    s2 = serialize_dict(d)

    if pd.isna(s1):
        assert pd.isna(s2)
        return

    assert s1 == s2
    expected = serialize_dict(d)
    if pd.isna(expected):
        assert pd.isna(s1)
    else:
        assert s1 == expected
