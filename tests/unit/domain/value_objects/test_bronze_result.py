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
"""Unit tests for BronzeWriteResult value object."""

from __future__ import annotations


import pytest
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

from bioetl.domain.types import BatchID
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


def _make_batch_id() -> BatchID:
    return deterministic_batch_uuid_from_callsite("test_bronze_result")


def _make_valid_result(**overrides) -> BronzeWriteResult:
    """Create a valid BronzeWriteResult with optional field overrides."""
    kwargs = {
        "batch_id": _make_batch_id(),
        "relative_path": "chembl/activity/2024-01-15/batch_abc.jsonl.zst",
        "absolute_path": "/data/output/bronze/chembl/activity/2024-01-15/batch_abc.jsonl.zst",
        "record_count": 1000,
        "compressed_size": 50000,
        "uncompressed_size": 200000,
        "checksum_blake2": "abc123deadbeef",
    }
    kwargs.update(overrides)
    return BronzeWriteResult(**kwargs)


@pytest.mark.unit
class TestBronzeWriteResultCreation:
    """Tests for BronzeWriteResult construction."""

    def test_write_result_creation__valid_creation__af018ff1(self) -> None:
        """Test creating a valid BronzeWriteResult."""
        result = _make_valid_result()
        assert result.record_count == 1000
        assert result.compressed_size == 50000
        assert result.uncompressed_size == 200000
        assert result.checksum_blake2 == "abc123deadbeef"

    def test_zero_record_count_is_valid(self) -> None:
        """Test that record_count of 0 is allowed."""
        result = _make_valid_result(record_count=0)
        assert result.record_count == 0

    def test_zero_sizes_are_valid(self) -> None:
        """Test that zero compressed/uncompressed sizes are allowed."""
        result = _make_valid_result(compressed_size=0, uncompressed_size=0)
        assert result.compressed_size == 0

    def test_write_result_creation__is_frozen__d211bd45(self) -> None:
        """Test that BronzeWriteResult is immutable."""
        result = _make_valid_result()
        with pytest.raises((AttributeError, TypeError)):
            result.record_count = 999  # type: ignore[misc]


@pytest.mark.unit
class TestBronzeWriteResultValidation:
    """Tests for BronzeWriteResult validation logic."""

    def test_negative_record_count_raises(self) -> None:
        """Test that negative record_count raises ValueError."""
        with pytest.raises(ValueError, match="record_count must be non-negative"):
            _make_valid_result(record_count=-1)

    def test_negative_compressed_size_raises(self) -> None:
        """Test that negative compressed_size raises ValueError."""
        with pytest.raises(ValueError, match="compressed_size must be non-negative"):
            _make_valid_result(compressed_size=-1)

    def test_negative_uncompressed_size_raises(self) -> None:
        """Test that negative uncompressed_size raises ValueError."""
        with pytest.raises(ValueError, match="uncompressed_size must be non-negative"):
            _make_valid_result(uncompressed_size=-1)

    def test_empty_relative_path_raises(self) -> None:
        """Test that empty relative_path raises ValueError."""
        with pytest.raises(ValueError, match="relative_path cannot be empty"):
            _make_valid_result(relative_path="")

    def test_empty_absolute_path_raises(self) -> None:
        """Test that empty absolute_path raises ValueError."""
        with pytest.raises(ValueError, match="absolute_path cannot be empty"):
            _make_valid_result(absolute_path="")

    def test_empty_checksum_raises(self) -> None:
        """Test that empty checksum_blake2 raises ValueError."""
        with pytest.raises(ValueError, match="checksum_blake2 cannot be empty"):
            _make_valid_result(checksum_blake2="")


@pytest.mark.unit
class TestBronzeWriteResultProperties:
    """Tests for BronzeWriteResult computed properties."""

    def test_compression_ratio_calculation(self) -> None:
        """Test compression ratio is uncompressed / compressed."""
        result = _make_valid_result(compressed_size=50000, uncompressed_size=200000)
        assert result.compression_ratio == pytest.approx(4.0)

    def test_compression_ratio_zero_uncompressed(self) -> None:
        """Test compression ratio returns 1.0 when uncompressed_size is 0."""
        result = _make_valid_result(compressed_size=50000, uncompressed_size=0)
        assert result.compression_ratio == pytest.approx(1.0)

    def test_compression_ratio_zero_compressed(self) -> None:
        """Test compression ratio returns 1.0 when compressed_size is 0."""
        result = _make_valid_result(compressed_size=0, uncompressed_size=200000)
        assert result.compression_ratio == pytest.approx(1.0)

    def test_exists_method_removed_from_domain_vo(self) -> None:
        """BronzeWriteResult must not perform filesystem I/O in domain layer."""
        result = _make_valid_result(absolute_path="/nonexistent/path/to/file.jsonl.zst")
        assert not hasattr(result, "exists")
