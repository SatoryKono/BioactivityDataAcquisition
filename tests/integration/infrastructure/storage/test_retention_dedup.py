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
"""Tests for RetentionPolicy.deduplicate_silver."""

from __future__ import annotations

import time
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake
from deltalake.exceptions import CommitFailedError

import bioetl.infrastructure.storage.support.retention_dedup as retention_module
from bioetl.domain.exceptions import StorageError
from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.infrastructure.storage.support.retention import (
    RetentionPolicy,
    _resolve_deduplication_timeout_seconds,
    _content_identity,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def tmp_delta_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for Delta tables."""
    return tmp_path / "silver"


def _write_test_table(
    table_dir: Path,
    records: list[dict],
    mode: str = "append",
) -> None:
    """Write records to a Delta table."""
    table_dir.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            pa.field("activity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )
    arrays = [
        pa.array([r["activity_id"] for r in records]),
        pa.array([r["value"] for r in records]),
        pa.array([r["_ingestion_ts"] for r in records]),
    ]
    table = pa.table(arrays, schema=schema)
    write_deltalake(str(table_dir), table, mode=mode)


def _write_content_hash_table(
    table_dir: Path,
    records: list[dict],
    mode: str = "append",
) -> None:
    """Write records to a Delta table without ingestion timestamps."""
    table_dir.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            pa.field("activity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("content_hash", pa.string()),
        ]
    )
    table = pa.table(
        [
            pa.array([r["activity_id"] for r in records]),
            pa.array([r["value"] for r in records]),
            pa.array([r["content_hash"] for r in records]),
        ],
        schema=schema,
    )
    write_deltalake(str(table_dir), table, mode=mode)


@pytest.mark.asyncio
async def test_deduplicate_removes_duplicates(tmp_delta_dir: Path) -> None:
    """Dedup should keep a deterministic winner without relying on timestamps."""
    table_path = tmp_delta_dir / "test_entity"

    # Write batch 1 (older)
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 10.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
            {
                "activity_id": "2",
                "value": 20.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
        ],
    )
    # Append batch 2 (newer, with duplicate for id=1)
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 15.0,
                "_ingestion_ts": "2024-01-02T00:00:00Z",
            },
            {
                "activity_id": "3",
                "value": 30.0,
                "_ingestion_ts": "2024-01-02T00:00:00Z",
            },
        ],
        mode="append",
    )

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])

    assert removed == 1  # One duplicate for activity_id=1

    # Verify the table has 3 unique records
    from deltalake import DeltaTable

    dt = DeltaTable(str(table_path))
    result = dt.to_pyarrow_table()
    assert result.num_rows == 3

    # Verify the deterministic winner for activity_id=1 is kept.
    # The compaction contract no longer depends on `_ingestion_ts`.
    rows = result.to_pylist()
    id1_rows = [r for r in rows if r["activity_id"] == "1"]
    assert len(id1_rows) == 1
    assert id1_rows[0]["value"] == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_deduplicate_no_duplicates(tmp_delta_dir: Path) -> None:
    """Dedup should return 0 when no duplicates exist."""
    table_path = tmp_delta_dir / "test_entity"
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 10.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
            {
                "activity_id": "2",
                "value": 20.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
        ],
    )

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])

    assert removed == 0


@pytest.mark.asyncio
async def test_deduplicate_empty_table(tmp_delta_dir: Path) -> None:
    """Dedup should return 0 for empty table."""
    table_path = tmp_delta_dir / "test_entity"
    table_path.mkdir(parents=True, exist_ok=True)

    schema = pa.schema(
        [
            pa.field("activity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )
    empty = pa.table(
        [
            pa.array([], type=pa.string()),
            pa.array([], type=pa.float64()),
            pa.array([], type=pa.string()),
        ],
        schema=schema,
    )
    write_deltalake(str(table_path), empty)

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])

    assert removed == 0


@pytest.mark.asyncio
async def test_deduplicate_missing_table(tmp_delta_dir: Path) -> None:
    """Dedup should raise TableNotFoundError for missing table."""
    from bioetl.domain.exceptions import TableNotFoundError

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))

    with pytest.raises(TableNotFoundError):
        await mgr.deduplicate_silver("nonexistent", primary_keys=["activity_id"])


@pytest.mark.asyncio
async def test_deduplicate_uses_content_hash_when_ingestion_ts_missing(
    tmp_delta_dir: Path,
) -> None:
    """Dedup should remain deterministic when persisted rows omit ingestion timestamps."""
    table_path = tmp_delta_dir / "test_entity_hash_only"
    _write_content_hash_table(
        table_path,
        [
            {"activity_id": "1", "value": 10.0, "content_hash": "z-hash"},
            {"activity_id": "1", "value": 9.0, "content_hash": "a-hash"},
            {"activity_id": "2", "value": 20.0, "content_hash": "m-hash"},
        ],
    )

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver(
        "test_entity_hash_only", primary_keys=["activity_id"]
    )

    assert removed == 1

    from deltalake import DeltaTable

    rows = DeltaTable(str(table_path)).to_pyarrow_table().to_pylist()
    id1_rows = [row for row in rows if row["activity_id"] == "1"]
    assert len(id1_rows) == 1
    assert id1_rows[0]["content_hash"] == "a-hash"


@pytest.mark.asyncio
async def test_deduplicate_prefers_content_hash_over_ingestion_timestamp(
    tmp_delta_dir: Path,
) -> None:
    """Content-aware winner selection should ignore newer ingestion timestamps."""
    table_path = tmp_delta_dir / "test_entity_hash_and_ts"
    table_path.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            pa.field("activity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("content_hash", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )
    table = pa.table(
        [
            pa.array(["1", "1"]),
            pa.array([10.0, 15.0]),
            pa.array(["a-hash", "z-hash"]),
            pa.array(["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"]),
        ],
        schema=schema,
    )
    write_deltalake(str(table_path), table)

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver(
        "test_entity_hash_and_ts", primary_keys=["activity_id"]
    )

    assert removed == 1

    from deltalake import DeltaTable

    rows = DeltaTable(str(table_path)).to_pyarrow_table().to_pylist()
    assert rows == [
        {
            "activity_id": "1",
            "value": 10.0,
            "content_hash": "a-hash",
            "_ingestion_ts": "2024-01-01T00:00:00Z",
        }
    ]


def test_deduplicate_full_read_uses_dataset_scanner_over_native_table_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dedup full reads should avoid native to_pyarrow_table scan paths."""
    import deltalake

    expected = pa.table(
        {
            "activity_id": ["1", "1", "2"],
            "value": [10.0, 15.0, 20.0],
            "_ingestion_ts": [
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-01T00:00:00Z",
            ],
        }
    )
    captured: dict[str, object] = {}

    class _FakeScanner:
        def head(self, limit: int) -> pa.Table:
            captured["limit"] = limit
            return expected

    class _FakeDataset:
        def scanner(self) -> _FakeScanner:
            captured["scanner_used"] = True
            return _FakeScanner()

    class _FakeSchema:
        def to_arrow(self) -> pa.Schema:
            return expected.schema

    class _FakeDeltaTable:
        def __init__(self, table_uri: str) -> None:
            captured["table_uri"] = table_uri

        def count(self) -> int:
            return expected.num_rows

        def schema(self) -> _FakeSchema:
            return _FakeSchema()

        def to_pyarrow_dataset(self) -> _FakeDataset:
            return _FakeDataset()

        def to_pyarrow_table(self, columns: list[str] | None = None) -> pa.Table:
            raise AssertionError(
                f"unexpected native full-table read: columns={columns}"
            )

    original_delta_table = deltalake.DeltaTable
    original_write = deltalake.write_deltalake

    def _capture_write(*args: object, **kwargs: object) -> None:
        captured["write_kwargs"] = kwargs

    monkeypatch.setattr(deltalake, "DeltaTable", _FakeDeltaTable)
    monkeypatch.setattr(deltalake, "write_deltalake", _capture_write)
    try:
        removed = retention_module.deduplicate_delta_rows(
            "/tmp/fake-table",
            ["activity_id"],
        )
    finally:
        monkeypatch.setattr(deltalake, "DeltaTable", original_delta_table)
        monkeypatch.setattr(deltalake, "write_deltalake", original_write)

    assert removed == 1
    assert captured["scanner_used"] is True
    assert captured["limit"] == expected.num_rows
    written = captured["write_kwargs"]
    assert isinstance(written, dict)
    output_table = written["data"]
    assert isinstance(output_table, pa.Table)
    assert output_table.to_pylist() == [
        {
            "activity_id": "1",
            "value": 10.0,
            "_ingestion_ts": "2024-01-01T00:00:00Z",
        },
        {
            "activity_id": "2",
            "value": 20.0,
            "_ingestion_ts": "2024-01-01T00:00:00Z",
        },
    ]


def test_content_identity_fallback_uses_canonical_hash_identity_contract() -> None:
    """Retention fallback must reuse the canonical hash-identity seam."""
    row = {
        "activity_id": "1",
        "value": 10.0,
        "measured_at": " 2025-01-01 ",
        "_ingestion_ts": "2026-01-01T00:00:00Z",
    }

    assert _content_identity(row) == serialize_hash_identity_canonical_json(
        normalize_hash_identity_record(row)
    )


def test_dedup_timeout_is_clamped_in_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-Windows test mode should keep the tighter default dedup budget."""

    class _Settings:
        test_mode = True
        silver_dedup_timeout_seconds = 60.0

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.retention_dedup.platform.system",
        lambda: "Linux",
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.retention.get_settings",
        lambda: _Settings(),
    )

    assert _resolve_deduplication_timeout_seconds() == pytest.approx(10.0)


def test_dedup_timeout_is_relaxed_in_windows_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows test mode should allow a larger dedup budget for delta-rs writes."""

    class _Settings:
        test_mode = True
        silver_dedup_timeout_seconds = 60.0

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.retention_dedup.platform.system",
        lambda: "Windows",
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.retention.get_settings",
        lambda: _Settings(),
    )

    assert _resolve_deduplication_timeout_seconds() == pytest.approx(60.0)


@pytest.mark.asyncio
async def test_deduplicate_times_out_for_slow_sync_dedup(tmp_delta_dir: Path) -> None:
    """Dedup should report timeout when synchronous Delta maintenance runs too long."""
    import deltalake

    class _StuckScanner:
        def head(self, limit: int) -> pa.Table:
            time.sleep(0.1)
            return pa.table(
                {
                    "activity_id": pa.array(["1"]),
                    "value": pa.array([10.0]),
                    "_ingestion_ts": pa.array(["2024-01-01T00:00:00Z"]),
                }
            )

    class _StuckDataset:
        def scanner(self) -> _StuckScanner:
            return _StuckScanner()

    class _StuckSchema:
        def to_arrow(self) -> pa.Schema:
            return pa.schema(
                [
                    pa.field("activity_id", pa.string()),
                    pa.field("value", pa.float64()),
                    pa.field("_ingestion_ts", pa.string()),
                ]
            )

    class _StuckDeltaTable:
        def __init__(self, table_path: str) -> None:
            self._table_path = table_path

        def count(self) -> int:
            return 1

        def schema(self) -> _StuckSchema:
            return _StuckSchema()

        def to_pyarrow_dataset(self) -> _StuckDataset:
            return _StuckDataset()

    original_delta_table = deltalake.DeltaTable
    deltalake.DeltaTable = _StuckDeltaTable
    try:
        mgr = RetentionPolicy(
            base_path=str(tmp_delta_dir),
            deduplicate_timeout_seconds=0.01,
        )
        with pytest.raises(TimeoutError, match="Silver deduplication timed out"):
            await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])
    finally:
        deltalake.DeltaTable = original_delta_table


@pytest.mark.asyncio
async def test_deduplicate_translates_commit_conflict_to_storage_error(
    tmp_delta_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Commit conflicts during dedup should surface as canonical storage errors."""
    import deltalake

    table_path = tmp_delta_dir / "test_entity_conflict"
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 10.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
            {
                "activity_id": "1",
                "value": 15.0,
                "_ingestion_ts": "2024-01-02T00:00:00Z",
            },
        ],
    )

    original_write = deltalake.write_deltalake

    def _raise_conflict(*args: object, **kwargs: object) -> None:
        raise CommitFailedError("conflict")

    monkeypatch.setattr(deltalake, "write_deltalake", _raise_conflict)
    try:
        mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
        with pytest.raises(StorageError, match="during deduplicate"):
            await mgr.deduplicate_silver(
                "test_entity_conflict",
                primary_keys=["activity_id"],
            )
    finally:
        monkeypatch.setattr(deltalake, "write_deltalake", original_write)
