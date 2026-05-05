"""Application service for immutable run-manifest creation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from bioetl.application.services.control_plane._run_manifest_service_mixins import (
    RunManifestHydrationMixin,
    RunManifestPayloadMixin,
)
from bioetl.application.services.control_plane.run_manifest_models import (
    RunManifestCreateSpec,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
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


class _ClockLike(Protocol):
    """Local clock seam to keep strict mypy stable under skipped imports."""

    def now(self) -> datetime:
        """Return the current timestamp."""
        ...


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


@dataclass(slots=True)
class RunManifestService(
    RunManifestHydrationMixin,
    RunManifestPayloadMixin,
):
    """Create and persist immutable run manifests."""

    manifest_port: RunManifestPort
    clock: _ClockLike | None = None
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
            contract_ref=request.contract_ref,
            contract_version=request.contract_version,
            contract_schema_hash=request.contract_schema_hash,
            dq_policy_ref=request.dq_policy_ref,
            rule_bundle_version=request.rule_bundle_version,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        )

    def _resolve_created_at(self) -> datetime:
        """Resolve manifest creation time through the configured seam."""
        if self.clock is not None:
            return self.clock.now()
        if self.created_at_factory is not None:
            return self.created_at_factory()
        return MISSING_RUNTIME_TIMESTAMP

    def create_manifest(self, request: RunManifestCreateSpec) -> RunManifest:
        """Build fingerprinted manifest and persist it through the port."""
        created_at = self._resolve_created_at()
        normalized_run_type = self._normalize_run_type(request.run_type)
        code_provenance = self._build_code_provenance(request)
        _validate_strict_code_provenance(request, code_provenance)
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
