"""Application service for immutable run-manifest creation."""

from __future__ import annotations

import hashlib
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
from bioetl.domain.normalization import (
    normalize_run_manifest_spec,
    serialize_json_canonical,
)
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType

__all__ = [
    "RunManifestCreateRequest",
    "RunManifestCreateSpec",
    "RunManifestService",
]


def _optional_payload_string(
    payload: dict[str, object],
    key: str,
) -> str | None:
    """Return a payload value as string when present."""
    value = payload.get(key)
    return None if value is None else str(value)


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
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
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
            config_hash=request.config_hash,
            contract_ref=request.contract_ref,
            contract_version=request.contract_version,
            contract_schema_hash=request.contract_schema_hash,
            dq_policy_ref=request.dq_policy_ref,
            rule_bundle_version=request.rule_bundle_version,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        )

    def _hydrate_code_provenance(
        self,
        payload: dict[str, object],
    ) -> RunCodeProvenance:
        """Rebuild typed code provenance from normalized payload data."""
        return RunCodeProvenance(
            pipeline_version=_optional_payload_string(payload, "pipeline_version"),
            git_commit=_optional_payload_string(payload, "git_commit"),
            config_hash=_optional_payload_string(payload, "config_hash"),
            contract_ref=_optional_payload_string(payload, "contract_ref"),
            contract_version=_optional_payload_string(payload, "contract_version"),
            contract_schema_hash=_optional_payload_string(
                payload,
                "contract_schema_hash",
            ),
            dq_policy_ref=_optional_payload_string(payload, "dq_policy_ref"),
            rule_bundle_version=_optional_payload_string(
                payload,
                "rule_bundle_version",
            ),
            dq_contract_compatibility_hash=_optional_payload_string(
                payload,
                "dq_contract_compatibility_hash",
            ),
            effective_config_artifact_id=_optional_payload_string(
                payload,
                "effective_config_artifact_id",
            ),
        )

    def _hydrate_source_refs(
        self,
        payload: list[object],
    ) -> tuple[RunSourceRef, ...]:
        """Rebuild typed source references from normalized payload data."""
        return tuple(
            RunSourceRef(
                provider=str(item["provider"]),
                entity=str(item["entity"]),
                pipeline_name=str(item["pipeline_name"]),
                query=(None if item.get("query") is None else str(item["query"])),
            )
            for item in payload
            if isinstance(item, dict)
        )

    def _hydrate_planned_artifacts(
        self,
        payload: list[object],
    ) -> tuple[RunArtifactRef, ...]:
        """Rebuild typed planned artifacts from normalized payload data."""
        return tuple(
            RunArtifactRef(layer=str(item["layer"]), path=str(item["path"]))
            for item in payload
            if isinstance(item, dict)
        )

    def _build_manifest(
        self,
        *,
        request: RunManifestCreateSpec,
        run_type: RunType,
        created_at: datetime,
        normalized_payload: dict[str, object],
        fingerprint: str,
    ) -> RunManifest:
        """Build the final typed manifest from normalized primitive payload."""
        code_provenance_payload = dict(normalized_payload["code_provenance"])
        return RunManifest(
            manifest_id=self._manifest_id_factory(),
            execution_fingerprint=fingerprint,
            schema_version=self.schema_version,
            created_at=created_at,
            run_id=request.run_id,
            run_type=run_type,
            pipeline_name=request.pipeline_name,
            provider=request.provider,
            entity=request.entity,
            launch_context=dict(normalized_payload["launch_context"]),
            runtime_config=dict(normalized_payload["runtime_config"]),
            resolved_config=dict(normalized_payload["resolved_config"]),
            code_provenance=self._hydrate_code_provenance(code_provenance_payload),
            source_refs=self._hydrate_source_refs(
                list(normalized_payload.get("source_refs", []))
            ),
            planned_artifacts=self._hydrate_planned_artifacts(
                list(normalized_payload.get("planned_artifacts", []))
            ),
        )

    def create_manifest(self, request: RunManifestCreateSpec) -> RunManifest:
        """Build fingerprinted manifest and persist it through the port."""
        created_at = datetime.now(UTC)
        normalized_run_type = self._normalize_run_type(request.run_type)
        code_provenance = self._build_code_provenance(request)
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
                payload=normalized_payload
            ),
        )
        self.manifest_port.save(manifest)
        return manifest

    def _build_manifest_payload(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> dict[str, object]:
        """Build the pre-fingerprint manifest payload in primitive form."""
        return {
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
                "contract_ref": code_provenance.contract_ref,
                "contract_version": code_provenance.contract_version,
                "contract_schema_hash": code_provenance.contract_schema_hash,
                "dq_policy_ref": code_provenance.dq_policy_ref,
                "rule_bundle_version": code_provenance.rule_bundle_version,
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

    def _compute_execution_fingerprint(self, *, payload: dict[str, object]) -> str:
        """Compute a deterministic fingerprint for replay/equivalence checks."""
        canonical = serialize_json_canonical(payload)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


RunManifestCreateRequest = RunManifestCreateSpec
