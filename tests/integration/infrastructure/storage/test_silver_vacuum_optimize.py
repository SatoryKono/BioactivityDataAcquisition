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
"""Integration tests for Silver maintenance vacuum and optimize on real Delta tables."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]


def _schema() -> pa.Schema:
    return pa.schema(
        [
            ("id", pa.string()),
            ("val", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ]
    )


def _records() -> list[dict[str, str]]:
    return [
        {
            "id": "1",
            "val": "A",
            "_run_id": "00000000-0000-4000-8000-000000000001",
            "_run_type": "incremental",
            "_source_batch_id": "batch-1",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
        }
    ]


@pytest.fixture
def temp_delta_path(tmp_path: Path) -> str:
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)


@pytest.fixture
def silver_writer(temp_delta_path: str, noop_logger: object) -> SilverWriter:
    return SilverWriter(base_path=temp_delta_path, logger=noop_logger)


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_silver_vacuum_dry_run_on_materialized_table(
    silver_writer: SilverWriter,
    temp_delta_path: str,
) -> None:
    """Vacuum dry-run must succeed without deleting rows from a freshly written table."""
    table_name = "maintenance_vacuum"
    await silver_writer.write_silver(
        table_name=table_name,
        records=_records(),
        primary_keys=["id"],
        schema=_schema(),
    )

    deleted = await silver_writer.vacuum(table_name, retention_hours=168, dry_run=True)

    assert isinstance(deleted, list)
    frame = DeltaTable(f"{temp_delta_path}/{table_name}").to_pandas()
    assert len(frame) == 1


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_silver_optimize_returns_metrics_on_materialized_table(
    silver_writer: SilverWriter,
) -> None:
    """Optimize compact must run against a real Delta table and return metrics payload."""
    table_name = "maintenance_optimize"
    await silver_writer.write_silver(
        table_name=table_name,
        records=_records(),
        primary_keys=["id"],
        schema=_schema(),
    )

    metrics = await silver_writer.optimize(table_name)

    assert isinstance(metrics, dict)
