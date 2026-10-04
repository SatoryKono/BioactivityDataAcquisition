"""Persist composite terminal evidence without borrowing a child's identity."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path

from bioetl.application.services.execution import finalize_terminal_evidence
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.run_reports.composite_evidence import (
    build_composite_report,
    composite_layer_counts,
    composite_terminal_status,
    read_child_observation_verdict,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    record_run_observation,
    reset_run_observations,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.ports import ClockPort, LoggerPort, RunReportStorePort

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
        status = composite_terminal_status(result, error)
        try:
            self.capture(self.pipeline_name, run_id, completed_at)
        except (OSError, RuntimeError, ValueError, TypeError):
            record_run_observation(
                "Control Plane",
                verdict="INCOMPLETE",
                reason="completion_assessment_failed",
                facts={},
            )
        self._record_child_evidence(children, "Provider")
        self._record_child_evidence(children, "Data Quality")
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
        layers = composite_layer_counts(result)
        report = build_composite_report(
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
            result=result,
            error=error,
            children=children,
            layers=layers,
            store=self.store,
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

    def _record_child_evidence(self, children: list[RunResult], domain: str) -> None:
        verdicts = [
            read_child_observation_verdict(self.store, child, domain)
            for child in children
        ]
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
            try:
                finalize_terminal_evidence(
                    partial(
                        self.write,
                        run_id=run_id,
                        started_at=started_at,
                        result=result,
                        error=error,
                        children=children,
                    ),
                    execution_error=error,
                    logger=self.logger,
                    event="composite_report_write_failed",
                )
            finally:
                _children.reset(children_token)
                reset_run_observations(observations_token)
