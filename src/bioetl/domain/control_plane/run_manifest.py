"""Control-plane run manifest models.

These immutable artifacts capture provenance, reproducibility, and audit data
for a launched run. They complement runtime execution contexts, but do not
replace ``PipelineRunContext`` or ``PipelineContext`` as the canonical runtime
descriptors.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import cast
from uuid import UUID

from bioetl.domain.normalization.control_plane import (
    normalize_control_plane_datetime,
    normalize_control_plane_uuid,
)
from bioetl.domain.types import RunID, RunType

__all__ = [
    "RunArtifactRef",
    "RunCodeProvenance",
    "RunManifest",
    "RunSourceRef",
]


def _normalize_mapping(value: Mapping[object, object]) -> dict[str, object]:
    """Normalize nested mappings into JSON-serializable primitives."""
    return {
        str(key): _normalize_serializable(item)
        for key, item in sorted(value.items(), key=lambda item: str(item[0]))
    }


def _normalize_scalar(value: object) -> object:
    """Normalize scalar values into JSON-serializable primitives."""
    if isinstance(value, datetime):
        return normalize_control_plane_datetime(value)
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, UUID):
        return normalize_control_plane_uuid(value)
    return value


def _normalize_dataclass_value(value: object) -> dict[str, object] | None:
    """Normalize dataclass instances when present."""
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return _normalize_mapping(cast("Mapping[object, object]", asdict(value)))


def _normalize_collection_value(value: object) -> object | None:
    """Normalize collection-like values into JSON-friendly shapes."""
    if isinstance(value, dict):
        return _normalize_mapping(value)
    sequence_value = _normalize_sequence_value(value)
    if sequence_value is not None:
        return sequence_value
    return _normalize_set_like_value(value)


def _normalize_sequence_value(value: object) -> list[object] | None:
    """Normalize ordered collection values when present."""
    if not isinstance(value, (list, tuple)):
        return None
    return [_normalize_serializable(item) for item in value]


def _normalize_set_like_value(value: object) -> list[object] | None:
    """Normalize set-like values into deterministically sorted lists."""
    if not isinstance(value, (set, frozenset)):
        return None
    normalized = [_normalize_serializable(item) for item in value]
    return sorted(normalized, key=lambda item: str(item))


def _normalize_serializable(value: object) -> object:
    """Normalize nested values into JSON-serializable primitives."""
    dataclass_value = _normalize_dataclass_value(value)
    if dataclass_value is not None:
        return dataclass_value
    collection_value = _normalize_collection_value(value)
    if collection_value is not None:
        return collection_value
    return _normalize_scalar(value)


def _normalize_manifest_created_at(value: datetime) -> datetime:
    """Canonicalize manifest timestamps to UTC-aware datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class RunSourceRef:
    """Canonical source reference captured in a run manifest."""

    provider: str
    entity: str
    pipeline_name: str
    query: str | None = None


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
    config_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    # Data Quality integration
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Immutable provenance snapshot for one launched run.

    This manifest is a control-plane artifact. It is not the universal runtime
    execution descriptor used by runner, processing, or writer paths.
    """

    manifest_id: str
    execution_fingerprint: str
    schema_version: str
    created_at: datetime
    run_id: RunID
    run_type: RunType
    pipeline_name: str
    provider: str
    entity: str
    launch_context: dict[str, object]
    runtime_config: dict[str, object]
    resolved_config: dict[str, object]
    code_provenance: RunCodeProvenance
    source_refs: tuple[RunSourceRef, ...] = ()
    planned_artifacts: tuple[RunArtifactRef, ...] = ()

    def __post_init__(self) -> None:
        """Keep manifest timestamps canonical across serialize/deserialize cycles."""
        object.__setattr__(
            self,
            "created_at",
            _normalize_manifest_created_at(self.created_at),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable manifest payload."""
        return {
            key: _normalize_serializable(value) for key, value in asdict(self).items()
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
            launch_context=_load_object_mapping(payload.get("launch_context")),
            runtime_config=_load_object_mapping(payload.get("runtime_config")),
            resolved_config=_load_object_mapping(payload.get("resolved_config")),
            code_provenance=_load_code_provenance(payload.get("code_provenance")),
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
        config_hash=_load_optional_str(payload, "config_hash"),
        contract_ref=_load_optional_str(payload, "contract_ref"),
        contract_version=_load_optional_str(payload, "contract_version"),
        contract_schema_hash=_load_optional_str(payload, "contract_schema_hash"),
        dq_policy_ref=_load_optional_str(payload, "dq_policy_ref"),
        rule_bundle_version=_load_optional_str(payload, "rule_bundle_version"),
        dq_contract_compatibility_hash=_load_optional_str(
            payload, "dq_contract_compatibility_hash"
        ),
        effective_config_artifact_id=_load_optional_str(
            payload, "effective_config_artifact_id"
        ),
    )


def _load_object_mapping(raw_mapping: object) -> dict[str, object]:
    """Deserialize an arbitrary mapping into a string-keyed object payload."""
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


def _load_source_refs(raw_sources: object) -> tuple[RunSourceRef, ...]:
    """Deserialize source references from serialized payload."""
    if not isinstance(raw_sources, list):
        return ()
    return tuple(
        RunSourceRef(
            provider=str(item["provider"]),
            entity=str(item["entity"]),
            pipeline_name=str(item["pipeline_name"]),
            query=(None if item.get("query") is None else str(item["query"])),
        )
        for item in raw_sources
        if isinstance(item, dict)
    )


def _load_artifacts(raw_artifacts: object) -> tuple[RunArtifactRef, ...]:
    """Deserialize planned artifact references from serialized payload."""
    if not isinstance(raw_artifacts, list):
        return ()
    return tuple(
        RunArtifactRef(layer=str(item["layer"]), path=str(item["path"]))
        for item in raw_artifacts
        if isinstance(item, dict)
    )
