"""Private helpers for effective configuration artifact construction."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import cast

from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
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
from bioetl.domain.control_plane.effective_config_environment import (
    AMBIENT_ENVIRONMENT_POLICY,
    MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY,
    semantic_runtime_env_dependencies,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.normalization import serialize_json_canonical
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef

ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {"execution_environment"}
)
EFFECTIVE_CONFIG_SCHEMA_VERSION = "1.0"


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
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def stable_hash(payload: object) -> str:
    serialized = serialize_json_canonical(cast(JsonDict, to_jsonable(payload)))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def apply_deep_update(target: JsonDict, source: JsonDict) -> None:
    for key, value in source.items():
        target_value = target.get(key)
        if isinstance(target_value, dict) and isinstance(value, dict):
            apply_deep_update(
                cast(JsonDict, target_value),
                cast(JsonDict, value),
            )
            continue
        target[key] = value


def apply_runtime_overrides(base_config: JsonDict, overrides: JsonDict) -> JsonDict:
    effective_config = copy.deepcopy(base_config)
    for layer in ("cli", "env", "runtime"):
        layer_overrides = overrides.get(layer)
        if isinstance(layer_overrides, dict):
            apply_deep_update(effective_config, layer_overrides)
    return effective_config


def build_dq_components(
    dq_config: DQConfig | None,
) -> tuple[list[DQPolicyRef], list[DQPolicySnapshot], dict[str, str]]:
    if dq_config is None:
        return [], [], {}

    resolver = DQPolicyResolver(dq_config)
    policy_ref = resolver.build_policy_ref()
    policy_snapshot = DQPolicySnapshot(
        contract_ref=policy_ref.contract_ref,
        contract_version=policy_ref.contract_version,
        rule_bundle_version=policy_ref.rule_bundle_version,
        policy_hash=policy_ref.policy_hash or "",
        default_disposition=dq_config.default_disposition_policy,
        disposition_overrides=dict(dq_config.disposition_overrides),
        strictness_mode=dq_config.strictness_mode or "standard",
    )
    dq_rule_bundle_versions: dict[str, str] = {}
    if policy_ref.contract_ref and policy_ref.rule_bundle_version:
        dq_rule_bundle_versions[policy_ref.contract_ref] = (
            policy_ref.rule_bundle_version
        )
    return [policy_ref], [policy_snapshot], dq_rule_bundle_versions


def extract_contract_refs(dq_config: DQConfig | None) -> list[str]:
    if dq_config is None or not dq_config.contract_ref:
        return []
    return [dq_config.contract_ref]


def resolve_resolution_policy(
    resolution_policy: ConfigResolutionPolicy | None,
) -> ConfigResolutionPolicy:
    if resolution_policy is not None:
        return resolution_policy
    return ConfigResolutionPolicy()


def compute_source_fingerprint(source_refs: list[ConfigSourceRef]) -> str:
    if not source_refs:
        return "no_sources"
    return stable_hash(
        [
            {
                "type": src.source_type,
                "path": src.source_path,
                "hash": src.source_hash or "no_hash",
                "priority": src.priority,
            }
            for src in canonical_source_refs(source_refs)
        ]
    )


def _source_ref_sort_key(
    src: ConfigSourceRef,
) -> tuple[int, str, str, str, str]:
    """Return the canonical source-ref ordering key for identity surfaces."""
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
            "priority": src.priority,
        }
        for src in canonical_source_refs(source_refs)
    ]


def build_effective_config_artifact_id(semantic_payload: JsonDict) -> str:
    return f"effective-config-{stable_hash(semantic_payload)[:16]}"


def build_resolved_config_snapshot(
    *,
    pipeline_kind: str,
    resolved_config: JsonDict,
) -> ResolvedConfigSnapshot:
    return ResolvedConfigSnapshot(
        config_type=pipeline_kind,
        config_data=resolved_config,
        config_hash=stable_hash(resolved_config),
    )


def coerce_runtime_override_layer(
    runtime_overrides: JsonDict,
    layer_name: str,
) -> JsonDict:
    layer_overrides = runtime_overrides.get(layer_name, {})
    if layer_overrides is None:
        return {}
    if not isinstance(layer_overrides, dict):
        raise TypeError(f"runtime_overrides.{layer_name} must be a mapping")
    return cast(JsonDict, layer_overrides)


def validate_runtime_environment_provenance(
    *,
    runtime_overrides: JsonDict,
    required_persistence_profile: object,
) -> None:
    profile = normalize_required_persistence_profile(required_persistence_profile)
    if profile not in STRICT_PERSISTENCE_PROFILES:
        return
    env_overrides = coerce_runtime_override_layer(runtime_overrides, "env")
    unsupported_keys = sorted(
        str(key)
        for key in env_overrides
        if str(key) not in ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS
    )
    if unsupported_keys:
        raise ValueError(
            "runtime_overrides.env contains non-allowlisted semantic environment "
            f"overrides for required persistence profile '{profile}': "
            f"{', '.join(unsupported_keys)}"
        )
    execution_environment = env_overrides.get("execution_environment")
    if execution_environment is None:
        raise ValueError(
            "runtime_overrides.env.execution_environment must be materialized "
            f"for required persistence profile '{profile}'"
        )
    if not isinstance(execution_environment, dict):
        raise TypeError("runtime_overrides.env.execution_environment must be a mapping")
    if not execution_environment:
        raise ValueError(
            "runtime_overrides.env.execution_environment must be non-empty for "
            f"required persistence profile '{profile}'"
        )


def build_runtime_override_snapshot(
    runtime_overrides: JsonDict,
) -> RuntimeOverrideSnapshot:
    return RuntimeOverrideSnapshot(
        cli_overrides=coerce_runtime_override_layer(runtime_overrides, "cli"),
        env_overrides=coerce_runtime_override_layer(runtime_overrides, "env"),
        runtime_adjustments=coerce_runtime_override_layer(runtime_overrides, "runtime"),
        override_hash=stable_hash(runtime_overrides),
    )


def build_execution_environment_snapshot(
    runtime_overrides: JsonDict,
    *,
    required_persistence_profile: object | None = None,
) -> ExecutionEnvironmentSnapshot:
    """Materialize explicit execution-affecting environment overrides."""
    env_overrides = coerce_runtime_override_layer(runtime_overrides, "env")
    materialized_env_overrides = {
        str(key): to_jsonable(value)
        for key, value in sorted(env_overrides.items(), key=lambda item: str(item[0]))
    }
    profile = normalize_required_persistence_profile(required_persistence_profile)
    execution_environment = env_overrides.get("execution_environment")
    execution_environment_materialized = isinstance(
        execution_environment, dict
    ) and bool(execution_environment)
    semantic_dependencies = (
        ()
        if execution_environment_materialized
        else semantic_runtime_env_dependencies()
    )
    ambient_environment_policy = (
        MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY
        if execution_environment_materialized
        else AMBIENT_ENVIRONMENT_POLICY
    )
    snapshot_payload = {
        "materialized_env_overrides": materialized_env_overrides,
        "non_materialized_semantic_env_dependencies": semantic_dependencies,
        "ambient_environment_policy": ambient_environment_policy,
        "required_persistence_profile": profile,
    }
    return ExecutionEnvironmentSnapshot(
        materialized_env_keys=tuple(materialized_env_overrides),
        materialized_env_overrides=materialized_env_overrides,
        ambient_environment_policy=ambient_environment_policy,
        non_materialized_semantic_env_dependencies=semantic_dependencies,
        environment_hash=stable_hash(snapshot_payload),
    )


def build_effective_execution_config(
    *,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
) -> EffectiveExecutionConfig:
    effective_config_data = apply_runtime_overrides(
        resolved_config,
        runtime_overrides,
    )
    return EffectiveExecutionConfig(
        config_data=effective_config_data,
        effective_hash=stable_hash(effective_config_data),
    )


def build_source_class_provenance() -> tuple[SourceClassProvenance, ...]:
    return (
        SourceClassProvenance(
            source_class="config_file",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.source_refs[*]",
            anchor_field="source_hash",
            notes=(
                "File-backed YAML config sources use canonical semantic source_hash "
                "values for identity; raw_source_hash preserves forensic byte-level "
                "integrity when available."
            ),
        ),
        SourceClassProvenance(
            source_class="cli_override",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.runtime_overrides.cli_overrides",
            anchor_field="override_hash",
            notes="CLI overrides are collapsed into the runtime override hash.",
        ),
        SourceClassProvenance(
            source_class="env_override",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.runtime_overrides.env_overrides",
            anchor_field="override_hash",
            notes=(
                "Explicit allowlisted environment overrides are materialized into "
                "env_overrides and collapsed into the runtime override hash; "
                "non-allowlisted semantic env overrides are rejected during "
                "artifact creation."
            ),
        ),
        SourceClassProvenance(
            source_class="runtime_adjustment",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.runtime_overrides.runtime_adjustments",
            anchor_field="override_hash",
            notes="Runtime adjustments are collapsed into the runtime override hash.",
        ),
        SourceClassProvenance(
            source_class="dq_policy_contract",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.dq_policy_refs[*]",
            anchor_field="policy_hash",
            notes=(
                "DQ policy anchors are persisted when DQ policy config participates "
                "in materialization."
            ),
        ),
        SourceClassProvenance(
            source_class="immutable_input_snapshot",
            provenance_status="external_anchor",
            artifact_surface="run_manifest.source_refs[*].input_snapshots[*]",
            anchor_field="content_hash",
            notes=(
                "Immutable Bronze input snapshots are anchored in the run manifest "
                "rather than the effective-config artifact."
            ),
        ),
        SourceClassProvenance(
            source_class="implicit_process_environment",
            provenance_status="policy_excluded",
            artifact_surface="semantic_artifact.execution_environment",
            anchor_field="environment_hash",
            notes=(
                "Ambient process environment is excluded by policy unless it is "
                "explicitly materialized through runtime_overrides.env; the "
                "execution_environment surface anchors that exclusion policy and "
                "the set of materialized semantic env overrides."
            ),
        ),
    )


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
            "config_type": request.resolved_config.config_type,
            "config_data": to_jsonable(request.resolved_config.config_data),
            "config_hash": request.resolved_config.config_hash,
        },
        "runtime_overrides": runtime_overrides_payload(request.runtime_overrides),
        "execution_environment": to_jsonable(request.execution_environment),
        "effective_execution_config": {
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
            "config_type": artifact.resolved_config.config_type,
            "config_data": to_jsonable(artifact.resolved_config.config_data),
            "config_hash": artifact.resolved_config.config_hash,
        },
        "runtime_overrides": runtime_overrides_payload(artifact.runtime_overrides),
        "execution_environment": to_jsonable(artifact.execution_environment),
        "effective_execution_config": {
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
