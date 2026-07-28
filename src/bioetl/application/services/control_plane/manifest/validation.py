"""Validation policy helpers for immutable run-manifest creation."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.models import (
    RunManifestCreateSpec,
)
from bioetl.application.services.control_plane.manifest.validation_provenance import (
    _validate_canonical_config_identity,
    _validate_documented_code_provenance,
    _validate_executable_code_provenance,
    _validate_production_provenance_gate,
)
from bioetl.domain.control_plane import ReplayCapability, RunCodeProvenance
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)

__all__ = ["validate_run_manifest_request"]


def validate_run_manifest_request(
    request: RunManifestCreateSpec,
    code_provenance: RunCodeProvenance,
) -> None:
    """Validate control-plane replay, snapshot, and code-provenance policy."""
    _validate_documented_code_provenance(code_provenance)
    _validate_canonical_config_identity(code_provenance)
    _validate_replay_capable_profile_floor(request)
    _validate_exact_replay_snapshot_claim(request)
    _validate_strict_input_snapshots(request)
    _validate_strict_replay_provenance(request, code_provenance)
    _validate_executable_code_provenance(request, code_provenance)
    _validate_production_provenance_gate(request, code_provenance)


def _validate_strict_input_snapshots(request: RunManifestCreateSpec) -> None:
    """Fail closed when strict replay contexts lack immutable input snapshots."""
    if not _is_strict_replay_context(request):
        return
    launch_time_snapshot_envelope_present = bool(request.source_refs) and all(
        source_ref.input_snapshots for source_ref in request.source_refs
    )
    if launch_time_snapshot_envelope_present:
        return
    raise RuntimeError(
        "Run manifest requires immutable input snapshots for exact "
        "replay, replay_ready, and forensic_grade contexts"
    )


def _is_strict_replay_context(request: RunManifestCreateSpec) -> bool:
    """Return whether manifest construction must satisfy strict replay invariants."""
    required_profile = str(
        request.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    normalized_profile = normalize_required_persistence_profile(required_profile)
    return (
        bool(request.launch_context.get("exact_replay"))
        or normalized_profile in STRICT_PERSISTENCE_PROFILES
    )


def _validate_strict_replay_provenance(
    request: RunManifestCreateSpec,
    code_provenance: RunCodeProvenance,
) -> None:
    """Require canonical provenance anchors before strict manifest persistence."""
    if not _is_strict_replay_context(request):
        return
    missing_fields = [
        field_name
        for field_name in (
            "contract_ref",
            "contract_version",
            "contract_schema_hash",
            "dq_policy_ref",
            "rule_bundle_version",
            "effective_config_artifact_id",
        )
        if not str(getattr(code_provenance, field_name) or "").strip()
    ]
    if missing_fields:
        raise RuntimeError(
            "Run manifest strict replay construction requires complete "
            "contract, DQ policy, and effective config provenance "
            f"(missing: {', '.join(missing_fields)})"
        )
    if not request.planned_artifacts:
        raise RuntimeError(
            "Run manifest strict replay construction requires planned_artifacts"
        )


def _validate_exact_replay_snapshot_claim(request: RunManifestCreateSpec) -> None:
    """Reject exact-replay capability claims without immutable input evidence."""
    if request.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return
    if not request.source_refs or any(
        not source_ref.input_snapshots for source_ref in request.source_refs
    ):
        raise RuntimeError(
            "Run manifest cannot claim exact_replay_supported without an "
            "immutable input snapshot envelope"
        )


def _validate_replay_capable_profile_floor(request: RunManifestCreateSpec) -> None:
    """Reject non-diagnostic opt-downs below replay-capable family floors."""
    configured_profile = normalize_required_persistence_profile(
        request.launch_context.get("required_persistence_profile")
    )
    if configured_profile != "degraded_observable":
        return
    execution_context = str(
        request.launch_context.get("execution_context") or "source"
    ).strip()
    profile = resolve_reproducibility_family_profile(
        provider=request.provider,
        entity=request.entity,
        contract_ref=request.contract_ref,
        execution_context=(
            "composite" if execution_context == "composite" else "source"
        ),
    )
    if (
        profile.strict_exact_replay_supported
        and profile.default_required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    ):
        if _is_explicit_degraded_profile_opt_down(request):
            return
        raise RuntimeError(
            "Run manifest cannot persist required_persistence_profile="
            "'degraded_observable' for replay-capable executable families; "
            "promote the run to the published strict persistence floor or fail closed"
        )


def _is_explicit_degraded_profile_opt_down(request: RunManifestCreateSpec) -> bool:
    """Return whether a local non-strict run explicitly opted down to degraded."""
    if bool(request.launch_context.get("exact_replay")):
        return False
    if not bool(request.launch_context.get("required_persistence_profile_opt_down")):
        return False
    configured_profile = normalize_required_persistence_profile(
        request.launch_context.get("configured_required_persistence_profile")
        or request.launch_context.get("required_persistence_profile")
    )
    return configured_profile == "degraded_observable"
