"""Bind workflow reference filters to the successful upstream Gold run."""

from collections.abc import Mapping
from dataclasses import replace

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.domain.workflow.config import WorkflowStepConfig
from bioetl.infrastructure.storage.delta_reader import DeltaReader


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
        try:
            table = await self.reader.read_table(
                cohort.table.replace(".", "/", 1),
                columns=[cohort.column, "_run_id"],
            )
        except (OSError, KeyError) as error:
            raise ValueError("reference_cohort source snapshot unavailable") from error
        rows = [
            row for row in table.to_pylist() if str(row["_run_id"]) == source.run_id
        ]
        if len(rows) != source.records_gold:
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
