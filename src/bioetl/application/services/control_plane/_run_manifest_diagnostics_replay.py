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
    if _collect_append_mode_semantic_sinks(manifest):
        return "append_mode_semantic_outputs_block_exact_replay"
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
    append_mode_sinks = _collect_append_mode_semantic_sinks(manifest)
    if (
        profile.strict_exact_replay_supported
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        and not append_mode_sinks
    ):
        return []
    blockers: list[str] = []
    if not profile.strict_exact_replay_supported:
        blockers.append("family_outside_supported_exact_replay_boundary")
    if append_mode_sinks:
        blockers.append("append_mode_semantic_outputs")
    if not input_snapshots:
        blockers.append("immutable_input_snapshots_missing")
    elif manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        blockers.append("exact_replay_capability_unavailable")
    return blockers


def _collect_append_mode_semantic_sinks(manifest: RunManifest) -> list[str]:
    """Return enabled Silver/Gold sinks that use append mode."""
    blocked: set[str] = set()
    for payload in (manifest.runtime_config, manifest.resolved_config):
        for sink in _candidate_sink_mappings(payload):
            for layer_name in ("silver", "gold"):
                layer_config = sink.get(layer_name)
                if not isinstance(layer_config, Mapping):
                    continue
                if (
                    _sink_layer_enabled(layer_config)
                    and _sink_layer_mode(layer_config) == "append"
                ):
                    blocked.add(f"sink.{layer_name}.mode=append")
    return sorted(blocked)


def _candidate_sink_mappings(
    payload: Mapping[str, object],
) -> list[Mapping[str, object]]:
    """Return possible sink mappings from known config payload shapes."""
    candidates: list[Mapping[str, object]] = []
    direct_sink = payload.get("sink")
    if isinstance(direct_sink, Mapping):
        candidates.append(direct_sink)
    pipeline = payload.get("pipeline")
    if isinstance(pipeline, Mapping):
        nested_sink = pipeline.get("sink")
        if isinstance(nested_sink, Mapping):
            candidates.append(nested_sink)
    return candidates


def _sink_layer_enabled(layer_config: Mapping[str, object]) -> bool:
    return bool(layer_config.get("enabled", True))


def _sink_layer_mode(layer_config: Mapping[str, object]) -> str:
    return str(layer_config.get("mode") or "").strip().lower()


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
    profile = _resolve_reproducibility_profile(manifest)
    requested_policy = _resolve_requested_checkpoint_compatibility_policy(manifest)
    required_persistence_profile = _resolve_required_persistence_profile(manifest)
    applied_policy = _resolve_applied_checkpoint_compatibility_policy(
        requested_exact_replay=requested_exact_replay,
        requested_policy=requested_policy,
        required_persistence_profile=required_persistence_profile,
    )
    strict_replay_requested = requested_exact_replay or required_persistence_profile in {
        "replay_ready",
        "forensic_grade",
    }
    is_composite = _is_composite_execution_context(manifest)
    execution_context = "composite" if is_composite else "ordinary"
    return {
        "resume_requested": resume_requested,
        "requested_exact_replay": requested_exact_replay,
        "requested_checkpoint_compatibility_policy": requested_policy,
        "applied_checkpoint_compatibility_policy": applied_policy,
        "strict_replay_safe": (
            strict_replay_requested
            and applied_policy == "hard_fail"
            and profile.strict_exact_replay_supported
            and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        ),
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


def _resolve_required_persistence_profile(manifest: RunManifest) -> str:
    """Resolve the declared minimum persistence profile from manifest context."""
    candidates = (
        manifest.launch_context.get("required_persistence_profile"),
        _lookup_mapping_path(
            manifest.runtime_config,
            "pipeline",
            "control_plane",
            "required_persistence_profile",
        ),
        _lookup_mapping_path(
            manifest.runtime_config,
            "control_plane",
            "required_persistence_profile",
        ),
        _lookup_mapping_path(
            manifest.runtime_config,
            "required_persistence_profile",
        ),
    )
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip().lower()
            if normalized in {"degraded_observable", "replay_ready", "forensic_grade"}:
                return normalized
    return "degraded_observable"


def _resolve_applied_checkpoint_compatibility_policy(
    *,
    requested_exact_replay: bool,
    requested_policy: str | None,
    required_persistence_profile: str,
) -> str:
    """Resolve the effective checkpoint policy shown in diagnostics."""
    if requested_exact_replay:
        return "hard_fail"
    if required_persistence_profile in {"replay_ready", "forensic_grade"}:
        if requested_policy in {"observe", "legacy_observe"}:
            return "soft_fail"
        return requested_policy or "soft_fail"
    return requested_policy or "observe"


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
            if normalized in {"observe", "legacy_observe", "soft_fail", "hard_fail"}:
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
                    "storage_provider": snapshot.storage_provider,
                    "object_bucket": snapshot.object_bucket,
                    "object_key": snapshot.object_key,
                    "object_version_id": snapshot.object_version_id,
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
