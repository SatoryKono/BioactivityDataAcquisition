"""Artifact and stable-text helpers for manifest diagnostics summary assembly."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest


def sorted_text_items(value: object) -> list[str]:
    """Return unique text items in stable content order."""
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    return sorted({text for item in value if (text := str(item).strip())})


def artifact_ref_sort_key(artifact_ref: dict[str, object]) -> tuple[str, ...]:
    """Return a stable ordering key for concrete produced artifacts."""
    return (
        str(artifact_ref.get("stage") or ""),
        str(artifact_ref.get("dataset_ref") or artifact_ref.get("artifact_id") or ""),
        str(artifact_ref.get("lineage_fragment_id") or ""),
        str(artifact_ref.get("artifact_path") or ""),
        str(artifact_ref.get("event_type") or ""),
    )


def build_trace_artifact_ref(
    artifact_ref: dict[str, object],
) -> dict[str, object]:
    """Return the concrete produced-artifact shape used by replay trace output."""
    from bioetl.application.services.control_plane.manifest.artifact_payloads import (
        ARTIFACT_TRACE_ORDERED_KEYS,
    )

    return {
        key: artifact_ref[key]
        for key in ARTIFACT_TRACE_ORDERED_KEYS
        if key in artifact_ref and artifact_ref[key] is not None
    }


def build_produced_artifact_trace(
    *,
    manifest: RunManifest,
    ledger_entries_present: bool,
    artifact_refs: list[dict[str, object]],
) -> dict[str, object]:
    """Return the manifest-id rooted concrete produced-artifact trace."""
    artifacts = [
        build_trace_artifact_ref(artifact_ref)
        for artifact_ref in sorted(artifact_refs, key=artifact_ref_sort_key)
    ]
    missing_requirements: list[str] = []
    if not ledger_entries_present:
        missing_requirements.append("run_ledger_history")
    if not artifacts:
        missing_requirements.append("artifact_publication_event")
    artifact_publication_closure = _resolve_artifact_publication_closure(
        artifact_refs=artifact_refs,
        missing_requirements=missing_requirements,
        planned_artifact_count=len(manifest.planned_artifacts),
    )
    return {
        "lookup": "run_ledger_by_manifest_id",
        "lookup_key": manifest.manifest_id,
        "manifest_id": manifest.manifest_id,
        "complete": not missing_requirements,
        "artifact_publication_closure": artifact_publication_closure,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "missing_requirements": missing_requirements,
    }


def _resolve_artifact_publication_closure(
    *,
    artifact_refs: list[dict[str, object]],
    missing_requirements: list[str],
    planned_artifact_count: int,
) -> str:
    """Classify produced-artifact publication evidence closure."""
    if any(
        str(ref.get("publication_status") or "").strip().lower() in {"failed", "error"}
        for ref in artifact_refs
    ):
        return "failed"
    if not artifact_refs:
        return "disabled"
    if missing_requirements:
        return "partial"
    if planned_artifact_count and len(artifact_refs) < planned_artifact_count:
        return "partial"
    return "closed"


def apply_artifact_publication_closure_policy(
    summary: dict[str, object],
) -> dict[str, object]:
    """Attach the canonical artifact-publication closure state."""
    updated = dict(summary)
    closure = str(updated.get("artifact_publication_closure") or "").strip()
    if not closure:
        trace = updated.get("produced_artifact_trace")
        if isinstance(trace, dict):
            closure = str(trace.get("artifact_publication_closure") or "").strip()
    closure = closure or "disabled"
    updated["artifact_publication_closure"] = closure
    return updated
