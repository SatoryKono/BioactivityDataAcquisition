"""
Property-based tests for normalization.

Tests verify key invariants:
- Idempotency: f(f(x)) == f(x)
- Determinism: f(x) always returns same result
- Type invariants: output types match contracts
- Format invariants: normalized values match expected patterns
"""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import assume, given, settings, strategies as st
import pandas as pd

from bioetl.domain.transform.serializers import (
    serialize_dict,
    serialize_list,
)
from bioetl.domain.transform.normalizers.identifiers import (
    normalize_chembl_id,
    normalize_doi,
    normalize_pmid,
    normalize_pcid,
)
from bioetl.domain.transform.normalizers.numeric import normalize_clinical_phase
from bioetl.infrastructure.transform.impl.normalize import normalize_scalar


# =============================================================================
# Scalar Normalization Property Tests
# =============================================================================


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


# =============================================================================
# Serialization Determinism Property Tests
# =============================================================================


@settings(suppress_health_check=[], database=None)
@given(st.lists(st.text()))
def test_serialize_list_determinism(lst):
    """Serialization should be deterministic for same input."""
    s1 = serialize_list(lst)
    s2 = serialize_list(lst)
    assert s1 is s2 or s1 == s2


@settings(suppress_health_check=[], database=None)
@given(st.dictionaries(st.text(), st.text()))
def test_serialize_dict_determinism_prop(d):
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


# =============================================================================
# ChEMBL ID Normalizer Property Tests
# =============================================================================


# Strategy for valid ChEMBL ID numeric parts
chembl_digits = st.integers(min_value=1, max_value=9999999999)


@settings(suppress_health_check=[], database=None)
@given(chembl_digits)
def test_chembl_id_idempotent(num):
    """ChEMBL ID normalization is idempotent."""
    # Start with just digits
    n1 = normalize_chembl_id(str(num))
    n2 = normalize_chembl_id(n1)
    assert n1 == n2


@settings(suppress_health_check=[], database=None)
@given(chembl_digits)
def test_chembl_id_format_invariant(num):
    """Normalized ChEMBL IDs always start with 'CHEMBL' prefix."""
    result = normalize_chembl_id(str(num))
    assert result is not None
    assert result.startswith("CHEMBL")
    assert result[6:].isdigit()  # After prefix must be digits


@settings(suppress_health_check=[], database=None)
@given(st.sampled_from(["chembl", "CHEMBL", "ChEmBl"]), chembl_digits)
def test_chembl_id_case_insensitive(prefix, num):
    """ChEMBL ID normalization handles case variations."""
    result = normalize_chembl_id(f"{prefix}{num}")
    assert result == f"CHEMBL{num}"


# =============================================================================
# Clinical Phase Normalizer Property Tests
# =============================================================================


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=0, max_value=4))
def test_clinical_phase_valid_range_preserved(phase):
    """Valid clinical phases (0-4) are preserved."""
    result = normalize_clinical_phase(phase)
    assert result == phase


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=5, max_value=100))
def test_clinical_phase_out_of_range_returns_none(phase):
    """Clinical phases > 4 return None."""
    result = normalize_clinical_phase(phase)
    assert result is None


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=-100, max_value=-1))
def test_clinical_phase_negative_returns_none(phase):
    """Negative clinical phases return None."""
    result = normalize_clinical_phase(phase)
    assert result is None


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=0, max_value=4))
def test_clinical_phase_idempotent(phase):
    """Clinical phase normalization is idempotent."""
    n1 = normalize_clinical_phase(phase)
    n2 = normalize_clinical_phase(n1)
    assert n1 == n2


@settings(suppress_health_check=[], database=None)
@given(st.floats(min_value=0.0, max_value=4.0))
def test_clinical_phase_float_handling(phase):
    """Floats are converted only if they're whole numbers in range."""
    result = normalize_clinical_phase(phase)
    if phase == phase and phase.is_integer() and 0 <= phase <= 4:
        # Valid integer float
        assert result == int(phase)
    else:
        # Non-integer or out of range
        assert result is None


# =============================================================================
# PMID Normalizer Property Tests
# =============================================================================


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=1, max_value=99999999))
def test_pmid_returns_int(num):
    """PMID normalizer always returns int for valid inputs."""
    result = normalize_pmid(num)
    assert isinstance(result, int)
    assert result == num


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=1, max_value=99999999))
def test_pmid_string_conversion(num):
    """PMID normalizer handles string inputs."""
    result = normalize_pmid(str(num))
    assert result == num


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=1, max_value=99999999))
def test_pmid_idempotent(num):
    """PMID normalization is idempotent."""
    n1 = normalize_pmid(num)
    n2 = normalize_pmid(n1)
    assert n1 == n2


# =============================================================================
# PubChem CID Normalizer Property Tests
# =============================================================================


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=1, max_value=99999999))
def test_pcid_returns_int(num):
    """PCID normalizer always returns int for valid inputs."""
    result = normalize_pcid(num)
    assert isinstance(result, int)
    assert result == num


@settings(suppress_health_check=[], database=None)
@given(st.integers(min_value=1, max_value=99999999))
def test_pcid_strips_prefix(num):
    """PCID normalizer strips CID/PCID prefixes."""
    result_cid = normalize_pcid(f"CID{num}")
    result_pcid = normalize_pcid(f"PCID{num}")
    result_plain = normalize_pcid(num)
    assert result_cid == result_pcid == result_plain == num


# =============================================================================
# DOI Normalizer Property Tests
# =============================================================================


# Strategy for valid DOI suffixes (simplified)
doi_suffix = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=".-_/"),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() and not x.startswith("/"))


@settings(suppress_health_check=[], database=None, max_examples=50)
@given(st.integers(min_value=1000, max_value=999999999), doi_suffix)
def test_doi_idempotent(prefix_num, suffix):
    """DOI normalization is idempotent for valid DOIs."""
    assume(suffix and suffix.strip())
    doi = f"10.{prefix_num}/{suffix}"
    try:
        n1 = normalize_doi(doi)
        if n1 is not None:
            n2 = normalize_doi(n1)
            assert n1 == n2
    except ValueError:
        pass  # Invalid DOI format, skip


@settings(suppress_health_check=[], database=None, max_examples=50)
@given(st.integers(min_value=1000, max_value=999999999), doi_suffix)
def test_doi_lowercase_output(prefix_num, suffix):
    """DOI normalization outputs lowercase."""
    assume(suffix and suffix.strip())
    doi = f"10.{prefix_num}/{suffix.upper()}"
    try:
        result = normalize_doi(doi)
        if result is not None:
            assert result == result.lower()
    except ValueError:
        pass  # Invalid DOI format, skip


@settings(suppress_health_check=[], database=None, max_examples=50)
@given(
    st.sampled_from(["https://doi.org/", "http://dx.doi.org/", "DOI:", ""]),
    st.integers(min_value=1000, max_value=999999999),
    doi_suffix,
)
def test_doi_prefix_stripping(url_prefix, prefix_num, suffix):
    """DOI normalization strips URL and DOI: prefixes."""
    assume(suffix and suffix.strip())
    doi_core = f"10.{prefix_num}/{suffix}"
    doi_with_prefix = f"{url_prefix}{doi_core}"
    try:
        result = normalize_doi(doi_with_prefix)
        if result is not None:
            assert result == doi_core.lower()
    except ValueError:
        pass  # Invalid DOI format, skip
