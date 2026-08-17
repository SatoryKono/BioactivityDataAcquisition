"""Serialization and payload helpers for effective-config artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import cast

from bioetl.domain.control_plane.effective_config_artifact import (
    EFFECTIVE_CONFIG_ARTIFACT_SCHEMA_VERSION,
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveConfigArtifact,
    EffectiveExecutionConfig,
    ExecutionEnvironmentSnapshot,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
    SourceClassProvenance,
)
from bioetl.domain.normalization import serialize_json_canonical
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef

EFFECTIVE_CONFIG_SCHEMA_VERSION = EFFECTIVE_CONFIG_ARTIFACT_SCHEMA_VERSION


def dataclass_to_dict(value: object) -> JsonDict | None:
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return asdict(value)


def to_jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, DQDisposition):
        return value.value
    dataclass_value = dataclass_to_dict(value)
    if dataclass_value is not None:
        return {k: to_jsonable(v) for k, v in dataclass_value.items()}
    if isinstance(value, Mapping):
        return {str(k): to_jsonable(v) for k, v in sorted(value.items())}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_jsonable(item) for item in value]
    return value


def stable_hash(payload: object) -> str:
    serialized = serialize_json_canonical(cast(JsonDict, to_jsonable(payload)))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _source_ref_sort_key(src: ConfigSourceRef) -> tuple[int, str, str, str, str]:
    return (
        src.priority,
        src.source_type,
        src.source_path,
        src.source_hash or "",
        src.raw_source_hash or "",
    )


def canonical_source_refs(source_refs: list[ConfigSourceRef]) -> list[ConfigSourceRef]:
    """Return source refs in the deterministic order used by semantic identity."""
    return sorted(source_refs, key=_source_ref_sort_key)


def semantic_source_refs_payload(source_refs: list[ConfigSourceRef]) -> list[JsonDict]:
    return [
        {
            "source_type": src.source_type,
            "source_path": src.source_path,
            "source_hash": src.source_hash,
            "source_hash_strategy": src.source_hash_strategy,
            "source_hash_version": src.source_hash_version,
            "priority": src.priority,
        }
        for src in canonical_source_refs(source_refs)
    ]


def build_effective_config_artifact_id(semantic_payload: JsonDict) -> str:
    return f"effective-config-{stable_hash(semantic_payload)[:16]}"


@dataclass(frozen=True)
class SemanticIdentityPayloadContext:
    pipeline_name: str
    pipeline_kind: str
    source_refs: list[ConfigSourceRef]
    source_class_provenance: tuple[SourceClassProvenance, ...]
    resolution_policy: ConfigResolutionPolicy
    resolved_config: ResolvedConfigSnapshot
    runtime_overrides: RuntimeOverrideSnapshot
    execution_environment: ExecutionEnvironmentSnapshot
    effective_execution_config: EffectiveExecutionConfig
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str
    contract_refs: list[str]
    normalization_profile_ref: str | None
    normalization_profile_version: str | None
    normalization_profile_hash: str | None
    dq_policy_refs: list[DQPolicyRef]
    dq_rule_bundle_versions: dict[str, str]
    dq_contract_compatibility_hash: str
    dq_policy_snapshots: list[DQPolicySnapshot]


def runtime_overrides_payload(overrides: RuntimeOverrideSnapshot) -> JsonDict:
    payload: JsonDict = {}
    if overrides.cli_overrides:
        payload["cli_overrides"] = to_jsonable(overrides.cli_overrides)
    if overrides.env_overrides:
        payload["env_overrides"] = to_jsonable(overrides.env_overrides)
    if overrides.runtime_adjustments:
        payload["runtime_adjustments"] = to_jsonable(overrides.runtime_adjustments)
    if payload and overrides.override_hash:
        payload["override_hash"] = overrides.override_hash
    return payload


def build_semantic_identity_payload(
    *,
    request: SemanticIdentityPayloadContext,
) -> JsonDict:
    return {
        "schema_version": EFFECTIVE_CONFIG_SCHEMA_VERSION,
        "pipeline_name": request.pipeline_name,
        "pipeline_kind": request.pipeline_kind,
        "source_refs": semantic_source_refs_payload(request.source_refs),
        "source_class_provenance": [
            to_jsonable(item) for item in request.source_class_provenance
        ],
        "resolution_policy": to_jsonable(request.resolution_policy),
        "resolved_config": {
            "identity_version": request.resolved_config.identity_version,
            "config_type": request.resolved_config.config_type,
            "config_data": to_jsonable(request.resolved_config.config_data),
            "config_hash": request.resolved_config.config_hash,
        },
        "runtime_overrides": runtime_overrides_payload(request.runtime_overrides),
        "execution_environment": to_jsonable(request.execution_environment),
        "effective_execution_config": {
            "identity_version": (request.effective_execution_config.identity_version),
            "config_data": to_jsonable(request.effective_execution_config.config_data),
            "effective_hash": request.effective_execution_config.effective_hash,
        },
        "resolved_config_hash": request.resolved_config_hash,
        "effective_config_hash": request.effective_config_hash,
        "source_fingerprint": request.source_fingerprint,
        "contract_refs": request.contract_refs,
        "normalization_profile_ref": request.normalization_profile_ref,
        "normalization_profile_version": request.normalization_profile_version,
        "normalization_profile_hash": request.normalization_profile_hash,
        "dq_policy_refs": [to_jsonable(ref) for ref in request.dq_policy_refs],
        "dq_rule_bundle_versions": request.dq_rule_bundle_versions,
        "dq_contract_compatibility_hash": request.dq_contract_compatibility_hash,
        "dq_policy_snapshots": [
            to_jsonable(snapshot) for snapshot in request.dq_policy_snapshots
        ],
    }


def semantic_artifact_payload(artifact: EffectiveConfigArtifact) -> JsonDict:
    return {
        "artifact_id": artifact.artifact_id,
        "schema_version": artifact.schema_version,
        "pipeline_name": artifact.pipeline_name,
        "pipeline_kind": artifact.pipeline_kind,
        "source_refs": [
            to_jsonable(src) for src in canonical_source_refs(artifact.source_refs)
        ],
        "source_class_provenance": [
            to_jsonable(item) for item in artifact.source_class_provenance
        ],
        "resolution_policy": to_jsonable(artifact.resolution_policy),
        "resolved_config": {
            "identity_version": artifact.resolved_config.identity_version,
            "config_type": artifact.resolved_config.config_type,
            "config_data": to_jsonable(artifact.resolved_config.config_data),
            "config_hash": artifact.resolved_config.config_hash,
        },
        "runtime_overrides": runtime_overrides_payload(artifact.runtime_overrides),
        "execution_environment": to_jsonable(artifact.execution_environment),
        "effective_execution_config": {
            "identity_version": (artifact.effective_execution_config.identity_version),
            "config_data": to_jsonable(artifact.effective_execution_config.config_data),
            "effective_hash": artifact.effective_execution_config.effective_hash,
        },
        "resolved_config_hash": artifact.resolved_config_hash,
        "effective_config_hash": artifact.effective_config_hash,
        "source_fingerprint": artifact.source_fingerprint,
        "contract_refs": artifact.contract_refs,
        "normalization_profile_ref": artifact.normalization_profile_ref,
        "normalization_profile_version": artifact.normalization_profile_version,
        "normalization_profile_hash": artifact.normalization_profile_hash,
        "dq_policy_refs": [to_jsonable(ref) for ref in artifact.dq_policy_refs],
        "dq_rule_bundle_versions": artifact.dq_rule_bundle_versions,
        "dq_contract_compatibility_hash": artifact.dq_contract_compatibility_hash,
        "dq_policy_snapshots": [
            to_jsonable(snapshot) for snapshot in artifact.dq_policy_snapshots
        ],
    }


def occurrence_envelope_payload(artifact: EffectiveConfigArtifact) -> JsonDict:
    return {
        "created_at": artifact.created_at.isoformat(),
        "resolved_config_timestamp": artifact.resolved_config.timestamp.isoformat(),
        "effective_execution_timestamp": (
            artifact.effective_execution_config.timestamp.isoformat()
        ),
    }


def serialize_artifact(artifact: EffectiveConfigArtifact) -> str:
    return json.dumps(
        {
            "artifact_id": artifact.artifact_id,
            "schema_version": artifact.schema_version,
            "semantic_artifact": semantic_artifact_payload(artifact),
            "occurrence_envelope": occurrence_envelope_payload(artifact),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
