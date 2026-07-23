"""Integration tests for version-aware Gold dual-write behavior."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from pandera.pandas import Column, DataFrameSchema

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import (
    GoldContractValidationError,
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.storage.delta.table_ops import (
    load_delta_table,
    read_delta_records,
)
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter


@pytest.fixture
def strict_schema() -> DataFrameSchema:
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "value": Column(float, nullable=False),
        },
        strict=True,
    )


@pytest.fixture
def legacy_schema() -> DataFrameSchema:
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "legacy_value": Column(str, nullable=False),
        },
        strict=True,
    )


def _build_runtime_services() -> GoldWriterRuntimeServices:
    return build_gold_writer_runtime_services(
        csv_exporter=None,
        tracing=None,
        metrics=None,
        audit=None,
        metadata_writer=None,
        metadata_coordinator=None,
        lineage_store=None,
        contract_rollout_policy=ContractRolloutPolicy(
            contract_ref="chembl.activity",
            active_version="2.0.0",
            mode="dual_write",
            read_order=("2.0.0", "1.0.0"),
            write_versions=("1.0.0", "2.0.0"),
        ),
    )


def _versioned_table_path(base_path: Path, table_name: str) -> Path:
    provider, entity = table_name.split(".", 1)
    return base_path / provider / entity


def _load_delta_rows(table_path: Path) -> list[dict[str, object]]:
    # Use the shared helper: native ``to_pyarrow_table()`` can hang on Windows.
    table = load_delta_table(str(table_path))
    return cast(list[dict[str, object]], read_delta_records(table))


def _load_gold_rows(base_path: Path, table_name: str) -> list[dict[str, object]]:
    return _load_delta_rows(_versioned_table_path(base_path, table_name))


@pytest.mark.integration
@pytest.mark.asyncio
# Cold deltalake/pyarrow bring-up on Windows regularly exceeds 2 minutes for
# dual-write of two versioned tables; keep a generous bound for local GDrive hosts.
@pytest.mark.timeout(300)
async def test_gold_writer_dual_write_projects_version_specific_schema(
    tmp_path: Path,
    noop_logger: object,
    strict_schema: DataFrameSchema,
    legacy_schema: DataFrameSchema,
) -> None:
    writer = GoldWriter(
        base_path=tmp_path / "gold",
        logger=cast(LoggerPort, noop_logger),
        runtime_services=_build_runtime_services(),
    )

    await writer.write_gold(
        table_name="chembl.activity",
        records=[
            {
                "entity_id": "CHEMBL123",
                "legacy_value": "old-shape",
                "value": 5.5,
                "extra": "drop-me",
            }
        ],
        schema=GoldSchemaPolicyByVersion(
            active_version="2.0.0",
            policies=(
                GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
                GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
            ),
        ),
        mode="append",
    )

    v1_rows = _load_gold_rows(tmp_path / "gold", "chembl.activity__v1_0_0")
    v2_rows = _load_gold_rows(tmp_path / "gold", "chembl.activity__v2_0_0")

    assert v1_rows == [{"entity_id": "CHEMBL123", "legacy_value": "old-shape"}]
    assert v2_rows == [{"entity_id": "CHEMBL123", "value": 5.5}]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gold_writer_dual_write_fails_fast_when_shadow_target_errors(
    tmp_path: Path,
    strict_schema: DataFrameSchema,
    legacy_schema: DataFrameSchema,
) -> None:
    logger = MagicMock()
    logger.bind.return_value = logger
    writer = GoldWriter(
        base_path=tmp_path / "gold",
        logger=logger,
        runtime_services=_build_runtime_services(),
    )
    original_dispatch = writer._dispatch_write
    calls: list[str] = []

    async def _dispatch_with_failure(
        context: GoldWriteDispatchContext,
    ) -> None:
        calls.append(context.request.table_name)
        if context.request.table_name.endswith("__v2_0_0"):
            raise RuntimeError("boom")
        await original_dispatch(context)

    writer._dispatch_write = _dispatch_with_failure  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="boom"):
        await writer.write_gold(
            table_name="chembl.activity",
            records=[
                {
                    "entity_id": "CHEMBL123",
                    "legacy_value": "old-shape",
                    "value": 5.5,
                }
            ],
            schema=GoldSchemaPolicyByVersion(
                active_version="2.0.0",
                policies=(
                    GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
                    GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
                ),
            ),
            mode="append",
        )

    assert calls == ["chembl.activity__v1_0_0", "chembl.activity__v2_0_0"]
    assert _versioned_table_path(
        tmp_path / "gold",
        "chembl.activity__v1_0_0",
    ).exists()
    assert not _versioned_table_path(
        tmp_path / "gold",
        "chembl.activity__v2_0_0",
    ).exists()
    logger.error.assert_called_once_with(
        "gold_dual_write_failed",
        logical_table="chembl.activity",
        failed_contract_version="2.0.0",
        failed_target_table="chembl.activity__v2_0_0",
        active_contract_version="2.0.0",
        write_versions=("1.0.0", "2.0.0"),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gold_writer_dual_write_validation_failure_carries_contract_version(
    tmp_path: Path,
    noop_logger: object,
    strict_schema: DataFrameSchema,
    legacy_schema: DataFrameSchema,
) -> None:
    writer = GoldWriter(
        base_path=tmp_path / "gold",
        logger=cast(LoggerPort, noop_logger),
        runtime_services=_build_runtime_services(),
    )

    with pytest.raises(GoldContractValidationError) as exc_info:
        await writer.write_gold(
            table_name="chembl.activity",
            records=[
                {
                    "entity_id": "CHEMBL123",
                    "legacy_value": "old-shape",
                    "value": "not-a-float",
                }
            ],
            schema=GoldSchemaPolicyByVersion(
                active_version="2.0.0",
                policies=(
                    GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
                    GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
                ),
            ),
            mode="append",
        )

    assert exc_info.value.reject_reason.reason_code == "gold_contract_schema_failure"
    assert exc_info.value.reject_reason.contract_version == "2.0.0"
    assert exc_info.value.reject_reason.rule_id == "gold.contract.schema"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_gold_writer_overwrite_is_idempotent_for_identical_records(
    tmp_path: Path,
    noop_logger: object,
    strict_schema: DataFrameSchema,
) -> None:
    writer = GoldWriter(
        base_path=tmp_path / "gold",
        logger=cast(LoggerPort, noop_logger),
        runtime_services=_build_runtime_services(),
    )
    records = [
        {"entity_id": "CHEMBL123", "value": 5.5},
        {"entity_id": "CHEMBL456", "value": 7.0},
    ]

    await writer.write_gold(
        table_name="chembl.activity",
        records=records,
        schema=strict_schema,
        mode="overwrite",
        run_id=deterministic_run_uuid_from_callsite("test_gold_writer_versioning"),
        ingestion_ts=datetime(2026, 5, 5, 12, 0, 0),
    )
    first_rows = _load_gold_rows(tmp_path / "gold", "chembl.activity")

    await writer.write_gold(
        table_name="chembl.activity",
        records=records,
        schema=strict_schema,
        mode="overwrite",
        run_id=deterministic_run_uuid_from_callsite("test_gold_writer_versioning"),
        ingestion_ts=datetime(2026, 5, 5, 12, 5, 0),
    )
    second_rows = _load_gold_rows(tmp_path / "gold", "chembl.activity")

    assert first_rows == [
        {"entity_id": "CHEMBL123", "value": 5.5},
        {"entity_id": "CHEMBL456", "value": 7.0},
    ]
    assert second_rows == first_rows
