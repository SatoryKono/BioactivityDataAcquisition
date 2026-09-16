"""Capture control-plane checks at run completion, never on a historical GET."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
    EvidenceScopeContext,
)
from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID


@dataclass(frozen=True, slots=True)
class CaptureControlPlaneSnapshot:
    """Use existing read-only validators with the completion time supplied by caller."""

    manifests: RunManifestPort
    evidence: ControlPlaneEvidenceService

    def __call__(self, pipeline: str, run_id: str, completed_at: datetime) -> None:
        manifest = self.manifests.get_by_run_id(cast(RunID, UUID(run_id)))
        if manifest is None or manifest.pipeline_name != pipeline:
            record_run_observation(
                "Control Plane",
                verdict="INCOMPLETE",
                reason="manifest_not_found",
                facts={"run_id": run_id},
            )
            return
        scope = EvidenceScopeContext(pipeline, run_id, (), "exact_run", manifest)
        payload = self.evidence.trust_summary(scope=scope, now=completed_at)
        status = str(payload.get("trust_status", payload.get("status", "UNKNOWN")))
        # Replace the provisional manifest observation only after the full checks.
        record_run_observation(
            "Control Plane",
            verdict={"WARNING": "WARN"}.get(status, status),
            reason="run_completion_trust_assessment",
            facts={"observed_at": completed_at.isoformat(), "checks": payload},
            replace_provisional=True,
        )
