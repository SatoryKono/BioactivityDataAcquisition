"""Application service for immutable run-manifest creation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType

__all__ = [
    "RunManifestCreateRequest",
    "RunManifestCreateSpec",
    "RunManifestService",
]


@dataclass(frozen=True, slots=True)
class RunManifestCreateSpec:
    """Normalized inputs required to build an immutable run manifest."""

    run_id: RunID
    run_type: RunType | str
    pipeline_name: str
    provider: str
    entity: str
    launch_context: dict[str, object]
    runtime_config: dict[str, object]
    resolved_config: dict[str, object]
    source_refs: tuple[RunSourceRef, ...] = ()
    planned_artifacts: tuple[RunArtifactRef, ...] = ()
    pipeline_version: str | None = None
    git_commit: str | None = None
    config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None


@dataclass(slots=True)
class RunManifestService:
    """Create and persist immutable run manifests."""

    manifest_port: RunManifestPort
    schema_version: str = "1.0"
    _manifest_id_factory: Callable[[], str] = field(
        default_factory=lambda: lambda: str(uuid4())
    )

    def create_manifest(self, request: RunManifestCreateSpec) -> RunManifest:
        """Build fingerprinted manifest and persist it through the port."""
        created_at = datetime.now(UTC)
        normalized_run_type = (
            request.run_type
            if isinstance(request.run_type, RunType)
            else RunType(str(request.run_type))
        )
        code_provenance = RunCodeProvenance(
            pipeline_version=request.pipeline_version,
            git_commit=request.git_commit,
            config_hash=request.config_hash,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        )
        fingerprint = self._compute_execution_fingerprint(
            request=request,
            code_provenance=code_provenance,
            run_type=normalized_run_type,
        )
        manifest = RunManifest(
            manifest_id=self._manifest_id_factory(),
            execution_fingerprint=fingerprint,
            schema_version=self.schema_version,
            created_at=created_at,
            run_id=request.run_id,
            run_type=normalized_run_type,
            pipeline_name=request.pipeline_name,
            provider=request.provider,
            entity=request.entity,
            launch_context=request.launch_context,
            runtime_config=request.runtime_config,
            resolved_config=request.resolved_config,
            code_provenance=code_provenance,
            source_refs=request.source_refs,
            planned_artifacts=request.planned_artifacts,
        )
        self.manifest_port.save(manifest)
        return manifest

    def _compute_execution_fingerprint(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> str:
        """Compute a deterministic fingerprint for replay/equivalence checks."""
        payload = {
            "schema_version": self.schema_version,
            "run_type": str(run_type.value),
            "pipeline_name": request.pipeline_name,
            "provider": request.provider,
            "entity": request.entity,
            "launch_context": request.launch_context,
            "runtime_config": request.runtime_config,
            "resolved_config": request.resolved_config,
            "code_provenance": {
                "pipeline_version": code_provenance.pipeline_version,
                "git_commit": code_provenance.git_commit,
                "config_hash": code_provenance.config_hash,
                "dq_contract_compatibility_hash": code_provenance.dq_contract_compatibility_hash,
                "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
            },
            "source_refs": [
                {
                    "provider": item.provider,
                    "entity": item.entity,
                    "pipeline_name": item.pipeline_name,
                    "query": item.query,
                }
                for item in request.source_refs
            ],
            "planned_artifacts": [
                {"layer": item.layer, "path": item.path}
                for item in request.planned_artifacts
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


RunManifestCreateRequest = RunManifestCreateSpec
