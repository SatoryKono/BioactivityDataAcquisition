"""Explicit, bounded discovery of an aggregate-complete run in the same scope."""

from __future__ import annotations

from datetime import datetime
from time import monotonic

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
    EvidenceScopeContext,
)
from bioetl.domain.control_plane import RunManifest, WorkflowManifest
from bioetl.interfaces.http._control_plane_selector_records import (
    build_workflow_aliases,
    narrow_manifest_catalog,
)

LATEST_COMPLETE_SCAN_LIMIT = 20
LATEST_COMPLETE_SCAN_SECONDS = 9.0


def build_latest_complete_run_payload(
    *,
    manifests: tuple[RunManifest, ...],
    workflow_manifests: tuple[WorkflowManifest, ...],
    service: ControlPlaneEvidenceService,
    pipeline: str,
    run_type: str,
    workflows: tuple[str, ...],
    selected_run_id: str | None,
    now: datetime,
) -> dict[str, object]:
    """Find the newest-created successful run whose aggregate Trust is OK.

    Historical selection is returned separately and never used to narrow this
    discovery. The outer forensic HTTP deadline also bounds catalog loading.
    Exhausting the scan does not assert that no complete run exists globally.
    """
    candidates = narrow_manifest_catalog(
        manifests,
        selected_workflows=workflows,
        selected_pipelines=(pipeline,),
        selected_run_types=(run_type,),
        selected_run_id=None,
        workflow_aliases=build_workflow_aliases(workflow_manifests),
        fail_open_when_empty=False,
    )
    ordered = sorted(
        candidates, key=lambda item: (item.created_at, item.manifest_id), reverse=True
    )
    scanned = 0
    started = monotonic()
    row: dict[str, object] = {
        "status": "NOT FOUND",
        "reason": "no_complete_run_in_scope",
        "candidate_run_id": None,
        "observed_at": None,
        "pipeline": pipeline,
        "run_type": run_type,
    }
    for manifest in ordered:
        if scanned >= LATEST_COMPLETE_SCAN_LIMIT or (
            monotonic() - started >= LATEST_COMPLETE_SCAN_SECONDS
        ):
            row.update(status="INCOMPLETE", reason="complete_run_scan_limit")
            break
        scope = EvidenceScopeContext(
            requested_pipeline=pipeline,
            selected_run_id=str(manifest.run_id),
            selected_run_types=(run_type,),
            resolved_via="selected_run_id",
            manifest=manifest,
        )
        evidence = service.trust_summary(scope=scope, now=now)
        scanned += 1
        if (
            evidence.get("trust_status") == "OK"
            and evidence.get("processing_status") == "success"
        ):
            row.update(
                status="OK",
                reason="aggregate_complete_run_found",
                candidate_run_id=str(manifest.run_id),
                observed_at=manifest.created_at.isoformat(),
            )
            break
    candidate_run_id = row.get("candidate_run_id")
    if candidate_run_id is None:
        # Grafana renders data links even for a null cell. Omit the linked
        # column entirely so an unsuccessful search cannot navigate to run_id=.
        row.pop("candidate_run_id")
        row.pop("observed_at")
    return {
        "contract": "control_plane_latest_complete_run_v1",
        "selected_run_id": selected_run_id,
        "candidate_run_id": candidate_run_id,
        "pipeline": pipeline,
        "run_type": run_type,
        "workflow": list(workflows),
        "order": "manifest_created_at_desc",
        "scanned": scanned,
        "candidate_count": len(ordered),
        "scan_limit": LATEST_COMPLETE_SCAN_LIMIT,
        "replay_authorized": False,
        "rows": [row],
    }


__all__ = ["build_latest_complete_run_payload"]
