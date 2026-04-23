"""Internal mixins for run-manifest payload and hydration helpers."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from .run_manifest_service import RunManifestCreateSpec


def _optional_payload_string(
    payload: dict[str, object],
    key: str,
) -> str | None:
    """Return a payload value as string when present."""
    value = payload.get(key)
    return None if value is None else str(value)


class RunManifestHydrationMixin:
    """Hydrate typed control-plane objects from normalized manifest payloads."""

    def _hydrate_code_provenance(
        self,
        payload: dict[str, object],
    ) -> RunCodeProvenance:
        """Rebuild typed code provenance from normalized payload data."""
        return RunCodeProvenance(
            pipeline_version=_optional_payload_string(payload, "pipeline_version"),
            git_commit=_optional_payload_string(payload, "git_commit"),
            source_revision_state=_optional_payload_string(
                payload,
                "source_revision_state",
            ),
            config_hash=_optional_payload_string(payload, "config_hash"),
            resolved_config_hash=_optional_payload_string(
                payload,
                "resolved_config_hash",
            ),
            effective_config_hash=_optional_payload_string(
                payload,
                "effective_config_hash",
            ),
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
                storage_provider=(
                    None
                    if item.get("storage_provider") is None
                    else str(item["storage_provider"])
                ),
                object_bucket=(
                    None
                    if item.get("object_bucket") is None
                    else str(item["object_bucket"])
                ),
                object_key=(
                    None if item.get("object_key") is None else str(item["object_key"])
                ),
                object_version_id=(
                    None
                    if item.get("object_version_id") is None
                    else str(item["object_version_id"])
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


class RunManifestPayloadMixin:
    """Build normalized manifest payloads and canonical identity anchors."""

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
            git_commit=code_provenance.git_commit,
            effective_config_hash=code_provenance.effective_config_hash,
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
                "source_revision_state": code_provenance.source_revision_state,
                "config_hash": code_provenance.config_hash,
                "resolved_config_hash": code_provenance.resolved_config_hash,
                "effective_config_hash": code_provenance.effective_config_hash,
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
                            "storage_provider": snapshot.storage_provider,
                            "object_bucket": snapshot.object_bucket,
                            "object_key": snapshot.object_key,
                            "object_version_id": snapshot.object_version_id,
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
