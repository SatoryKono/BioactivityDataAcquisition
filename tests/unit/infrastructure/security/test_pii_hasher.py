"""Unit tests for PII Hasher implementation.

Tests RULES.md §5.4 compliance: Silver layer MUST hash PII fields using
sha256(lowercase(value) + SALT).
"""

from __future__ import annotations

import hashlib
import os
import unicodedata
from unittest.mock import patch

import pytest

from bioetl.domain.ports import PiiHasherPort
from bioetl.domain.ports.noop import NoOpPiiHasher
from bioetl.infrastructure.security.pii_hasher import SaltConfig, Sha256PiiHasher

pytestmark = pytest.mark.unit


class TestSaltConfig:
    """Tests for SaltConfig value object."""

    def test_valid_salt(self) -> None:
        """Test creating SaltConfig with valid salt."""
        salt = "a" * 64
        config = SaltConfig(current_salt=salt)
        assert config.current_salt == salt
        assert config.next_salt is None
        assert config.rotation_active is False

    def test_salt_too_short_raises(self) -> None:
        """Test that short salt raises ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            SaltConfig(current_salt="short")

    def test_empty_salt_raises(self) -> None:
        """Test that empty salt raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SaltConfig(current_salt="")

    def test_from_env(self) -> None:
        """Test creating SaltConfig from environment."""
        salt = "x" * 64
        with patch.dict(
            os.environ,
            {
                "BIOETL_PII_SALT_CURRENT": salt,
                "BIOETL_PII_SALT_NEXT": "y" * 64,
                "BIOETL_SALT_ROTATION_ACTIVE": "true",
            },
        ):
            config = SaltConfig.from_env()
            assert config.current_salt == salt
            assert config.next_salt == "y" * 64
            assert config.rotation_active is True

    def test_from_env_empty_next_salt(self) -> None:
        """Test that empty NEXT salt becomes None."""
        salt = "x" * 64
        with patch.dict(
            os.environ,
            {
                "BIOETL_PII_SALT_CURRENT": salt,
                "BIOETL_PII_SALT_NEXT": "",
            },
            clear=True,
        ):
            config = SaltConfig.from_env()
            assert config.next_salt is None


class TestSha256PiiHasher:
    """Tests for SHA256 PII Hasher implementation."""

    @pytest.fixture
    def hasher(self) -> Sha256PiiHasher:
        """Create a hasher with test salt."""
        config = SaltConfig(current_salt="test_salt_" + "x" * 54)
        return Sha256PiiHasher(salt_config=config)

    def test_implements_port(self, hasher: Sha256PiiHasher) -> None:
        """Test that Sha256PiiHasher implements PiiHasherPort."""
        assert isinstance(hasher, PiiHasherPort)

    def test_hash_value_deterministic(self, hasher: Sha256PiiHasher) -> None:
        """Test that same input produces same hash."""
        hash1 = hasher.hash_value("John Doe")
        hash2 = hasher.hash_value("John Doe")
        assert hash1 == hash2

    def test_hash_value_different_inputs(self, hasher: Sha256PiiHasher) -> None:
        """Test that different inputs produce different hashes."""
        hash1 = hasher.hash_value("John Doe")
        hash2 = hasher.hash_value("Jane Doe")
        assert hash1 != hash2

    def test_hash_value_none_returns_none(self, hasher: Sha256PiiHasher) -> None:
        """Test that None input returns None."""
        assert hasher.hash_value(None) is None

    def test_hash_value_empty_returns_none(self, hasher: Sha256PiiHasher) -> None:
        """Test that empty string returns None."""
        assert hasher.hash_value("") is None

    def test_hash_value_whitespace_only_returns_none(
        self, hasher: Sha256PiiHasher
    ) -> None:
        """Test that whitespace-only string returns None."""
        assert hasher.hash_value("   ") is None
        assert hasher.hash_value("\t\n") is None

    def test_hash_value_case_insensitive(self, hasher: Sha256PiiHasher) -> None:
        """Test that hashing is case-insensitive."""
        hash_upper = hasher.hash_value("JOHN DOE")
        hash_lower = hasher.hash_value("john doe")
        hash_mixed = hasher.hash_value("John Doe")
        assert hash_upper == hash_lower == hash_mixed

    def test_hash_value_strips_whitespace(self, hasher: Sha256PiiHasher) -> None:
        """Test that whitespace is stripped before hashing."""
        hash_clean = hasher.hash_value("John Doe")
        hash_padded = hasher.hash_value("  John Doe  ")
        assert hash_clean == hash_padded

    def test_hash_value_unicode_normalization(self, hasher: Sha256PiiHasher) -> None:
        """Test that unicode is normalized (NFKC) before hashing."""
        # é as single char vs e + combining accent
        composed = "café"
        decomposed = "cafe\u0301"

        # After NFKC normalization, they should be the same
        normalized_composed = unicodedata.normalize("NFKC", composed)
        normalized_decomposed = unicodedata.normalize("NFKC", decomposed)
        assert normalized_composed == normalized_decomposed

        hash1 = hasher.hash_value(composed)
        hash2 = hasher.hash_value(decomposed)
        assert hash1 == hash2

    def test_hash_value_is_sha256_hex(self, hasher: Sha256PiiHasher) -> None:
        """Test that output is valid SHA256 hex digest."""
        result = hasher.hash_value("test")
        assert result is not None
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_value_includes_salt(self) -> None:
        """Test that different salts produce different hashes."""
        config1 = SaltConfig(current_salt="salt1_" + "a" * 58)
        config2 = SaltConfig(current_salt="salt2_" + "b" * 58)

        hasher1 = Sha256PiiHasher(salt_config=config1)
        hasher2 = Sha256PiiHasher(salt_config=config2)

        hash1 = hasher1.hash_value("John Doe")
        hash2 = hasher2.hash_value("John Doe")

        assert hash1 != hash2

    def test_hash_list_basic(self, hasher: Sha256PiiHasher) -> None:
        """Test hashing a list of values."""
        result = hasher.hash_list(["Alice", "Bob", "Charlie"])
        assert result is not None
        assert len(result) == 3
        assert all(len(h) == 64 for h in result)

    def test_hash_list_none_returns_none(self, hasher: Sha256PiiHasher) -> None:
        """Test that None list returns None."""
        assert hasher.hash_list(None) is None

    def test_hash_list_empty_returns_empty(self, hasher: Sha256PiiHasher) -> None:
        """Test that empty list returns empty list."""
        result = hasher.hash_list([])
        assert result == []

    def test_hash_list_filters_none_values(self, hasher: Sha256PiiHasher) -> None:
        """Test that None/empty values in list are filtered out."""
        # hash_value returns None for empty strings
        result = hasher.hash_list(["Alice", "", "Bob", "   "])
        assert result is not None
        assert len(result) == 2  # Only Alice and Bob

    def test_get_salt_id(self, hasher: Sha256PiiHasher) -> None:
        """Test that salt ID is first 8 chars of salt hash."""
        salt_id = hasher.get_salt_id()
        assert len(salt_id) == 8
        assert all(c in "0123456789abcdef" for c in salt_id)

    def test_get_salt_id_deterministic(self, hasher: Sha256PiiHasher) -> None:
        """Test that salt ID is deterministic."""
        id1 = hasher.get_salt_id()
        id2 = hasher.get_salt_id()
        assert id1 == id2

    def test_sha256_pii_hasher__from_env__b0facfb5(self) -> None:
        """Test creating hasher from environment."""
        salt = "env_salt_" + "z" * 55
        with patch.dict(os.environ, {"BIOETL_PII_SALT_CURRENT": salt}):
            hasher = Sha256PiiHasher.from_env()
            assert hasher.salt_config.current_salt == salt


class TestNoOpPiiHasher:
    """Tests for NoOp PII Hasher implementation."""

    @pytest.fixture
    def hasher(self) -> NoOpPiiHasher:
        """Create a NoOp hasher."""
        return NoOpPiiHasher()

    def test_no_op_pii_hasher__implements_port__b7b822fb(
        self, hasher: NoOpPiiHasher
    ) -> None:
        """Test that NoOpPiiHasher implements PiiHasherPort."""
        assert isinstance(hasher, PiiHasherPort)

    def test_no_op_pii_hasher__returns_unchanged__5c18dba9(
        self, hasher: NoOpPiiHasher
    ) -> None:
        """Test that value is returned unchanged."""
        assert hasher.hash_value("John Doe") == "John Doe"

    def test_no_op_pii_hasher__none_returns_none__ec2e2f93(
        self, hasher: NoOpPiiHasher
    ) -> None:
        """Test that None returns None."""
        assert hasher.hash_value(None) is None

    def test_no_op_pii_hasher__returns_unchanged__eab645ca(
        self, hasher: NoOpPiiHasher
    ) -> None:
        """Test that list is returned unchanged."""
        values = ["Alice", "Bob"]
        assert hasher.hash_list(values) == values

    def test_no_op_pii_hasher__none_returns_none__6455eafe(
        self, hasher: NoOpPiiHasher
    ) -> None:
        """Test that None returns None."""
        assert hasher.hash_list(None) is None

    def test_no_op_pii_hasher__get_salt_id__fb899f11(
        self, hasher: NoOpPiiHasher
    ) -> None:
        """Test that salt ID is 'noop'."""
        assert hasher.get_salt_id() == "noop"


class TestPiiHasherAlgorithmCompliance:
    """Tests verifying RULES.md §5.4 compliance.

    Algorithm: sha256(lowercase(value) + SALT)
    """

    def test_algorithm_matches_specification(self) -> None:
        """Verify algorithm matches RULES.md §5.4 specification."""
        salt = "test_salt_for_verification_" + "a" * 37
        config = SaltConfig(current_salt=salt)
        hasher = Sha256PiiHasher(salt_config=config)

        value = "John Doe"

        # Manual computation per spec
        normalized = unicodedata.normalize("NFKC", value).lower().strip()
        data = normalized.encode("utf-8") + salt.encode("utf-8")
        expected_hash = hashlib.sha256(data).hexdigest()

        # Hasher should produce the same result
        actual_hash = hasher.hash_value(value)

        assert actual_hash == expected_hash

    def test_hash_is_salted_not_plain(self) -> None:
        """Verify that hash includes salt (not plain SHA256)."""
        salt = "unique_salt_" + "x" * 52
        config = SaltConfig(current_salt=salt)
        hasher = Sha256PiiHasher(salt_config=config)

        value = "test"

        # Plain SHA256 without salt
        plain_hash = hashlib.sha256(value.encode()).hexdigest()

        # Salted hash from hasher
        salted_hash = hasher.hash_value(value)

        # They MUST be different (proves salt is used)
        assert salted_hash != plain_hash
