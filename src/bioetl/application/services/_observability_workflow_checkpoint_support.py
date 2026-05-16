"""Checkpoint compatibility helpers for observability workflow dossiers."""

from __future__ import annotations

from bioetl.application.services.checkpoint_service import CheckpointInfo
from bioetl.application.services.control_plane._run_manifest_replay_taxonomy import (
    resolve_replay_taxonomy_projection,
)
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionResult,
)

_CHECKPOINT_COMPATIBILITY_ANCHORS = (
    "run_id",
    "manifest_id",
    "execution_fingerprint",
    "effective_config_hash",
    "effective_config_artifact_id",
    "contract_ref",
    "contract_version",
    "dq_contract_compatibility_hash",
    "exact_replay",
    "input_snapshot_fingerprint",
)


def build_checkpoint_compatibility_section(
    *,
    checkpoint: CheckpointInfo | None,
    run_manifest: RunManifestInspectionResult | None,
) -> dict[str, object]:
    """Build a bounded CLI/API compatibility view for checkpoint diagnostics."""
    replay_context = _replay_context(run_manifest)
    if checkpoint is None:
        return _checkpoint_compatibility_missing(
            taxonomy="missing_checkpoint",
            replay_context=replay_context,
            missing_anchor="checkpoint",
        )
    if _checkpoint_payload_is_corrupt(checkpoint):
        return {
            "status": "corruption",
            "compatible": False,
            "taxonomy": "corrupted_checkpoint_payload",
            **replay_context,
            "matched_anchors": [],
            "mismatched_anchors": [],
            "missing_anchors": [],
        }
    if run_manifest is None:
        return _checkpoint_compatibility_missing(
            taxonomy="missing_run_manifest",
            replay_context=replay_context,
            missing_anchor="run_manifest",
        )

    checkpoint_anchors = _checkpoint_anchors(checkpoint)
    manifest_anchors = _manifest_anchors(run_manifest)
    matched, mismatched, missing = _compare_checkpoint_manifest_anchors(
        checkpoint_anchors=checkpoint_anchors,
        manifest_anchors=manifest_anchors,
    )
    compatible = not mismatched and not missing
    taxonomy = _checkpoint_taxonomy(
        compatible=compatible,
        replay_context=replay_context,
        checkpoint_anchors=checkpoint_anchors,
        run_manifest=run_manifest,
    )
    return {
        "status": "compatible" if compatible else "incompatible",
        "compatible": compatible,
        "taxonomy": taxonomy,
        **replay_context,
        "matched_anchors": matched,
        "mismatched_anchors": mismatched,
        "missing_anchors": missing,
        "checkpoint_anchors": checkpoint_anchors,
        "manifest_anchors": manifest_anchors,
    }


def _checkpoint_compatibility_missing(
    *,
    taxonomy: str,
    replay_context: dict[str, object],
    missing_anchor: str,
) -> dict[str, object]:
    return {
        "status": "missing_evidence",
        "compatible": False,
        "taxonomy": taxonomy,
        **replay_context,
        "matched_anchors": [],
        "mismatched_anchors": [],
        "missing_anchors": [missing_anchor],
    }


def _checkpoint_payload_is_corrupt(checkpoint: CheckpointInfo) -> bool:
    status = str(checkpoint.metadata.get("status") or "").strip().lower()
    return status in {"corrupt", "corrupted", "corrupted_checkpoint_payload"}


def _checkpoint_anchors(checkpoint: CheckpointInfo) -> dict[str, object]:
    metadata = checkpoint.metadata
    return {
        "run_id": checkpoint.run_id or metadata.get("run_id"),
        "manifest_id": metadata.get("manifest_id"),
        "execution_fingerprint": metadata.get("execution_fingerprint"),
        "effective_config_hash": metadata.get("effective_config_hash"),
        "effective_config_artifact_id": metadata.get("effective_config_artifact_id"),
        "contract_ref": metadata.get("contract_ref"),
        "contract_version": metadata.get("contract_version"),
        "dq_contract_compatibility_hash": metadata.get(
            "dq_contract_compatibility_hash"
        ),
        "exact_replay": metadata.get("exact_replay"),
        "input_snapshot_fingerprint": metadata.get("input_snapshot_fingerprint"),
    }


def _manifest_anchors(run_manifest: RunManifestInspectionResult) -> dict[str, object]:
    manifest = run_manifest.manifest
    provenance = getattr(manifest, "code_provenance", None)
    diagnostics = run_manifest.diagnostics
    return {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "execution_fingerprint": manifest.execution_fingerprint,
        "effective_config_hash": getattr(provenance, "effective_config_hash", None),
        "effective_config_artifact_id": getattr(
            provenance,
            "effective_config_artifact_id",
            None,
        ),
        "contract_ref": getattr(provenance, "contract_ref", None),
        "contract_version": getattr(provenance, "contract_version", None),
        "dq_contract_compatibility_hash": getattr(
            provenance,
            "dq_contract_compatibility_hash",
            None,
        ),
        "exact_replay": _requested_exact_replay(run_manifest),
        "input_snapshot_fingerprint": diagnostics.get(
            "input_snapshot_identity_fingerprint"
        ),
    }


def _compare_checkpoint_manifest_anchors(
    *,
    checkpoint_anchors: dict[str, object],
    manifest_anchors: dict[str, object],
) -> tuple[list[str], list[dict[str, object]], list[str]]:
    matched: list[str] = []
    mismatched: list[dict[str, object]] = []
    missing: list[str] = []
    for key in _CHECKPOINT_COMPATIBILITY_ANCHORS:
        checkpoint_value = checkpoint_anchors.get(key)
        manifest_value = manifest_anchors.get(key)
        if _anchor_missing(checkpoint_value) or _anchor_missing(manifest_value):
            if not (
                _anchor_missing(checkpoint_value) and _anchor_missing(manifest_value)
            ):
                missing.append(key)
            continue
        if _normalized_anchor(checkpoint_value) == _normalized_anchor(manifest_value):
            matched.append(key)
            continue
        mismatched.append(
            {
                "anchor": key,
                "checkpoint": checkpoint_value,
                "manifest": manifest_value,
            }
        )
    return matched, mismatched, missing


def _checkpoint_taxonomy(
    *,
    compatible: bool,
    replay_context: dict[str, object],
    checkpoint_anchors: dict[str, object],
    run_manifest: RunManifestInspectionResult,
) -> str:
    if not compatible:
        return "blocked_resume"
    configured_taxonomy = _configured_checkpoint_taxonomy(replay_context)
    if configured_taxonomy is not None:
        return configured_taxonomy
    capability_taxonomy = _checkpoint_capability_taxonomy(
        replay_capability=replay_context.get("replay_capability"),
        exact_replay_requested=_checkpoint_exact_replay_requested(
            checkpoint_anchors=checkpoint_anchors,
            run_manifest=run_manifest,
        ),
    )
    return capability_taxonomy or "compatible_resume"


def _configured_checkpoint_taxonomy(
    replay_context: dict[str, object],
) -> str | None:
    continuation_mode = replay_context.get("continuation_mode")
    if isinstance(continuation_mode, str) and continuation_mode:
        return continuation_mode
    replay_mode = replay_context.get("replay_mode")
    if isinstance(replay_mode, str) and replay_mode in {
        "exact_replay",
        "same_data_state_recovery",
        "resume",
        "rebuild",
    }:
        return replay_mode
    return None


def _checkpoint_exact_replay_requested(
    *,
    checkpoint_anchors: dict[str, object],
    run_manifest: RunManifestInspectionResult,
) -> bool:
    return checkpoint_anchors.get("exact_replay") is True or (
        _requested_exact_replay(run_manifest) is True
    )


def _checkpoint_capability_taxonomy(
    *,
    replay_capability: object,
    exact_replay_requested: bool,
) -> str | None:
    if replay_capability == "exact_replay_supported" and exact_replay_requested:
        return "exact_replay"
    if replay_capability == "resume_only":
        return "resume_only"
    if replay_capability == "rebuild_only":
        return "rebuild_only"
    return None


def _replay_capability(run_manifest: RunManifestInspectionResult | None) -> object:
    if run_manifest is None:
        return None
    return run_manifest.identity_graph.get(
        "replay_capability"
    ) or run_manifest.diagnostics.get("replay_capability")


def _replay_context(
    run_manifest: RunManifestInspectionResult | None,
) -> dict[str, object]:
    """Return replay taxonomy fields used by checkpoint compatibility views."""
    if run_manifest is None:
        return {
            "replay_capability": None,
            "replay_mode": None,
            "continuation_mode": None,
            "operator_replay_mode": None,
            "replay_readiness_verdict": None,
        }
    replay_taxonomy = resolve_replay_taxonomy_projection(
        run_manifest.diagnostics,
        fallback=run_manifest.identity_graph,
    )
    return {
        "replay_capability": replay_taxonomy.get("replay_capability")
        or _replay_capability(run_manifest),
        "replay_mode": replay_taxonomy.get("replay_mode"),
        "continuation_mode": replay_taxonomy.get("continuation_mode"),
        "operator_replay_mode": replay_taxonomy.get("operator_replay_mode"),
        "replay_readiness_verdict": replay_taxonomy.get("replay_readiness_verdict"),
    }


def _requested_exact_replay(run_manifest: RunManifestInspectionResult) -> object:
    diagnostics = run_manifest.diagnostics
    if "requested_exact_replay" in diagnostics:
        return diagnostics["requested_exact_replay"]
    manifest = run_manifest.manifest
    launch_context = getattr(manifest, "launch_context", None)
    if isinstance(launch_context, dict):
        return launch_context.get("exact_replay")
    return None


def _anchor_missing(value: object) -> bool:
    return value is None or value == "" or value == ()


def _normalized_anchor(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value).strip()
