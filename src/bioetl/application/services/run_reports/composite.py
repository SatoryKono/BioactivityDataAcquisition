"""Persist composite terminal evidence without borrowing a child's identity."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    record_run_observation,
    reset_run_observations,
    run_observations,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.ports import ClockPort, LoggerPort, RunReportStorePort
from bioetl.domain.run_reports.models import (
    LayerCounts,
    PipelineRunReport,
    TrackingCoverage,
)
from bioetl.domain.run_reports.reason_catalog import default_reason_catalog

_children: ContextVar[list[RunResult] | None] = ContextVar(
    "composite_report_children", default=None
)


def record_composite_child(result: RunResult) -> None:
    """Attach a completed child to the currently executing composite only."""
    children = _children.get()
    if children is not None:
        children.append(result)


@dataclass(frozen=True)
class CompositeRunReportService:
    """Write real merge counts, terminal errors and exact child report references."""

    pipeline_name: str
    manifest_id: str | None
    store: RunReportStorePort
    root: Path | None
    clock: ClockPort
    logger: LoggerPort
    capture: Callable[[str, str, datetime], None]
    archive: Callable[[RunResult], None] | None = None

    def write(
        self,
        *,
        run_id: str,
        started_at: datetime,
        result: CompositeResult | None,
        error: BaseException | None,
        children: list[RunResult],
    ) -> None:
        completed_at = self.clock.now()
        status = (
            "success"
            if result is not None and result.is_success and error is None
            else "failed"
        )
        if isinstance(error, (asyncio.CancelledError, PipelineShutdownError)):
            status = "shutdown"
        try:
            self.capture(self.pipeline_name, run_id, completed_at)
        except (OSError, RuntimeError, ValueError, TypeError):
            record_run_observation(
                "Control Plane",
                verdict="INCOMPLETE",
                reason="completion_assessment_failed",
                facts={},
            )
        self._record_child_provider_evidence(children)
        if result is not None and (
            result.had_warnings or any(not child.is_success for child in children)
        ):
            record_run_observation(
                "Data Quality",
                verdict="WARN",
                reason="composite_partial_stage_execution",
                facts={
                    "failed_children": [
                        child.run_id for child in children if not child.is_success
                    ]
                },
            )
        merge = result.merge_result if result is not None else None
        # These are the parent's actual merge writes. Child extraction layers are
        # referenced separately and must not be counted again as parent Bronze.
        layers = LayerCounts(
            silver_valid=merge.records_merged
            if merge and merge.output_silver_path
            else 0,
            gold_written=merge.records_merged
            if merge and merge.output_gold_path
            else 0,
        )
        report = PipelineRunReport(
            identity={
                "pipeline_name": self.pipeline_name,
                "run_id": run_id,
                "manifest_id": self.manifest_id,
                "provider": "composite",
                "entity": "merged",
                "run_type": "composite",
                "status": status,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
            },
            funnel=(),
            layers=layers,
            reasons_top_n=(),
            reconciliation={
                "scope": "composite_merge",
                "seed_records": merge.records_from_seed if merge else None,
                "merged_records": merge.records_merged if merge else None,
            },
            tracking_coverage=TrackingCoverage.PARTIAL,
            reason_catalog_version=default_reason_catalog().version,
            artifacts=tuple(
                {
                    "kind": "composite_child_run_report",
                    "ref": child.run_report_json_path,
                    "run_id": child.run_id,
                    "pipeline_name": child.pipeline_name,
                    "manifest_id": child.manifest_id,
                }
                for child in children
                if child.run_report_json_path
            ),
            failure={"error_type": type(error).__name__, "error_message": str(error)}
            if error
            else None,
            io={
                "execution_context": "composite",
                "child_runs": [
                    {
                        "pipeline_name": c.pipeline_name,
                        "run_id": c.run_id,
                        "status": c.status.value,
                        "report_ref": c.run_report_json_path,
                    }
                    for c in children
                ],
            },
            observations=run_observations(),
        )
        paths = write_pipeline_run_report(report, root=self.root, store=self.store)
        if status == "success" and self.archive is not None:
            self.archive(
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name=self.pipeline_name,
                    run_id=run_id,
                    run_type="composite",
                    manifest_id=self.manifest_id,
                    started_at=started_at,
                    completed_at=completed_at,
                    records_silver=layers.silver_valid,
                    records_gold=layers.gold_written,
                    run_report_json_path=str(paths.json_path),
                    run_report_markdown_path=str(paths.markdown_path),
                )
            )

    def _record_child_provider_evidence(self, children: list[RunResult]) -> None:
        verdicts: list[str] = []
        for child in children:
            try:
                if not child.run_report_json_path:
                    raise ValueError("child_report_missing")
                report = json.loads(self.store.read_text(child.run_report_json_path))
                if report["identity"]["run_id"] != child.run_id:
                    raise ValueError("child_report_identity_mismatch")
                verdicts.append(
                    str(
                        report.get("observations", {})
                        .get("Provider", {})
                        .get("verdict", "INCOMPLETE")
                    )
                )
            except (OSError, ValueError, KeyError, TypeError):
                verdicts.append("INCOMPLETE")
        allowed = {"ERROR", "INCOMPLETE", "UNKNOWN", "WARN", "OK", "N/A"}
        verdicts = [value if value in allowed else "INCOMPLETE" for value in verdicts]
        verdict = next(
            (
                v
                for v in ("ERROR", "INCOMPLETE", "UNKNOWN", "WARN", "OK", "N/A")
                if v in verdicts
            ),
            "INCOMPLETE",
        )
        record_run_observation(
            "Provider",
            verdict=verdict,
            reason="composite_child_provider_evidence",
            facts={"child_count": len(children), "verdicts": verdicts},
        )

    async def execute(
        self, run_id: str, body: Callable[[], Awaitable[CompositeResult]]
    ) -> CompositeResult:
        """Isolate the parent scope and retain reports on failure or cancellation."""
        observations_token = bind_run_observations()
        children: list[RunResult] = []
        children_token = _children.set(children)
        started_at = self.clock.now()
        result = None
        error = None
        try:
            result = await body()
            return result
        except BaseException as exc:
            error = exc
            raise
        finally:
            try:
                self.write(
                    run_id=run_id,
                    started_at=started_at,
                    result=result,
                    error=error,
                    children=children,
                )
            except Exception as report_error:
                if error is None:
                    raise
                self.logger.error(
                    "composite_report_write_failed", error=str(report_error)
                )
            finally:
                _children.reset(children_token)
                reset_run_observations(observations_token)
