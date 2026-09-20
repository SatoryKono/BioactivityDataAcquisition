"""L12 residuals: bronze/delta/atomic/fk/row recon. No gold_writer or silver_writer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pyarrow as pa
import pytest

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
    BronzeWriteArtifacts,
    BronzeWritePostwriteContext,
    BronzeWritePrepared,
    BronzeWriteRequest,
)
from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)
from bioetl.infrastructure.storage.bronze.side_effects_mixin import (
    BronzeWriterSideEffectsMixin,
)
from bioetl.infrastructure.storage.bronze.write_execution import (
    run_bronze_post_write_actions,
)
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy
from bioetl.infrastructure.storage.delta_reader_helpers import (
    try_native_delta_row_count,
)
from bioetl.infrastructure.storage.metadata.builder_base import _MetadataBuilderBase
from bioetl.infrastructure.storage.metadata_writer_public import MetadataWriter
from bioetl.infrastructure.storage.support import atomic_ops
from bioetl.infrastructure.storage.support._atomic_replace import (
    AtomicWriteError,
    _replace_prevalidated_with_retry,
)
from bioetl.infrastructure.storage.support.atomic_ops import atomic_write
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    CheckpointPathError,
    FileCompositeCheckpointWriter,
)
from bioetl.infrastructure.storage.support.retention_dedup import deduplicate_delta_rows
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    normalize_row_key,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import _supported_kwargs

pytestmark = pytest.mark.unit


def test_atomic_ops_unlink_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.bin"

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(atomic_ops, "_replace_with_retry", _boom)
    original_unlink = Path.unlink

    def _unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self.parent == target.parent and self != target:
            raise OSError("busy")
        original_unlink(self, *args, **kwargs)  # type: ignore[misc]

    monkeypatch.setattr(Path, "unlink", _unlink)
    with pytest.raises(AtomicWriteError):
        with atomic_write(target) as handle:
            handle.write(b"payload")


def test_supported_kwargs_signature_type_error() -> None:
    filtered = _supported_kwargs(object(), {"keep": 1, "drop": None})
    assert filtered == {"keep": 1}


def test_normalize_row_key_nulls_not_equal() -> None:
    assert normalize_row_key({"id": None}, ("id",), nulls_equal=False) is None


def test_checkpoint_escapes_root(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path / "ckpts")
    outside = tmp_path / "other" / "file.json"
    outside.parent.mkdir()
    with pytest.raises(CheckpointPathError, match="escapes"):
        writer._ensure_contained(outside, source="other/file.json")


def test_atomic_replace_sleeps_on_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slept: list[float] = []
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support._atomic_replace.time.sleep",
        slept.append,
    )
    temp = tmp_path / "tmp.bin"
    target = tmp_path / "out.bin"
    temp.write_bytes(b"a")
    calls = {"n": 0}

    def _replace(self: Path, _dst: Path) -> Path:
        calls["n"] += 1
        if calls["n"] == 1:
            error = OSError(13, "denied")
            error.winerror = 32  # type: ignore[attr-defined]
            raise error
        target.write_bytes(b"ok")
        return target

    monkeypatch.setattr(Path, "replace", _replace)
    _replace_prevalidated_with_retry(
        temp,
        target,
        retry_policy=AdaptiveRetryPolicy(
            enabled=True,
            max_retries=2,
            base_delay_seconds=0.01,
            max_delay_seconds=0.01,
        ),
    )
    assert slept
    assert calls["n"] == 2


def test_try_native_delta_row_count_runtime_error() -> None:
    class _Table:
        def count(self) -> int:
            raise RuntimeError("unavailable")

    assert try_native_delta_row_count(_Table()) is None  # type: ignore[arg-type]


def test_arrow_converter_fallback_to_string() -> None:
    class _Col:
        def __len__(self) -> int:
            return 2

        def cast(self, _new_type: object) -> pa.Array:
            raise pa.ArrowInvalid("cannot cast")

        def to_pylist(self) -> list[int]:
            return [1, 2]

    converter = ArrowDataConverter(logger=MagicMock())
    column, effective = converter._sanitize_single_null_column(
        _Col(),  # type: ignore[arg-type]
        pa.int64(),
        object(),  # type: ignore[arg-type]
    )
    assert effective == pa.string()
    assert column.to_pylist() == ["1", "2"]


def test_metadata_builder_no_cv_signal() -> None:
    summary = _MetadataBuilderBase._build_merged_dq_summary([])
    assert summary.total_records == 0
    assert summary.error_records == 0


@pytest.mark.asyncio
async def test_metadata_writer_finalize_existing_delegates() -> None:
    writer = MetadataWriter.__new__(MetadataWriter)
    writer._operations = SimpleNamespace(  # type: ignore[attr-defined]
        finalize_existing_layer_metadata=AsyncMock(return_value="meta.yaml"),
    )
    path = await writer._finalize_existing_layer_metadata(
        base_path="base",
        layer="gold",
        apply_finalization=lambda _meta: None,
        table_name="activity",
    )
    assert path == "meta.yaml"


def test_bronze_cleanup_rmdir(tmp_path: Path) -> None:
    date_dir = tmp_path / "2020-01-01"
    date_dir.mkdir()

    class _Host(BronzeWriterReadCleanupMixin):
        def _find_old_date_dirs(
            self,
            _cutoff_str: str,
            _provider: str | None,
            _entity: str | None,
        ) -> list[Path]:
            return [date_dir]

        def _remove_old_dir_files(
            self,
            *,
            date_dir: Path,
            dry_run: bool,
        ) -> tuple[int, int]:
            del date_dir, dry_run
            return 1, 10

    files, bytes_total, dirs = _Host()._cleanup_old_files_sync(
        "2021-01-01",
        False,
        "chembl",
        "activity",
    )
    assert (files, bytes_total, dirs) == (1, 10, 1)
    assert not date_dir.exists()


@pytest.mark.asyncio
async def test_bronze_side_effects_persist_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = BronzeWriterSideEffectsMixin()
    host._metadata_writer = SimpleNamespace(  # type: ignore[attr-defined]
        write_bronze_metadata=AsyncMock(),
    )
    host._lineage_store = None  # type: ignore[attr-defined]
    host._metrics = None  # type: ignore[attr-defined]
    host._metadata_coordinator = None  # type: ignore[attr-defined]
    host.logger = MagicMock()  # type: ignore[attr-defined]
    prepared = SimpleNamespace(
        metadata_base_path=tmp_path,
        metadata=object(),
        lineage_fragment=None,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.side_effects_mixin.prepare_bronze_metadata_write",
        lambda *_args, **_kwargs: prepared,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.side_effects_mixin.persist_lineage_fragment_if_present",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.side_effects_mixin.lineage_fragment_publication_required",
        lambda _coord: False,
    )
    await host._maybe_write_bronze_metadata(
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000002")),
        run_type=RunType.INCREMENTAL,
        provider="chembl",
        entity="activity",
        batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000003")),
        record_count=1,
        compressed_size=2,
        relative_path="chembl/activity/x.jsonl.zst",
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        duration=0.1,
        source_metadata=None,
    )
    host.logger.debug.assert_called()


@pytest.mark.asyncio
async def test_bronze_post_write_saves_metadata() -> None:
    request = BronzeWriteRequest(
        records=iter([]),
        provider="chembl",
        entity="activity",
        date=datetime(2026, 1, 1, tzinfo=UTC),
        batch_id=BatchID(uuid4()),
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
    )
    prepared = BronzeWritePrepared(
        records_iter=iter([]),
        record_list=[],
        date_str="2026-01-01",
        relative_path="chembl/activity/x",
        metadata={},
        full_path=Path("x"),
        meta_path=Path("m"),
    )
    context = BronzeWritePostwriteContext(
        request=request,
        prepared=prepared,
        write_artifacts=BronzeWriteArtifacts(1, 2, 3),
        duration=0.2,
    )
    host = SimpleNamespace(
        save_json=False,
        _audit=None,
        _save_metadata=True,
        _emit_bronze_write_metrics=lambda **_kwargs: None,
        _maybe_write_bronze_metadata=AsyncMock(),
    )
    await run_bronze_post_write_actions(host, context)  # type: ignore[arg-type]
    host._maybe_write_bronze_metadata.assert_awaited()


@pytest.mark.asyncio
async def test_bronze_writer_cleanup_bronze() -> None:
    writer = BronzeWriter.__new__(BronzeWriter)
    writer.cleanup_old_files = AsyncMock(return_value={"removed_files": 2})  # type: ignore[method-assign]
    result = await writer.cleanup_bronze(datetime(2026, 1, 1, tzinfo=UTC), dry_run=True)
    assert result == {"removed_files": 2}
    writer.cleanup_old_files.assert_awaited_once()


def test_retention_dedup_skips_duplicate_primary_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"id": "1", "content_hash": "aaa", "v": 1},
        {"id": "1", "content_hash": "bbb", "v": 2},
    ]
    arrow = pa.Table.from_pylist(rows)

    class _Handle:
        def to_pyarrow_dataset(self) -> SimpleNamespace:
            return SimpleNamespace(
                scanner=lambda: SimpleNamespace(head=lambda _n: arrow)
            )

        def schema(self) -> object:
            return object()

    monkeypatch.setattr("deltalake.DeltaTable", lambda _path: _Handle())
    monkeypatch.setattr("deltalake.write_deltalake", lambda **_kwargs: None)
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.retention_dedup.delta_schema_to_pyarrow",
        lambda _schema: arrow.schema,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.retention_dedup.try_native_delta_row_count",
        lambda _dt: 2,
    )
    removed = deduplicate_delta_rows("table-path", ["id"])
    assert removed == 1
