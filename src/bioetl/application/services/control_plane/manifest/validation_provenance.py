"""Code-provenance validation helpers for immutable run-manifest creation."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.models import (
    RunManifestCreateSpec,
)
from bioetl.domain.control_plane import RunCodeProvenance
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.control_plane.run_manifest import (
    DOCUMENTED_SOURCE_REVISION_STATES,
    validate_production_provenance,
)

__all__ = [
    "_format_strict_code_provenance_profile_context",
    "_validate_canonical_config_identity",
    "_validate_documented_code_provenance",
    "_validate_executable_code_provenance",
    "_validate_production_provenance_gate",
]


def _validate_production_provenance_gate(
    request: RunManifestCreateSpec,
    code_provenance: RunCodeProvenance,
) -> None:
    """Fail closed when production runs omit the required provenance set."""
    launch = request.launch_context if isinstance(request.launch_context, dict) else {}
    env = str(launch.get("env") or launch.get("environment") or "").strip().lower()
    execution_context = str(launch.get("execution_context") or "").strip().lower()
    is_production = env in {"prod", "production"} or execution_context == "production"
    # Also treat forensic_grade / replay_ready as production-grade evidence paths.
    required_profile = (
        str(launch.get("required_persistence_profile") or "").strip().lower()
    )
    is_production = is_production or required_profile in {
        "forensic_grade",
        "replay_ready",
        "production",
    }
    try:
        validate_production_provenance(code_provenance, production=is_production)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc


def _validate_executable_code_provenance(
    request: RunManifestCreateSpec,
    code_provenance: RunCodeProvenance,
) -> None:
    """Fail closed when executable runs cannot pin code and dependency state."""
    required_profile = normalize_required_persistence_profile(
        request.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    strict_code_provenance_required = (
        bool(request.launch_context.get("exact_replay"))
        or required_profile in STRICT_PERSISTENCE_PROFILES
    )
    if not str(code_provenance.git_commit or "").strip():
        raise RuntimeError(
            "Run manifest requires git_commit code provenance for every "
            "executable run manifest"
        )
    if (
        strict_code_provenance_required
        and str(code_provenance.source_revision_state or "").strip().lower() != "clean"
    ):
        profile_context = _format_strict_code_provenance_profile_context(request)
        raise RuntimeError(
            "Run manifest requires clean source_revision_state for exact "
            "replay, replay_ready, and forensic_grade contexts"
            f" ({profile_context})"
        )
    if not str(code_provenance.dependency_lock_hash or "").strip():
        raise RuntimeError(
            "Run manifest requires dependency_lock_hash code provenance for "
            "every executable run manifest"
        )


def _validate_canonical_config_identity(
    code_provenance: RunCodeProvenance,
) -> None:
    """Require explicit config identity anchors instead of legacy alias fallback."""
    if not str(code_provenance.resolved_config_hash or "").strip():
        raise RuntimeError(
            "Run manifest requires resolved_config_hash as a canonical config "
            "identity anchor; legacy config_hash is compatibility-only"
        )
    if not str(code_provenance.effective_config_hash or "").strip():
        raise RuntimeError(
            "Run manifest requires effective_config_hash as the replay identity "
            "config anchor; legacy config_hash is compatibility-only"
        )


def _format_strict_code_provenance_profile_context(
    request: RunManifestCreateSpec,
) -> str:
    """Return operator-facing profile context for strict dirty-source failures."""
    raw_required_profile = (
        request.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    required_profile = normalize_required_persistence_profile(raw_required_profile)
    configured_profile = normalize_required_persistence_profile(
        request.launch_context.get("configured_required_persistence_profile")
        or raw_required_profile
    )
    fields = [
        f"pipeline={request.pipeline_name}",
        f"configured_required_persistence_profile={configured_profile}",
        f"required_persistence_profile={required_profile}",
    ]
    if configured_profile != required_profile:
        fields.append("profile_was_promoted=true")
    return ", ".join(fields)


def _validate_documented_code_provenance(
    code_provenance: RunCodeProvenance,
) -> None:
    """Reject undocumented or internally inconsistent code provenance states."""
    state = str(code_provenance.source_revision_state or "").strip().lower()
    if not state or state not in DOCUMENTED_SOURCE_REVISION_STATES:
        raise RuntimeError(
            "Run manifest requires a documented source_revision_state "
            f"(allowed: {sorted(DOCUMENTED_SOURCE_REVISION_STATES)})"
        )
    if code_provenance.git_commit and state == "git_unavailable":
        raise RuntimeError(
            "Run manifest cannot persist source_revision_state=git_unavailable "
            "when git_commit is present"
        )
