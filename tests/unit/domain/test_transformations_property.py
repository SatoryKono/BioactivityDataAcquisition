"""Property-based tests for domain transformations."""

import math
import pytest
from hypothesis import given, strategies as st, assume

from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    normalize_float,
)


# Strategies
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)

json_values = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
    ),
    max_leaves=20,
)

simple_records = st.dictionaries(
    st.text(min_size=1, max_size=20),
    json_primitives,
    min_size=1,
    max_size=10,
)


class TestContentHashProperties:
    """Property-based tests for content hash generation."""

    @given(simple_records)
    def test_deterministic(self, record):
        """Content hash must be deterministic."""
        hash1 = generate_content_hash(record, "test_provider")
        hash2 = generate_content_hash(record, "test_provider")
        assert hash1 == hash2

    @given(simple_records, st.text(min_size=1, max_size=20))
    def test_different_providers_different_hash(self, record, provider):
        """Different providers should produce different hashes."""
        assume(provider != "chembl")
        hash1 = generate_content_hash(record, "chembl")
        hash2 = generate_content_hash(record, provider)
        assert hash1 != hash2

    @given(simple_records)
    def test_hash_length(self, record):
        """Content hash should be 64 characters (SHA256 hex)."""
        hash_value = generate_content_hash(record, "test")
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    @given(simple_records, simple_records)
    def test_different_records_different_hash(self, record1, record2):
        """Different records should produce different hashes."""
        assume(record1 != record2)
        hash1 = generate_content_hash(record1, "test")
        hash2 = generate_content_hash(record2, "test")
        assert hash1 != hash2


class TestEntityIdProperties:
    """Property-based tests for entity ID generation."""

    @given(st.text(min_size=1, max_size=100), st.text(min_size=1, max_size=20))
    def test_deterministic(self, id_value, provider):
        """Entity ID must be deterministic."""
        record = {"test_id": id_value}
        id1 = generate_entity_id(record, provider, "test_id")
        id2 = generate_entity_id(record, provider, "test_id")
        assert id1 == id2

    @given(st.text(min_size=1, max_size=100))
    def test_format(self, id_value):
        """Entity ID should have provider prefix."""
        record = {"my_id": id_value}
        entity_id = generate_entity_id(record, "chembl", "my_id")
        assert entity_id.startswith("chembl:")


class TestFloatNormalizationProperties:
    """Property-based tests for float normalization."""

    @given(st.floats(allow_nan=True, allow_infinity=True))
    def test_nan_inf_to_none(self, value):
        """NaN and Inf should become None."""
        result = normalize_float(value)
        if math.isnan(value) or math.isinf(value):
            assert result is None
        else:
            assert isinstance(result, float)

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_precision(self, value):
        """Floats should be rounded to 10 decimal places."""
        result = normalize_float(value)
        if result is not None:
            # Check that precision is limited
            assert result == round(value, 10)
