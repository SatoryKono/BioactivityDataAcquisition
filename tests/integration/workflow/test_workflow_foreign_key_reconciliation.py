"""Integration tests for workflow foreign-key reconciliation transforms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pyarrow as pa
import pytest
from pandera.pandas import Column, DataFrameSchema

from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.builtins import (
    register_builtin_workflow_transforms,
)
from bioetl.domain.workflow import TransformStepConfig
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)

pytestmark = pytest.mark.integration


@dataclass
class _RecordingMetrics:
    counters: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)
    histograms: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.counters.append((name, value, labels or {}))

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.histograms.append((name, value, labels or {}))

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        del name, value, labels

    def close(self) -> None:
        return None


@dataclass
class _RecordingLogger:
    events: list[tuple[str, str, dict[str, object]]] = field(default_factory=list)

    def bind(self, **kwargs: object) -> _RecordingLogger:
        return self

    def info(self, event: str, **kwargs: object) -> None:
        self.events.append(("info", event, dict(kwargs)))

    def warning(self, event: str, **kwargs: object) -> None:
        self.events.append(("warning", event, dict(kwargs)))

    def error(self, event: str, **kwargs: object) -> None:
        self.events.append(("error", event, dict(kwargs)))

    def debug(self, event: str, **kwargs: object) -> None:
        self.events.append(("debug", event, dict(kwargs)))

    def exception(self, event: str, **kwargs: object) -> None:
        self.events.append(("exception", event, dict(kwargs)))


@dataclass
class _RecordingQuarantine:
    writes: list[dict[str, object]] = field(default_factory=list)

    async def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, object],
        bronze_batch_id: object,
        run_id: object | None = None,
        entry_id: str | None = None,
        metadata: dict[str, object] | None = None,
        *,
        ingestion_ts: object,
    ) -> None:
        del run_id, entry_id, metadata, ingestion_ts
        self.writes.append(
            {
                "pipeline": pipeline,
                "error_code": error_code,
                "payload": payload,
                "bronze_batch_id": bronze_batch_id,
            }
        )

    async def write_many(
        self,
        records: list[dict[str, object]],
    ) -> None:
        for record in records:
            await self.write(
                pipeline=record["pipeline"],
                error_code=record["error_code"],
                payload=record["payload"],
                bronze_batch_id=record["bronze_batch_id"],
                run_id=record.get("run_id"),
                entry_id=record.get("entry_id"),
                metadata=record.get("metadata"),
                ingestion_ts=record["ingestion_ts"],
            )


def _gold_schema(columns: list[str]) -> DataFrameSchema:
    return DataFrameSchema(
        {column: Column(str, nullable=True) for column in columns},
        strict=True,
    )


def _gold_writer(tmp_path, logger, metrics) -> GoldWriter:
    return GoldWriter(
        base_path=tmp_path / "gold",
        logger=logger,
        runtime_services=build_gold_writer_runtime_services(
            csv_exporter=None,
            tracing=None,
            metrics=metrics,
            audit=None,
            metadata_writer=None,
            metadata_coordinator=None,
            lineage_store=None,
        ),
    )


def _scd_config(primary_key: str) -> dict[str, object]:
    return {
        "business_key": primary_key,
        "valid_from_col": "_valid_from",
        "valid_to_col": "_valid_to",
        "current_flag_col": "_is_current",
        "version_col": "_version",
    }


@pytest.mark.asyncio
async def test_reconcile_foreign_keys_is_idempotent(
    tmp_path,
) -> None:
    logger = _RecordingLogger()
    silver_writer = SilverWriter(base_path=tmp_path / "silver", logger=logger)
    reference_schema = pa.schema(
        [
            ("target_id", pa.string()),
            ("target_name", pa.string()),
        ]
    )
    source_schema = pa.schema(
        [
            ("assay_id", pa.string()),
            ("target_id", pa.string()),
            ("assay_name", pa.string()),
        ]
    )
    await silver_writer.write_silver(
        table_name="chembl_target",
        records=[
            {"target_id": "CHEMBL_T1", "target_name": "target-1"},
        ],
        primary_keys=["target_id"],
        schema=reference_schema,
        mode="merge",
    )
    await silver_writer.write_silver(
        table_name="chembl_assay",
        records=[
            {
                "assay_id": "CHEMBL_A1",
                "target_id": "CHEMBL_T1",
                "assay_name": "keep",
            },
            {
                "assay_id": "CHEMBL_A2",
                "target_id": "CHEMBL_T999",
                "assay_name": "orphan",
            },
        ],
        primary_keys=["assay_id"],
        schema=source_schema,
        mode="merge",
    )

    metrics = _RecordingMetrics()
    registry = register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=silver_writer,
            logger=logger,
            metrics=metrics,
        ),
    )
    service = WorkflowTransformService(registry=registry, metrics=metrics)
    step = TransformStepConfig(
        step_id="reconcile_assay_target_orphans",
        transform_name="reconcile_foreign_keys",
        config={
            "source_table": "chembl_assay",
            "reference_table": "chembl_target",
            "source_key": "target_id",
            "reference_key": "target_id",
            "primary_keys": ["assay_id"],
            "action": "delete_orphans",
        },
    )

    first = await service.run_step(
        workflow_name="chembl_core",
        step=step,
    )
    after_first = await silver_writer.read_silver("chembl_assay")
    second = await service.run_step(
        workflow_name="chembl_core",
        step=step,
    )
    after_second = await silver_writer.read_silver("chembl_assay")

    assert first.status == "success"
    assert isinstance(first.output, dict)
    assert first.output["orphan_rows_deleted"] == 1
    assert len(after_first) == 1
    assert after_first[0]["assay_id"] == "CHEMBL_A1"
    assert second.status == "success"
    assert isinstance(second.output, dict)
    assert second.output["orphan_rows_deleted"] == 0
    assert second.output["mutated"] is False
    assert after_second == after_first
    assert any(
        event == "workflow foreign-key reconciliation completed with mutation"
        for _level, event, _kwargs in logger.events
    )


@pytest.mark.asyncio
async def test_reconcile_foreign_keys_sends_orphans_to_quarantine(
    tmp_path,
) -> None:
    logger = _RecordingLogger()
    silver_writer = SilverWriter(base_path=tmp_path / "silver", logger=logger)
    quarantine = _RecordingQuarantine()
    reference_schema = pa.schema(
        [
            ("target_id", pa.string()),
            ("target_name", pa.string()),
        ]
    )
    source_schema = pa.schema(
        [
            ("assay_id", pa.string()),
            ("target_id", pa.string()),
            ("assay_name", pa.string()),
        ]
    )
    await silver_writer.write_silver(
        table_name="chembl_target",
        records=[{"target_id": "CHEMBL_T1", "target_name": "target-1"}],
        primary_keys=["target_id"],
        schema=reference_schema,
        mode="merge",
    )
    await silver_writer.write_silver(
        table_name="chembl_assay",
        records=[
            {
                "assay_id": "CHEMBL_A1",
                "target_id": "CHEMBL_T1",
                "assay_name": "keep",
            },
            {
                "assay_id": "CHEMBL_A2",
                "target_id": "CHEMBL_T999",
                "assay_name": "orphan",
            },
        ],
        primary_keys=["assay_id"],
        schema=source_schema,
        mode="merge",
    )

    metrics = _RecordingMetrics()
    registry = register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=silver_writer,
            logger=logger,
            metrics=metrics,
            quarantine=quarantine,
            quarantine_pipeline_name="workflow_transforms",
        ),
    )
    service = WorkflowTransformService(registry=registry, metrics=metrics)
    step = TransformStepConfig(
        step_id="reconcile_assay_target_orphans",
        transform_name="reconcile_foreign_keys",
        config={
            "source_table": "chembl_assay",
            "reference_table": "chembl_target",
            "source_key": "target_id",
            "reference_key": "target_id",
            "primary_keys": ["assay_id"],
            "action": "delete_orphans",
        },
    )

    result = await service.run_step(
        workflow_name="chembl_baseline",
        step=step,
    )
    after_first = await silver_writer.read_silver("chembl_assay")

    assert result.status == "success"
    assert result.output is not None
    assert result.output["orphan_rows_deleted"] == 1
    assert len(after_first) == 1
    assert after_first[0]["assay_id"] == "CHEMBL_A1"
    assert len(quarantine.writes) == 1
    assert quarantine.writes[0]["pipeline"] == "chembl_baseline"
    assert quarantine.writes[0]["error_code"] == "FILTERED_OUT_SILVER"
    assert quarantine.writes[0]["payload"]["assay_id"] == "CHEMBL_A2"


@pytest.mark.asyncio
async def test_reconcile_foreign_keys_supports_composite_keys_and_null_policy(
    tmp_path,
) -> None:
    logger = _RecordingLogger()
    silver_writer = SilverWriter(base_path=tmp_path / "silver", logger=logger)
    reference_schema = pa.schema(
        [
            ("target_record_id", pa.string()),
            ("target_id", pa.string()),
            ("target_type", pa.string()),
        ]
    )
    source_schema = pa.schema(
        [
            ("assay_id", pa.string()),
            ("target_id", pa.string()),
            ("target_type", pa.string()),
        ]
    )
    await silver_writer.write_silver(
        table_name="chembl_target",
        records=[
            {
                "target_record_id": "CHEMBL_T1",
                "target_id": "CHEMBL_T1",
                "target_type": "protein",
            },
            {
                "target_record_id": "CHEMBL_T_NULL",
                "target_id": None,
                "target_type": None,
            },
        ],
        primary_keys=["target_record_id"],
        schema=reference_schema,
        mode="merge",
    )
    await silver_writer.write_silver(
        table_name="chembl_assay",
        records=[
            {
                "assay_id": "CHEMBL_A1",
                "target_id": "CHEMBL_T1",
                "target_type": "protein",
            },
            {
                "assay_id": "CHEMBL_A2",
                "target_id": "CHEMBL_T999",
                "target_type": "protein",
            },
            {
                "assay_id": "CHEMBL_A3",
                "target_id": None,
                "target_type": None,
            },
        ],
        primary_keys=["assay_id"],
        schema=source_schema,
        mode="merge",
    )

    metrics = _RecordingMetrics()
    logger = _RecordingLogger()
    registry = register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=silver_writer,
            logger=logger,
            metrics=metrics,
        ),
    )
    service = WorkflowTransformService(registry=registry, metrics=metrics)
    step = TransformStepConfig(
        step_id="reconcile_assay_target_orphans",
        transform_name="reconcile_foreign_keys",
        config={
            "source_table": "chembl_assay",
            "reference_table": "chembl_target",
            "source_keys": ["target_id", "target_type"],
            "reference_keys": ["target_id", "target_type"],
            "primary_keys": ["assay_id"],
            "action": "delete_orphans",
            "nulls_equal": True,
        },
    )

    result = await service.run_step(
        workflow_name="chembl_core",
        step=step,
    )
    after_first = await silver_writer.read_silver("chembl_assay")

    assert result.status == "success"
    assert isinstance(result.output, dict)
    assert result.output["source_keys"] == ["target_id", "target_type"]
    assert result.output["reference_keys"] == ["target_id", "target_type"]
    assert result.output["nulls_equal"] is True
    assert result.output["orphan_rows_deleted"] == 1
    assert len(after_first) == 2
    assert {row["assay_id"] for row in after_first} == {
        "CHEMBL_A1",
        "CHEMBL_A3",
    }
    assert (
        "bioetl_workflow_reconciliation_rows_scanned_total",
        3,
        {},
    ) in metrics.counters
    assert (
        "bioetl_workflow_reconciliation_rows_retained_total",
        2,
        {},
    ) in metrics.counters
    assert (
        "bioetl_workflow_reconciliation_rows_deleted_total",
        1,
        {},
    ) in metrics.counters


@pytest.mark.asyncio
async def test_reconcile_foreign_keys_dry_run_previews_without_mutation(
    tmp_path,
) -> None:
    logger = _RecordingLogger()
    silver_writer = SilverWriter(base_path=tmp_path / "silver", logger=logger)
    reference_schema = pa.schema(
        [
            ("target_id", pa.string()),
            ("target_name", pa.string()),
        ]
    )
    source_schema = pa.schema(
        [
            ("assay_id", pa.string()),
            ("target_id", pa.string()),
            ("assay_name", pa.string()),
        ]
    )
    await silver_writer.write_silver(
        table_name="chembl_target",
        records=[
            {"target_id": "CHEMBL_T1", "target_name": "target-1"},
        ],
        primary_keys=["target_id"],
        schema=reference_schema,
        mode="merge",
    )
    await silver_writer.write_silver(
        table_name="chembl_assay",
        records=[
            {
                "assay_id": "CHEMBL_A1",
                "target_id": "CHEMBL_T1",
                "assay_name": "keep",
            },
            {
                "assay_id": "CHEMBL_A2",
                "target_id": "CHEMBL_T999",
                "assay_name": "orphan",
            },
        ],
        primary_keys=["assay_id"],
        schema=source_schema,
        mode="merge",
    )

    metrics = _RecordingMetrics()
    registry = register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=silver_writer,
            logger=logger,
            metrics=metrics,
        ),
    )
    service = WorkflowTransformService(registry=registry, metrics=metrics)
    step = TransformStepConfig(
        step_id="reconcile_assay_target_orphans",
        transform_name="reconcile_foreign_keys",
        config={
            "source_table": "chembl_assay",
            "reference_table": "chembl_target",
            "source_key": "target_id",
            "reference_key": "target_id",
            "primary_keys": ["assay_id"],
            "action": "delete_orphans",
        },
    )

    result = await service.run_step(
        workflow_name="chembl_core",
        step=step,
        dry_run=True,
    )
    after_preview = await silver_writer.read_silver("chembl_assay")

    assert result.status == "success"
    assert isinstance(result.output, dict)
    assert result.output["dry_run"] is True
    assert result.output["would_mutate"] is True
    assert result.output["mutated"] is False
    assert result.output["mutation_blocked_reason"] == "workflow_dry_run"
    assert {row["assay_id"] for row in after_preview} == {"CHEMBL_A1", "CHEMBL_A2"}
    assert any(
        event == "workflow foreign-key reconciliation dry-run blocked mutation"
        for _level, event, _kwargs in logger.events
    )


@pytest.mark.asyncio
async def test_reconcile_foreign_keys_expires_gold_orphans_without_dropping_history(
    tmp_path,
) -> None:
    logger = _RecordingLogger()
    metrics = _RecordingMetrics()
    silver_writer = SilverWriter(base_path=tmp_path / "silver", logger=logger)
    gold_writer = _gold_writer(tmp_path, logger, metrics)
    quarantine = _RecordingQuarantine()
    ingestion_ts = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)

    await gold_writer.write_gold(
        table_name="chembl.target",
        records=[{"target_id": "CHEMBL_T1", "target_name": "target-1"}],
        schema=_gold_schema(["target_id", "target_name"]),
        primary_keys=["target_id"],
        mode="scd2",
        scd_config=_scd_config("target_id"),
        ingestion_ts=ingestion_ts,
    )
    await gold_writer.write_gold(
        table_name="chembl.assay",
        records=[
            {
                "assay_id": "CHEMBL_A1",
                "target_id": "CHEMBL_T1",
                "assay_name": "keep",
            },
            {
                "assay_id": "CHEMBL_A2",
                "target_id": "CHEMBL_T999",
                "assay_name": "orphan",
            },
        ],
        schema=_gold_schema(["assay_id", "target_id", "assay_name"]),
        primary_keys=["assay_id"],
        mode="scd2",
        scd_config=_scd_config("assay_id"),
        ingestion_ts=ingestion_ts,
    )

    registry = register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=silver_writer,
            gold_writer=gold_writer,
            logger=logger,
            metrics=metrics,
            quarantine=quarantine,
            quarantine_pipeline_name="workflow_transforms",
        ),
    )
    service = WorkflowTransformService(registry=registry, metrics=metrics)
    step = TransformStepConfig(
        step_id="reconcile_assay_target_orphans",
        transform_name="reconcile_foreign_keys",
        config={
            "source_layer": "gold",
            "reference_layer": "gold",
            "mutation_layer": "gold",
            "source_table": "chembl.assay",
            "reference_table": "chembl.target",
            "source_key": "target_id",
            "reference_key": "target_id",
            "primary_keys": ["assay_id"],
            "action": "delete_orphans",
        },
    )

    result = await service.run_step(
        workflow_name="chembl_baseline",
        step=step,
    )

    current_rows = await gold_writer.read_gold("chembl.assay", current_only=True)
    all_rows = await gold_writer.read_gold("chembl.assay", current_only=False)
    expired = [row for row in all_rows if row["assay_id"] == "CHEMBL_A2"]

    assert result.status == "success"
    assert result.output is not None
    assert result.output["source_layer"] == "gold"
    assert result.output["mutation_layer"] == "gold"
    assert result.output["orphan_rows_deleted"] == 1
    assert {row["assay_id"] for row in current_rows} == {"CHEMBL_A1"}
    assert len(expired) == 1
    assert expired[0]["_is_current"] is False
    assert expired[0]["_valid_to"] is not None
    assert len(quarantine.writes) == 1
    assert quarantine.writes[0]["error_code"] == "FILTERED_OUT_GOLD"
