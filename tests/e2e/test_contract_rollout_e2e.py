"""Local E2E tests for versioned contract rollout behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    SilverWriterRuntimeServices,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_versioned_table_name,
)


@pytest.fixture
def silver_rollout_schema() -> pa.Schema:
    return pa.schema(
        [
            ("id", pa.string()),
            ("value", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ]
    )


def _make_rollout_policy(*, affects_hash: bool) -> ContractRolloutPolicy:
    return ContractRolloutPolicy(
        contract_ref="chembl.activity",
        active_version="1.0.0",
        mode="dual_read_write",
        read_order=("1.0.0", "2.0.0"),
        write_versions=("1.0.0", "2.0.0"),
        affects_hash=affects_hash,
    )


def _make_record(
    *,
    record_id: str,
    value: str,
    content_hash: str,
    version_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": record_id,
        "value": value,
        "content_hash": content_hash,
        "_run_id": "run-1",
        "_run_type": "incremental",
        "_source_batch_id": "batch-1",
        "_ingestion_ts": "2026-04-01T00:00:00Z",
    }
    if version_hashes is not None:
        record["_content_hashes_by_version"] = version_hashes
    return record


def _build_rollout_runtime_services(
    *,
    affects_hash: bool,
    base_path: Path,
) -> SilverWriterRuntimeServices:
    return build_silver_writer_runtime_services(
        SilverWriterRuntimeServicesRequest(
            csv_exporter=None,
            tracing=None,
            write_policy=None,
            metrics=None,
            audit=None,
            logger=None,
            silver_validator=None,
            metadata_writer=None,
            metadata_coordinator=None,
            lineage_store=None,
            dq_calculator=None,
            merge_resilience_policy=None,
            base_path=base_path,
            contract_rollout_policy=_make_rollout_policy(affects_hash=affects_hash),
        )
    )


def _versioned_table_path(
    base_path: Path, logical_table: str, contract_version: str
) -> Path:
    provider, _ = logical_table.split(".", 1)
    table_name = resolve_versioned_table_name(logical_table, contract_version)
    return base_path / provider / table_name.split(".", 1)[1]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_contract_rollout_affects_hash_false_dual_write_keeps_same_hash(
    e2e_data_dir: Path,
    silver_rollout_schema: pa.Schema,
) -> None:
    logical_table = "chembl.activity"
    writer = SilverWriter(
        base_path=e2e_data_dir / "silver",
        logger=NoOpLogger(),
        runtime_services=_build_rollout_runtime_services(
            affects_hash=False,
            base_path=e2e_data_dir / "silver",
        ),
    )

    await writer.write_silver(
        table_name=logical_table,
        records=[
            _make_record(record_id="1", value="same-hash", content_hash="stable-hash")
        ],
        primary_keys=["id"],
        schema=silver_rollout_schema,
    )

    v1_table = DeltaTable(
        str(_versioned_table_path(e2e_data_dir / "silver", logical_table, "1.0.0"))
    )
    v2_table = DeltaTable(
        str(_versioned_table_path(e2e_data_dir / "silver", logical_table, "2.0.0"))
    )

    assert (
        v1_table.to_pyarrow_table().to_pylist()
        == v2_table.to_pyarrow_table().to_pylist()
    )
    assert v1_table.to_pyarrow_table().to_pylist()[0]["content_hash"] == "stable-hash"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_contract_rollout_affects_hash_true_dual_write_projects_version_hashes(
    e2e_data_dir: Path,
    silver_rollout_schema: pa.Schema,
) -> None:
    logical_table = "chembl.activity"
    writer = SilverWriter(
        base_path=e2e_data_dir / "silver",
        logger=NoOpLogger(),
        runtime_services=_build_rollout_runtime_services(
            affects_hash=True,
            base_path=e2e_data_dir / "silver",
        ),
    )

    await writer.write_silver(
        table_name=logical_table,
        records=[
            _make_record(
                record_id="1",
                value="versioned-hash",
                content_hash="legacy-hash",
                version_hashes={"1.0.0": "hash-v1", "2.0.0": "hash-v2"},
            )
        ],
        primary_keys=["id"],
        schema=silver_rollout_schema,
    )

    v1_rows = (
        DeltaTable(
            str(_versioned_table_path(e2e_data_dir / "silver", logical_table, "1.0.0"))
        )
        .to_pyarrow_table()
        .to_pylist()
    )
    v2_rows = (
        DeltaTable(
            str(_versioned_table_path(e2e_data_dir / "silver", logical_table, "2.0.0"))
        )
        .to_pyarrow_table()
        .to_pylist()
    )

    assert v1_rows[0]["content_hash"] == "hash-v1"
    assert v2_rows[0]["content_hash"] == "hash-v2"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_contract_rollout_cutover_and_rollback_change_read_priority(
    e2e_data_dir: Path,
) -> None:
    logical_table = "chembl.activity"
    silver_base_path = e2e_data_dir / "silver"
    logger = NoOpLogger()
    reader = DeltaReader(base_path=silver_base_path, logger=logger)

    v1_path = _versioned_table_path(silver_base_path, logical_table, "1.0.0")
    v2_path = _versioned_table_path(silver_base_path, logical_table, "2.0.0")
    v1_path.parent.mkdir(parents=True, exist_ok=True)
    v2_path.parent.mkdir(parents=True, exist_ok=True)
    write_deltalake(
        str(v1_path), pa.Table.from_pylist([{"id": "1", "value": "legacy"}])
    )
    write_deltalake(
        str(v2_path), pa.Table.from_pylist([{"id": "1", "value": "shadow"}])
    )

    before_cutover = await reader.read_with_fallback(logical_table, ["1.0.0", "2.0.0"])
    after_cutover = await reader.read_with_fallback(logical_table, ["2.0.0", "1.0.0"])
    after_rollback = await reader.read_with_fallback(logical_table, ["1.0.0", "2.0.0"])

    assert before_cutover.to_pylist() == [{"id": "1", "value": "legacy"}]
    assert after_cutover.to_pylist() == [{"id": "1", "value": "shadow"}]
    assert after_rollback.to_pylist() == [{"id": "1", "value": "legacy"}]
