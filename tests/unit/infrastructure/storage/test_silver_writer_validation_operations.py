"""Unit tests for Silver writer validation operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.domain.exceptions import PolicyViolationError, SchemaViolationError
from bioetl.domain.medallion import SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _strict_replay_merge_contract_required,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _content_identity,
    _deduplicate_by_primary_keys_impl,
    _enforce_write_policy,
    _to_policy_write_mode_impl,
    _validate_records,
    _validate_silver_pandera,
    _validate_write_mode_impl,
)


@pytest.mark.unit
class TestValidateWriteModeImpl:
    """Tests for Silver write mode validation."""

    def test_valid_merge_mode(self) -> None:
        """Should return SilverWriteMode.MERGE for 'merge' string."""
        assert _validate_write_mode_impl("merge") == SilverWriteMode.MERGE

    def test_valid_append_mode(self) -> None:
        """Should return SilverWriteMode.APPEND for 'append' string."""
        assert _validate_write_mode_impl("append") == SilverWriteMode.APPEND

    def test_invalid_mode_raises(self) -> None:
        """Should raise ValueError for unrecognized mode."""
        with pytest.raises(ValueError, match="Invalid Silver write mode"):
            _validate_write_mode_impl("invalid")


@pytest.mark.unit
class TestDeduplicateByPrimaryKeysImpl:
    """Tests for batch-level record deduplication."""

    def test_deduplicates_by_keys(self) -> None:
        """Should keep a deterministic winner for duplicate primary keys."""
        records = [
            {"id": 1, "name": "second", "content_hash": "z-hash"},
            {"id": 2, "name": "only"},
            {"id": 1, "name": "first", "content_hash": "a-hash"},
        ]
        result = _deduplicate_by_primary_keys_impl(records, ["id"])
        assert len(result) == 2
        id_to_name = {r["id"]: r["name"] for r in result}
        assert id_to_name[1] == "first"

    def test_deduplication_is_order_insensitive(self) -> None:
        """Reordering the input batch should not change the selected winner."""
        forward = [
            {"id": 1, "name": "winner", "content_hash": "a-hash"},
            {"id": 1, "name": "loser", "content_hash": "z-hash"},
        ]
        reverse = list(reversed(forward))

        forward_result = _deduplicate_by_primary_keys_impl(forward, ["id"])
        reverse_result = _deduplicate_by_primary_keys_impl(reverse, ["id"])

        assert len(forward_result) == 1
        assert len(reverse_result) == 1
        assert forward_result[0]["name"] == "winner"
        assert reverse_result[0]["name"] == "winner"

    def test_exact_duplicates_collapse_to_one_row(self) -> None:
        """Exact duplicates should collapse by business key and content identity."""
        record = {"id": 1, "name": "same", "content_hash": "a-hash"}
        result = _deduplicate_by_primary_keys_impl([record, dict(record)], ["id"])

        assert result == [record]

    def test_empty_primary_keys_returns_original(self) -> None:
        """Should return records unchanged when no primary keys."""
        records = [{"id": 1}, {"id": 1}]
        result = _deduplicate_by_primary_keys_impl(records, [])
        assert len(result) == 2

    def test_empty_records_returns_empty(self) -> None:
        """Should return empty list for empty input."""
        result = _deduplicate_by_primary_keys_impl([], ["id"])
        assert result == []

    def test_content_identity_fallback_uses_canonical_hash_identity_contract(
        self,
    ) -> None:
        """Batch dedup fallback must reuse the canonical hash-identity seam."""
        record = {
            "id": 1,
            "name": "  Alpha  ",
            "measured_at": "2025-01-01",
            "_run_id": "run-1",
        }

        assert _content_identity(record) == serialize_hash_identity_canonical_json(
            normalize_hash_identity_record(record)
        )


@pytest.mark.unit
class TestStrictReplayMergeContractRequired:
    """Tests for strict replay merge guard activation."""

    def test_missing_mock_run_context_does_not_enable_strict_contract(self) -> None:
        """Bare MagicMock coordinators must not implicitly enable exact replay."""
        host = MagicMock()
        host._metadata_coordinator = MagicMock()

        assert _strict_replay_merge_contract_required(host) is False

    def test_exact_replay_true_enables_strict_contract(self) -> None:
        """Explicit exact replay requests should enforce replay-safe merge guards."""
        run_context = MagicMock()
        run_context.exact_replay = True
        run_context.required_persistence_profile = ""
        coordinator = MagicMock()
        coordinator.run_context = run_context
        host = MagicMock()
        host._metadata_coordinator = coordinator

        assert _strict_replay_merge_contract_required(host) is True

    def test_strict_required_profile_enables_strict_contract(self) -> None:
        """Strict persistence profiles should enforce replay-safe merge guards."""
        run_context = MagicMock()
        run_context.exact_replay = False
        run_context.required_persistence_profile = "replay_ready"
        coordinator = MagicMock()
        coordinator.run_context = run_context
        host = MagicMock()
        host._metadata_coordinator = coordinator

        assert _strict_replay_merge_contract_required(host) is True


@pytest.mark.unit
class TestToPolicyWriteModeImpl:
    """Tests for Silver to policy write mode mapping."""

    def test_merge_maps_to_merge(self) -> None:
        """SilverWriteMode.MERGE should map to WriteMode.MERGE."""
        assert _to_policy_write_mode_impl(SilverWriteMode.MERGE) == WriteMode.MERGE

    def test_append_maps_to_append(self) -> None:
        """SilverWriteMode.APPEND should map to WriteMode.APPEND."""
        assert _to_policy_write_mode_impl(SilverWriteMode.APPEND) == WriteMode.APPEND

    def test_delete_maps_to_overwrite(self) -> None:
        """SilverWriteMode.DELETE should map to WriteMode.OVERWRITE."""
        assert _to_policy_write_mode_impl(SilverWriteMode.DELETE) == WriteMode.OVERWRITE


@pytest.mark.unit
class TestEnforceWritePolicy:
    """Tests for write mode policy enforcement."""

    def test_allowed_mode_passes(self) -> None:
        """Should not raise when policy allows the mode."""
        host = MagicMock()
        host._write_policy = WriteModePolicy()
        host._to_policy_write_mode.return_value = WriteMode.MERGE
        _enforce_write_policy(host, SilverWriteMode.MERGE, "test_table")

    def test_disallowed_mode_raises_and_logs(self) -> None:
        """Should raise PolicyViolationError and log error for disallowed mode."""
        host = MagicMock()
        host._write_policy = MagicMock()
        host._write_policy.validate.side_effect = PolicyViolationError(
            "OVERWRITE not allowed for Silver"
        )
        host._to_policy_write_mode.return_value = WriteMode.OVERWRITE
        host._metrics = MagicMock()

        with pytest.raises(PolicyViolationError):
            _enforce_write_policy(host, SilverWriteMode.DELETE, "test_table")
        host.logger.error.assert_called_once()
        host._metrics.increment_counter.assert_called_once()


@pytest.mark.unit
class TestValidateRecords:
    """Tests for Silver record validation."""

    def test_empty_records_raises(self) -> None:
        """Should raise ValueError when records list is empty."""
        host = MagicMock()
        schema = pa.schema([("id", pa.int64())])
        with pytest.raises(ValueError, match="No records to write"):
            _validate_records(host, [], "test_table", schema)

    def test_records_without_runtime_metadata_pass(self) -> None:
        """Silver validation should not require runtime provenance in row payload."""
        host = MagicMock()
        schema = pa.schema([("id", pa.int64())])
        records = [{"id": 1}]
        _validate_records(host, records, "test_table", schema)

    def test_valid_records_pass(self) -> None:
        """Silver validation accepts records regardless of runtime provenance fields."""
        host = MagicMock()
        schema = pa.schema([("id", pa.int64())])
        records = [
            {
                "id": 1,
                "_run_id": "r1",
                "_run_type": "incremental",
                "_source_batch_id": "b1",
                "_ingestion_ts": "2025-01-01T00:00:00Z",
            }
        ]
        _validate_records(host, records, "test_table", schema)

    def test_null_source_batch_id_in_payload_is_ignored(self) -> None:
        """Runtime provenance should not be validated from row payload anymore."""
        host = MagicMock()
        schema = pa.schema([("id", pa.int64())])
        records = [
            {
                "id": 1,
                "_run_id": "r1",
                "_run_type": "incremental",
                "_source_batch_id": None,
                "_ingestion_ts": "2025-01-01T00:00:00Z",
            }
        ]
        _validate_records(host, records, "test_table", schema)

    def test_blank_source_batch_id_in_payload_is_ignored(self) -> None:
        """Blank row-level provenance should not fail Silver validation."""
        host = MagicMock()
        schema = pa.schema([("id", pa.int64())])
        records = [
            {
                "id": 1,
                "_run_id": "r1",
                "_run_type": "incremental",
                "_source_batch_id": "   ",
                "_ingestion_ts": "2025-01-01T00:00:00Z",
            }
        ]
        _validate_records(host, records, "test_table", schema)


@pytest.mark.unit
class TestValidateSilverPandera:
    """Tests for Pandera schema validation of Silver records."""

    def test_valid_records_pass(self) -> None:
        """Should pass when validator returns valid result."""
        host = MagicMock()
        host._silver_validator.validate.return_value = MagicMock(valid=True)
        records = [{"id": 1, "_state": "active"}]
        _validate_silver_pandera(host, records, "test_table")
        # _state should be stripped before validation
        call_args = host._silver_validator.validate.call_args.args[0]
        assert all("_state" not in r for r in call_args)

    def test_invalid_records_raise_schema_violation(self) -> None:
        """Should raise SchemaViolationError when validation fails."""
        host = MagicMock()
        host._silver_validator.validate.return_value = MagicMock(
            valid=False, errors=["col 'x' is null"]
        )
        host._metrics = MagicMock()
        records = [{"id": 1}]
        with pytest.raises(SchemaViolationError):
            _validate_silver_pandera(host, records, "test_table")
        host.logger.error.assert_called_once()
        host._metrics.increment_counter.assert_called_once()

    def test_invalid_records_emit_canonical_silver_validation_metric(self) -> None:
        """Validation failures should increment the shipped Silver alert metric."""
        host = MagicMock()
        host._silver_validator.validate.return_value = MagicMock(
            valid=False, errors=["col 'x' is null"]
        )
        host._metrics = MagicMock()
        records = [{"id": 1}]

        with pytest.raises(SchemaViolationError):
            _validate_silver_pandera(host, records, "test_table")

        host._metrics.increment_counter.assert_called_once_with(
            "bioetl_silver_validation_failures_total",
            1,
            {"table": "test_table", "pipeline": "test_table"},
        )

    def test_invalid_records_for_versioned_tables_emit_normalized_pipeline_label(
        self,
    ) -> None:
        """Versioned table names should still expose stable pipeline labels."""
        host = MagicMock()
        host._silver_validator.validate.return_value = MagicMock(
            valid=False, errors=["col 'x' is null"]
        )
        host._metrics = MagicMock()
        records = [{"id": 1}]

        with pytest.raises(SchemaViolationError):
            _validate_silver_pandera(host, records, "chembl.activity__v1_0_0")

        host._metrics.increment_counter.assert_called_once_with(
            "bioetl_silver_validation_failures_total",
            1,
            {
                "table": "chembl.activity__v1_0_0",
                "pipeline": "chembl_activity",
            },
        )
