"""Internal mixins for run-manifest payload and hydration helpers."""

from __future__ import annotations

from collections.abc import Callable
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
    from .run_manifest_models import RunManifestCreateSpec


def _optional_payload_string(
    payload: dict[str, object],
    key: str,
) -> str | None:
    """Return a payload value as string when present."""
    value = payload.get(key)
    return None if value is None else str(value)


def _optional_snapshot_string(
    payload: dict[str, object],
    key: str,
) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)


def _optional_snapshot_datetime(
    payload: dict[str, object],
    key: str,
) -> datetime | None:
    value = payload.get(key)
    return None if value is None else datetime.fromisoformat(str(value))


class RunManifestHydrationMixin:
    """Hydrate typed control-plane objects from normalized manifest payloads."""

    _manifest_id_factory: Callable[[], str]
    schema_version: str

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
            dependency_lock_hash=_optional_payload_string(
                payload,
                "dependency_lock_hash",
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
            source_fingerprint=_optional_payload_string(
                payload,
                "source_fingerprint",
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
            normalization_profile_ref=_optional_payload_string(
                payload,
                "normalization_profile_ref",
            ),
            normalization_profile_version=_optional_payload_string(
                payload,
                "normalization_profile_version",
            ),
            normalization_profile_hash=_optional_payload_string(
                payload,
                "normalization_profile_hash",
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
                immutable_uri=_optional_snapshot_string(item, "immutable_uri"),
                query_fingerprint=_optional_snapshot_string(
                    item,
                    "query_fingerprint",
                ),
                storage_provider=_optional_snapshot_string(item, "storage_provider"),
                object_bucket=_optional_snapshot_string(item, "object_bucket"),
                object_key=_optional_snapshot_string(item, "object_key"),
                object_version_id=_optional_snapshot_string(
                    item,
                    "object_version_id",
                ),
                etag=_optional_snapshot_string(item, "etag"),
                last_modified=_optional_snapshot_string(item, "last_modified"),
                captured_at=_optional_snapshot_datetime(item, "captured_at"),
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

    schema_version: str

    def _build_execution_identity_payload(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> dict[str, object]:
        """Build the canonical execution-identity payload shared across layers."""
        snapshots = [
            snapshot
            for source_ref in request.source_refs
            for snapshot in source_ref.input_snapshots
        ]
        return cast(
            dict[str, object],
            build_execution_identity_payload(
                pipeline_name=request.pipeline_name,
                run_type=run_type.value,
                pipeline_version=code_provenance.pipeline_version,
                git_commit=code_provenance.git_commit,
                dependency_lock_hash=code_provenance.dependency_lock_hash,
                effective_config_hash=code_provenance.effective_config_hash,
                dq_contract_compatibility_hash=(
                    code_provenance.dq_contract_compatibility_hash
                ),
                contract_ref=code_provenance.contract_ref,
                contract_version=code_provenance.contract_version,
                normalization_profile_ref=code_provenance.normalization_profile_ref,
                normalization_profile_version=(
                    code_provenance.normalization_profile_version
                ),
                normalization_profile_hash=code_provenance.normalization_profile_hash,
                effective_config_artifact_id=code_provenance.effective_config_artifact_id,
                exact_replay=bool(request.launch_context.get("exact_replay")),
                input_snapshot_fingerprint=(
                    compute_input_snapshot_identity_fingerprint(snapshots)
                ),
                silver_filter_compatibility_mode=str(
                    request.runtime_config.get(
                        "silver_filter_compatibility_mode",
                        "structural_only_auto_promote",
                    )
                ),
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
                "dependency_lock_hash": code_provenance.dependency_lock_hash,
                "config_hash": code_provenance.config_hash,
                "resolved_config_hash": code_provenance.resolved_config_hash,
                "effective_config_hash": code_provenance.effective_config_hash,
                "source_fingerprint": code_provenance.source_fingerprint,
                "contract_ref": code_provenance.contract_ref,
                "contract_version": code_provenance.contract_version,
                "contract_schema_hash": code_provenance.contract_schema_hash,
                "dq_policy_ref": code_provenance.dq_policy_ref,
                "rule_bundle_version": code_provenance.rule_bundle_version,
                "normalization_profile_ref": code_provenance.normalization_profile_ref,
                "normalization_profile_version": (
                    code_provenance.normalization_profile_version
                ),
                "normalization_profile_hash": code_provenance.normalization_profile_hash,
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
