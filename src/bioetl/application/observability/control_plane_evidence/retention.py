"""Read-only retention and archive evidence checks for the selected manifest."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
    EvidenceStatus,
)
from bioetl.application.observability.control_plane_evidence.retention_checks import (
    retention_evidence_checks,
)
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactRef,
    RunManifest,
)


class ControlPlaneLifecyclePlanner(Protocol):
    """Read-only planner seam required by control-plane evidence."""

    def plan(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        dry_run: bool = True,
    ) -> ControlPlaneArtifactLifecyclePlan: ...

    def plan_for_manifest(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        manifest: RunManifest,
        dry_run: bool = True,
    ) -> ControlPlaneArtifactLifecyclePlan: ...


class ArchiveVerifierProtocol(Protocol):
    def verify(
        self, *, manifest: RunManifest, plan: ControlPlaneArtifactLifecyclePlan
    ) -> tuple[bool | None, str]: ...


def build_retention_checks(
    *,
    manifest: RunManifest,
    plan: ControlPlaneArtifactLifecyclePlan,
    archive_verifier: ArchiveVerifierProtocol | None = None,
) -> tuple[tuple[EvidenceCheckResult, ...], tuple[ControlPlaneArtifactRef, ...]]:
    relevant = tuple(
        artifact
        for artifact in plan.artifacts
        if _artifact_matches_manifest(artifact, manifest)
    )
    checks = retention_evidence_checks(manifest, relevant, cutoff=plan.cutoff)
    if archive_verifier is not None and checks[-1].reason != "archive_not_applicable":
        verified, reason = archive_verifier.verify(manifest=manifest, plan=plan)
        archive = EvidenceCheckResult(
            "archive",
            _archive_status(verified),
            reason,
            "Local archive and restored copies are hash-checked against selected-run "
            "evidence on every read. This is not an off-host durability guarantee.",
        )
        checks = (*checks[:-1], archive)
    return checks, relevant


def _archive_status(verified: bool | None) -> EvidenceStatus:
    if verified is True:
        return "OK"
    if verified is False:
        return "ERROR"
    return "UNKNOWN"


def _artifact_matches_manifest(
    artifact: ControlPlaneArtifactRef,
    manifest: RunManifest,
) -> bool:
    anchors = (f"manifest:{manifest.manifest_id}", f"run:{manifest.run_id}")
    if artifact.artifact_id in {manifest.manifest_id, str(manifest.run_id)}:
        return True
    if any(
        reason == anchor or reason.endswith(f":{anchor}")
        for reason in artifact.protected_by
        for anchor in anchors
    ):
        return True
    effective_config_id = manifest.code_provenance.effective_config_artifact_id
    if effective_config_id and artifact.artifact_id == effective_config_id:
        return True
    return artifact.artifact_id in _manifest_snapshot_ids(manifest)


def _manifest_snapshot_ids(manifest: RunManifest) -> set[str]:
    return {
        snapshot.snapshot_id
        for source in manifest.source_refs
        for snapshot in source.input_snapshots
    }


def serialize_resolution_issues(
    plan: ControlPlaneArtifactLifecyclePlan,
) -> list[dict[str, object]]:
    issues = getattr(plan, "resolution_issues", ())
    return [
        {
            "code": issue.code.value,
            "surface": issue.surface.value,
            "detail": issue.detail,
        }
        for issue in issues
    ]


def summarize_retention_artifacts(
    artifacts: Iterable[ControlPlaneArtifactRef],
) -> list[dict[str, object]]:
    """Return bounded surface/reason counts without exposing filesystem paths."""
    counts: dict[tuple[str, str, str], int] = {}
    for artifact in artifacts:
        key = (
            artifact.surface.value,
            artifact.decision.value,
            artifact.reason,
        )
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "surface": surface,
            "decision": decision,
            "reason": reason,
            "count": count,
        }
        for (surface, decision, reason), count in sorted(counts.items())
    ]


__all__ = [
    "ArchiveVerifierProtocol",
    "ControlPlaneLifecyclePlanner",
    "build_retention_checks",
    "serialize_resolution_issues",
    "summarize_retention_artifacts",
]
