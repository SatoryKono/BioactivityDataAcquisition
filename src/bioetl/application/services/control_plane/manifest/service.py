"""Application service for immutable run-manifest creation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from bioetl.application.services.control_plane.manifest._service_support import (
    RunManifestHydrationMixin,
    RunManifestPayloadMixin,
)
from bioetl.application.services.control_plane.manifest.models import (
    RunManifestCreateSpec,
)
from bioetl.application.services.control_plane.manifest.service_scaffold import (
    ManifestServiceScaffoldMixin,
)
from bioetl.application.services.control_plane.manifest.validation import (
    validate_run_manifest_request,
)
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
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


@runtime_checkable
class _RunManifestSaveAssertionPort(Protocol):
    """Optional fast post-save persistence assertion for concrete stores."""

    def assert_saved(self, manifest: RunManifest) -> None:
        """Raise if the just-saved manifest is not durably materialized."""
        ...


@dataclass(slots=True, kw_only=True)
class RunManifestService(
    ManifestServiceScaffoldMixin,
    RunManifestHydrationMixin,
    RunManifestPayloadMixin,
):
    """Create and persist immutable run manifests."""

    manifest_port: RunManifestPort

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

    def create_manifest(self, request: RunManifestCreateSpec) -> RunManifest:
        """Build fingerprinted manifest and persist it through the port."""
        created_at = self._resolve_created_at()
        normalized_run_type = self._normalize_run_type(request.run_type)
        code_provenance = self._build_code_provenance(request)
        validate_run_manifest_request(request, code_provenance)
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
        if isinstance(self.manifest_port, _RunManifestSaveAssertionPort):
            self.manifest_port.assert_saved(manifest)
            return
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
