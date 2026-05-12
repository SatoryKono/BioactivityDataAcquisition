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


@pytest.mark.asyncio
async def test_reconcile_foreign_keys_is_idempotent(
    tmp_path,
    noop_logger,
) -> None:
    silver_writer = SilverWriter(base_path=tmp_path / "silver", logger=noop_logger)
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
            silver_writer=silver_writer
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
