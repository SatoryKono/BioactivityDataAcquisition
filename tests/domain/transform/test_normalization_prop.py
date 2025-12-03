"""
Property-based tests for normalization.
"""
from hypothesis import given, strategies as st
import pandas as pd

from bioetl.domain.transform.impl.normalize import normalize_scalar
from bioetl.domain.transform.impl.serializer import serialize_list, serialize_dict


@given(st.text())
def test_normalize_scalar_idempotent_default(s):
    """Normalizing twice gives same result (idempotency)."""
    n1 = normalize_scalar(s)
    n2 = normalize_scalar(n1)
    # If n1 is None, n2 is None.
    # If n1 is string (lower), n2 is string (lower) -> same.
    assert n1 == n2


@given(st.text())
def test_normalize_scalar_idempotent_id(s):
    """Normalizing ID twice gives same result."""
    n1 = normalize_scalar(s, mode="id")
    n2 = normalize_scalar(n1, mode="id")
    assert n1 == n2


@given(st.lists(st.text()))
def test_serialize_list_determinism(lst):
    """Serialization should be deterministic for same input."""
    s1 = serialize_list(lst)
    s2 = serialize_list(lst)
    assert s1 is s2 or s1 == s2


@given(st.dictionaries(st.text(), st.text()))
def test_serialize_dict_determinism(d):
    """Dictionary serialization sorts keys, so must be deterministic."""
    s1 = serialize_dict(d)
    s2 = serialize_dict(d)
    
    # Check determinism (handling pd.NA)
    if pd.isna(s1):
        assert pd.isna(s2)
    else:
        assert s1 == s2
    
    # Check sorting logic by reconstructing expected output
    # This avoids parsing ambiguity with delimiters in keys/values
    parts = []
    for k in sorted(d.keys()):
        v = d[k]
        if v is None:
            continue
        # serialize_dict skips nested types, but st.text() generates strings only
        # It also uses a default normalizer (lambda x: x) if none provided
        # And skips empty strings if they result from normalization? 
        # No, logic is: if val_norm is not pd.NA and val_norm is not None.
        # Empty string is not None/NA.
        
        # logic from serialize_dict:
        # val_norm = norm_func(v) -> v (identity)
        # if val_norm is not pd.NA and val_norm is not None:
        #      parts.append(f"{k}:{val_norm}")
        
        if v is not None:
             parts.append(f"{k}:{v}")
        
    expected = "|".join(parts) if parts else pd.NA
    
    # pd.NA equality check
    if pd.isna(s1):
        assert pd.isna(expected)
    else:
        assert s1 == expected

