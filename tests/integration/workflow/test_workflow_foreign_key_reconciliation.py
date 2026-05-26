"""Integration tests for workflow foreign-key reconciliation transforms."""

from __future__ import annotations

from dataclasses import dataclass, field

import pyarrow as pa
import pytest

from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.builtins import (
    register_builtin_workflow_transforms,
)
from bioetl.domain.workflow import TransformStepConfig
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
