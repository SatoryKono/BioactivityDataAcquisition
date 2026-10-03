"""Pure parent report assembly and source-bound child observation reads."""

from __future__ import annotations

import asyncio
import json

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.application.services.run_reports.observations import run_observations
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.models import (
    LayerCounts,
    PipelineRunReport,
    TrackingCoverage,
)
from bioetl.domain.run_reports.reason_catalog import default_reason_catalog


def composite_terminal_status(
    result: CompositeResult | None, error: BaseException | None
) -> str:
    """Separate orderly cancellation from unsuccessful completion."""
    if isinstance(error, (asyncio.CancelledError, PipelineShutdownError)):
        return "shutdown"
    return (
        "success"
        if result is not None and result.is_success and error is None
        else "failed"
    )


def composite_layer_counts(result: CompositeResult | None) -> LayerCounts:
    """Count only the parent's actual merge writes, without child Bronze."""
    merge = result.merge_result if result is not None else None
    return LayerCounts(
        silver_valid=merge.records_merged if merge and merge.output_silver_path else 0,
        gold_written=merge.records_merged if merge and merge.output_gold_path else 0,
    )


def _child_artifacts(children: list[RunResult]) -> tuple[dict[str, str | None], ...]:
    return tuple(
        {
            "kind": "composite_child_run_report",
            "ref": child.run_report_json_path,
            "run_id": child.run_id,
            "pipeline_name": child.pipeline_name,
            "manifest_id": child.manifest_id,
        }
        for child in children
        if child.run_report_json_path
    )


def _failure(error: BaseException | None) -> dict[str, str] | None:
    if error is None:
        return None
    return {"error_type": type(error).__name__, "error_message": str(error)}


def build_composite_report(
    *,
    identity: dict[str, object],
    result: CompositeResult | None,
    error: BaseException | None,
    children: list[RunResult],
    layers: LayerCounts,
) -> PipelineRunReport:
    """Assemble parent evidence without borrowing any child run identity."""
    merge = result.merge_result if result is not None else None
    return PipelineRunReport(
        identity=identity,
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
        artifacts=_child_artifacts(children),
        failure=_failure(error),
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
        observations=dict(run_observations()),
    )


def read_child_observation_verdict(
    store: RunReportStorePort, child: RunResult, domain: str
) -> str:
    """Reject missing, malformed or identity-mismatched child evidence."""
    try:
        if not child.run_report_json_path:
            raise ValueError("child_report_missing")
        report = json.loads(store.read_text(child.run_report_json_path))
        if report["identity"]["run_id"] != child.run_id:
            raise ValueError("child_report_identity_mismatch")
        return str(
            report.get("observations", {}).get(domain, {}).get("verdict", "INCOMPLETE")
        )
    except (OSError, ValueError, KeyError, TypeError):
        return "INCOMPLETE"
