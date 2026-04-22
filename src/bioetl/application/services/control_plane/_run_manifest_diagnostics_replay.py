"""Replay, resume, and input-snapshot helpers for manifest diagnostics."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_profiles import (
    build_replay_family_contract,
    resolve_reproducibility_family_profile,
)
from bioetl.domain.normalization import serialize_json_canonical


def _resolve_replay_mode(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
) -> str:
    """Resolve operator-facing replay mode from manifest intent and capability."""
    profile = _resolve_reproducibility_profile(manifest)
    if (
        requested_exact_replay
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        and profile.strict_exact_replay_supported
    ):
        return "exact_replay"
    if manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return "same_data_state_recovery"
    if resume_requested or manifest.replay_capability == ReplayCapability.RESUME_ONLY:
        return "resume"
    return "rebuild"


def _resolve_replay_capability_reason(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    resume_requested: bool,
) -> str:
    """Return one operator-facing explanation for replay capability."""
    profile = _resolve_reproducibility_profile(manifest)
    if not profile.strict_exact_replay_supported:
        return "family_outside_supported_exact_replay_boundary"
    if (
        manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        and input_snapshots
    ):
        return "immutable_input_snapshots_present"
    if manifest.replay_capability == ReplayCapability.RESUME_ONLY or resume_requested:
        return "resume_requested_without_snapshot_backed_inputs"
    if _is_composite_execution_context(manifest):
        return "composite_snapshot_envelope_missing"
    return "immutable_input_snapshots_missing"


def _resolve_exact_replay_blockers(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Return explicit blockers preventing exact replay eligibility."""
    profile = _resolve_reproducibility_profile(manifest)
    if (
        profile.strict_exact_replay_supported
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        return []
    blockers: list[str] = []
    if not profile.strict_exact_replay_supported:
        blockers.append("family_outside_supported_exact_replay_boundary")
    if not input_snapshots:
        blockers.append("immutable_input_snapshots_missing")
    elif manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        blockers.append("exact_replay_capability_unavailable")
    return blockers


def _resolve_exact_replay_support_boundary(manifest: RunManifest) -> str:
    """Return the supported exact-replay boundary for one manifested run."""
    return _resolve_reproducibility_profile(manifest).exact_replay_support_boundary


def _resolve_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    """Return the canonical per-family replay contract for one manifested run."""
    execution_context = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _is_composite_execution_context(manifest: RunManifest) -> bool:
    """Return whether the manifest represents composite execution."""
    execution_context = str(manifest.launch_context.get("execution_context") or "")
    return execution_context == "composite" or manifest.provider == "composite"


def _resolve_reproducibility_profile(manifest: RunManifest):
    """Resolve the canonical reproducibility profile for one manifested run."""
    execution_context = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _build_replay_parentage(manifest: RunManifest) -> dict[str, object]:
    """Return explicit replay ancestry for one manifested run."""
    replay_of_run_id = manifest.replay_of_run_id
    replay_of_manifest_id = manifest.replay_of_manifest_id
    return {
        "is_exact_replay": (
            replay_of_run_id is not None or replay_of_manifest_id is not None
        ),
        "replay_of_run_id": replay_of_run_id,
        "replay_of_manifest_id": replay_of_manifest_id,
    }


def _build_resume_contract(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
) -> dict[str, object]:
    """Return the published checkpoint/resume contract for one manifested run."""
    requested_policy = _resolve_requested_checkpoint_compatibility_policy(manifest)
    applied_policy = (
        "hard_fail" if requested_exact_replay else requested_policy or "observe"
    )
    is_composite = _is_composite_execution_context(manifest)
    execution_context = "composite" if is_composite else "ordinary"
    return {
        "resume_requested": resume_requested,
        "requested_exact_replay": requested_exact_replay,
        "requested_checkpoint_compatibility_policy": requested_policy,
        "applied_checkpoint_compatibility_policy": applied_policy,
        "strict_replay_safe": applied_policy == "hard_fail",
        "execution_context": execution_context,
        "resume_mode": (
            "checkpoint_snapshot_plus_ledger_suffix"
            if is_composite
            else "checkpoint_snapshot_only"
        ),
        "semantic_identity_anchor": "execution_fingerprint",
        "occurrence_identity_anchor": (
            "composite_run_identity" if is_composite else None
        ),
    }


def _resolve_requested_checkpoint_compatibility_policy(
    manifest: RunManifest,
) -> str | None:
    """Resolve requested checkpoint compatibility policy from manifest context."""
    candidates = (
        manifest.launch_context.get("checkpoint_compatibility_policy"),
        _lookup_mapping_path(
            manifest.runtime_config,
            "pipeline",
            "control_plane",
            "checkpoint_compatibility_policy",
        ),
        _lookup_mapping_path(
            manifest.runtime_config,
            "control_plane",
            "checkpoint_compatibility_policy",
        ),
        _lookup_mapping_path(
            manifest.runtime_config,
            "checkpoint_compatibility_policy",
        ),
    )
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip().lower()
            if normalized in {"observe", "soft_fail", "hard_fail"}:
                return normalized
    return None


def _lookup_mapping_path(
    mapping: Mapping[str, object],
    *path: str,
) -> object | None:
    """Read one nested mapping path using only mapping-shaped objects."""
    current: object = mapping
    for component in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(component)
    return current


def _collect_input_snapshot_refs(manifest: RunManifest) -> list[dict[str, object]]:
    """Return deterministic flattened snapshot provenance extracted from source refs."""
    refs: list[dict[str, object]] = []
    for source_ref in manifest.source_refs:
        for snapshot in source_ref.input_snapshots:
            refs.append(
                {
                    "provider": source_ref.provider,
                    "entity": source_ref.entity,
                    "pipeline_name": source_ref.pipeline_name,
                    "query": source_ref.query,
                    "snapshot_id": snapshot.snapshot_id,
                    "content_hash": snapshot.content_hash,
                    "immutable_uri": snapshot.immutable_uri,
                    "query_fingerprint": snapshot.query_fingerprint,
                    "etag": snapshot.etag,
                    "last_modified": snapshot.last_modified,
                    "captured_at": snapshot.captured_at.isoformat()
                    if snapshot.captured_at is not None
                    else None,
                }
            )
    refs.sort(
        key=lambda item: (
            str(item.get("provider") or ""),
            str(item.get("entity") or ""),
            str(item.get("pipeline_name") or ""),
            str(item.get("snapshot_id") or ""),
        )
    )
    return refs


def _collect_input_snapshot_ids(input_snapshots: list[dict[str, object]]) -> list[str]:
    """Return deterministic snapshot identities for resume/exact-replay anchors."""
    return [
        str(snapshot_id)
        for snapshot_id in (snapshot.get("snapshot_id") for snapshot in input_snapshots)
        if snapshot_id is not None
    ]


def _collect_input_snapshot_content_hashes(
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Return deterministic snapshot content hashes for operator inspection."""
    return [
        str(content_hash)
        for content_hash in (
            snapshot.get("content_hash") for snapshot in input_snapshots
        )
        if content_hash is not None
    ]


def _compute_input_snapshot_identity_fingerprint(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Compute the same stable replay-anchor fingerprint shape used by checkpoints."""
    snapshot_ids = _collect_input_snapshot_ids(input_snapshots)
    if not snapshot_ids:
        return None
    encoded = serialize_json_canonical(snapshot_ids)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
