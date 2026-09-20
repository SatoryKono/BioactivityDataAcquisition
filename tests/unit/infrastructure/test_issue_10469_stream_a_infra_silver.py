"""Bronze/silver mixins and FK adapter isolated because they import deltalake."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.workflow.foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.bronze.io_mixin import (
    BronzeWriterIOMixin,
    write_bytes_if_absent_or_same,
)
from bioetl.infrastructure.storage.bronze.metadata_mixin import (
    BronzeWriterMetadataMixin,
)
from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)
from bioetl.infrastructure.storage.silver.metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
    filter_current_rows,
    _current_flag_column,
    _is_current_flag_value,
)

pytestmark = pytest.mark.unit


class _BronzeHost(BronzeWriterIOMixin):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.logger = MagicMock()
        self._logger = MagicMock()
        self._metrics = MagicMock()
        self.COMPRESSION_LEVEL = 1
        self.COMPRESSION_THREADS = -3
        self.COMPRESSION_CHUNK_SIZE = 8
        self._flat_structure = False
        self._resolve_bronze_path = lambda provider, entity, date_str, filename: (
            f"{provider}/{entity}/{date_str}/{filename}"
        )


class _SilverHost(SilverWriterMetadataMixin):
    def __init__(self) -> None:
        self._dq_calculator = MagicMock()
        self._metadata_writer = NoOpMetadataWriter()
        self._metadata_coordinator = None
        self._audit = None
        self._flat_structure = False


def _fk_request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload = {
        "source_table": "src",
        "reference_table": "ref",
        "source_key": "parent_id",
        "reference_key": "id",
        "primary_keys": ("id",),
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)


class TestBronzeMixins:
    def test_io_mixin_threads_and_atomic_write(self, tmp_path: Path) -> None:
        host = _BronzeHost(tmp_path)
        assert host._effective_compression_threads() == 0
        target = tmp_path / "batch.jsonl"
        write_bytes_if_absent_or_same(target, b"abc", mismatch_message="mismatch")
        write_bytes_if_absent_or_same(target, b"abc", mismatch_message="mismatch")
        with pytest.raises(FileExistsError, match="mismatch"):
            write_bytes_if_absent_or_same(target, b"xyz", mismatch_message="mismatch")
        with pytest.raises(ValueError, match="No records to write"):
            host._finalize_atomic_stream_write(
                target_path=target, temp_path=target, record_count=0
            )
        other = tmp_path / "other.jsonl"
        other.write_bytes(b"xyz")
        host._compressed_payload_matches = lambda *_args: True  # type: ignore[method-assign]
        host._finalize_atomic_stream_write(
            target_path=target, temp_path=other, record_count=1
        )
        host._compressed_payload_matches = lambda *_args: False  # type: ignore[method-assign]
        with pytest.raises(FileExistsError, match="different payload"):
            host._finalize_atomic_stream_write(
                target_path=target, temp_path=other, record_count=1
            )

    async def test_read_cleanup_and_checksum(self, tmp_path: Path) -> None:
        host = _BronzeHost(tmp_path)
        preview = host.preview_cleanup(provider="chembl", entity="activity")
        assert preview["exists"] is False
        assert host._list_batches_sync("chembl", "activity") == []
        date_dir = tmp_path / "chembl" / "activity" / "2020-01-01"
        date_dir.mkdir(parents=True)
        stale = date_dir / "batch.jsonl.zst"
        stale.write_bytes(b"x")
        assert host._is_old_date_dir(date_dir, "2021-01-01") is True
        previewed = host.preview_cleanup("chembl", "activity")
        assert previewed["exists"] is True
        checksum = await host._calculate_checksum(stale)
        assert isinstance(checksum, str)
        cleaned = await host.cleanup_old_files(
            datetime(2021, 1, 1, tzinfo=UTC),
            dry_run=True,
            provider="chembl",
            entity="activity",
        )
        assert cleaned["files_removed"] == 1

    def test_metadata_mixin_coordinator_and_legacy(self) -> None:
        mixin = BronzeWriterMetadataMixin()
        now = datetime(2024, 1, 1, tzinfo=UTC)
        run_id = RunID(UUID("00000000-0000-4000-8000-000000000001"))
        legacy = mixin._build_bronze_metadata(
            run_id,
            RunType.INCREMENTAL,
            now,
            "chembl",
            "activity",
            BatchID(UUID("00000000-0000-4000-8000-000000000002")),
        )
        assert "sidecar_truth_boundary" in legacy
        mixin._metadata_coordinator = SimpleNamespace(
            create_bronze_lineage_sidecar=lambda **_k: {"via": "coordinator"}
        )
        coordinated = mixin._build_bronze_metadata(
            run_id,
            RunType.INCREMENTAL,
            now,
            "chembl",
            "activity",
            BatchID(UUID("00000000-0000-4000-8000-000000000002")),
        )
        assert coordinated == {"via": "coordinator"}
        with pytest.raises(RuntimeError, match="create_bronze_metadata_bundle"):
            mixin._build_full_bronze_metadata(
                run_id,
                RunType.INCREMENTAL,
                "chembl",
                "activity",
                BatchID(UUID("00000000-0000-4000-8000-000000000002")),
                1,
                1,
                "out.jsonl",
                now,
                now,
                0.1,
            )


class TestSilverMetadataMixin:
    def test_skip_and_delta_version(self) -> None:
        host = _SilverHost()
        assert host._should_skip_silver_metadata_write(
            records=[], table_path="/t", event_name="skip"
        )
        assert host._should_skip_silver_metadata_write(
            records=[{"id": "1"}], table_path="/t", event_name="skip"
        )
        host._metadata_writer = object()
        with pytest.raises(RuntimeError, match="create_silver_metadata_bundle"):
            host._should_skip_silver_metadata_write(
                records=[{"id": "1"}], table_path="/t", event_name="skip"
            )
        host._metadata_coordinator = object()
        assert (
            host._should_skip_silver_metadata_write(
                records=[{"id": "1"}], table_path="/t", event_name="ok"
            )
            is False
        )

    async def test_get_delta_version_and_audit_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        host = _SilverHost()

        def _missing(_path: str) -> int:
            raise DeltaTableNotFoundError("missing")

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.silver.metadata_mixin._read_delta_version",
            _missing,
        )
        assert await host._get_delta_version("/missing") is None
        await host._maybe_log_silver_audit(
            table_name="t",
            records=[],
            mode=SilverWriteMode.APPEND,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
        host._audit = MagicMock()
        host._log_silver_audit = AsyncMock()
        await host._maybe_log_silver_audit(
            table_name="t",
            records=[{"id": "1"}],
            mode=SilverWriteMode.APPEND,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
        host._log_silver_audit.assert_awaited()


class TestForeignKeyAdapter:
    def test_filter_current_rows(self) -> None:
        assert filter_current_rows([], current_only=True, layer="silver") == []
        rows = [{"id": "1"}, {"id": "2"}]
        assert filter_current_rows(rows, current_only=False, layer="silver") == rows
        assert filter_current_rows(rows, current_only=True, layer="silver") == rows
        flagged = [
            {"id": "1", "is_current": True},
            {"id": "2", "is_current": False},
            {"id": "3", "is_current": "true"},
            {"id": "4", "is_current": 1},
        ]
        current = filter_current_rows(flagged, current_only=True, layer="gold")
        assert [row["id"] for row in current] == ["1", "3", "4"]
        assert _current_flag_column([]) is None
        assert _is_current_flag_value("yes") is True
        assert _is_current_flag_value("no") is False
        assert _is_current_flag_value(object()) is False

    async def test_adapter_missing_source_empty_and_unproven(self) -> None:
        logger = MagicMock()

        class _MissingSilver:
            async def read_silver(self, table: str, columns=None):
                raise FileNotFoundError(table)

        missing = SilverForeignKeyReconciliationAdapter(
            silver_writer=_MissingSilver(),  # type: ignore[arg-type]
            logger=logger,
        )
        missing_result = await missing.reconcile_foreign_keys(_fk_request())
        assert missing_result.mutation_mode == "missing_source"

        class _EmptySilver:
            async def read_silver(self, table: str, columns=None):
                return []

        empty = SilverForeignKeyReconciliationAdapter(
            silver_writer=_EmptySilver(),  # type: ignore[arg-type]
            logger=logger,
        )
        empty_result = await empty.reconcile_foreign_keys(_fk_request())
        assert empty_result.mutation_mode == "no_op"

        blocked_request = _fk_request(source_scope="current_run", source_run_ids=())

        class _Scoped:
            async def read_silver(self, table: str, columns=None):
                return [{"id": "1", "parent_id": "x"}]

        blocked = SilverForeignKeyReconciliationAdapter(
            silver_writer=_Scoped(),  # type: ignore[arg-type]
            logger=logger,
        )
        with pytest.raises(ValueError, match="current_run scope unbound"):
            await blocked.reconcile_foreign_keys(blocked_request)

        class _Rows:
            async def read_silver(self, table: str, columns=None):
                if table == "src":
                    return [{"id": "1", "parent_id": "missing"}]
                return [{"id": "present"}]

        unproven = SilverForeignKeyReconciliationAdapter(
            silver_writer=_Rows(),  # type: ignore[arg-type]
            logger=logger,
        )
        result = await unproven.reconcile_foreign_keys(_fk_request())
        assert result.mutation_blocked_reason == "reference_completeness_unproven"

        gold = SilverForeignKeyReconciliationAdapter(
            silver_writer=_Rows(),  # type: ignore[arg-type]
            logger=logger,
            gold_writer=None,
        )
        with pytest.raises(ValueError, match="requires a configured gold_writer"):
            await gold.reconcile_foreign_keys(_fk_request(source_layer="gold"))

        mismatch = await unproven.reconcile_foreign_keys(
            _fk_request(
                reference_completeness="complete",
                reference_identity="other_table",
                completeness_evidence_ref="ev-1",
            )
        )
        assert (
            mismatch.mutation_blocked_reason
            == "reference_completeness_identity_mismatch"
        )

        request = _fk_request()
        object.__setattr__(request, "action", "flag_orphans")
        with pytest.raises(ValueError, match="supports only delete_orphans"):
            await unproven.reconcile_foreign_keys(request)
