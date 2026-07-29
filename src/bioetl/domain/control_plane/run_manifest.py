"""Immutable control-plane provenance artifacts.
replace ``PipelineRunContext`` or ``PipelineContext`` for provenance tracking."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from bioetl.domain.control_plane._run_manifest_deserialization import (
    _load_artifacts,
    _load_code_provenance,
    _load_object_mapping,
    _load_optional_str,
    _load_replay_capability,
    _load_source_refs,
)
from bioetl.domain.control_plane._run_manifest_serialization import (
    freeze_manifest_payload,
    normalize_manifest_created_at,
    normalize_manifest_serializable,
)
from bioetl.domain.types import RunID, RunType

__all__ = [
    "PRODUCTION_PROVENANCE_REQUIRED_FIELDS",
    "ReplayCapability",
    "RunArtifactRef",
    "RunCodeProvenance",
    "RunInputSnapshotRef",
    "RunManifest",
    "RunSourceRef",
    "validate_production_provenance",
]

DOCUMENTED_SOURCE_REVISION_STATES = frozenset(
    {"clean", "dirty", "dirty_state_unknown", "git_unavailable"}
)
# Production provenance fields required for fail-closed production runs.
# config_hash is legacy/compatibility-only; resolved + effective hashes are
# the canonical identity anchors (see manifest validation policy).
PRODUCTION_PROVENANCE_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "pipeline_version",
        "git_commit",
        "source_revision_state",
        "dependency_lock_hash",
        "resolved_config_hash",
        "effective_config_hash",
        "contract_ref",
        "contract_version",
    }
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

    def missing_production_fields(self) -> tuple[str, ...]:
        """Return required production provenance fields that are empty."""
        missing: list[str] = []
        for field_name in sorted(PRODUCTION_PROVENANCE_REQUIRED_FIELDS):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                missing.append(field_name)
        return tuple(missing)


def validate_production_provenance(
    provenance: RunCodeProvenance,
    *,
    production: bool = True,
) -> None:
    """Fail closed when production runs lack required provenance fields.

    Non-production callers pass ``production=False`` to skip enforcement.
    """
    if not production:
        return
    missing = provenance.missing_production_fields()
    if missing:
        raise ValueError(
            "RunManifest code_provenance is incomplete for production runs: "
            f"missing {', '.join(missing)}"
        )


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

    def __post_init__(self) -> None:
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
            code_provenance=_load_code_provenance(
                payload.get("code_provenance"),
                provenance_type=RunCodeProvenance,
            ),
            replay_of_run_id=_load_optional_str(payload, "replay_of_run_id"),
            replay_of_manifest_id=_load_optional_str(payload, "replay_of_manifest_id"),
            replay_capability=_load_replay_capability(
                payload.get("replay_capability"),
                capability_type=ReplayCapability,
                rebuild_only=ReplayCapability.REBUILD_ONLY,
            ),
            source_refs=_load_source_refs(
                payload.get("source_refs"),
                source_ref_type=RunSourceRef,
                snapshot_ref_type=RunInputSnapshotRef,
            ),
            planned_artifacts=_load_artifacts(
                payload.get("planned_artifacts"),
                artifact_type=RunArtifactRef,
            ),
        )
