"""Helper functions for replay diagnostics.

Extracted from _run_manifest_diagnostics_replay.py to meet file size limits.
"""

from __future__ import annotations

from bioetl.application.services.control_plane._historical_replay_certification import (
    HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_snapshot_support import (
    lookup_mapping_path,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    ReproducibilityPolicyAssessment,
    normalize_required_persistence_profile,
)


def _has_partial_input_snapshot_envelope(snapshot_envelope: object) -> bool:
    any_snapshots = bool(getattr(snapshot_envelope, "any_input_snapshots", False))
    full_envelope = bool(getattr(snapshot_envelope, "full_snapshot_envelope", False))
    return any_snapshots and not full_envelope


def _resolve_exact_replay_supported_reason(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    snapshot_envelope: object,
) -> str | None:
    if manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return None
    if not bool(getattr(snapshot_envelope, "full_snapshot_envelope", False)):
        return None
    if _has_live_capture_materialized_snapshots(input_snapshots):
        return "materialized_live_capture_snapshot_envelope_present"
    return "full_immutable_input_snapshot_envelope_present"


def _requires_resume_without_snapshot_reason(
    *,
    manifest: RunManifest,
    resume_requested: bool,
) -> bool:
    return (
        manifest.replay_capability == ReplayCapability.RESUME_ONLY or resume_requested
    )


def _has_historical_composite_certified_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    """Return whether ledger/manifest snapshots carry composite certification."""
    return any(
        _resolve_snapshot_materialization_mode(snapshot)
        == HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED
        for snapshot in input_snapshots
    )


def _has_historical_source_certified_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    """Return whether ledger/manifest snapshots carry source certification."""
    return any(
        _resolve_snapshot_materialization_mode(snapshot)
        == HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED
        for snapshot in input_snapshots
    )


def _has_live_capture_materialized_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    """Return whether ledger/manifest snapshots were materialized post-launch."""
    return any(
        _resolve_snapshot_materialization_mode(snapshot)
        == LIVE_CAPTURE_SNAPSHOT_MATERIALIZED
        for snapshot in input_snapshots
    )


def _resolve_snapshot_materialization_mode(snapshot: dict[str, object]) -> str | None:
    """Read the canonical snapshot promotion/materialization marker.

    Historical fixtures used `certification`; current ledger-derived projections
    populate `materialization_mode`. Accept both to keep diagnostics backward
    compatible.
    """
    for field_name in ("materialization_mode", "certification"):
        value = snapshot.get(field_name)
        text = str(value or "").strip()
        if text:
            return text
    return None


def _is_full_scan_idempotent_rebuild(manifest: RunManifest) -> bool:
    if manifest.launch_context.get("full_scan_idempotent_rebuild", False):
        return True
    candidates = (
        manifest.runtime_config.get("loading_strategy"),
        lookup_mapping_path(manifest.runtime_config, "pipeline", "loading_strategy"),
        manifest.resolved_config.get("loading_strategy"),
        lookup_mapping_path(manifest.resolved_config, "pipeline", "loading_strategy"),
    )
    return any(
        str(candidate or "").strip().lower() == "full_scan_only"
        for candidate in candidates
    )


def _is_composite_execution_context(manifest: RunManifest) -> bool:
    return manifest.launch_context.get("execution_context") == "composite"


def _collect_append_mode_semantic_sinks(manifest: RunManifest) -> list[str]:
    normalized = _normalize_declared_append_mode_sinks(
        manifest.launch_context.get("append_mode_semantic_sinks")
    )
    if normalized:
        return normalized
    return sorted(_derive_append_mode_semantic_sinks_from_manifest(manifest))


def _derive_append_mode_semantic_sinks_from_manifest(manifest: RunManifest) -> set[str]:
    """Derive append mode semantic sinks from runtime and resolved configs."""
    derived: set[str] = set()
    for config in (manifest.runtime_config, manifest.resolved_config):
        derived.update(_derive_append_mode_sinks_from_config(config))
    return derived


def _normalize_declared_append_mode_sinks(raw_sinks: object) -> list[str]:
    if not isinstance(raw_sinks, list):
        return []
    return [
        str(sink).strip()
        for sink in raw_sinks
        if isinstance(sink, str) and str(sink).strip()
    ]


def _derive_append_mode_sinks_from_config(config: dict[str, object]) -> set[str]:
    sink_config = lookup_mapping_path(config, "sink")
    if not isinstance(sink_config, dict):
        return set()
    return {
        f"sink.{sink_name}.mode=append"
        for sink_name, sink_settings in sink_config.items()
        if _is_append_enabled_sink(sink_name, sink_settings)
    }


def _is_append_enabled_sink(sink_name: object, sink_settings: object) -> bool:
    if not isinstance(sink_name, str) or not isinstance(sink_settings, dict):
        return False
    mode = str(sink_settings.get("mode") or "").strip().lower()
    enabled = sink_settings.get("enabled")
    return mode == "append" and enabled is not False


def _profile_exact_replay_blockers(profile: object) -> list[str]:
    if getattr(profile, "strict_exact_replay_supported", False):
        return []
    return ["family_outside_supported_exact_replay_boundary"]


def _append_mode_exact_replay_blockers(append_mode_sinks: list[str]) -> list[str]:
    if not append_mode_sinks:
        return []
    return ["append_mode_semantic_outputs"]


def _snapshot_exact_replay_blockers(
    *,
    manifest: RunManifest,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> list[str]:
    snapshot_envelope = policy_assessment.snapshot_envelope
    if not getattr(snapshot_envelope, "any_input_snapshots", False):
        return ["immutable_input_snapshots_missing"]
    if not getattr(snapshot_envelope, "full_snapshot_envelope", False):
        return [
            "partial_input_snapshot_envelope",
            *(
                f"input_snapshot_missing:{source_ref}"
                for source_ref in getattr(
                    snapshot_envelope, "missing_snapshot_source_refs", []
                )
            ),
        ]
    if manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return ["exact_replay_capability_unavailable"]
    return []


def _dependency_lock_exact_replay_blockers(
    *,
    manifest: RunManifest,
    profile: object,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> list[str]:
    if not _requires_dependency_lock_provenance(
        manifest=manifest,
        profile=profile,
        policy_assessment=policy_assessment,
    ):
        return []
    return ["dependency_lock_provenance_missing"]


def _requires_dependency_lock_provenance(
    *,
    manifest: RunManifest,
    profile: object,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> bool:
    if not getattr(profile, "strict_exact_replay_supported", False):
        return False
    if (
        not getattr(policy_assessment, "strict_requirement_requested", False)
        and manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        return False
    return not manifest.code_provenance.dependency_lock_hash


def _resolve_required_persistence_profile(manifest: RunManifest) -> str:
    """Resolve the declared minimum persistence profile from manifest context."""
    candidates = (
        manifest.launch_context.get("required_persistence_profile"),
        lookup_mapping_path(
            manifest.runtime_config,
            "pipeline",
            "control_plane",
            "required_persistence_profile",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "control_plane",
            "required_persistence_profile",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "required_persistence_profile",
        ),
    )
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = normalize_required_persistence_profile(candidate).lower()
            if normalized in {
                DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
                *STRICT_PERSISTENCE_PROFILES,
            }:
                return normalized
    return DEFAULT_REQUIRED_PERSISTENCE_PROFILE


def _resolve_applied_checkpoint_compatibility_policy(
    *,
    requested_exact_replay: bool,
    requested_policy: str | None,
    required_persistence_profile: str,
) -> str:
    """Resolve the effective checkpoint policy shown in diagnostics."""
    if requested_exact_replay:
        return "hard_fail"
    if required_persistence_profile in STRICT_PERSISTENCE_PROFILES:
        return "hard_fail" if requested_policy != "hard_fail" else requested_policy
    return requested_policy or "observe"


def _resolve_requested_checkpoint_compatibility_policy(
    manifest: RunManifest,
) -> str | None:
    """Resolve requested checkpoint compatibility policy from manifest context."""
    candidates = (
        manifest.launch_context.get("checkpoint_compatibility_policy"),
        lookup_mapping_path(
            manifest.runtime_config,
            "pipeline",
            "control_plane",
            "checkpoint_compatibility_policy",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "control_plane",
            "checkpoint_compatibility_policy",
        ),
        lookup_mapping_path(
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


__all__ = [
    "_append_mode_exact_replay_blockers",
    "_collect_append_mode_semantic_sinks",
    "_dependency_lock_exact_replay_blockers",
    "_has_historical_composite_certified_snapshots",
    "_has_historical_source_certified_snapshots",
    "_has_live_capture_materialized_snapshots",
    "_has_partial_input_snapshot_envelope",
    "_is_composite_execution_context",
    "_is_full_scan_idempotent_rebuild",
    "_profile_exact_replay_blockers",
    "_requires_dependency_lock_provenance",
    "_requires_resume_without_snapshot_reason",
    "_resolve_applied_checkpoint_compatibility_policy",
    "_resolve_exact_replay_supported_reason",
    "_resolve_requested_checkpoint_compatibility_policy",
    "_resolve_required_persistence_profile",
    "_snapshot_exact_replay_blockers",
]
