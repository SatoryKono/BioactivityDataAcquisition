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
"""Integration tests for Silver merge idempotency and replay consistency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from bioetl.domain.transformations import generate_content_hash
from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]


def _content_hash_schema() -> pa.Schema:
    return pa.schema(
        [
            ("id", pa.string()),
            ("val", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ]
    )


def _record(
    *,
    record_id: str,
    val: str,
    run_id: str = "00000000-0000-4000-8000-000000000001",
    ingestion_ts: str = "2026-01-01T00:00:00+00:00",
) -> dict[str, str]:
    payload = {"id": record_id, "val": val}
    return {
        "id": record_id,
        "val": val,
        "content_hash": str(generate_content_hash(payload, "replay-test")),
        "_run_id": run_id,
        "_run_type": "incremental",
        "_source_batch_id": "batch-1",
        "_ingestion_ts": ingestion_ts,
    }


def _table_checksum(table_path: str) -> str:
    frame = DeltaTable(table_path).to_pandas().sort_values("id").reset_index(drop=True)
    canonical = json.dumps(frame.to_dict(orient="records"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@pytest.fixture
def temp_delta_path(tmp_path: Path) -> str:
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)


@pytest.fixture
def silver_writer(temp_delta_path: str, noop_logger: object) -> SilverWriter:
    return SilverWriter(base_path=temp_delta_path, logger=noop_logger)


@pytest.mark.asyncio
async def test_silver_merge_replay_is_idempotent_by_table_checksum(
    silver_writer: SilverWriter,
    temp_delta_path: str,
) -> None:
    """Re-merging identical payloads must leave canonical table bytes unchanged."""
    schema = _content_hash_schema()
    records = [_record(record_id="1", val="A"), _record(record_id="2", val="B")]
    table_name = "replay_idempotent"

    await silver_writer.write_silver(
        table_name=table_name,
        records=records,
        primary_keys=["id"],
        schema=schema,
    )
    first_checksum = _table_checksum(f"{temp_delta_path}/{table_name}")

    await silver_writer.write_silver(
        table_name=table_name,
        records=records,
        primary_keys=["id"],
        schema=schema,
    )
    second_checksum = _table_checksum(f"{temp_delta_path}/{table_name}")

    assert first_checksum == second_checksum


@pytest.mark.asyncio
async def test_silver_merge_replay_preserves_business_columns_on_metadata_rerun(
    silver_writer: SilverWriter,
    temp_delta_path: str,
) -> None:
    """Metadata-only reruns must not mutate business columns or content hashes."""
    schema = _content_hash_schema()
    table_name = "replay_metadata_only"
    first = [_record(record_id="1", val="stable")]
    rerun = [
        _record(
            record_id="1",
            val="stable",
            run_id="00000000-0000-4000-8000-000000000002",
            ingestion_ts="2026-01-02T00:00:00+00:00",
        )
    ]

    await silver_writer.write_silver(
        table_name=table_name,
        records=first,
        primary_keys=["id"],
        schema=schema,
    )
    before_rows = (
        DeltaTable(f"{temp_delta_path}/{table_name}")
        .to_pandas()
        .sort_values("id")
        .reset_index(drop=True)
        .to_dict(orient="records")
    )

    await silver_writer.write_silver(
        table_name=table_name,
        records=rerun,
        primary_keys=["id"],
        schema=schema,
    )
    after_rows = (
        DeltaTable(f"{temp_delta_path}/{table_name}")
        .to_pandas()
        .sort_values("id")
        .reset_index(drop=True)
        .to_dict(orient="records")
    )

    assert after_rows == before_rows
