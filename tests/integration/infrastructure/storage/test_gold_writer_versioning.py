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
"""Integration tests for version-aware Gold dual-write behavior."""

from __future__ import annotations
from bioetl.domain.exceptions.gold_write import GoldWriteFailure

from datetime import datetime, UTC
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest
import pyarrow as pa

from pandera.pandas import Column, DataFrameSchema

from bioetl.domain.contracts.gold._chembl_reference_publication_schemas import (
    ChEMBLPublicationGoldSchema,
)
from bioetl.domain.types.gold_contracts import GoldWriteCategory
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
    ScdConfig,
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
    GoldWritePostwriteContext,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


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

    with pytest.raises(GoldWriteFailure) as outcome:
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
        committed_targets=[
            {
                "contract_version": "1.0.0",
                "physical_table": "chembl.activity__v1_0_0",
            }
        ],
        partial_dual_write=True,
        recovery_action="operator_compensate_committed_targets",
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

    with pytest.raises(GoldWriteFailure) as exc_info:
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

    assert (
        exc_info.value.__cause__.reject_reason.reason_code
        == "gold_contract_schema_failure"
    )
    assert exc_info.value.__cause__.reject_reason.contract_version == "2.0.0"
    assert exc_info.value.__cause__.reject_reason.rule_id == "gold.contract.schema"


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
    table_path = _versioned_table_path(tmp_path / "gold", "chembl.activity")
    physical = load_delta_table(str(table_path)).schema().to_pyarrow()
    expected = {"entity_id": pa.string(), "value": pa.float64()}
    assert {field.name: field.type for field in physical} == expected
    assert all(field.nullable for field in physical)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gold_writer_dual_write_postwrite_failure_preserves_committed_target(
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
    original_post_write = writer._post_write_gold
    calls: list[str] = []

    async def _post_write_with_failure(
        context: GoldWritePostwriteContext,
    ) -> None:
        calls.append(context.prepared.table_name)
        if context.prepared.table_name.endswith("__v1_0_0"):
            raise RuntimeError("postwrite boom")
        await original_post_write(context)

    writer._post_write_gold = _post_write_with_failure  # type: ignore[method-assign]

    with pytest.raises(GoldWriteFailure) as caught:
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

    assert (
        caught.value.receipt.category == GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
    )
    assert caught.value.receipt.committed_targets == ("chembl.activity__v1_0_0",)
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert str(caught.value.__cause__) == "postwrite boom"
    assert calls == ["chembl.activity__v1_0_0"]
    assert _load_gold_rows(tmp_path / "gold", "chembl.activity__v1_0_0") == [
        {"entity_id": "CHEMBL123", "legacy_value": "old-shape"}
    ]
    assert not _versioned_table_path(
        tmp_path / "gold",
        "chembl.activity__v2_0_0",
    ).exists()
    logger.error.assert_called_once_with(
        "gold_dual_write_failed",
        logical_table="chembl.activity",
        failed_contract_version="1.0.0",
        failed_target_table="chembl.activity__v1_0_0",
        committed_targets=[
            {
                "contract_version": "1.0.0",
                "physical_table": "chembl.activity__v1_0_0",
            }
        ],
        partial_dual_write=True,
        recovery_action="operator_compensate_committed_targets",
        active_contract_version="2.0.0",
        write_versions=("1.0.0", "2.0.0"),
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_issue_12475_gold_scd2_repeat_write_keeps_history_and_current_row(
    tmp_path: Path,
) -> None:
    """Repeated SCD2 writes close old rows and insert only changed versions."""
    schema = ChEMBLPublicationGoldSchema.to_schema()

    def publication_record(
        *,
        title: str,
        content_hash: str,
        entity_id: str = "CHEMBL123",
    ) -> dict[str, object]:
        record = dict.fromkeys(schema.columns)
        record.update(
            {
                "_dq_warn": False,
                "_dq_error": False,
                "_index": 0,
                "entity_id": entity_id,
                "content_hash": content_hash * 64,
                "publication_id": entity_id,
                "title": title,
                "publication_year": 2025.0,
                "citations_received": 4.0,
                "citations_made": 2.0,
                "src_id": 123.0,
                "_lookup_method": "direct",
            }
        )
        return record

    writer = GoldWriter(
        base_path=tmp_path / "gold",
        logger=NoOpLogger(),
    )
    scd_config = ScdConfig(
        business_key="entity_id",
        valid_from_col="_valid_from",
        valid_to_col="_valid_to",
        current_flag_col="_is_current",
        version_col="_version",
    )
    first_ingestion = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    second_ingestion = datetime(2026, 10, 28, 13, 0, tzinfo=UTC)

    await writer.write_gold(
        table_name="chembl.publication",
        records=[publication_record(title="Title v1", content_hash="a")],
        schema=schema,
        primary_keys=["entity_id"],
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=first_ingestion,
    )
    await writer.write_gold(
        table_name="chembl.publication",
        records=[publication_record(title="Title v2", content_hash="b")],
        schema=schema,
        primary_keys=["entity_id"],
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=second_ingestion,
    )

    rows = _load_gold_rows(tmp_path / "gold", "chembl.publication")
    table_path = tmp_path / "gold" / "chembl" / "publication"
    physical_schema = load_delta_table(str(table_path)).schema().to_pyarrow()
    arrow_types = {
        "str": pa.string(),
        "string[pyarrow]": pa.string(),
        "bool": pa.bool_(),
        "int64": pa.int64(),
        "float64": pa.float64(),
    }
    expected_types = {
        name: arrow_types[str(column.dtype)] for name, column in schema.columns.items()
    }
    expected_types.update(
        {
            "_is_current": pa.bool_(),
            "_valid_from": pa.string(),
            "_valid_to": pa.string(),
            "_version": pa.int64(),
        }
    )
    actual_types = {field.name: field.type for field in physical_schema}
    assert actual_types == expected_types
    actual_nullability = {field.name: field.nullable for field in physical_schema}
    assert all(actual_nullability.values())
    logically_nonnullable = {
        name for name, column in schema.columns.items() if not column.nullable
    } | {"_is_current", "_valid_from", "_version"}
    assert {
        name for name in logically_nonnullable if actual_nullability[name]
    } == logically_nonnullable
    assert len(rows) == 2
    old, current = sorted(rows, key=lambda row: int(row["_version"]))
    assert old["title"] == "Title v1"
    assert old["_is_current"] is False
    assert old["_version"] == 1
    assert old["_valid_from"] == first_ingestion.isoformat()
    assert old["_valid_to"] == second_ingestion.isoformat()
    assert current["title"] == "Title v2"
    assert current["_is_current"] is True
    assert current["_version"] == 2
    assert current["_valid_from"] == second_ingestion.isoformat()
    assert current["_valid_to"] is None

    await writer.write_gold(
        table_name="chembl.publication",
        records=[publication_record(title="Title v2", content_hash="b")],
        schema=schema,
        primary_keys=["entity_id"],
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=datetime(2026, 10, 28, 14, 0, tzinfo=UTC),
    )
    assert _load_gold_rows(tmp_path / "gold", "chembl.publication") == rows

    await writer.write_gold(
        table_name="chembl.publication",
        records=[
            publication_record(
                entity_id="CHEMBL456",
                title="New key",
                content_hash="c",
            )
        ],
        schema=schema,
        primary_keys=["entity_id"],
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=datetime(2026, 10, 28, 15, 0, tzinfo=UTC),
    )
    rows_after_new_key = _load_gold_rows(tmp_path / "gold", "chembl.publication")
    new_key = next(row for row in rows_after_new_key if row["entity_id"] == "CHEMBL456")
    assert new_key["_is_current"] is True
    assert new_key["_version"] == 1

    await writer.write_gold(
        table_name="chembl.publication",
        records=[
            publication_record(title="Title v3", content_hash="d"),
            publication_record(
                entity_id="CHEMBL789",
                title="Mixed batch new key",
                content_hash="e",
            ),
        ],
        schema=schema,
        primary_keys=["entity_id"],
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=datetime(2026, 10, 28, 16, 0, tzinfo=UTC),
    )
    final_rows = _load_gold_rows(tmp_path / "gold", "chembl.publication")
    assert len(final_rows) == 5
    current_by_key = {row["entity_id"]: row for row in final_rows if row["_is_current"]}
    assert current_by_key["CHEMBL123"]["_version"] == 3
    assert current_by_key["CHEMBL123"]["title"] == "Title v3"
    assert current_by_key["CHEMBL456"]["_version"] == 1
    assert current_by_key["CHEMBL789"]["_version"] == 1
