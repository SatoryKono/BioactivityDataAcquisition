"""Immutable control-plane provenance artifacts.
replace ``PipelineRunContext`` or ``PipelineContext`` for provenance tracking."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field, fields
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from bioetl.domain.control_plane._run_manifest_serialization import (
    freeze_manifest_payload,
    normalize_manifest_created_at,
    normalize_manifest_serializable,
)
from bioetl.domain.types import RunID, RunType

__all__ = [
    "ReplayCapability",
    "RunArtifactRef",
    "RunCodeProvenance",
    "RunInputSnapshotRef",
    "RunManifest",
    "RunSourceRef",
]

DOCUMENTED_SOURCE_REVISION_STATES = frozenset(
    {"clean", "dirty", "dirty_state_unknown", "git_unavailable"}
)
_DEFAULT_RUN_ID = RunID(UUID(int=0))
_DEFAULT_CREATED_AT = datetime(1970, 1, 1, tzinfo=UTC)


def _require_non_empty_text(value: object, field_name: str) -> None:
    """Reject missing semantic identity fields before manifest persistence."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"RunManifest.{field_name} must be a non-empty string")


class ReplayCapability(StrEnum):
    """Exact-replay capability classification for one manifested run."""

    EXACT_REPLAY_SUPPORTED = "exact_replay_supported"
    RESUME_ONLY = "resume_only"
    REBUILD_ONLY = "rebuild_only"


@dataclass(frozen=True, slots=True)
class RunInputSnapshotRef:
    """Immutable snapshot reference captured for one external input batch."""

    snapshot_id: str
    content_hash: str
    immutable_uri: str | None = None
    query_fingerprint: str | None = None
    storage_provider: str | None = None
    object_bucket: str | None = None
    object_key: str | None = None
    object_version_id: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RunSourceRef:
    """Canonical source reference captured in a run manifest."""

    provider: str
    entity: str
    pipeline_name: str
    query: str | None = None
    input_snapshots: tuple[RunInputSnapshotRef, ...] = ()


@dataclass(frozen=True, slots=True)
class RunArtifactRef:
    """Planned artifact location captured in a run manifest."""

    layer: str
    path: str


@dataclass(frozen=True, slots=True)
class RunCodeProvenance:
    """Code/config provenance fields required for reproducibility."""

    pipeline_version: str | None = None
    git_commit: str | None = None
    source_revision_state: str | None = None
    dependency_lock_hash: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    source_fingerprint: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    # Data Quality integration
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Immutable provenance/control-plane artifact for one launched run.

    This is not the universal runtime execution object; runtime flows keep using
    ``PipelineRunContext`` and ``PipelineContext``.
    """

    manifest_id: str = "legacy-manifest"
    execution_fingerprint: str = "legacy-fingerprint"
    schema_version: str = "1.0"
    created_at: datetime = _DEFAULT_CREATED_AT
    run_id: RunID = _DEFAULT_RUN_ID
    run_type: RunType = RunType.INCREMENTAL
    pipeline_name: str = "unknown_pipeline"
    provider: str = "unknown"
    entity: str = "unknown"
    workflow_run_id: str | None = None
    workflow_name: str | None = None
    workflow_step_id: str | None = None
    launch_context: dict[str, object] = field(default_factory=dict)
    runtime_config: dict[str, object] = field(default_factory=dict)
    resolved_config: dict[str, object] = field(default_factory=dict)
    code_provenance: RunCodeProvenance = field(default_factory=RunCodeProvenance)
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    replay_capability: ReplayCapability = ReplayCapability.REBUILD_ONLY
    source_refs: tuple[RunSourceRef, ...] = ()
    planned_artifacts: tuple[RunArtifactRef, ...] = ()
    pipeline_config: InitVar[object | None] = None
    pipeline_identity: InitVar[object | None] = None
    artifacts: InitVar[object | None] = None

    def __post_init__(self, *_legacy: object | None) -> None:
        """Keep manifest timestamps canonical across serialize/deserialize cycles."""
        for field_name in (
            "manifest_id",
            "execution_fingerprint",
            "schema_version",
            "pipeline_name",
            "provider",
            "entity",
        ):
            _require_non_empty_text(getattr(self, field_name), field_name)
        set_attr = object.__setattr__
        freeze = freeze_manifest_payload
        set_attr(self, "created_at", normalize_manifest_created_at(self.created_at))
        for field_name in ("launch_context", "runtime_config", "resolved_config"):
            set_attr(self, field_name, freeze(getattr(self, field_name)))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable manifest payload."""
        return {
            key: normalize_manifest_serializable(value)
            for key, value in (
                (field.name, getattr(self, field.name)) for field in fields(self)
            )
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> RunManifest:
        """Hydrate a manifest from serialized JSON payload."""
        return cls(
            manifest_id=str(payload["manifest_id"]),
            execution_fingerprint=str(payload["execution_fingerprint"]),
            schema_version=str(payload["schema_version"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            run_id=RunID(UUID(str(payload["run_id"]))),
            run_type=RunType(str(payload["run_type"])),
            pipeline_name=str(payload["pipeline_name"]),
            provider=str(payload["provider"]),
            entity=str(payload["entity"]),
            workflow_run_id=_load_optional_str(payload, "workflow_run_id"),
            workflow_name=_load_optional_str(payload, "workflow_name"),
            workflow_step_id=_load_optional_str(payload, "workflow_step_id"),
            launch_context=_load_object_mapping(payload.get("launch_context")),
            runtime_config=_load_object_mapping(payload.get("runtime_config")),
            resolved_config=_load_object_mapping(payload.get("resolved_config")),
            code_provenance=_load_code_provenance(payload.get("code_provenance")),
            replay_of_run_id=_load_optional_str(payload, "replay_of_run_id"),
            replay_of_manifest_id=_load_optional_str(payload, "replay_of_manifest_id"),
            replay_capability=_load_replay_capability(payload.get("replay_capability")),
            source_refs=_load_source_refs(payload.get("source_refs")),
            planned_artifacts=_load_artifacts(payload.get("planned_artifacts")),
        )


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Extract an optional string field from a serialized mapping."""
    value = payload.get(key)
    return None if value is None else str(value)


def _load_code_provenance(raw_code: object) -> RunCodeProvenance:
    """Deserialize code provenance payload safely."""
    payload = _load_object_mapping(raw_code)
    return RunCodeProvenance(
        pipeline_version=_load_optional_str(payload, "pipeline_version"),
        git_commit=_load_optional_str(payload, "git_commit"),
        source_revision_state=_load_optional_str(payload, "source_revision_state"),
        dependency_lock_hash=_load_optional_str(payload, "dependency_lock_hash"),
        config_hash=_load_optional_str(payload, "config_hash"),
        resolved_config_hash=_load_optional_str(payload, "resolved_config_hash"),
        effective_config_hash=_load_optional_str(payload, "effective_config_hash"),
        source_fingerprint=_load_optional_str(payload, "source_fingerprint"),
        contract_ref=_load_optional_str(payload, "contract_ref"),
        contract_version=_load_optional_str(payload, "contract_version"),
        contract_schema_hash=_load_optional_str(payload, "contract_schema_hash"),
        dq_policy_ref=_load_optional_str(payload, "dq_policy_ref"),
        rule_bundle_version=_load_optional_str(payload, "rule_bundle_version"),
        normalization_profile_ref=_load_optional_str(
            payload, "normalization_profile_ref"
        ),
        normalization_profile_version=_load_optional_str(
            payload, "normalization_profile_version"
        ),
        normalization_profile_hash=_load_optional_str(
            payload, "normalization_profile_hash"
        ),
        dq_contract_compatibility_hash=_load_optional_str(
            payload, "dq_contract_compatibility_hash"
        ),
        effective_config_artifact_id=_load_optional_str(
            payload, "effective_config_artifact_id"
        ),
    )


def _load_replay_capability(raw_value: object) -> ReplayCapability:
    if raw_value is None:
        return ReplayCapability.REBUILD_ONLY
    return ReplayCapability(str(raw_value))


def _load_object_mapping(raw_mapping: object) -> dict[str, object]:
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


def _load_source_refs(raw_sources: object) -> tuple[RunSourceRef, ...]:
    if not isinstance(raw_sources, list):
        return ()
    return tuple(
        RunSourceRef(
            provider=str(item["provider"]),
            entity=str(item["entity"]),
            pipeline_name=str(item["pipeline_name"]),
            query=(None if item.get("query") is None else str(item["query"])),
            input_snapshots=_load_input_snapshots(item.get("input_snapshots")),
        )
        for item in raw_sources
        if isinstance(item, dict)
    )


def _load_input_snapshots(raw_snapshots: object) -> tuple[RunInputSnapshotRef, ...]:
    if not isinstance(raw_snapshots, list):
        return ()
    return tuple(
        _load_input_snapshot_ref(item)
        for item in raw_snapshots
        if isinstance(item, dict)
    )


def _load_input_snapshot_ref(item: dict[str, object]) -> RunInputSnapshotRef:
    return RunInputSnapshotRef(
        snapshot_id=str(item["snapshot_id"]),
        content_hash=str(item["content_hash"]),
        immutable_uri=_load_optional_snapshot_field(item, "immutable_uri"),
        query_fingerprint=_load_optional_snapshot_field(item, "query_fingerprint"),
        storage_provider=_load_optional_snapshot_field(item, "storage_provider"),
        object_bucket=_load_optional_snapshot_field(item, "object_bucket"),
        object_key=_load_optional_snapshot_field(item, "object_key"),
        object_version_id=_load_optional_snapshot_field(item, "object_version_id"),
        etag=_load_optional_snapshot_field(item, "etag"),
        last_modified=_load_optional_snapshot_field(item, "last_modified"),
        captured_at=_load_optional_snapshot_field(
            item, "captured_at", is_datetime=True
        ),
    )


def _load_optional_snapshot_field(
    item: dict[str, object],
    field_name: str,
    is_datetime: bool = False,
) -> str | datetime | None:
    raw_value = item.get(field_name)
    if raw_value is None:
        return None
    return datetime.fromisoformat(str(raw_value)) if is_datetime else str(raw_value)


def _load_artifacts(raw_artifacts: object) -> tuple[RunArtifactRef, ...]:
    if not isinstance(raw_artifacts, list):
        return ()
    return tuple(
        RunArtifactRef(layer=str(item["layer"]), path=str(item["path"]))
        for item in raw_artifacts
        if isinstance(item, dict)
    )
