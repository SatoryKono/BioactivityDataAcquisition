"""Checkpoint metadata model with compatibility and replay anchors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from bioetl.domain.normalization import (
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
    normalize_execution_identity_payload,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types._checkpoint_metadata_support import (
    coerce_json_dict_sequence as _coerce_json_dict_sequence,
)
from bioetl.domain.types._checkpoint_metadata_support import (
    coerce_records_processed as _coerce_records_processed,
)
from bioetl.domain.types._checkpoint_metadata_support import (
    coerce_snapshot_ids,
    coerce_snapshot_refs,
    is_empty_checkpoint_metadata_value,
)
from bioetl.domain.types._checkpoint_metadata_support import (
    extract_checkpoint_anchor as _extract_anchor,
)
from bioetl.domain.types._checkpoint_metadata_support import (
    optional_stripped_text as _optional_stripped_text,
)
from bioetl.domain.types._checkpoint_metadata_support import (
    snapshot_fingerprint_inputs as _snapshot_fingerprint_inputs,
)
from bioetl.domain.types.checkpoint_compatibility_result import (
    CheckpointCompatibilityResult,
)

_OPTIONAL_STR = str | None
_OPTIONAL_BOOL = bool | None


@dataclass(frozen=True, slots=True)
class CheckpointMetadata:
    """Extended checkpoint metadata with compatibility and replay anchors."""

    records_processed: int
    dq_contract_compatibility_hash: _OPTIONAL_STR = None
    dq_policy_hash: _OPTIONAL_STR = None
    dq_rule_bundle_version: _OPTIONAL_STR = None
    pipeline_name: _OPTIONAL_STR = None
    run_type: _OPTIONAL_STR = None
    pipeline_version: _OPTIONAL_STR = None
    git_commit: _OPTIONAL_STR = None
    dependency_lock_hash: _OPTIONAL_STR = None
    effective_config_hash: _OPTIONAL_STR = None
    effective_config_artifact_id: _OPTIONAL_STR = None
    execution_fingerprint: _OPTIONAL_STR = None
    composite_run_identity: _OPTIONAL_STR = None
    manifest_id: _OPTIONAL_STR = None
    contract_ref: _OPTIONAL_STR = None
    contract_version: _OPTIONAL_STR = None
    normalization_profile_ref: _OPTIONAL_STR = None
    normalization_profile_version: _OPTIONAL_STR = None
    normalization_profile_hash: _OPTIONAL_STR = None
    exact_replay: _OPTIONAL_BOOL = None
    required_persistence_profile: _OPTIONAL_STR = None
    input_snapshot_refs: tuple[JsonDict, ...] = ()
    input_snapshot_ids: tuple[str, ...] = ()
    input_snapshot_fingerprint: _OPTIONAL_STR = None
    silver_filter_compatibility_mode: _OPTIONAL_STR = None
    memory_decision_trace: tuple[JsonDict, ...] = ()
    run_context: JsonDict | None = None  # Any: run context has heterogeneous values

    @staticmethod
    def from_legacy_metadata(legacy_metadata: JsonDict) -> CheckpointMetadata:
        """Create CheckpointMetadata from legacy metadata format."""
        return CheckpointMetadata(
            records_processed=_coerce_records_processed(
                legacy_metadata.get("records_processed", 0)
            ),
            dq_contract_compatibility_hash=legacy_metadata.get(
                "dq_contract_compatibility_hash"
            ),
            dq_policy_hash=legacy_metadata.get("dq_policy_hash"),
            dq_rule_bundle_version=legacy_metadata.get("dq_rule_bundle_version"),
            pipeline_name=cast(_OPTIONAL_STR, legacy_metadata.get("pipeline_name")),
            run_type=cast(_OPTIONAL_STR, legacy_metadata.get("run_type")),
            pipeline_version=legacy_metadata.get("pipeline_version"),
            git_commit=cast(_OPTIONAL_STR, legacy_metadata.get("git_commit")),
            dependency_lock_hash=_extract_anchor(
                legacy_metadata, "dependency_lock_hash"
            ),
            effective_config_hash=legacy_metadata.get("effective_config_hash"),
            effective_config_artifact_id=legacy_metadata.get(
                "effective_config_artifact_id"
            ),
            execution_fingerprint=legacy_metadata.get("execution_fingerprint"),
            composite_run_identity=_extract_anchor(
                legacy_metadata, "composite_run_identity"
            ),
            manifest_id=_extract_anchor(legacy_metadata, "manifest_id"),
            contract_ref=cast(_OPTIONAL_STR, legacy_metadata.get("contract_ref")),
            contract_version=cast(
                _OPTIONAL_STR,
                legacy_metadata.get("contract_version"),
            ),
            normalization_profile_ref=_extract_anchor(
                legacy_metadata,
                "normalization_profile_ref",
            ),
            normalization_profile_version=_extract_anchor(
                legacy_metadata,
                "normalization_profile_version",
            ),
            normalization_profile_hash=_extract_anchor(
                legacy_metadata,
                "normalization_profile_hash",
            ),
            exact_replay=cast(_OPTIONAL_BOOL, legacy_metadata.get("exact_replay")),
            required_persistence_profile=_extract_anchor(
                legacy_metadata,
                "required_persistence_profile",
            ),
            input_snapshot_refs=coerce_snapshot_refs(
                legacy_metadata.get("input_snapshot_refs")
            ),
            input_snapshot_ids=coerce_snapshot_ids(
                legacy_metadata.get("input_snapshot_ids")
            ),
            input_snapshot_fingerprint=cast(
                _OPTIONAL_STR, legacy_metadata.get("input_snapshot_fingerprint")
            ),
            silver_filter_compatibility_mode=_extract_anchor(
                legacy_metadata,
                "silver_filter_compatibility_mode",
            ),
            memory_decision_trace=_coerce_json_dict_sequence(
                legacy_metadata.get("memory_decision_trace")
            ),
            run_context=legacy_metadata.get("run_context"),
        )

    def to_dict(self) -> JsonDict:
        """Convert to dictionary for serialization."""
        result: JsonDict = {"records_processed": self.records_processed}
        optional_values: tuple[tuple[str, object | None], ...] = (
            ("dq_contract_compatibility_hash", self.dq_contract_compatibility_hash),
            ("dq_policy_hash", self.dq_policy_hash),
            ("dq_rule_bundle_version", self.dq_rule_bundle_version),
            ("pipeline_name", self.pipeline_name),
            ("run_type", self.run_type),
            ("pipeline_version", self.pipeline_version),
            ("git_commit", self.git_commit),
            ("dependency_lock_hash", self.dependency_lock_hash),
            ("effective_config_hash", self.effective_config_hash),
            ("effective_config_artifact_id", self.effective_config_artifact_id),
            ("execution_fingerprint", self.execution_fingerprint),
            ("composite_run_identity", self.composite_run_identity),
            ("manifest_id", self.manifest_id),
            ("contract_ref", self.contract_ref),
            ("contract_version", self.contract_version),
            ("normalization_profile_ref", self.normalization_profile_ref),
            ("normalization_profile_version", self.normalization_profile_version),
            ("normalization_profile_hash", self.normalization_profile_hash),
            ("exact_replay", self.exact_replay),
            ("required_persistence_profile", self.required_persistence_profile),
            ("input_snapshot_refs", list(self.input_snapshot_refs)),
            ("input_snapshot_ids", list(self.input_snapshot_ids)),
            ("input_snapshot_fingerprint", self.input_snapshot_fingerprint),
            (
                "silver_filter_compatibility_mode",
                self.silver_filter_compatibility_mode,
            ),
            ("memory_decision_trace", list(self.memory_decision_trace)),
            ("run_context", self.run_context),
        )
        for key, value in optional_values:
            if is_empty_checkpoint_metadata_value(value):
                continue
            result[key] = value
        return result

    @staticmethod
    def from_dict(data: JsonDict) -> CheckpointMetadata:
        """Create CheckpointMetadata from dictionary."""
        return CheckpointMetadata(
            records_processed=_coerce_records_processed(
                data.get("records_processed", 0)
            ),
            dq_contract_compatibility_hash=data.get("dq_contract_compatibility_hash"),
            dq_policy_hash=data.get("dq_policy_hash"),
            dq_rule_bundle_version=data.get("dq_rule_bundle_version"),
            pipeline_name=_optional_stripped_text(data.get("pipeline_name")),
            run_type=_optional_stripped_text(data.get("run_type")),
            pipeline_version=data.get("pipeline_version"),
            git_commit=cast(_OPTIONAL_STR, data.get("git_commit")),
            dependency_lock_hash=_extract_anchor(data, "dependency_lock_hash"),
            effective_config_hash=data.get("effective_config_hash"),
            effective_config_artifact_id=data.get("effective_config_artifact_id"),
            execution_fingerprint=data.get("execution_fingerprint"),
            composite_run_identity=_extract_anchor(data, "composite_run_identity"),
            manifest_id=_extract_anchor(data, "manifest_id"),
            contract_ref=cast(_OPTIONAL_STR, data.get("contract_ref")),
            contract_version=cast(_OPTIONAL_STR, data.get("contract_version")),
            normalization_profile_ref=_extract_anchor(
                data,
                "normalization_profile_ref",
            ),
            normalization_profile_version=_extract_anchor(
                data,
                "normalization_profile_version",
            ),
            normalization_profile_hash=_extract_anchor(
                data,
                "normalization_profile_hash",
            ),
            exact_replay=cast(_OPTIONAL_BOOL, data.get("exact_replay")),
            required_persistence_profile=_extract_anchor(
                data,
                "required_persistence_profile",
            ),
            input_snapshot_refs=coerce_snapshot_refs(data.get("input_snapshot_refs")),
            input_snapshot_ids=coerce_snapshot_ids(data.get("input_snapshot_ids")),
            input_snapshot_fingerprint=cast(
                _OPTIONAL_STR, data.get("input_snapshot_fingerprint")
            ),
            silver_filter_compatibility_mode=_extract_anchor(
                data,
                "silver_filter_compatibility_mode",
            ),
            memory_decision_trace=_coerce_json_dict_sequence(
                data.get("memory_decision_trace")
            ),
            run_context=data.get("run_context"),
        )

    def checkpoint_execution_identity_payload(self) -> JsonDict:
        """Return the canonical checkpoint execution-identity fallback payload."""
        snapshot_fingerprint = (
            self.input_snapshot_fingerprint
            if self.input_snapshot_fingerprint is not None
            else compute_input_snapshot_identity_fingerprint(
                _snapshot_fingerprint_inputs(
                    self.input_snapshot_refs, self.input_snapshot_ids
                )
            )
        )
        normalized_payload = normalize_execution_identity_payload(
            {
                "pipeline_name": self.pipeline_name,
                "run_type": self.run_type,
                "pipeline_version": self.pipeline_version,
                "git_commit": self.git_commit,
                "dependency_lock_hash": self.dependency_lock_hash,
                "effective_config_hash": self.effective_config_hash,
                "dq_contract_compatibility_hash": self.dq_contract_compatibility_hash,
                "contract_ref": self.contract_ref,
                "contract_version": self.contract_version,
                "normalization_profile_ref": self.normalization_profile_ref,
                "normalization_profile_version": (self.normalization_profile_version),
                "normalization_profile_hash": self.normalization_profile_hash,
                "effective_config_artifact_id": self.effective_config_artifact_id,
                "exact_replay": self.exact_replay,
                "input_snapshot_fingerprint": snapshot_fingerprint,
                "silver_filter_compatibility_mode": (
                    self.silver_filter_compatibility_mode
                ),
            }
        )
        return {
            key: value for key, value in normalized_payload.items() if value is not None
        }

    def checkpoint_execution_identity_fingerprint(self) -> str | None:
        """Return the deterministic checkpoint execution-identity fingerprint."""
        payload = self.checkpoint_execution_identity_payload()
        if not payload:
            return None
        return compute_execution_identity_fingerprint(payload)

    def missing_required_anchors(
        self,
        required_fields: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return required checkpoint anchors that are absent on this metadata."""
        missing: list[str] = []
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if is_empty_checkpoint_metadata_value(value):
                missing.append(field_name)
        return tuple(missing)


__all__ = [
    "CheckpointCompatibilityResult",
    "CheckpointMetadata",
]
