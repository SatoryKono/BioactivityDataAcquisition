"""Coverage boost tests for gold_writer_metadata_mixin.py.

Targets uncovered lines: 48-50, 71-78, 117, 154-181, 287-301, 317, 369, 380-388.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.gold_writer_metadata_mixin import (
    GoldWriterMetadataMixin,
    _GoldWriterMergedMetadataInputMixin,
)


def _make_run_id() -> RunID:
    return RunID(uuid4())


def _make_record(
    *,
    lineage_created_at: str | datetime | None = None,
    ingestion_ts: str | None = None,
    extra: dict | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {}
    if lineage_created_at is not None:
        record["_lineage_created_at"] = lineage_created_at
    if ingestion_ts is not None:
        record["_ingestion_ts"] = ingestion_ts
    if extra:
        record.update(extra)
    return record


class _ConcreteGoldMixin(GoldWriterMetadataMixin):
    """Concrete subclass for testing the mixin."""

    def __init__(
        self,
        audit: object | None = None,
        metadata_coordinator: object | None = None,
        metadata_writer: object | None = None,
    ) -> None:
        self.logger = MagicMock()
        self.logger.warning = MagicMock()
        self.logger.debug = MagicMock()
        self.logger.info = MagicMock()
        self._audit = audit
        self._metadata_coordinator = metadata_coordinator
        self._metadata_writer = metadata_writer or MagicMock()
        self._metadata_writer.write_gold_metadata = AsyncMock(
            return_value="path/meta.yaml"
        )
        self._flat_structure = False
        self._transform_version = "1.0.0"
        self._transform_steps = ("step1", "step2")

        # Gold writer module stub
        self._gold_module = MagicMock()
        self._gold_module.TableNotFoundError = type(
            "TableNotFoundError", (Exception,), {}
        )

    def _load_gold_writer_module(self) -> Any:
        return self._gold_module

    async def _run_in_executor(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, fn)


@pytest.mark.unit
class TestExtractCompletedAt:
    """Tests for _extract_completed_at (lines 64-78)."""

    def test_lineage_created_at_iso_string(self) -> None:
        """Line 74-75: string is parsed via fromisoformat."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "1.0"
        mixin._transform_steps = ()

        record = {"_lineage_created_at": "2025-01-15T10:00:00"}
        result = mixin._extract_completed_at(record)

        assert result is not None
        assert result.year == 2025

    def test_lineage_created_at_datetime_object(self) -> None:
        """Line 76-77: datetime object returned as-is."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "1.0"
        mixin._transform_steps = ()

        dt = datetime(2025, 3, 10, 12, 0, 0, tzinfo=UTC)
        record = {"_lineage_created_at": dt}
        result = mixin._extract_completed_at(record)

        assert result is dt

    def test_ingestion_ts_fallback(self) -> None:
        """Line 71-72: falls back to _ingestion_ts when _lineage_created_at absent."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "1.0"
        mixin._transform_steps = ()

        record = {"_ingestion_ts": "2025-06-01T08:00:00"}
        result = mixin._extract_completed_at(record)

        assert result is not None
        assert result.month == 6

    def test_no_timestamps_returns_none(self) -> None:
        """Line 78: no timestamp field returns None."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "1.0"
        mixin._transform_steps = ()

        record = {"activity_id": "CHEMBL1"}
        result = mixin._extract_completed_at(record)

        assert result is None

    def test_non_string_non_datetime_returns_none(self) -> None:
        """Line 78: non-string/datetime value returns None."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "1.0"
        mixin._transform_steps = ()

        record = {"_lineage_created_at": 12345}
        result = mixin._extract_completed_at(record)

        assert result is None


@pytest.mark.unit
class TestBuildGoldMergedMetadataInput:
    """Tests for _build_gold_merged_metadata_input (lines 48-62)."""

    def test_build_metadata_input_overwrite_mode(self) -> None:
        """Lines 48-62: builds GoldMetadataInput with OVERWRITE mode."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "2.0.0"
        mixin._transform_steps = ("normalize", "enrich")

        records = [{"_lineage_created_at": "2025-01-15T10:00:00", "id": 1}]
        result = mixin._build_gold_merged_metadata_input(
            table_path="gold/publication",
            table_name="composite_publication",
            records=records,
            schema=None,
        )

        assert result.mode == GoldWriteMode.OVERWRITE
        assert result.transform_version == "2.0.0"
        assert result.transform_steps == ("normalize", "enrich")
        assert result.schema_validation_enabled is False

    def test_build_metadata_input_with_schema(self) -> None:
        """Lines 60-61: schema_validation_enabled=True when schema is not None."""
        mixin = _GoldWriterMergedMetadataInputMixin()
        mixin._transform_version = "1.0"
        mixin._transform_steps = ()

        mock_schema = MagicMock()
        records = [{"id": 1}]
        result = mixin._build_gold_merged_metadata_input(
            table_path="gold/t",
            table_name="t",
            records=records,
            schema=mock_schema,
        )

        assert result.schema_validation_enabled is True
        assert result.schema_validation_strict is True


@pytest.mark.unit
class TestLogGoldAudit:
    """Tests for _log_gold_audit (lines 232-279)."""

    @pytest.mark.asyncio
    async def test_log_audit_with_valid_inputs(self) -> None:
        """Line 279: audit.log_write called when inputs are valid."""
        audit = MagicMock()
        audit.log_write = AsyncMock()
        mixin = _ConcreteGoldMixin(audit=audit)

        run_id = _make_run_id()
        ingestion_ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)

        await mixin._log_gold_audit(
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
        )

        audit.log_write.assert_called_once()
        entry: AuditEntry = audit.log_write.call_args[0][0]
        assert entry.table_name == "chembl.activity"
        assert entry.layer.value == "gold"

    @pytest.mark.asyncio
    async def test_log_audit_missing_ingestion_ts_raises(self) -> None:
        """Line 251: missing ingestion_ts raises ValueError."""
        audit = MagicMock()
        audit.log_write = AsyncMock()
        mixin = _ConcreteGoldMixin(audit=audit)

        with pytest.raises(ValueError, match="ingestion_ts is required"):
            await mixin._log_gold_audit(
                table_name="chembl.activity",
                records=[{"id": 1}],
                mode=GoldWriteMode.OVERWRITE,
                ingestion_ts=None,
                run_id=_make_run_id(),
            )

        mixin.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_log_audit_missing_run_id_generates_uuid(self) -> None:
        """Lines 255-260: missing run_id generates a new UUID."""
        audit = MagicMock()
        audit.log_write = AsyncMock()
        mixin = _ConcreteGoldMixin(audit=audit)

        ingestion_ts = datetime(2025, 1, 15, tzinfo=UTC)

        await mixin._log_gold_audit(
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            ingestion_ts=ingestion_ts,
            run_id=None,
        )

        audit.log_write.assert_called_once()
        mixin.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_log_audit_all_write_modes(self) -> None:
        """Lines 261-266: operation_map covers all GoldWriteMode values."""
        audit = MagicMock()
        audit.log_write = AsyncMock()
        mixin = _ConcreteGoldMixin(audit=audit)

        ingestion_ts = datetime(2025, 1, 15, tzinfo=UTC)
        run_id = _make_run_id()

        for mode in GoldWriteMode:
            audit.log_write.reset_mock()
            await mixin._log_gold_audit(
                table_name="t",
                records=[{"id": 1}],
                mode=mode,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
            )
            audit.log_write.assert_called_once()


@pytest.mark.unit
class TestGetDeltaVersion:
    """Tests for _get_delta_version (lines 281-301)."""

    @pytest.mark.asyncio
    async def test_delta_version_returns_int(self) -> None:
        """Lines 293-298: DeltaTable.version() returns int."""
        mixin = _ConcreteGoldMixin()

        dt = MagicMock()
        dt.version = MagicMock(return_value=42)
        mixin._gold_module.DeltaTable = MagicMock(return_value=dt)

        result = await mixin._get_delta_version("gold/path")

        assert result == 42

    @pytest.mark.asyncio
    async def test_delta_version_returns_string_digit(self) -> None:
        """Lines 297-298: DeltaTable.version() returns string digit, converted to int."""
        mixin = _ConcreteGoldMixin()

        dt = MagicMock()
        dt.version = MagicMock(return_value="  7  ")
        mixin._gold_module.DeltaTable = MagicMock(return_value=dt)

        result = await mixin._get_delta_version("gold/path")

        assert result == 7

    @pytest.mark.asyncio
    async def test_delta_version_table_not_found_returns_none(self) -> None:
        """Line 300-301: TableNotFoundError returns None."""
        mixin = _ConcreteGoldMixin()
        NotFoundErr = mixin._gold_module.TableNotFoundError

        mixin._gold_module.DeltaTable = MagicMock(side_effect=NotFoundErr("not found"))

        result = await mixin._get_delta_version("gold/path")

        assert result is None

    @pytest.mark.asyncio
    async def test_delta_version_non_callable_version(self) -> None:
        """Lines 291-292: non-callable version attribute returns None."""
        mixin = _ConcreteGoldMixin()

        dt = MagicMock()
        dt.version = "not_callable"  # Not callable
        mixin._gold_module.DeltaTable = MagicMock(return_value=dt)

        result = await mixin._get_delta_version("gold/path")

        assert result is None

    @pytest.mark.asyncio
    async def test_delta_version_non_int_non_digit_returns_none(self) -> None:
        """Line 299: version returns non-parseable value → None."""
        mixin = _ConcreteGoldMixin()

        dt = MagicMock()
        dt.version = MagicMock(return_value="not-a-number")
        mixin._gold_module.DeltaTable = MagicMock(return_value=dt)

        result = await mixin._get_delta_version("gold/path")

        assert result is None


@pytest.mark.unit
class TestWriteGoldMetadata:
    """Tests for _write_gold_metadata (lines 303-336)."""

    @pytest.mark.asyncio
    async def test_empty_records_skips_write(self) -> None:
        """Line 316-317: empty records returns early without writing."""
        mixin = _ConcreteGoldMixin()
        metadata_writer = MagicMock()
        metadata_writer.write_gold_metadata = AsyncMock()
        mixin._metadata_writer = metadata_writer

        await mixin._write_gold_metadata(
            table_path="gold/t",
            table_name="chembl.activity",
            records=[],
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )

        metadata_writer.write_gold_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_writes_metadata_for_non_empty_records(self) -> None:
        """Lines 318-336: writes metadata when records present."""
        coordinator = MagicMock()
        coordinator.create_gold_metadata = MagicMock(return_value=MagicMock())

        mixin = _ConcreteGoldMixin(metadata_coordinator=coordinator)
        records = [{"id": 1}]

        await mixin._write_gold_metadata(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )

        mixin._metadata_writer.write_gold_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepares_resolved_metadata_context_before_write(self) -> None:
        """Standard Gold metadata path should resolve provider/entity before persist."""
        metadata = MagicMock()
        mixin = _ConcreteGoldMixin(metadata_coordinator=MagicMock())
        mixin._create_gold_metadata_payload = MagicMock(return_value=metadata)  # type: ignore[method-assign]
        mixin._write_gold_metadata_file = AsyncMock()  # type: ignore[method-assign]

        await mixin._write_gold_metadata(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )

        mixin._create_gold_metadata_payload.assert_called_once_with(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
            silver_refs=None,
            gold_schema=None,
        )
        mixin._write_gold_metadata_file.assert_awaited_once_with(
            table_path="gold/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )


@pytest.mark.unit
class TestWriteGoldMergedMetadata:
    """Tests for _write_gold_merged_metadata (lines 357-395)."""

    @pytest.mark.asyncio
    async def test_empty_records_skips_write(self) -> None:
        """Line 369: empty records returns early."""
        mixin = _ConcreteGoldMixin()
        await mixin._write_gold_merged_metadata(
            table_path="gold/t",
            table_name="composite.publication",
            records=[],
        )
        mixin._metadata_writer.write_gold_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_coordinator_skips_write_with_debug_log(self) -> None:
        """Lines 373-379: no metadata_coordinator logs debug and returns."""
        mixin = _ConcreteGoldMixin(metadata_coordinator=None)
        records = [{"id": 1, "_source_providers": ["chembl"]}]

        await mixin._write_gold_merged_metadata(
            table_path="gold/t",
            table_name="composite.publication",
            records=records,
        )

        mixin._metadata_writer.write_gold_metadata.assert_not_called()
        mixin.logger.debug.assert_called()
        debug_call = mixin.logger.debug.call_args
        assert debug_call[0][0] == "gold_merged_metadata_skipped"

    @pytest.mark.asyncio
    async def test_with_coordinator_writes_metadata(self) -> None:
        """Lines 380-395: coordinator present writes metadata."""
        coordinator = MagicMock()
        coordinator.create_gold_metadata = MagicMock(return_value=MagicMock())

        mixin = _ConcreteGoldMixin(metadata_coordinator=coordinator)
        records = [{"id": 1}]

        await mixin._write_gold_merged_metadata(
            table_path="gold/composite/publication",
            table_name="composite.publication",
            records=records,
        )

        coordinator.create_gold_metadata.assert_called_once()
        mixin._metadata_writer.write_gold_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepares_merged_metadata_context_before_write(self) -> None:
        """Merged Gold metadata path should resolve provider/entity before persist."""
        metadata = MagicMock()
        coordinator = MagicMock()
        coordinator.create_gold_metadata = MagicMock(return_value=metadata)
        mixin = _ConcreteGoldMixin(metadata_coordinator=coordinator)
        mixin._build_gold_merged_metadata_input = MagicMock(  # type: ignore[method-assign]
            return_value=MagicMock()
        )
        mixin._write_gold_metadata_file = AsyncMock()  # type: ignore[method-assign]

        await mixin._write_gold_merged_metadata(
            table_path="gold/composite/publication",
            table_name="composite.publication",
            records=[{"id": 1}],
        )

        mixin._build_gold_merged_metadata_input.assert_called_once_with(
            table_path="gold/composite/publication",
            table_name="composite.publication",
            records=[{"id": 1}],
            schema=None,
        )
        mixin._write_gold_metadata_file.assert_awaited_once_with(
            table_path="gold/composite/publication",
            metadata=metadata,
            table_name="composite.publication",
            provider_name="composite",
            entity_name="publication",
        )


@pytest.mark.unit
class TestCreateGoldMetadataPayload:
    """Tests for _create_gold_metadata_payload (lines 98-135)."""

    def test_uses_coordinator_when_present(self) -> None:
        """Line 117: coordinator path is used when coordinator is set."""
        coordinator = MagicMock()
        coordinator.create_gold_metadata = MagicMock(return_value=MagicMock())

        mixin = _ConcreteGoldMixin(metadata_coordinator=coordinator)
        records = [{"id": 1}]

        mixin._create_gold_metadata_payload(
            table_path="gold/t",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )

        coordinator.create_gold_metadata.assert_called_once()

    def test_uses_fallback_when_no_coordinator(self) -> None:
        """Line 127-135: fallback builder used when coordinator is None."""
        mixin = _ConcreteGoldMixin(metadata_coordinator=None)
        records = [{"id": 1}]
        run_id = _make_run_id()

        with patch(
            "bioetl.infrastructure.storage.metadata_builder.GoldMetadataBuilder.build_fallback_metadata",
            return_value=MagicMock(),
        ) as mock_fallback:
            mixin._create_gold_metadata_payload(
                table_path="gold/t",
                table_name="chembl.activity",
                records=records,
                mode=GoldWriteMode.OVERWRITE,
                scd_config=None,
                ingestion_ts=None,
                run_id=run_id,
            )

            mock_fallback.assert_called_once()


@pytest.mark.unit
class TestCreateGoldMetadataViaCoordinator:
    """Tests for _create_gold_metadata_via_coordinator (lines 154-181)."""

    def test_silver_refs_converted_to_silver_ref_objects(self) -> None:
        """Lines 156-166: silver_refs are converted to SilverRef objects."""
        coordinator = MagicMock()
        coordinator.create_gold_metadata = MagicMock(return_value=MagicMock())

        mixin = _ConcreteGoldMixin(metadata_coordinator=coordinator)

        silver_ref = MagicMock()
        silver_ref.table_name = "chembl.activity"
        silver_ref.table_path = "silver/chembl/activity"
        silver_ref.delta_version = 5

        mixin._create_gold_metadata_via_coordinator(
            table_path="gold/t",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
            silver_refs=[silver_ref],
            gold_schema=None,
        )

        coordinator.create_gold_metadata.assert_called_once()
        input_arg = coordinator.create_gold_metadata.call_args[0][0]
        assert input_arg.silver_refs is not None
        assert len(input_arg.silver_refs) == 1

    def test_no_silver_refs_passes_none(self) -> None:
        """Lines 163-166: None silver_refs stays None."""
        coordinator = MagicMock()
        coordinator.create_gold_metadata = MagicMock(return_value=MagicMock())

        mixin = _ConcreteGoldMixin(metadata_coordinator=coordinator)

        mixin._create_gold_metadata_via_coordinator(
            table_path="gold/t",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
            silver_refs=None,
            gold_schema=None,
        )

        input_arg = coordinator.create_gold_metadata.call_args[0][0]
        assert input_arg.silver_refs is None
