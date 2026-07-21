"""Private manifest-service support helpers owned by the manifest package."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_code_provenance_dict,
    build_execution_identity_payload_from_code_provenance,
)
from bioetl.application.services.control_plane.manifest.snapshot_payloads import (
    source_refs_payload,
)
from bioetl.domain.config.runtime import CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.models import (
        RunManifestCreateSpec,
    )


def _optional_payload_string(
    payload: dict[str, object],
    key: str,
) -> str | None:
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
            workflow_run_id=_optional_payload_string(
                normalized_payload, "workflow_run_id"
            ),
            workflow_name=_optional_payload_string(normalized_payload, "workflow_name"),
            workflow_step_id=_optional_payload_string(
                normalized_payload, "workflow_step_id"
            ),
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
        snapshots = [
            snapshot
            for source_ref in request.source_refs
            for snapshot in source_ref.input_snapshots
        ]
        return build_execution_identity_payload_from_code_provenance(
            pipeline_name=request.pipeline_name,
            run_type=run_type.value,
            code_provenance=code_provenance,
            exact_replay=bool(request.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=compute_input_snapshot_identity_fingerprint(
                snapshots
            ),
            silver_filter_compatibility_mode=str(
                request.runtime_config.get(
                    "silver_filter_compatibility_mode",
                    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
                )
            ),
        )

    def _build_manifest_payload(
        self,
        *,
        request: RunManifestCreateSpec,
        code_provenance: RunCodeProvenance,
        run_type: RunType,
    ) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_type": str(run_type.value),
            "pipeline_name": request.pipeline_name,
            "provider": request.provider,
            "entity": request.entity,
            "workflow_run_id": request.workflow_run_id,
            "workflow_name": request.workflow_name,
            "workflow_step_id": request.workflow_step_id,
            "launch_context": request.launch_context,
            "runtime_config": request.runtime_config,
            "resolved_config": request.resolved_config,
            "replay_of_run_id": request.replay_of_run_id,
            "replay_of_manifest_id": request.replay_of_manifest_id,
            "replay_capability": request.replay_capability.value,
            "code_provenance": build_code_provenance_dict(
                code_provenance,
                include_execution_anchors=True,
            ),
            "source_refs": source_refs_payload(request.source_refs),
            "planned_artifacts": [
                {"layer": item.layer, "path": item.path}
                for item in request.planned_artifacts
            ],
        }
