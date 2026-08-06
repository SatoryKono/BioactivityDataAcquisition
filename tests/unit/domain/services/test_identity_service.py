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
"""Unit tests for EntityIdentityGenerator.

Tests cover:
- Determinism (same input → same hash)
- Float normalization (round to 10 decimals)
- Meta-field exclusion
- Canonical JSON (sorted keys)
- Entity ID generation from source_id and hash fallback
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.behavior.identity_service import (
    META_FIELDS,
    EntityIdentityGenerator,
)


pytestmark = pytest.mark.unit

_HASH_SAFE_TEXT = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-.:/ ",
    ),
    max_size=32,
)
_BUSINESS_KEY_TEXT = st.text(
    min_size=1,
    max_size=20,
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-.:/ ",
    ),
)
_HASH_SAFE_SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    _HASH_SAFE_TEXT,
)


class TestEntityIdentityGeneratorHashPolicySurface:
    """Public hash-policy collaborator API (#7811)."""

    def test_has_explicit_content_hash_policy_false_by_default(self) -> None:
        service = EntityIdentityGenerator()
        assert service.has_explicit_content_hash_policy() is False

    def test_has_explicit_content_hash_policy_true_with_include(self) -> None:
        service = EntityIdentityGenerator(content_hash_include_fields={"a"})
        assert service.has_explicit_content_hash_policy() is True

    def test_has_explicit_content_hash_policy_true_with_exclude(self) -> None:
        service = EntityIdentityGenerator(content_hash_exclude_fields={"b"})
        assert service.has_explicit_content_hash_policy() is True


class TestEntityIdentityGeneratorDeterminism:
    """Test determinism of content hash generation."""

    def test_same_input_produces_same_hash(self) -> None:
        """Same input should always produce the same content hash."""
        service = EntityIdentityGenerator()
        record = {"field_a": "value1", "field_b": 42, "field_c": 3.14}

        hash1 = service.compute_content_hash("chembl", record)
        hash2 = service.compute_content_hash("chembl", record)

        assert hash1 == hash2
        # ContentHash is a NewType (str alias), check it's a valid hex string
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_different_providers_produce_different_hashes(self) -> None:
        """Different providers should produce different hashes for same data."""
        service = EntityIdentityGenerator()
        record = {"id": "123", "value": 100}

        hash_chembl = service.compute_content_hash("chembl", record)
        hash_pubchem = service.compute_content_hash("pubchem", record)

        assert hash_chembl != hash_pubchem

    def test_field_order_does_not_affect_hash(self) -> None:
        """Field order should not affect hash (canonical JSON uses sorted keys)."""
        service = EntityIdentityGenerator()
        record1 = {"a": 1, "b": 2, "c": 3}
        record2 = {"c": 3, "a": 1, "b": 2}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2


class TestFloatNormalization:
    """Test float normalization for consistent hashing."""

    def test_float_rounded_to_10_decimals(self) -> None:
        """Floats should be rounded to 10 decimal places."""
        service = EntityIdentityGenerator()

        # These should produce the same hash after rounding
        record1 = {"value": 3.14159265358979323846}
        record2 = {"value": 3.1415926536}  # Rounded to 10 decimals

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2

    def test_nan_normalized_to_none(self) -> None:
        """NaN values should be normalized to None."""
        service = EntityIdentityGenerator()
        record_with_nan = {"value": float("nan")}
        record_with_none = {"value": None}

        hash1 = service.compute_content_hash("test", record_with_nan)
        hash2 = service.compute_content_hash("test", record_with_none)

        assert hash1 == hash2

    def test_inf_normalized_to_none(self) -> None:
        """Infinity values should be normalized to None."""
        service = EntityIdentityGenerator()
        record_with_inf = {"value": float("inf")}
        record_with_none = {"value": None}

        hash1 = service.compute_content_hash("test", record_with_inf)
        hash2 = service.compute_content_hash("test", record_with_none)

        assert hash1 == hash2

    def test_negative_inf_normalized_to_none(self) -> None:
        """Negative infinity values should be normalized to None."""
        service = EntityIdentityGenerator()
        record_with_neg_inf = {"value": float("-inf")}
        record_with_none = {"value": None}

        hash1 = service.compute_content_hash("test", record_with_neg_inf)
        hash2 = service.compute_content_hash("test", record_with_none)

        assert hash1 == hash2


class TestMetaFieldExclusion:
    """Test that meta-fields are excluded from hash calculation."""

    @pytest.mark.parametrize(
        "meta_field",
        [
            "_ingestion_ts",
            "_run_id",
            "_run_type",
            "_dq_warn",
            "_dq_error",
            "_source_batch_id",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",
        ],
    )
    def test_meta_field_excluded_from_hash(self, meta_field: str) -> None:
        """Meta-fields should not affect content hash."""
        service = EntityIdentityGenerator()
        base_record = {"id": "123", "value": 100}

        record_with_meta = {**base_record, meta_field: "should_be_ignored"}

        hash_base = service.compute_content_hash("test", base_record)
        hash_with_meta = service.compute_content_hash("test", record_with_meta)

        assert hash_base == hash_with_meta

    def test_all_meta_fields_in_constant(self) -> None:
        """Verify META_FIELDS constant contains expected fields."""
        expected = {
            "_ingestion_ts",
            "_run_id",
            "_run_type",
            "_dq_warn",
            "_dq_error",
            "_source_batch_id",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",
        }
        assert META_FIELDS == expected

    @staticmethod
    @pytest.mark.hypothesis
    # The invariant only depends on metadata exclusion, not on full-Unicode or
    # giant numeric domains. Keep the strategy broad enough for mixed scalars
    # while avoiding expensive Hypothesis constant discovery in the full suite.
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        business_record=st.dictionaries(
            keys=_BUSINESS_KEY_TEXT.filter(lambda key: not key.startswith("_")),
            values=_HASH_SAFE_SCALAR,
            max_size=6,
        ),
        meta_value=_HASH_SAFE_SCALAR,
    )
    def test_hash_is_stable_when_only_metadata_changes(
        business_record: dict[str, object],
        meta_value: object,
    ) -> None:
        """Metadata-only mutations MUST NOT alter content hash."""
        service = EntityIdentityGenerator()
        base_hash = service.compute_content_hash("test", business_record)

        augmented = {
            **business_record,
            "_lookup_method": "doi",
            "_original_id": "pmid:123",
            "_source": "pubmed",
            "_future_meta_field": meta_value,
        }
        augmented_hash = service.compute_content_hash("test", augmented)

        assert base_hash == augmented_hash


class TestCanonicalJSON:
    """Test canonical JSON serialization."""

    def test_nested_dicts_sorted(self) -> None:
        """Nested dictionaries should also have sorted keys."""
        service = EntityIdentityGenerator()
        record1 = {"outer": {"z": 1, "a": 2}}
        record2 = {"outer": {"a": 2, "z": 1}}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2

    def test_list_order_preserved(self) -> None:
        """List order should be preserved (not sorted)."""
        service = EntityIdentityGenerator()
        record1 = {"items": [1, 2, 3]}
        record2 = {"items": [3, 2, 1]}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        # Different order should produce different hashes
        assert hash1 != hash2


class TestDateNormalization:
    """Test date/datetime normalization."""

    def test_datetime_normalized_to_date_iso(self) -> None:
        """Datetime should be normalized to date ISO string with v1_date policy."""
        service = EntityIdentityGenerator()

        # Different times on same date should produce same hash with v1_date policy
        dt1 = datetime(2024, 1, 15, 10, 30, 0)
        dt2 = datetime(2024, 1, 15, 23, 59, 59)

        record1 = {"timestamp": dt1}
        record2 = {"timestamp": dt2}

        # Use v1_date policy to collapse datetime to date-only
        hash1 = service.compute_content_hash("test", record1, datetime_policy="v1_date")
        hash2 = service.compute_content_hash("test", record2, datetime_policy="v1_date")

        assert hash1 == hash2

    def test_date_normalized_to_iso(self) -> None:
        """Date should be normalized to ISO string."""
        service = EntityIdentityGenerator()
        d = date(2024, 1, 15)

        record = {"date_field": d}
        normalized = service._normalize_for_hash(record)

        assert normalized["date_field"] == "2024-01-15"


class TestStringNormalization:
    """Test string normalization."""

    def test_string_stripped(self) -> None:
        """Strings should be stripped of whitespace."""
        service = EntityIdentityGenerator()
        record1 = {"name": "  test  "}
        record2 = {"name": "test"}

        hash1 = service.compute_content_hash("test", record1)
        hash2 = service.compute_content_hash("test", record2)

        assert hash1 == hash2


class TestEntityIdGeneration:
    """Test entity ID generation."""

    def test_entity_id_with_source_id(self) -> None:
        """Entity ID should use source_id when provided."""
        service = EntityIdentityGenerator()

        entity_id = service.compute_entity_id(
            provider="chembl",
            entity_type="activity",
            source_id="12345",
            record={"any": "data"},
        )

        assert entity_id == "chembl:12345"

    def test_entity_id_without_source_id_uses_hash(self) -> None:
        """Entity ID should use hash prefix when source_id is None."""
        service = EntityIdentityGenerator()

        entity_id = service.compute_entity_id(
            provider="chembl",
            entity_type="activity",
            source_id=None,
            record={"field": "value"},
        )

        # Should start with provider and be based on hash
        assert str(entity_id).startswith("chembl:")
        # Hash prefix should be 16 characters
        assert len(str(entity_id)) == len("chembl:") + 16

    def test_entity_id_generation__entity_id_format__1592b928(self) -> None:
        """Entity ID should have correct format."""
        service = EntityIdentityGenerator()

        entity_id = service.compute_entity_id(
            provider="pubchem",
            entity_type="compound",
            source_id="CID123",
            record={},
        )

        # EntityID is a NewType (str alias)
        assert isinstance(entity_id, str)
        assert entity_id == "pubchem:CID123"

    def test_entity_id_deterministic_without_source(self) -> None:
        """Entity ID without source_id should be deterministic."""
        service = EntityIdentityGenerator()
        record = {"stable": "data"}

        id1 = service.compute_entity_id("test", "entity", None, record)
        id2 = service.compute_entity_id("test", "entity", None, record)

        assert id1 == id2


class TestExcludeNone:
    """Test exclude_none parameter behavior."""

    def test_exclude_none_true(self) -> None:
        """When exclude_none=True, None values should be excluded."""
        service = EntityIdentityGenerator()
        record_with_none = {"a": 1, "b": None}
        record_without_none = {"a": 1}

        hash1 = service.compute_content_hash(
            "test", record_with_none, exclude_none=True
        )
        hash2 = service.compute_content_hash(
            "test", record_without_none, exclude_none=True
        )

        assert hash1 == hash2

    def test_exclude_none_false(self) -> None:
        """When exclude_none=False, None values should be included."""
        service = EntityIdentityGenerator()
        record_with_none = {"a": 1, "b": None}
        record_without_none = {"a": 1}

        hash1 = service.compute_content_hash(
            "test", record_with_none, exclude_none=False
        )
        hash2 = service.compute_content_hash(
            "test", record_without_none, exclude_none=False
        )

        assert hash1 != hash2


class TestNestedStructures:
    """Test normalization of nested structures."""

    def test_nested_dict_normalized(self) -> None:
        """Nested dicts should be normalized recursively."""
        service = EntityIdentityGenerator()
        record = {"outer": {"inner": {"value": 3.14159265358979}}}

        normalized = service._normalize_for_hash(record)

        # Float should be rounded
        assert normalized["outer"]["inner"]["value"] == round(3.14159265358979, 10)

    def test_nested_list_normalized(self) -> None:
        """Lists should have elements normalized recursively."""
        service = EntityIdentityGenerator()
        record = {"items": [1.23456789012345, "  text  ", {"key": float("nan")}]}

        normalized = service._normalize_for_hash(record)

        assert normalized["items"][0] == round(1.23456789012345, 10)
        assert normalized["items"][1] == "text"
        assert normalized["items"][2]["key"] is None


class TestHashFormat:
    """Test hash output format."""

    def test_hash_is_sha256_hex(self) -> None:
        """Hash should be SHA256 hex digest (64 characters)."""
        service = EntityIdentityGenerator()
        content_hash = service.compute_content_hash("test", {"id": "123"})

        assert len(str(content_hash)) == 64
        assert all(c in "0123456789abcdef" for c in str(content_hash))


class TestServiceStateless:
    """Test that service is stateless and reusable."""

    def test_multiple_calls_independent(self) -> None:
        """Multiple calls should be independent (no state)."""
        service = EntityIdentityGenerator()

        hash1 = service.compute_content_hash("provider1", {"a": 1})
        hash2 = service.compute_content_hash("provider2", {"b": 2})
        hash3 = service.compute_content_hash("provider1", {"a": 1})

        # First and third should be equal (same input)
        assert hash1 == hash3
        # Different inputs should be different
        assert hash1 != hash2
