"""Coverage boost tests for gold/metadata_mixin.py.

Targets uncovered lines: 48-50, 71-78, 117, 154-181, 287-301, 317, 369, 380-388.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.gold.metadata_mixin import (
    GoldWriterMetadataMixin,
)
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
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


def _make_bundle_safe_metadata(run_id: str = "test-run") -> MagicMock:
    """Create metadata mocks compatible with MetadataLineageBundleResult identity checks."""
    metadata = MagicMock()
    metadata.runtime = SimpleNamespace(run_id=run_id, manifest_id=None)
    metadata.output = SimpleNamespace(lineage_fragment_id=None, artifact_id=None)
    return metadata


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
    async def test_log_audit_missing_run_id_raises(self) -> None:
        """Missing run_id must fail closed instead of generating a UUID."""
        audit = MagicMock()
        audit.log_write = AsyncMock()
        mixin = _ConcreteGoldMixin(audit=audit)

        ingestion_ts = datetime(2025, 1, 15, tzinfo=UTC)

        with pytest.raises(ValueError, match="run_id is required"):
            await mixin._log_gold_audit(
                table_name="chembl.activity",
                records=[{"id": 1}],
                mode=GoldWriteMode.APPEND,
                ingestion_ts=ingestion_ts,
                run_id=None,
            )

        audit.log_write.assert_not_called()
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
        not_found_err_cls = mixin._gold_module.TableNotFoundError

        mixin._gold_module.DeltaTable = MagicMock(
            side_effect=not_found_err_cls("not found")
        )

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
        from bioetl.application.services.lineage import (
            MetadataLineageBundleResult,
        )

        metadata = _make_bundle_safe_metadata()

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundleResult:
                _ = input_data
                return MetadataLineageBundleResult(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="gold:write-fragment",
                        layer="gold",
                        logical_name="chembl.activity",
                    ),
                )

        mixin = _ConcreteGoldMixin(metadata_coordinator=_Coordinator())
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
        from bioetl.application.services.lineage import (
            MetadataLineageBundleResult,
        )

        metadata = _make_bundle_safe_metadata()

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundleResult:
                _ = input_data
                return MetadataLineageBundleResult(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="gold:resolved-fragment",
                        layer="gold",
                        logical_name="chembl.activity",
                    ),
                )

        mixin = _ConcreteGoldMixin(metadata_coordinator=_Coordinator())
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
    async def test_no_coordinator_fails_closed(self) -> None:
        """Merged Gold metadata must fail closed without the coordinator bundle."""
        mixin = _ConcreteGoldMixin(metadata_coordinator=None)
        records = [{"id": 1, "_source_providers": ["chembl"]}]

        with pytest.raises(
            RuntimeError,
            match="create_gold_metadata_bundle is required for Gold metadata publication",
        ):
            await mixin._write_gold_merged_metadata(
                table_path="gold/t",
                table_name="composite.publication",
                records=records,
            )

        mixin._metadata_writer.write_gold_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_with_coordinator_writes_metadata(self) -> None:
        """Lines 380-395: coordinator present writes metadata."""
        from bioetl.application.services.lineage import (
            MetadataLineageBundleResult,
        )

        metadata = _make_bundle_safe_metadata()

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundleResult:
                _ = input_data
                return MetadataLineageBundleResult(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="gold:merged-write-fragment",
                        layer="gold",
                        logical_name="composite.publication",
                    ),
                )

        mixin = _ConcreteGoldMixin(metadata_coordinator=_Coordinator())
        records = [{"id": 1}]

        await mixin._write_gold_merged_metadata(
            table_path="gold/composite/publication",
            table_name="composite.publication",
            records=records,
        )

        mixin._metadata_writer.write_gold_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepares_merged_metadata_context_before_write(self) -> None:
        """Merged Gold metadata path should resolve provider/entity before persist."""
        from bioetl.application.services.lineage import (
            MetadataLineageBundleResult,
        )

        metadata = _make_bundle_safe_metadata()

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundleResult:
                _ = input_data
                return MetadataLineageBundleResult(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="gold:merged-context-fragment",
                        layer="gold",
                        logical_name="composite.publication",
                    ),
                )

        mixin = _ConcreteGoldMixin(metadata_coordinator=_Coordinator())
        mixin._write_gold_metadata_file = AsyncMock()  # type: ignore[method-assign]

        with patch(
            "bioetl.infrastructure.storage.gold.metadata_operations.build_gold_merged_metadata_input",
            return_value=MagicMock(),
        ) as mock_build:
            await mixin._write_gold_merged_metadata(
                table_path="gold/composite/publication",
                table_name="composite.publication",
                records=[{"id": 1}],
            )

        mock_build.assert_called_once_with(
            table_path="gold/composite/publication",
            table_name="composite.publication",
            records=[{"id": 1}],
            completed_at=None,
            composite_run_id=None,
            schema=None,
            transform_version="1.0.0",
            transform_steps=("step1", "step2"),
        )
        mixin._write_gold_metadata_file.assert_awaited_once_with(
            table_path="gold/composite/publication",
            metadata=metadata,
            table_name="composite.publication",
            provider_name="composite",
            entity_name="publication",
        )
