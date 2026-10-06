"""Persist composite terminal evidence without borrowing a child's identity."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.run_reports.composite_report_support import (
    assess_result,
    build_composite_report,
    child_artifacts,
    child_verdict,
    completion_status,
    merge_layers,
    record_stage_quality,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    record_run_observation,
    reset_run_observations,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
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
    execution_scope: Callable[[], AbstractContextManager[object]] = nullcontext
    replay_artifacts: Callable[[str], tuple[dict[str, object], ...]] | None = None

    def write(
        self,
        *,
        run_id: str,
        started_at: datetime,
        result: CompositeResult | None,
        error: BaseException | None,
        children: list[RunResult],
    ) -> CompositeResult | None:
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
        provider_warnings = self._record_child_evidence(children, "Provider")
        self._record_child_evidence(children, "Data Quality")
        record_stage_quality(result, children)
        result = assess_result(result, children, provider_warnings)
        layers = merge_layers(result)
        identity: dict[str, object] = {
            "pipeline_name": self.pipeline_name,
            "run_id": run_id,
            "manifest_id": self.manifest_id,
            "provider": "composite",
            "entity": "merged",
            "run_type": "composite",
            "status": status,
            "completion_status": completion_status(status, result, provider_warnings),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }
        artifacts = child_artifacts(self.store, children)
        if self.replay_artifacts is not None:
            artifacts += self.replay_artifacts(run_id)
        report = build_composite_report(identity, result, error, children, artifacts)
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

        return result

    def _record_child_evidence(
        self, children: list[RunResult], domain: str
    ) -> tuple[str, ...]:
        verdicts = [child_verdict(self.store, child, domain) for child in children]
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
        return tuple(
            child.pipeline_name
            for child, value in zip(children, verdicts, strict=True)
            if value not in {"OK", "N/A"}
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
            with self.execution_scope():
                result = await body()
        except BaseException as exc:
            error = exc
            raise
        finally:
            try:
                result = self.write(
                    run_id=run_id,
                    started_at=started_at,
                    result=result,
                    error=error,
                    children=children,
                )
            finally:
                try:
                    report_error = sys.exception()
                    if error is not None and report_error is not error:
                        try:
                            self.logger.error(
                                "composite_report_write_failed", error=str(report_error)
                            )
                        finally:
                            raise error
                finally:
                    _children.reset(children_token)
                    reset_run_observations(observations_token)
        assert result is not None
        return result
