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
"""Unit tests for SilverWriteResult value object.

Tests the SilverWriteResult that captures Silver layer write operation results
for downstream Gold lineage tracking (REQ-LINEAGE-002).
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.silver_result import SilverWriteResult


pytestmark = pytest.mark.unit


class TestSilverWriteResult:
    """Tests for SilverWriteResult value object."""

    def test_create_valid_result(self) -> None:
        """Test creating SilverWriteResult with valid data."""
        result = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=42,
            record_count=1000,
        )

        assert result.table_name == "chembl.activity"
        assert result.table_path == "/data/silver/chembl/activity"
        assert result.delta_version == 42
        assert result.record_count == 1000

    def test_result_is_immutable(self) -> None:
        """Test that SilverWriteResult is immutable (frozen)."""
        result = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=1,
            record_count=100,
        )

        with pytest.raises(AttributeError):
            result.table_name = "new_name"  # type: ignore[misc]

    def test_negative_delta_version_raises(self) -> None:
        """Test that negative delta_version raises ValueError."""
        with pytest.raises(ValueError, match="delta_version must be non-negative"):
            SilverWriteResult(
                table_name="chembl.activity",
                table_path="/data/silver/chembl/activity",
                delta_version=-1,
                record_count=100,
            )

    def test_silver_write_result__record_count_raises__e1423c88(self) -> None:
        """Test that negative record_count raises ValueError."""
        with pytest.raises(ValueError, match="record_count must be non-negative"):
            SilverWriteResult(
                table_name="chembl.activity",
                table_path="/data/silver/chembl/activity",
                delta_version=1,
                record_count=-1,
            )

    def test_empty_table_name_raises(self) -> None:
        """Test that empty table_name raises ValueError."""
        with pytest.raises(ValueError, match="table_name cannot be empty"):
            SilverWriteResult(
                table_name="",
                table_path="/data/silver/chembl/activity",
                delta_version=1,
                record_count=100,
            )

    def test_empty_table_path_raises(self) -> None:
        """Test that empty table_path raises ValueError."""
        with pytest.raises(ValueError, match="table_path cannot be empty"):
            SilverWriteResult(
                table_name="chembl.activity",
                table_path="",
                delta_version=1,
                record_count=100,
            )

    def test_zero_delta_version_valid(self) -> None:
        """Test that delta_version=0 is valid (first write)."""
        result = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=0,
            record_count=100,
        )

        assert result.delta_version == 0

    def test_zero_record_count_valid(self) -> None:
        """Test that record_count=0 is valid (empty batch)."""
        result = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=1,
            record_count=0,
        )

        assert result.record_count == 0

    def test_silver_write_result__equality__62cd0f85(self) -> None:
        """Test that two SilverWriteResults with same values are equal."""
        result1 = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=42,
            record_count=1000,
        )
        result2 = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=42,
            record_count=1000,
        )

        assert result1 == result2

    def test_inequality_different_version(self) -> None:
        """Test that SilverWriteResults with different versions are not equal."""
        result1 = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=42,
            record_count=1000,
        )
        result2 = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=43,
            record_count=1000,
        )

        assert result1 != result2


class TestSilverWriteResultForLineage:
    """Tests for using SilverWriteResult in Gold lineage tracking."""

    def test_can_convert_to_silver_ref_attributes(self) -> None:
        """Test that SilverWriteResult has all attributes needed for SilverRef."""
        result = SilverWriteResult(
            table_name="chembl.activity",
            table_path="/data/silver/chembl/activity",
            delta_version=42,
            record_count=1000,
        )

        # These are the attributes needed for SilverRef conversion
        assert hasattr(result, "table_name")
        assert hasattr(result, "table_path")
        assert hasattr(result, "delta_version")

        # Verify we can create a dict for lineage
        lineage_dict = {result.table_name: result.delta_version}
        assert lineage_dict == {"chembl.activity": 42}
