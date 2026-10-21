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
"""Integration tests for Silver maintenance time travel on real Delta tables."""

from __future__ import annotations

from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)

from tests.helpers.clock import fixed_test_clock

from pathlib import Path

import pyarrow as pa
import pytest

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


def _records_v1() -> list[dict[str, str]]:
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


def _records_v2() -> list[dict[str, str]]:
    return [
        {
            "id": "2",
            "val": "B",
            "_run_id": "00000000-0000-4000-8000-000000000002",
            "_run_type": "incremental",
            "_source_batch_id": "batch-2",
            "_ingestion_ts": "2026-01-02T00:00:00+00:00",
        }
    ]


@pytest.fixture
def temp_delta_path(tmp_path: Path) -> str:
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)


@pytest.fixture
def silver_writer(temp_delta_path: str, noop_logger: object) -> SilverWriter:
    return SilverWriter(
        runtime_request=SilverWriterRuntimeServicesRequest(clock=fixed_test_clock()),
        base_path=temp_delta_path,
        logger=noop_logger,
    )


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_silver_time_travel_returns_named_versions(
    silver_writer: SilverWriter,
    temp_delta_path: str,
) -> None:
    """Verify time_travel successfully loads versions before/after updates and vacuum dry-run."""
    table_name = "maintenance_time_travel"
    await silver_writer.write_silver(
        table_name=table_name,
        records=_records_v1(),
        primary_keys=["id"],
        schema=_schema(),
    )

    await silver_writer.write_silver(
        table_name=table_name,
        records=_records_v2(),
        primary_keys=["id"],
        schema=_schema(),
    )

    # Version 0 has the first key. Version 1 merges the second distinct key.
    dt_v0 = await silver_writer.time_travel(table_name, version=0)
    assert len(dt_v0.to_pandas()) == 1

    dt_v1 = await silver_writer.time_travel(table_name, version=1)
    assert len(dt_v1.to_pandas()) == 2

    # Dry-run vacuum should not affect time travel
    await silver_writer.vacuum(table_name, retention_hours=168, dry_run=True)
    dt_v0_after = await silver_writer.time_travel(table_name, version=0)
    assert len(dt_v0_after.to_pandas()) == 1
