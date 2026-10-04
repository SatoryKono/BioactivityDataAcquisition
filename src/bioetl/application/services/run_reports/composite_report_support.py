"""Build parent evidence without conflating stage outcomes and provider health."""

from __future__ import annotations

import json
from dataclasses import replace

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.application.services.run_reports.observations import (
    record_run_observation,
    run_observations,
)
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.models import (
    LayerCounts,
    PipelineRunReport,
    TrackingCoverage,
)
from bioetl.domain.run_reports.reason_catalog_data import default_reason_catalog


def completion_status(
    status: str, result: CompositeResult | None, provider_warnings: tuple[str, ...]
) -> str:
    """Keep terminal provider warnings separate from partial execution."""
    if status != "success" or result is None:
        return status
    if result.had_warnings or result.provider_warnings or provider_warnings:
        return "completed_with_warnings"
    return status


def merge_layers(result: CompositeResult | None) -> LayerCounts:
    """Count only parent merge writes, never child extraction layers."""
    merge = result.merge_result if result else None
    if merge is None:
        return LayerCounts()
    return LayerCounts(
        silver_valid=merge.records_merged if merge.output_silver_path else 0,
        gold_written=merge.records_merged if merge.output_gold_path else 0,
    )


def child_verdict(store: RunReportStorePort, child: RunResult, domain: str) -> str:
    """Read one exact child identity and reject missing or unknown evidence."""
    try:
        if not child.run_report_json_path:
            return "INCOMPLETE"
        report = json.loads(store.read_text(child.run_report_json_path))
        if report["identity"]["run_id"] != child.run_id:
            return "INCOMPLETE"
        verdict = str(
            report.get("observations", {}).get(domain, {}).get("verdict", "INCOMPLETE")
        )
        return (
            verdict
            if verdict in {"ERROR", "INCOMPLETE", "UNKNOWN", "WARN", "OK", "N/A"}
            else "INCOMPLETE"
        )
    except (OSError, ValueError, KeyError, TypeError):
        return "INCOMPLETE"


def record_stage_quality(
    result: CompositeResult | None, children: list[RunResult]
) -> None:
    """Preserve child DQ severity while recording actual stage failures."""
    if result is None:
        return
    failures = [child.run_id for child in children if not child.is_success]
    if not result.had_warnings and not failures:
        return
    evidence = run_observations().get("Data Quality", {})
    verdict = str(evidence.get("verdict", "WARN"))
    facts = evidence.get("facts", {})
    record_run_observation(
        "Data Quality",
        verdict=verdict if verdict in {"ERROR", "INCOMPLETE", "UNKNOWN"} else "WARN",
        reason="composite_partial_stage_execution",
        facts={
            **(facts if isinstance(facts, dict) else {}),
            "failed_children": failures,
        },
    )


def _child_artifact(child: RunResult, store: RunReportStorePort) -> dict[str, object]:
    """Persist portable child references and bind available evidence by digest."""
    artifact: dict[str, object] = {
        "kind": "composite_child_run_report",
        "ref": f"pipeline/{child.pipeline_name}/{child.run_id}/pipeline-run-report.json",
        "run_id": child.run_id,
        "pipeline_name": child.pipeline_name,
        "manifest_id": child.manifest_id,
    }
    try:
        payload = json.loads(store.read_text(str(child.run_report_json_path)))
        if isinstance(payload, dict):
            artifact["sha256"] = canonical_report_sha256(payload)
    except (OSError, ValueError, TypeError):
        # Preserve the reference: readers must expose missing/invalid evidence.
        pass
    return artifact


def child_artifacts(
    store: RunReportStorePort, children: list[RunResult]
) -> tuple[dict[str, object], ...]:
    """Bind exact child reports using the current canonical report digest."""
    return tuple(
        _child_artifact(child, store)
        for child in children
        if child.run_report_json_path
    )


def build_composite_report(
    identity: dict[str, object],
    result: CompositeResult | None,
    error: BaseException | None,
    children: list[RunResult],
    artifacts: tuple[dict[str, object], ...],
) -> PipelineRunReport:
    """Build the report from observed parent writes and immutable references."""
    merge = result.merge_result if result else None
    return PipelineRunReport(
        identity=identity,
        funnel=(),
        layers=merge_layers(result),
        reasons_top_n=(),
        reconciliation={
            "scope": "composite_merge",
            "seed_records": merge.records_from_seed if merge else None,
            "merged_records": merge.records_merged if merge else None,
        },
        tracking_coverage=TrackingCoverage.PARTIAL,
        reason_catalog_version=default_reason_catalog().version,
        artifacts=artifacts,
        failure={"error_type": type(error).__name__, "error_message": str(error)}
        if error
        else None,
        io={
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
        },
        observations=dict(run_observations()),
    )


def assess_result(
    result: CompositeResult | None,
    children: list[RunResult],
    provider_warnings: tuple[str, ...],
) -> CompositeResult | None:
    """Return terminal execution warnings independently of archive staging."""
    if result is None:
        return None
    return replace(
        result,
        provider_warnings=provider_warnings,
        had_warnings=result.had_warnings
        or any(not child.is_success for child in children)
        or any(
            run_observations().get(domain, {}).get("verdict") not in {"OK", "N/A"}
            for domain in ("Provider", "Data Quality")
        ),
    )
