"""Unit tests for ChEMBL deduplication helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.chembl.deduplication import (
    compute_composite_key,
    is_duplicate_record,
    is_duplicate_record_composite,
)


@pytest.mark.unit
class TestComputeCompositeKey:
    """Tests for compute_composite_key()."""

    def test_builds_pipe_joined_key(self) -> None:
        """Composite key should preserve pk_fields order and normalize values."""
        record = {"a": 1, "b": "x", "c": None}

        key = compute_composite_key(record, ("a", "b", "c"))

        assert key == "1|x|"

    def test_handles_missing_fields_as_empty_string(self) -> None:
        """Missing fields should contribute empty key segments."""
        key = compute_composite_key({"a": "v"}, ("a", "missing"))
        assert key == "v|"


@pytest.mark.unit
class TestIsDuplicateRecordComposite:
    """Tests for is_duplicate_record_composite()."""

    def test_empty_composite_key_is_not_duplicate(self) -> None:
        """Records with empty composite key should be ignored (not duplicate)."""
        seen_keys: set[str] = set()
        logger = MagicMock()
        metrics = MagicMock()

        is_dup = is_duplicate_record_composite(
            record={"a": None, "b": None},
            pk_fields=("a", "b"),
            seen_keys=seen_keys,
            entity_type="test_entity",
            logger=logger,
            metrics=metrics,
        )

        assert is_dup is False
        assert seen_keys == set()
        logger.debug.assert_not_called()
        metrics.record_dropped_duplicates.assert_not_called()

    def test_duplicate_flow_logs_and_increments_metrics(self) -> None:
        """Second record with same composite key should be detected as duplicate."""
        seen_keys: set[str] = set()
        logger = MagicMock()
        metrics = MagicMock()

        first = is_duplicate_record_composite(
            record={"a": "A", "b": "B"},
            pk_fields=("a", "b"),
            seen_keys=seen_keys,
            entity_type="test_entity",
            logger=logger,
            metrics=metrics,
        )
        second = is_duplicate_record_composite(
            record={"a": "A", "b": "B"},
            pk_fields=("a", "b"),
            seen_keys=seen_keys,
            entity_type="test_entity",
            logger=logger,
            metrics=metrics,
        )

        assert first is False
        assert second is True
        assert "A|B" in seen_keys
        logger.debug.assert_called_once()
        metrics.record_dropped_duplicates.assert_called_once_with("test_entity")


@pytest.mark.unit
class TestIsDuplicateRecord:
    """Tests for is_duplicate_record()."""

    def test_empty_id_is_not_duplicate(self) -> None:
        """Records without pk should not be marked as duplicates."""
        seen_ids: set[str] = set()
        logger = MagicMock()
        metrics = MagicMock()

        result = is_duplicate_record(
            record={"id": ""},
            pk_field="id",
            seen_ids=seen_ids,
            entity_type="activity",
            logger=logger,
            metrics=metrics,
        )

        assert result is False
        assert seen_ids == set()
        logger.debug.assert_not_called()
        metrics.record_dropped_duplicates.assert_not_called()

    def test_duplicate_id_logs_and_increments_metrics(self) -> None:
        """Second record with same pk should be marked as duplicate."""
        seen_ids: set[str] = set()
        logger = MagicMock()
        metrics = MagicMock()

        first = is_duplicate_record(
            record={"id": "CHEMBL1"},
            pk_field="id",
            seen_ids=seen_ids,
            entity_type="activity",
            logger=logger,
            metrics=metrics,
        )
        second = is_duplicate_record(
            record={"id": "CHEMBL1"},
            pk_field="id",
            seen_ids=seen_ids,
            entity_type="activity",
            logger=logger,
            metrics=metrics,
        )

        assert first is False
        assert second is True
        assert "CHEMBL1" in seen_ids
        logger.debug.assert_called_once()
        metrics.record_dropped_duplicates.assert_called_once_with("activity")
