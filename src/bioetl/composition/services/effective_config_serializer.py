"""Deterministic serialization for EffectiveConfigArtifact with DQ support."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime

from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveConfigArtifact,
    EffectiveConfigHashes,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef


def _dataclass_to_dict(value: object) -> JsonDict | None:
    """Convert dataclass instances into JsonDict payloads when possible."""
    if not is_dataclass(value) or isinstance(value, type):
        return None
    return asdict(value)


def _to_jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, DQDisposition):
        return value.value
    dataclass_value = _dataclass_to_dict(value)
    if dataclass_value is not None:
        return {key: _to_jsonable(raw) for key, raw in dataclass_value.items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(raw) for key, raw in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(raw) for raw in value]
    return value


def _stable_hash(value: object) -> str:
    serialized = json.dumps(_to_jsonable(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class EffectiveConfigSerializer:
    """Serializer for EffectiveConfigArtifact with deterministic output."""

    def serialize_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize one persisted artifact envelope with semantic + occurrence data."""
        artifact_dict = self._artifact_to_dict(artifact)
        return json.dumps(artifact_dict, sort_keys=True, separators=(",", ":"))

    def serialize_semantic_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize only the semantic effective-config payload deterministically."""
        artifact_dict = self._semantic_artifact_to_dict(artifact)
        return json.dumps(artifact_dict, sort_keys=True, separators=(",", ":"))

    def compute_artifact_hashes(
        self,
        artifact: EffectiveConfigArtifact,
    ) -> EffectiveConfigHashes:
        """Compute deterministic section hashes for one artifact."""
        return EffectiveConfigHashes(
            resolved_config_hash=self._compute_section_hash(artifact.resolved_config),
            effective_config_hash=self._compute_section_hash(
                artifact.effective_execution_config
            ),
            source_fingerprint=self._compute_source_fingerprint(artifact.source_refs),
            dq_contract_compatibility_hash=self._compute_dq_compatibility_hash(
                artifact
            ),
        )

    def _compute_section_hash(self, section: object) -> str:
        return _stable_hash(self._normalize_section(section))

    def _compute_source_fingerprint(self, source_refs: list[ConfigSourceRef]) -> str:
        if not source_refs:
            return "no_sources"
        source_data = [
            {
                "type": src.source_type,
                "path": src.source_path,
                "hash": src.source_hash or "no_hash",
            }
            for src in sorted(source_refs, key=lambda item: item.source_path)
        ]
        return _stable_hash(source_data)

    def _compute_dq_compatibility_hash(self, artifact: EffectiveConfigArtifact) -> str:
        if not artifact.dq_policy_refs and not artifact.dq_policy_snapshots:
            return "no_dq_policies"
        dq_data: list[JsonDict] = []
        for policy_ref in artifact.dq_policy_refs:
            dq_data.append(self._dq_policy_ref_to_dict(policy_ref))
        for snapshot in artifact.dq_policy_snapshots:
            dq_data.append(self._dq_policy_snapshot_to_dict(snapshot))
        dq_data.sort(key=lambda item: str(item["contract_ref"]))
        return _stable_hash(dq_data)

    def _artifact_to_dict(self, artifact: EffectiveConfigArtifact) -> JsonDict:
        return {
            "artifact_id": artifact.artifact_id,
            "schema_version": artifact.schema_version,
            "semantic_artifact": self._semantic_artifact_to_dict(artifact),
            "occurrence_envelope": self._occurrence_envelope_to_dict(artifact),
        }

    def _semantic_artifact_to_dict(
        self,
        artifact: EffectiveConfigArtifact,
    ) -> JsonDict:
        return {
            "artifact_id": artifact.artifact_id,
            "schema_version": artifact.schema_version,
            "pipeline_name": artifact.pipeline_name,
            "pipeline_kind": artifact.pipeline_kind,
            "source_refs": [
                self._source_ref_to_dict(src) for src in artifact.source_refs
            ],
            "resolution_policy": self._resolution_policy_to_dict(
                artifact.resolution_policy
            ),
            "resolved_config": self._resolved_config_to_dict(artifact.resolved_config),
            "runtime_overrides": self._runtime_overrides_to_dict(
                artifact.runtime_overrides
            ),
            "effective_execution_config": self._effective_config_to_dict(
                artifact.effective_execution_config
            ),
            "resolved_config_hash": artifact.resolved_config_hash,
            "effective_config_hash": artifact.effective_config_hash,
            "source_fingerprint": artifact.source_fingerprint,
            "contract_refs": artifact.contract_refs,
            "normalization_profile_ref": artifact.normalization_profile_ref,
            "normalization_profile_version": artifact.normalization_profile_version,
            "normalization_profile_hash": artifact.normalization_profile_hash,
            "dq_policy_refs": [
                self._dq_policy_ref_to_dict(ref) for ref in artifact.dq_policy_refs
            ],
            "dq_rule_bundle_versions": artifact.dq_rule_bundle_versions,
            "dq_contract_compatibility_hash": artifact.dq_contract_compatibility_hash,
            "dq_policy_snapshots": [
                self._dq_policy_snapshot_to_dict(snapshot)
                for snapshot in artifact.dq_policy_snapshots
            ],
        }

    def _occurrence_envelope_to_dict(
        self,
        artifact: EffectiveConfigArtifact,
    ) -> JsonDict:
        return {
            "created_at": artifact.created_at.isoformat(),
            "resolved_config_timestamp": artifact.resolved_config.timestamp.isoformat(),
            "effective_execution_timestamp": (
                artifact.effective_execution_config.timestamp.isoformat()
            ),
        }

    def _source_ref_to_dict(self, source_ref: ConfigSourceRef) -> JsonDict:
        result: JsonDict = {
            "source_type": source_ref.source_type,
            "source_path": source_ref.source_path,
            "priority": source_ref.priority,
        }
        if source_ref.source_hash:
            result["source_hash"] = source_ref.source_hash
        if source_ref.raw_source_hash:
            result["raw_source_hash"] = source_ref.raw_source_hash
        if source_ref.source_hash_strategy:
            result["source_hash_strategy"] = source_ref.source_hash_strategy
        return result

    def _resolution_policy_to_dict(
        self,
        policy: ConfigResolutionPolicy,
    ) -> JsonDict:
        return {
            "merge_strategy": policy.merge_strategy,
            "default_materialization": policy.default_materialization,
            "strict_validation": policy.strict_validation,
            "allow_runtime_overrides": policy.allow_runtime_overrides,
        }

    def _resolved_config_to_dict(self, config: ResolvedConfigSnapshot) -> JsonDict:
        return {
            "config_type": config.config_type,
            "config_data": self._normalize_config_data(config.config_data),
            "config_hash": config.config_hash,
        }

    def _runtime_overrides_to_dict(
        self,
        overrides: RuntimeOverrideSnapshot,
    ) -> JsonDict:
        result: JsonDict = {}
        if overrides.cli_overrides:
            result["cli_overrides"] = self._normalize_config_data(
                overrides.cli_overrides
            )
        if overrides.env_overrides:
            result["env_overrides"] = self._normalize_config_data(
                overrides.env_overrides
            )
        if overrides.runtime_adjustments:
            result["runtime_adjustments"] = self._normalize_config_data(
                overrides.runtime_adjustments
            )
        if result and overrides.override_hash:
            result["override_hash"] = overrides.override_hash
        return result

    def _effective_config_to_dict(
        self, config: EffectiveExecutionConfig
    ) -> JsonDict:  # Any: EffectiveExecutionConfig serialization
        return {
            "config_data": self._normalize_config_data(config.config_data),
            "effective_hash": config.effective_hash,
        }

    def _dq_policy_ref_to_dict(self, policy_ref: DQPolicyRef) -> JsonDict:
        return {
            "contract_ref": policy_ref.contract_ref,
            "contract_version": policy_ref.contract_version,
            "rule_bundle_version": policy_ref.rule_bundle_version,
            "policy_hash": policy_ref.policy_hash,
        }

    def _dq_policy_snapshot_to_dict(
        self,
        snapshot: DQPolicySnapshot,
    ) -> JsonDict:  # Any: DQPolicySnapshot serialization
        return {
            "contract_ref": snapshot.contract_ref,
            "contract_version": snapshot.contract_version,
            "rule_bundle_version": snapshot.rule_bundle_version,
            "policy_hash": snapshot.policy_hash,
            "default_disposition": snapshot.default_disposition.value,
            "disposition_overrides": {
                str(key): value.value
                for key, value in snapshot.disposition_overrides.items()
            },
            "strictness_mode": snapshot.strictness_mode,
        }

    def _normalize_config_data(self, data: JsonDict) -> JsonDict:
        normalized: JsonDict = {}
        for key, value in sorted(data.items()):
            normalized[str(key)] = self._normalize_value(value)
        return normalized

    def _normalize_value(self, value: object) -> object:
        if isinstance(value, dict):
            return self._normalize_config_data(value)
        if isinstance(value, (list, tuple)):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, DQDisposition):
            return value.value
        return value

    def _normalize_section(self, section: object) -> JsonDict:
        dataclass_value = _dataclass_to_dict(section)
        if dataclass_value is not None:
            return self._normalize_config_data(dataclass_value)
        if isinstance(section, dict):
            return self._normalize_config_data(section)
        return {"value": self._normalize_value(section)}


def create_effective_config_serializer() -> EffectiveConfigSerializer:
    """Factory function to create EffectiveConfigSerializer instance."""
    return EffectiveConfigSerializer()
