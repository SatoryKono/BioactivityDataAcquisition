"""Application service for creating effective configuration artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import cast

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveConfigArtifact,
    EffectiveConfigHashes,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
    SourceClassProvenance,
)
from bioetl.domain.services.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef


def _dataclass_to_dict(value: object) -> JsonDict | None:
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return asdict(value)


def _stable_hash(payload: object) -> str:
    serialized = json.dumps(
        _to_jsonable(payload),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _to_jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, DQDisposition):
        return value.value
    dataclass_value = _dataclass_to_dict(value)
    if dataclass_value is not None:
        return {k: _to_jsonable(v) for k, v in dataclass_value.items()}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _apply_deep_update(target: JsonDict, source: JsonDict) -> None:
    for key, value in source.items():
        target_value = target.get(key)
        if isinstance(target_value, dict) and isinstance(value, dict):
            nested_target = cast(JsonDict, target_value)
            nested_source = cast(JsonDict, value)
            _apply_deep_update(nested_target, nested_source)
            continue
        target[key] = value


def _apply_runtime_overrides(base_config: JsonDict, overrides: JsonDict) -> JsonDict:
    effective_config = copy.deepcopy(base_config)
    for layer in ("cli", "env", "runtime"):
        layer_overrides = overrides.get(layer)
        if isinstance(layer_overrides, dict):
            _apply_deep_update(effective_config, layer_overrides)
    return effective_config


def _build_dq_components(
    dq_config: DQConfig | None,
) -> tuple[list[DQPolicyRef], list[DQPolicySnapshot], dict[str, str]]:
    """Build DQ policy references, snapshots, and bundle versions from config."""
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


def _extract_contract_refs(dq_config: DQConfig | None) -> list[str]:
    if dq_config is None or not dq_config.contract_ref:
        return []
    return [dq_config.contract_ref]


def _resolve_resolution_policy(
    resolution_policy: ConfigResolutionPolicy | None,
) -> ConfigResolutionPolicy:
    if resolution_policy is not None:
        return resolution_policy
    return ConfigResolutionPolicy()


def _compute_source_fingerprint(source_refs: list[ConfigSourceRef]) -> str:
    if not source_refs:
        return "no_sources"
    normalized = [
        {
            "type": src.source_type,
            "path": src.source_path,
            "hash": src.source_hash or "no_hash",
            "priority": src.priority,
        }
        for src in sorted(source_refs, key=lambda item: item.source_path)
    ]
    return _stable_hash(normalized)


def _build_effective_config_artifact_id(
    *,
    pipeline_name: str,
    pipeline_kind: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str,
    dq_contract_compatibility_hash: str,
) -> str:
    """Build one deterministic semantic artifact identifier."""
    semantic_payload = {
        "pipeline_name": pipeline_name,
        "pipeline_kind": pipeline_kind,
        "resolved_config_hash": resolved_config_hash,
        "effective_config_hash": effective_config_hash,
        "source_fingerprint": source_fingerprint,
        "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
    }
    return f"effective-config-{_stable_hash(semantic_payload)[:16]}"


def _build_resolved_config_snapshot(
    *,
    pipeline_kind: str,
    resolved_config: JsonDict,
) -> ResolvedConfigSnapshot:
    """Build the resolved-config snapshot and its stable hash."""
    return ResolvedConfigSnapshot(
        config_type=pipeline_kind,
        config_data=resolved_config,
        config_hash=_stable_hash(resolved_config),
    )


def _build_runtime_override_snapshot(
    runtime_overrides: JsonDict,
) -> RuntimeOverrideSnapshot:
    """Build the runtime override snapshot and its stable hash."""
    return RuntimeOverrideSnapshot(
        cli_overrides=runtime_overrides.get("cli", {}),
        env_overrides=runtime_overrides.get("env", {}),
        runtime_adjustments=runtime_overrides.get("runtime", {}),
        override_hash=_stable_hash(runtime_overrides),
    )


def _build_effective_execution_config(
    *,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
) -> EffectiveExecutionConfig:
    """Apply runtime overrides and capture the effective execution snapshot."""
    effective_config_data = _apply_runtime_overrides(
        resolved_config,
        runtime_overrides,
    )
    return EffectiveExecutionConfig(
        config_data=effective_config_data,
        effective_hash=_stable_hash(effective_config_data),
    )


def _build_source_class_provenance() -> tuple[SourceClassProvenance, ...]:
    """Return the canonical provenance table for supported config/input source classes."""
    return (
        SourceClassProvenance(
            source_class="config_file",
            provenance_status="identity_anchored",
            artifact_surface="semantic_artifact.source_refs[*]",
            anchor_field="source_hash",
            notes="File-backed config sources are persisted when they participate in materialization.",
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
            notes="Explicit environment overrides are collapsed into the runtime override hash.",
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
                "DQ policy anchors are persisted when DQ policy config "
                "participates in materialization."
            ),
        ),
        SourceClassProvenance(
            source_class="immutable_input_snapshot",
            provenance_status="external_anchor",
            artifact_surface="run_manifest.source_refs[*].input_snapshots[*]",
            anchor_field="content_hash",
            notes=(
                "Immutable Bronze input snapshots are anchored in the run "
                "manifest rather than the effective-config artifact."
            ),
        ),
        SourceClassProvenance(
            source_class="implicit_process_environment",
            provenance_status="unsupported",
            artifact_surface="not_persisted",
            notes=(
                "Ambient process environment outside explicit overrides is "
                "intentionally excluded from semantic identity."
            ),
        ),
    )


def _serialize_artifact(artifact: EffectiveConfigArtifact) -> str:
    payload = {
        "artifact_id": artifact.artifact_id,
        "schema_version": artifact.schema_version,
        "semantic_artifact": _semantic_artifact_payload(artifact),
        "occurrence_envelope": _occurrence_envelope_payload(artifact),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _semantic_artifact_payload(artifact: EffectiveConfigArtifact) -> JsonDict:
    return {
        "artifact_id": artifact.artifact_id,
        "schema_version": artifact.schema_version,
        "pipeline_name": artifact.pipeline_name,
        "pipeline_kind": artifact.pipeline_kind,
        "source_refs": [_to_jsonable(src) for src in artifact.source_refs],
        "source_class_provenance": [
            _to_jsonable(item) for item in artifact.source_class_provenance
        ],
        "resolution_policy": _to_jsonable(artifact.resolution_policy),
        "resolved_config": {
            "config_type": artifact.resolved_config.config_type,
            "config_data": _to_jsonable(artifact.resolved_config.config_data),
            "config_hash": artifact.resolved_config.config_hash,
        },
        "runtime_overrides": _to_jsonable(artifact.runtime_overrides),
        "effective_execution_config": {
            "config_data": _to_jsonable(
                artifact.effective_execution_config.config_data
            ),
            "effective_hash": artifact.effective_execution_config.effective_hash,
        },
        "resolved_config_hash": artifact.resolved_config_hash,
        "effective_config_hash": artifact.effective_config_hash,
        "source_fingerprint": artifact.source_fingerprint,
        "contract_refs": artifact.contract_refs,
        "dq_policy_refs": [_to_jsonable(ref) for ref in artifact.dq_policy_refs],
        "dq_rule_bundle_versions": artifact.dq_rule_bundle_versions,
        "dq_contract_compatibility_hash": artifact.dq_contract_compatibility_hash,
        "dq_policy_snapshots": [
            _to_jsonable(snapshot) for snapshot in artifact.dq_policy_snapshots
        ],
    }


def _occurrence_envelope_payload(artifact: EffectiveConfigArtifact) -> JsonDict:
    return {
        "created_at": artifact.created_at.isoformat(),
        "resolved_config_timestamp": artifact.resolved_config.timestamp.isoformat(),
        "effective_execution_timestamp": (
            artifact.effective_execution_config.timestamp.isoformat()
        ),
    }


class EffectiveConfigService:
    """Create and compare effective configuration artifacts."""

    def create_effective_config_artifact(
        self,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: JsonDict,
        runtime_overrides: JsonDict,
        source_refs: list[ConfigSourceRef],
        dq_config: DQConfig | None = None,
        resolution_policy: ConfigResolutionPolicy | None = None,
        artifact_id: str | None = None,
    ) -> EffectiveConfigArtifact:
        """Create a reproducible effective-config artifact from resolved inputs."""
        resolved_policy = _resolve_resolution_policy(resolution_policy)
        resolved_snapshot = _build_resolved_config_snapshot(
            pipeline_kind=pipeline_kind,
            resolved_config=resolved_config,
        )
        overrides_snapshot = _build_runtime_override_snapshot(runtime_overrides)
        effective_snapshot = _build_effective_execution_config(
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
        )

        dq_policy_refs, dq_policy_snapshots, dq_rule_bundle_versions = (
            _build_dq_components(dq_config)
        )
        dq_contract_compatibility_hash = (
            "no_dq_policies"
            if not dq_policy_refs
            else ":".join(
                sorted(
                    ref.policy_hash
                    for ref in dq_policy_refs
                    if ref.policy_hash is not None and ref.policy_hash
                )
            )
            or "no_dq_policy_hashes"
        )
        resolved_artifact_id = artifact_id or _build_effective_config_artifact_id(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config_hash=resolved_snapshot.config_hash,
            effective_config_hash=effective_snapshot.effective_hash,
            source_fingerprint=_compute_source_fingerprint(source_refs),
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        )
        return EffectiveConfigArtifact(
            artifact_id=resolved_artifact_id,
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            source_refs=source_refs,
            source_class_provenance=_build_source_class_provenance(),
            resolution_policy=resolved_policy,
            resolved_config=resolved_snapshot,
            runtime_overrides=overrides_snapshot,
            effective_execution_config=effective_snapshot,
            resolved_config_hash=resolved_snapshot.config_hash,
            effective_config_hash=effective_snapshot.effective_hash,
            source_fingerprint=_compute_source_fingerprint(source_refs),
            contract_refs=_extract_contract_refs(dq_config),
            dq_policy_refs=dq_policy_refs,
            dq_rule_bundle_versions=dq_rule_bundle_versions,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            dq_policy_snapshots=dq_policy_snapshots,
        )

    def serialize_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize one persisted artifact envelope with semantic + occurrence data."""
        return _serialize_artifact(artifact)

    def serialize_semantic_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize only the semantic effective-config payload deterministically."""
        return json.dumps(
            _semantic_artifact_payload(artifact),
            sort_keys=True,
            separators=(",", ":"),
        )

    def compute_artifact_hashes(
        self, artifact: EffectiveConfigArtifact
    ) -> EffectiveConfigHashes:
        """Extract the canonical hash bundle from an effective-config artifact."""
        return EffectiveConfigHashes(
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            source_fingerprint=artifact.source_fingerprint,
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
        )

    def check_dq_compatibility(
        self,
        artifact1: EffectiveConfigArtifact,
        artifact2: EffectiveConfigArtifact,
    ) -> bool:
        """Compare artifacts by their DQ compatibility hash."""
        return bool(
            artifact1.dq_contract_compatibility_hash
            == artifact2.dq_contract_compatibility_hash
        )

    def create_artifact_from_pipeline_config(
        self,
        pipeline_name: str,
        pipeline_kind: str,
        pipeline_config: JsonDict,
        dq_config: DQConfig | None = None,
        runtime_overrides: JsonDict | None = None,
        source_refs: list[ConfigSourceRef] | None = None,
    ) -> EffectiveConfigArtifact:
        """Create an artifact directly from pipeline config and optional overrides."""
        if runtime_overrides is None:
            runtime_overrides = {}
        if source_refs is None:
            source_refs = []
        return self.create_effective_config_artifact(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config=pipeline_config,
            runtime_overrides=runtime_overrides,
            source_refs=source_refs,
            dq_config=dq_config,
        )


def create_effective_config_service() -> EffectiveConfigService:
    """Factory for the effective configuration service."""
    return EffectiveConfigService()
