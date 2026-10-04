"""Bind workflow reference filters to the successful upstream Gold run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.composition.workflow_cohort_lineage import resolve_cohort_lineage
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    filter_current_rows,
)
from bioetl.infrastructure.storage.workflow_producer_ownership import (
    RUN_COLUMNS,
    filter_owned_entities,
)

if TYPE_CHECKING:
    from bioetl.domain.workflow.config import WorkflowStepConfig
    from bioetl.infrastructure.storage.delta_reader import DeltaReader
    from bioetl.infrastructure.storage.workflow_cohort_snapshot import (
        WorkflowCohortSnapshotReader,
    )


class WorkflowCohortResolver:
    """Read actual selected keys; a missing or oversized cohort fails closed."""

    def __init__(
        self,
        reader: DeltaReader,
        source_reader: WorkflowCohortSnapshotReader | None = None,
    ) -> None:
        self.reader = reader
        self.source_reader = source_reader

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
        snapshots = source.selected_snapshots
        entry: Mapping[str, object] | None = (
            None if snapshots is None else snapshots.get(f"gold:{cohort.table}")
        )
        expected_count = source.records_gold
        if entry is not None:
            entry, expected_count = resolve_cohort_lineage(
                source, upstream, f"gold:{cohort.table}"
            )
        if entry is not None and (
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
            if entry is None:
                if self.source_reader is None:
                    raise ValueError(
                        "reference_cohort producer snapshot identity mismatch"
                    )
                identities = await self.source_reader.read_run_identities(
                    cohort.table,
                    source.pipeline_name,
                    source.run_id,
                    source.records_silver,
                )
                if not identities:
                    raise ValueError(
                        "reference_cohort source run has no Silver identities"
                    )
                table = await self.reader.read_table(
                    cohort.table.replace(".", "/", 1),
                    columns=[cohort.column, "entity_id", "content_hash", "_is_current"],
                )
            else:
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
        if entry is None:
            rows = [
                row
                for row in current
                if identities.get(str(row["entity_id"])) == str(row["content_hash"])
            ]
        elif run_column is not None:
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
        return replace(
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
