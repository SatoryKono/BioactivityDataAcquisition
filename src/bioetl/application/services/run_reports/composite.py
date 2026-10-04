"""Persist composite terminal evidence without borrowing a child's identity."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.ops.error_handler import handle_operation_errors
from bioetl.application.services.run_reports.composite_evidence import (
    snapshot_child_reports,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    record_run_observation,
    reset_run_observations,
    run_observations,
)
from bioetl.application.services.run_reports.writer import (
    resolve_pipeline_report_dir,
    write_pipeline_run_report,
)
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.ports import ClockPort, LoggerPort, RunReportStorePort
from bioetl.domain.run_reports.models import (
    LayerCounts,
    PipelineRunReport,
    TrackingCoverage,
)
from bioetl.domain.run_reports.reason_catalog_data import default_reason_catalog
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.composite.result import CompositeResult, MergeResult


_children: ContextVar[list[RunResult] | None] = ContextVar(
    "composite_report_children", default=None
)


def record_composite_child(result: RunResult) -> None:
    """Attach a completed child to the currently executing composite only."""
    children = _children.get()
    if children is not None:
        children.append(result)


def _terminal_status(
    result: CompositeResult | None, error: BaseException | None
) -> str:
    """Distinguish cancellation from successful and failed terminal runs."""
    if isinstance(error, (asyncio.CancelledError, PipelineShutdownError)):
        return "shutdown"
    if result is not None and result.is_success and error is None:
        return "success"
    return "failed"


def _merge_layers(merge: MergeResult | None) -> LayerCounts:
    """Count parent merge writes without counting child extraction layers twice."""
    return LayerCounts(
        silver_valid=merge.records_merged if merge and merge.output_silver_path else 0,
        gold_written=merge.records_merged if merge and merge.output_gold_path else 0,
    )


def _child_run_io(children: list[RunResult]) -> JsonDict:
    """Include every child outcome, even when its report is unavailable."""
    return {
        "execution_context": "composite",
        "child_runs": [
            {
                "pipeline_name": child.pipeline_name,
                "run_id": child.run_id,
                "status": child.status.value,
                "report_ref": child.run_report_json_path,
            }
            for child in children
        ],
    }


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
    bind_replay: Callable[[list[RunResult]], None] | None = None

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
        status = _terminal_status(result, error)
        self._capture_completion(run_id, completed_at, result, children, status)
        self._record_child_evidence(children, "Provider")
        self._record_child_evidence(children, "Data Quality")
        self._record_partial_execution(result, children)
        merge = result.merge_result if result is not None else None
        layers = _merge_layers(merge)
        report = PipelineRunReport(
            identity={
                "pipeline_name": self.pipeline_name,
                "run_id": run_id,
                "manifest_id": self.manifest_id,
                "provider": "composite",
                "entity": "merged",
                "run_type": "composite",
                "status": status,
                "completion_status": (
                    "completed_with_warnings"
                    if status == "success"
                    and result is not None
                    and result.had_warnings
                    else status
                ),
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
            artifacts=self._snapshot_children(run_id, children),
            failure={"error_type": type(error).__name__, "error_message": str(error)}
            if error
            else None,
            io=_child_run_io(children),
            observations=dict(run_observations()),
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

    def _snapshot_children(
        self, run_id: str, children: list[RunResult]
    ) -> tuple[dict[str, object], ...]:
        """Retain the parent failure report even when a child cannot be captured."""
        try:
            return snapshot_child_reports(
                children,
                resolve_pipeline_report_dir(
                    pipeline_name=self.pipeline_name, run_id=run_id, root=self.root
                ),
                self.store,
            )
        except (OSError, ValueError, TypeError) as exc:
            record_run_observation(
                "Control Plane",
                verdict="INCOMPLETE",
                reason="child_report_capture_failed",
                facts={"error": str(exc)},
            )
            return tuple(
                {
                    "kind": "composite_child_run_report",
                    "ref": str(child.run_report_json_path).replace("\\", "/"),
                    "run_id": child.run_id,
                    "pipeline_name": child.pipeline_name,
                    "manifest_id": child.manifest_id,
                }
                for child in children
                if child.run_report_json_path
            )

    def _capture_completion(
        self,
        run_id: str,
        completed_at: datetime,
        result: CompositeResult | None,
        children: list[RunResult],
        status: str,
    ) -> None:
        """Capture replay bindings and completion without hiding the run outcome."""
        try:
            if (
                status == "success"
                and result is not None
                and not result.had_warnings
                and children
                and all(child.is_success for child in children)
                and self.bind_replay is not None
            ):
                self.bind_replay(children)
            self.capture(self.pipeline_name, run_id, completed_at)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            self.logger.warning(
                "composite_completion_assessment_failed", error=str(exc)
            )
            record_run_observation(
                "Control Plane",
                verdict="INCOMPLETE",
                reason="completion_assessment_failed",
                facts={},
            )

    def _record_partial_execution(
        self, result: CompositeResult | None, children: list[RunResult]
    ) -> None:
        """Keep stage warnings and unsuccessful children in parent DQ evidence."""
        if result is not None and (
            result.had_warnings or any(not child.is_success for child in children)
        ):
            child_dq = run_observations().get("Data Quality", {})
            child_verdict = str(child_dq.get("verdict", "WARN"))
            child_facts = child_dq.get("facts", {})
            record_run_observation(
                "Data Quality",
                verdict=child_verdict
                if child_verdict in {"ERROR", "INCOMPLETE", "UNKNOWN"}
                else "WARN",
                reason="composite_partial_stage_execution",
                facts={
                    **(child_facts if isinstance(child_facts, dict) else {}),
                    "failed_children": [
                        child.run_id for child in children if not child.is_success
                    ],
                },
            )

    def _child_verdict(self, child: RunResult, domain: str) -> str:
        """Read one child's domain verdict only from its own identified report."""
        try:
            if not child.run_report_json_path:
                raise ValueError("child_report_missing")
            report = json.loads(self.store.read_text(child.run_report_json_path))
            if report["identity"]["run_id"] != child.run_id:
                raise ValueError("child_report_identity_mismatch")
            return str(
                report.get("observations", {})
                .get(domain, {})
                .get("verdict", "INCOMPLETE")
            )
        except (OSError, ValueError, KeyError, TypeError):
            return "INCOMPLETE"

    def _record_child_evidence(self, children: list[RunResult], domain: str) -> None:
        verdicts = [self._child_verdict(child, domain) for child in children]
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
            domain,
            verdict=verdict,
            reason="composite_child_provider_evidence"
            if domain == "Provider"
            else "composite_child_dq_evidence",
            facts={
                "child_count": len(children),
                "verdicts": verdicts,
                "child_run_ids": [child.run_id for child in children],
                "report_refs": [child.run_report_json_path for child in children],
            },
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

            def preserve_primary_error(report_error: Exception) -> None:
                if error is None:
                    raise report_error
                self.logger.error(
                    "composite_report_write_failed", error=str(report_error)
                )

            try:
                with handle_operation_errors(preserve_primary_error):
                    self.write(
                        run_id=run_id,
                        started_at=started_at,
                        result=result,
                        error=error,
                        children=children,
                    )
            finally:
                _children.reset(children_token)
                reset_run_observations(observations_token)
