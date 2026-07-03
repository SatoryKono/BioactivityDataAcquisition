"""Diagnostic helpers for forensic run diff reporting."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestDiffResult,
    RunManifestInspectionResult,
)


def _dict_or_empty(value: object) -> dict[str, object]:
    """Return a plain dict for JSON-safe nested diagnostics."""
    return dict(value) if isinstance(value, Mapping) else {}


def _artifact_refs(diagnostics: dict[str, object]) -> list[dict[str, object]]:
    refs = diagnostics.get("artifact_refs")
    if not isinstance(refs, list):
        return []
    return [dict(ref) for ref in refs if isinstance(ref, Mapping)]


def _coerce_int(value: object) -> int:
    """Return a stable integer view for loosely-typed diagnostics payloads."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _metadata_sidecar_missing_count(diagnostics: dict[str, object]) -> int:
    return sum(1 for ref in _artifact_refs(diagnostics) if not ref.get("metadata_path"))


def _trace_missing_requirements(diagnostics: dict[str, object]) -> tuple[str, ...]:
    trace = _dict_or_empty(diagnostics.get("produced_artifact_trace"))
    missing = trace.get("missing_requirements")
    if not isinstance(missing, list):
        return ()
    return tuple(str(item) for item in missing)


def _string_list_or_empty(value: object) -> list[str]:
    """Return a stringified list view for loosely typed diagnostics payloads."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _string_list(value: tuple[str, ...]) -> list[str]:
    """Return a concrete list for tuple-backed string fields."""
    return list(value)


def _trace_complete(diagnostics: dict[str, object]) -> bool:
    trace = _dict_or_empty(diagnostics.get("produced_artifact_trace"))
    return bool(trace.get("complete", False))


def _lineage_closure_payload(result: RunManifestInspectionResult) -> dict[str, object]:
    diagnostics = result.diagnostics
    boundary = _dict_or_empty(diagnostics.get("lineage_closure_boundary"))
    supported = boundary.get("supported")
    if supported is None:
        status = "missing"
    elif bool(supported):
        status = "supported"
    else:
        status = "unsupported"
    return {
        "manifest_id": result.manifest.manifest_id,
        "status": status,
        "supported": supported,
        "boundary": boundary,
    }


def _artifact_completeness(result: RunManifestInspectionResult) -> dict[str, object]:
    diagnostics = result.diagnostics
    artifact_refs = _artifact_refs(diagnostics)
    missing_sidecars = _metadata_sidecar_missing_count(diagnostics)
    published_count = _coerce_int(diagnostics.get("published_artifact_count", 0) or 0)
    missing_links = _coerce_int(diagnostics.get("missing_artifact_links", 0) or 0)
    return {
        "manifest_id": result.manifest.manifest_id,
        "published_artifact_count": published_count,
        "missing_artifact_links": missing_links,
        "metadata_sidecar_count": len(artifact_refs) - missing_sidecars,
        "metadata_sidecar_missing_count": missing_sidecars,
        "produced_artifact_trace_complete": _trace_complete(diagnostics),
        "produced_artifact_trace_missing_requirements": list(
            _trace_missing_requirements(diagnostics)
        ),
        "complete": (
            published_count > 0
            and missing_links == 0
            and missing_sidecars == 0
            and _trace_complete(diagnostics)
        ),
    }


def _replay_capability_payload(
    *,
    left: RunManifestInspectionResult,
    right: RunManifestInspectionResult,
) -> dict[str, object]:
    left_snapshot = _diagnostic_snapshot(left)
    right_snapshot = _diagnostic_snapshot(right)
    return {
        "left": {
            "manifest_id": left.manifest.manifest_id,
            "replay_capability": left_snapshot.get("replay_capability"),
            "exact_replay_eligible": left_snapshot.get("exact_replay_eligible"),
            "exact_replay_blockers": left_snapshot.get("exact_replay_blockers", []),
            "persistence_profile": left_snapshot.get("persistence_profile"),
        },
        "right": {
            "manifest_id": right.manifest.manifest_id,
            "replay_capability": right_snapshot.get("replay_capability"),
            "exact_replay_eligible": right_snapshot.get("exact_replay_eligible"),
            "exact_replay_blockers": right_snapshot.get("exact_replay_blockers", []),
            "persistence_profile": right_snapshot.get("persistence_profile"),
        },
        "capability_match": left_snapshot.get("replay_capability")
        == right_snapshot.get("replay_capability"),
    }


def _checkpoint_compatibility_payload(
    forensic_diff: dict[str, object],
) -> dict[str, object]:
    anchors = _dict_or_empty(forensic_diff.get("checkpoint_anchors"))
    return {
        "available": bool(anchors),
        "compatible": anchors.get("compatible") if anchors else None,
        "matching_fields": _string_list_or_empty(anchors.get("matching_fields")),
        "mismatched_fields": _string_list_or_empty(anchors.get("mismatched_fields")),
    }


def _resolve_forensic_verdict(
    *,
    manifest_diff: RunManifestDiffResult,
    forensic_diff: dict[str, object],
) -> str:
    if manifest_diff.classification == "semantic_drift":
        return "semantic_drift"
    anchors = _dict_or_empty(forensic_diff.get("checkpoint_anchors"))
    if anchors.get("compatible") is False:
        return "checkpoint_incompatible"
    if manifest_diff.occurrence_only:
        return "occurrence_only_replay"
    return "semantic_equivalent_replay"


def _forensic_diff_payload(manifest_diff: RunManifestDiffResult) -> dict[str, object]:
    payload = _dict_or_empty(manifest_diff.cross_surface_replay_diff)
    verdict = payload.get("verdict")
    if not isinstance(verdict, str):
        payload["verdict"] = _resolve_forensic_verdict(
            manifest_diff=manifest_diff,
            forensic_diff=payload,
        )
    return payload


def _diagnostic_snapshot(result: RunManifestInspectionResult) -> dict[str, object]:
    """Return the bounded diagnostic fields used by forensic diff reports."""
    diagnostics = result.diagnostics
    return {
        "manifest_id": result.manifest.manifest_id,
        "run_id": str(result.manifest.run_id),
        "replay_capability": diagnostics.get("replay_capability"),
        "exact_replay_eligible": diagnostics.get("exact_replay_eligible"),
        "exact_replay_blockers": diagnostics.get("exact_replay_blockers", []),
        "persistence_profile": diagnostics.get("persistence_profile"),
        "published_artifact_count": diagnostics.get("published_artifact_count", 0),
        "missing_artifact_links": diagnostics.get("missing_artifact_links", 0),
        "lineage_closure_boundary": diagnostics.get("lineage_closure_boundary"),
        "produced_artifact_trace": diagnostics.get("produced_artifact_trace"),
    }


def _missing_evidence(result: RunManifestInspectionResult) -> tuple[str, ...]:
    """Classify optional forensic evidence gaps instead of hiding them."""
    diagnostics = result.diagnostics
    missing: list[str] = []
    if not result.ledger_entries:
        missing.append("run_ledger_entries_missing")
    if _coerce_int(diagnostics.get("published_artifact_count", 0) or 0) == 0:
        missing.append("published_artifacts_missing")
    if _coerce_int(diagnostics.get("missing_artifact_links", 0) or 0) > 0:
        missing.append("artifact_links_incomplete")
    if _metadata_sidecar_missing_count(diagnostics) > 0:
        missing.append("metadata_sidecars_missing")
    if not _trace_complete(diagnostics):
        missing.append("produced_artifact_trace_incomplete")
    lineage_closure = _lineage_closure_payload(result)
    if lineage_closure["status"] == "missing":
        missing.append("lineage_closure_boundary_missing")
    elif lineage_closure["status"] == "unsupported":
        missing.append("lineage_closure_boundary_unsupported")
    return tuple(missing)
