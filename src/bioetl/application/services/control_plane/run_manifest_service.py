"""Application service for immutable run-manifest creation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
    normalize_run_manifest_spec,
)
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID, RunType

__all__ = [
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
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
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
    replay_capability: ReplayCapability = ReplayCapability.REBUILD_ONLY


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
                input_snapshots=self._hydrate_input_snapshots(
                    list(item.get("input_snapshots", []))
                ),
            )
            for item in payload
            if isinstance(item, dict)
        )

    def _hydrate_input_snapshots(
        self,
        payload: list[object],
    ) -> tuple[RunInputSnapshotRef, ...]:
        """Rebuild immutable input snapshot refs from normalized payload data."""
        return tuple(
            RunInputSnapshotRef(
                snapshot_id=str(item["snapshot_id"]),
                content_hash=str(item["content_hash"]),
                immutable_uri=(
                    None
                    if item.get("immutable_uri") is None
                    else str(item["immutable_uri"])
                ),
                query_fingerprint=(
                    None
                    if item.get("query_fingerprint") is None
                    else str(item["query_fingerprint"])
                ),
                etag=None if item.get("etag") is None else str(item["etag"]),
                last_modified=(
                    None
                    if item.get("last_modified") is None
                    else str(item["last_modified"])
                ),
                captured_at=(
                    None
                    if item.get("captured_at") is None
                    else datetime.fromisoformat(str(item["captured_at"]))
                ),
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
        code_provenance_payload = cast(
            dict[str, object],
            normalized_payload["code_provenance"],
        )
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
            launch_context=cast(
                dict[str, object],
                normalized_payload["launch_context"],
            ),
            runtime_config=cast(
                dict[str, object],
                normalized_payload["runtime_config"],
            ),
            resolved_config=cast(
                dict[str, object],
                normalized_payload["resolved_config"],
            ),
            code_provenance=self._hydrate_code_provenance(code_provenance_payload),
            replay_of_run_id=_optional_payload_string(
                normalized_payload,
                "replay_of_run_id",
            ),
            replay_of_manifest_id=_optional_payload_string(
                normalized_payload,
                "replay_of_manifest_id",
            ),
            replay_capability=request.replay_capability,
            source_refs=self._hydrate_source_refs(
                cast(list[object], normalized_payload.get("source_refs", []))
            ),
            planned_artifacts=self._hydrate_planned_artifacts(
                cast(list[object], normalized_payload.get("planned_artifacts", []))
            ),
        )

    def _build_execution_identity_payload(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> dict[str, str | None]:
        """Build the canonical execution-identity payload shared across layers."""
        snapshot_ids = sorted(
            snapshot.snapshot_id
            for source_ref in request.source_refs
            for snapshot in source_ref.input_snapshots
        )
        return build_execution_identity_payload(
            pipeline_name=request.pipeline_name,
            run_type=run_type.value,
            pipeline_version=code_provenance.pipeline_version,
            effective_config_hash=code_provenance.config_hash,
            dq_contract_compatibility_hash=(
                code_provenance.dq_contract_compatibility_hash
            ),
            contract_ref=code_provenance.contract_ref,
            contract_version=code_provenance.contract_version,
            effective_config_artifact_id=code_provenance.effective_config_artifact_id,
            exact_replay=bool(request.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=(
                compute_input_snapshot_identity_fingerprint(snapshot_ids)
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
            "replay_of_run_id": request.replay_of_run_id,
            "replay_of_manifest_id": request.replay_of_manifest_id,
            "replay_capability": request.replay_capability.value,
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
                    "input_snapshots": [
                        {
                            "snapshot_id": snapshot.snapshot_id,
                            "content_hash": snapshot.content_hash,
                            "immutable_uri": snapshot.immutable_uri,
                            "query_fingerprint": snapshot.query_fingerprint,
                            "etag": snapshot.etag,
                            "last_modified": snapshot.last_modified,
                            "captured_at": snapshot.captured_at,
                        }
                        for snapshot in item.input_snapshots
                    ],
                }
                for item in request.source_refs
            ],
            "planned_artifacts": [
                {"layer": item.layer, "path": item.path}
                for item in request.planned_artifacts
            ],
        }

    def _compute_execution_fingerprint(self, *, payload: dict[str, object]) -> str:
        """Compute the canonical execution-identity fingerprint contract."""
        return cast(str, compute_execution_identity_fingerprint(payload))
