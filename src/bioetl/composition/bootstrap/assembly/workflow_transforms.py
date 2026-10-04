"""Assemble generic workflow reconciliation storage and its transform registry.

This workflow bootstrap is separate from validated entity-pipeline factories.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from bioetl.domain.workflow.config import WorkflowStepConfig
from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.infrastructure.storage.delta_reader import DeltaReader

from typing import TYPE_CHECKING, cast

from bioetl.application.workflow.transforms.selected_snapshot_inputs import (
    resolve_cohort_lineage,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    filter_current_rows,
)
from bioetl.infrastructure.storage.workflow_producer_ownership import (
    RUN_COLUMNS,
    filter_owned_entities,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.application.workflow.transforms.builtins import (
    register_builtin_workflow_transforms,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator
from bioetl.infrastructure.quarantine import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import (
    StorageRowReconciliationAdapter,
)
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.control_plane import FileWorkflowTransformArtifactStore


def _workflow_reconciliation_loggers() -> tuple[LoggerPort, LoggerPort]:
    """Return FK and row reconciliation loggers for workflow transforms."""
    root = bootstrap_logger("workflow_reconciliation").bind(
        component="workflow_reconciliation",
    )
    return (
        root.bind(adapter="SilverForeignKeyReconciliationAdapter"),
        root.bind(adapter="StorageRowReconciliationAdapter"),
    )


def build_workflow_transform_registry(
    settings: Settings,
    metrics: MetricsPort,
    artifact_sink: FileWorkflowTransformArtifactStore | None = None,
) -> WorkflowTransformRegistry:
    """Assemble workflow transform storage and builtin transform registry."""
    workflow_storage_logger = create_noop_logger()
    transform_storage = SilverWriter(
        base_path=settings.silver_path,
        logger=workflow_storage_logger,
        runtime_services=build_silver_writer_runtime_services(
            SilverWriterRuntimeServicesRequest(
                csv_exporter=None,
                tracing=NoOpTracing(),
                write_policy=None,
                metrics=metrics,
                audit=NoOpAudit(),
                logger=workflow_storage_logger,
                silver_validator=NoOpValidator(),
                metadata_writer=NoOpMetadataWriter(),
                metadata_coordinator=None,
                lineage_store=None,
                dq_calculator=None,
                merge_resilience_policy=None,
                base_path=settings.silver_path,
                pipeline_name="workflow_transforms",
            )
        ),
        pipeline_name="workflow_transforms",
    )
    transform_gold_storage = GoldWriter(
        base_path=settings.gold_path,
        logger=create_noop_logger(),
        runtime_services=GoldWriterRuntimeServices(
            csv_exporter=None,
            tracing=NoOpTracing(),
            metrics=metrics,
            audit=NoOpAudit(),
            metadata_writer=NoOpMetadataWriter(),
            metadata_coordinator=None,
            lineage_store=None,
        ),
    )
    foreign_key_reconciliation_logger, row_reconciliation_logger = (
        _workflow_reconciliation_loggers()
    )
    reconciliation_quarantine = UnifiedQuarantineAdapter(
        base_path=str(settings.quarantine_path),
    )
    return register_builtin_workflow_transforms(
        WorkflowTransformRegistry(),
        foreign_key_reconciliation_port=SilverForeignKeyReconciliationAdapter(
            silver_writer=transform_storage,
            logger=foreign_key_reconciliation_logger,
            clock=SystemClock(),
            metrics=metrics,
            quarantine=reconciliation_quarantine,
            quarantine_pipeline_name="workflow_transforms",
            gold_writer=transform_gold_storage,
            artifact_sink=artifact_sink,
        ),
        row_reconciliation_port=StorageRowReconciliationAdapter(
            silver_reader=transform_storage,
            gold_reader=transform_gold_storage,
            logger=row_reconciliation_logger,
            metrics=metrics,
        ),
    )


class WorkflowCohortResolver:
    """Read actual selected keys; a missing or oversized cohort fails closed."""

    def __init__(self, reader: DeltaReader) -> None:
        self.reader = reader

    async def __call__(
        self, step: WorkflowStepConfig, upstream: Mapping[str, object]
    ) -> WorkflowStepConfig:
        cohort = step.reference_cohort
        if cohort is None:
            return step
        source = upstream.get(cohort.step_id)
        if not isinstance(source, RunResult) or not source.is_success:
            raise ValueError("reference_cohort requires a successful source run")
        if source.pipeline_name != cohort.table.replace(".", "_", 1):
            raise ValueError("reference_cohort source identity mismatch")
        entry, expected_count = resolve_cohort_lineage(
            source, upstream, f"gold:{cohort.table}"
        )
        if (
            not isinstance(entry, Mapping)
            or type(entry.get("version")) is not int
            or cast(int, entry.get("version")) < 0
            or not isinstance(entry.get("table_id"), str)
            or not entry.get("table_id")
            or entry.get("run_ids") != [source.run_id]
            or entry.get("producer_pipeline") != source.pipeline_name
        ):
            raise ValueError("reference_cohort producer snapshot identity mismatch")
        try:
            table = await self.reader.read_table(
                cohort.table.replace(".", "/", 1),
                snapshot_version=cast(int, entry["version"]),
                snapshot_table_id=cast(str, entry["table_id"]),
            )
        except (OSError, KeyError) as error:
            raise ValueError("reference_cohort source snapshot unavailable") from error
        current = filter_current_rows(
            table.to_pylist(), current_only=True, layer="gold"
        )
        run_column = next(
            (name for name in RUN_COLUMNS if name in table.column_names), None
        )
        if run_column is not None:
            rows = [row for row in current if str(row[run_column]) == source.run_id]
        else:
            rows = filter_owned_entities(current, entry)
        if len(rows) != expected_count:
            raise ValueError("reference_cohort source count or run identity mismatch")
        keys = tuple(
            sorted(
                {
                    str(row[cohort.column])
                    for row in rows
                    if row[cohort.column] is not None
                }
            )
        )
        if not keys:
            raise ValueError("reference_cohort contains no reference keys")
        if step.run_options.limit is not None and len(keys) > step.run_options.limit:
            raise ValueError("reference_cohort exceeds the requested record limit")
        resolved_step = replace(
            step,
            run_options=replace(
                step.run_options,
                filter_ids=keys,
                filter_field=cohort.filter_field,
                input_csv=None,
                multi_filter_ids=None,
                ignore_yaml_filter=True,
            ),
        )
        if not isinstance(resolved_step, WorkflowStepConfig):
            raise TypeError("Cohort resolution must preserve WorkflowStepConfig")
        return resolved_step
