"""Replay-blocker invariants for manifest diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.nested_mapping import (
    lookup_mapping_path,
)
from bioetl.application.services.control_plane.run_manifest_exact_replay_blockers import (
    append_mode_exact_replay_blockers as _append_mode_exact_replay_blockers,
    dependency_lock_exact_replay_blockers as _dependency_lock_exact_replay_blockers,
    profile_exact_replay_blockers as _profile_exact_replay_blockers,
    snapshot_exact_replay_blockers as _snapshot_exact_replay_blockers,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        ReplayFamilyContext,
    )


def _requires_resume_without_snapshot_reason(
    *,
    manifest: RunManifest,
    resume_requested: bool,
) -> bool:
    return (
        manifest.replay_capability == ReplayCapability.RESUME_ONLY or resume_requested
    )


def _collect_append_mode_semantic_sinks(manifest: RunManifest) -> list[str]:
    normalized = _normalize_declared_append_mode_sinks(
        manifest.launch_context.get("append_mode_semantic_sinks")
    )
    if normalized:
        return normalized
    return sorted(_derive_append_mode_semantic_sinks_from_manifest(manifest))


def _normalize_declared_append_mode_sinks(raw_sinks: object) -> list[str]:
    if not isinstance(raw_sinks, list):
        return []
    return [
        str(sink).strip()
        for sink in raw_sinks
        if isinstance(sink, str) and str(sink).strip()
    ]


def _derive_append_mode_semantic_sinks_from_manifest(manifest: RunManifest) -> set[str]:
    derived: set[str] = set()
    for config in (manifest.runtime_config, manifest.resolved_config):
        derived.update(_derive_append_mode_sinks_from_config(config))
    return derived


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


def _resolve_exact_replay_blockers(
    *,
    manifest: RunManifest,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
) -> list[str]:
    profile = replay_family_context.profile
    append_mode_sinks = _collect_append_mode_semantic_sinks(manifest)
    return [
        *_profile_exact_replay_blockers(profile),
        *_append_mode_exact_replay_blockers(append_mode_sinks),
        *_snapshot_exact_replay_blockers(
            manifest=manifest,
            policy_assessment=policy_assessment,
        ),
        *_dependency_lock_exact_replay_blockers(
            manifest=manifest,
            profile=profile,
            policy_assessment=policy_assessment,
        ),
    ]


__all__ = [
    "_collect_append_mode_semantic_sinks",
    "_requires_resume_without_snapshot_reason",
    "_resolve_exact_replay_blockers",
]
