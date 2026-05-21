"""Application service for immutable run-manifest creation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from bioetl.application.services.control_plane._manifest_time_support import (
    ManifestClock,
    resolve_manifest_created_at,
)
from bioetl.application.services.control_plane._run_manifest_service_mixins import (
    RunManifestHydrationMixin,
    RunManifestPayloadMixin,
)
from bioetl.application.services.control_plane.run_manifest_models import (
    RunManifestCreateSpec,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.control_plane.run_manifest import (
    DOCUMENTED_SOURCE_REVISION_STATES,
)
from bioetl.domain.normalization import (
    compute_execution_identity_fingerprint,
    normalize_run_manifest_spec,
)
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunType

__all__ = [
    "RunManifestCreateSpec",
    "RunManifestService",
]


def _validate_strict_code_provenance(
    request: RunManifestCreateSpec,
    code_provenance: RunCodeProvenance,
) -> None:
    """Fail closed when strict replay contexts cannot pin code revision."""
    required_profile = str(
        request.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    strict_context = (
        bool(request.launch_context.get("exact_replay"))
        or required_profile in STRICT_PERSISTENCE_PROFILES
    )
    if not strict_context:
        return
    if not code_provenance.git_commit:
        raise RuntimeError(
            "Run manifest requires git_commit code provenance for exact "
            "replay, replay_ready, and forensic_grade contexts"
        )
    if str(code_provenance.source_revision_state or "").strip().lower() != "clean":
        raise RuntimeError(
            "Run manifest requires clean source_revision_state for exact "
            "replay, replay_ready, and forensic_grade contexts"
        )
    if not code_provenance.dependency_lock_hash:
        raise RuntimeError(
            "Run manifest requires dependency_lock_hash code provenance for "
            "exact replay, replay_ready, and forensic_grade contexts"
        )


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
    if not code_provenance.git_commit and state not in {
        "git_unavailable",
        "dirty_state_unknown",
    }:
        raise RuntimeError(
            "Run manifest cannot persist missing git_commit unless "
            "source_revision_state is git_unavailable or dirty_state_unknown"
        )
    if code_provenance.git_commit and state == "git_unavailable":
        raise RuntimeError(
            "Run manifest cannot persist source_revision_state=git_unavailable "
            "when git_commit is present"
        )


def _validate_strict_input_snapshots(request: RunManifestCreateSpec) -> None:
    """Fail closed when strict replay contexts lack immutable input snapshots."""
    required_profile = str(
        request.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    )
    strict_context = (
        bool(request.launch_context.get("exact_replay"))
        or required_profile in STRICT_PERSISTENCE_PROFILES
    )
    if not strict_context:
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


@dataclass(slots=True)
class RunManifestService(
    RunManifestHydrationMixin,
    RunManifestPayloadMixin,
):
    """Create and persist immutable run manifests."""

    manifest_port: RunManifestPort
    clock: ManifestClock | None = None
    created_at_factory: Callable[[], datetime] | None = None
    schema_version: str = "1.0"
    _manifest_id_factory: Callable[[], str] = field(
        default_factory=lambda: lambda: str(uuid4())
    )

    def _normalize_run_type(self, run_type: RunType | str) -> RunType:
        """Return the normalized runtime run type enum."""
        return run_type if isinstance(run_type, RunType) else RunType(str(run_type))

    def _build_code_provenance(
        self,
        request: RunManifestCreateSpec,
    ) -> RunCodeProvenance:
        """Build code provenance from the manifest request."""
        return RunCodeProvenance(
            pipeline_version=request.pipeline_version,
            git_commit=request.git_commit,
            source_revision_state=request.source_revision_state,
            dependency_lock_hash=request.dependency_lock_hash,
            config_hash=request.config_hash,
            resolved_config_hash=request.resolved_config_hash,
            effective_config_hash=request.effective_config_hash,
            source_fingerprint=request.source_fingerprint,
            contract_ref=request.contract_ref,
            contract_version=request.contract_version,
            contract_schema_hash=request.contract_schema_hash,
            dq_policy_ref=request.dq_policy_ref,
            rule_bundle_version=request.rule_bundle_version,
            normalization_profile_ref=request.normalization_profile_ref,
            normalization_profile_version=request.normalization_profile_version,
            normalization_profile_hash=request.normalization_profile_hash,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        )

    def _resolve_created_at(self) -> datetime:
        """Resolve manifest creation time through the configured seam."""
        return resolve_manifest_created_at(
            clock=self.clock,
            created_at_factory=self.created_at_factory,
        )

    def create_manifest(self, request: RunManifestCreateSpec) -> RunManifest:
        """Build fingerprinted manifest and persist it through the port."""
        created_at = self._resolve_created_at()
        normalized_run_type = self._normalize_run_type(request.run_type)
        code_provenance = self._build_code_provenance(request)
        _validate_strict_code_provenance(request, code_provenance)
        _validate_documented_code_provenance(code_provenance)
        _validate_exact_replay_snapshot_claim(request)
        _validate_strict_input_snapshots(request)
        normalized_payload = normalize_run_manifest_spec(
            self._build_manifest_payload(
                request=request,
                code_provenance=code_provenance,
                run_type=normalized_run_type,
            )
        )
        manifest = self._build_manifest(
            request=request,
            run_type=normalized_run_type,
            created_at=created_at,
            normalized_payload=normalized_payload,
            fingerprint=self._compute_execution_fingerprint(
                payload=self._build_execution_identity_payload(
                    request=request,
                    code_provenance=code_provenance,
                    run_type=normalized_run_type,
                )
            ),
        )
        self.manifest_port.save(manifest)
        self._assert_manifest_persisted(manifest)
        return manifest

    def _assert_manifest_persisted(self, manifest: RunManifest) -> None:
        """Fail closed when a persisted manifest cannot be reconstructed."""
        persisted_by_manifest_id = self.manifest_port.get(manifest.manifest_id)
        if persisted_by_manifest_id is None:
            raise RuntimeError(
                "Run manifest persistence failed: manifest is not resolvable by manifest_id"
            )
        if persisted_by_manifest_id.run_id != manifest.run_id:
            raise RuntimeError(
                "Run manifest persistence failed: persisted manifest run_id does not match the requested run_id"
            )
        persisted_by_run_id = self.manifest_port.get_by_run_id(manifest.run_id)
        if persisted_by_run_id is None:
            raise RuntimeError(
                "Run manifest persistence failed: manifest is not resolvable by run_id"
            )
        if persisted_by_run_id.manifest_id != manifest.manifest_id:
            raise RuntimeError(
                "Run manifest persistence failed: run_id resolves to a different manifest_id"
            )

    def _compute_execution_fingerprint(self, *, payload: dict[str, object]) -> str:
        """Compute the canonical execution-identity fingerprint contract."""
        return compute_execution_identity_fingerprint(payload)
