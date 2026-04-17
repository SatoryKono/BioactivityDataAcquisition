"""Domain types for checkpoint metadata with DQ contract compatibility."""

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
    coerce_snapshot_ids,
    extract_run_context_anchor,
    is_empty_checkpoint_metadata_value,
)
from bioetl.domain.types.checkpoint_compatibility_result import (
    CheckpointCompatibilityResult,
)

_OPTIONAL_STR = str | None
_OPTIONAL_BOOL = bool | None


@dataclass(frozen=True, slots=True)
class CheckpointMetadata:
    """Extended checkpoint metadata with DQ contract compatibility information.

    Attributes:
        records_processed: Count of records processed so far.
        dq_contract_compatibility_hash: Hash of DQ contract for compatibility checking.
        dq_policy_hash: Hash of DQ policy configuration.
        dq_rule_bundle_version: Version of DQ rule bundle.
        pipeline_name: Canonical pipeline name used for execution identity.
        run_type: Canonical run type used for execution identity.
        pipeline_version: Version of the pipeline configuration.
        effective_config_hash: Canonical effective-config hash for execution identity.
        effective_config_artifact_id: Effective-config artifact reference for provenance.
        execution_fingerprint: Canonical execution-identity fingerprint shared
            across manifest, checkpoint, and runtime compatibility surfaces.
        composite_run_identity: Occurrence-scoped composite resume anchor used
            to prevent resume across different composite executions.
        manifest_id: Persisted run-manifest identifier for resume identity checks.
        contract_ref: Canonical contract reference for checkpoint compatibility.
        contract_version: Canonical contract version for checkpoint compatibility.
        exact_replay: Whether the checkpoint was created under exact-replay mode.
        input_snapshot_ids: Snapshot identities required for replay-safe resume.
        run_context: Additional run context information.
    """

    records_processed: int
    dq_contract_compatibility_hash: _OPTIONAL_STR = None
    dq_policy_hash: _OPTIONAL_STR = None
    dq_rule_bundle_version: _OPTIONAL_STR = None
    pipeline_name: _OPTIONAL_STR = None
    run_type: _OPTIONAL_STR = None
    pipeline_version: _OPTIONAL_STR = None
    effective_config_hash: _OPTIONAL_STR = None
    effective_config_artifact_id: _OPTIONAL_STR = None
    execution_fingerprint: _OPTIONAL_STR = None
    composite_run_identity: _OPTIONAL_STR = None
    manifest_id: _OPTIONAL_STR = None
    contract_ref: _OPTIONAL_STR = None
    contract_version: _OPTIONAL_STR = None
    exact_replay: _OPTIONAL_BOOL = None
    input_snapshot_ids: tuple[str, ...] = ()
    input_snapshot_fingerprint: _OPTIONAL_STR = None
    run_context: JsonDict | None = None  # Any: run context has heterogeneous values

    @staticmethod
    def from_legacy_metadata(legacy_metadata: JsonDict) -> CheckpointMetadata:
        """Create CheckpointMetadata from legacy metadata format.

        Args:
            legacy_metadata: Legacy checkpoint metadata dictionary.

        Returns:
            CheckpointMetadata instance with legacy data.
        """
        return CheckpointMetadata(
            records_processed=legacy_metadata.get("records_processed", 0),
            dq_contract_compatibility_hash=legacy_metadata.get(
                "dq_contract_compatibility_hash"
            ),
            dq_policy_hash=legacy_metadata.get("dq_policy_hash"),
            dq_rule_bundle_version=legacy_metadata.get("dq_rule_bundle_version"),
            pipeline_name=cast(_OPTIONAL_STR, legacy_metadata.get("pipeline_name")),
            run_type=cast(_OPTIONAL_STR, legacy_metadata.get("run_type")),
            pipeline_version=legacy_metadata.get("pipeline_version"),
            effective_config_hash=legacy_metadata.get("effective_config_hash"),
            effective_config_artifact_id=legacy_metadata.get(
                "effective_config_artifact_id"
            ),
            execution_fingerprint=legacy_metadata.get("execution_fingerprint"),
            composite_run_identity=cast(
                _OPTIONAL_STR,
                legacy_metadata.get("composite_run_identity")
                or extract_run_context_anchor(
                    legacy_metadata,
                    "composite_run_identity",
                ),
            ),
            manifest_id=cast(
                _OPTIONAL_STR,
                legacy_metadata.get("manifest_id")
                or extract_run_context_anchor(legacy_metadata, "manifest_id"),
            ),
            contract_ref=cast(_OPTIONAL_STR, legacy_metadata.get("contract_ref")),
            contract_version=cast(
                _OPTIONAL_STR,
                legacy_metadata.get("contract_version"),
            ),
            exact_replay=cast(_OPTIONAL_BOOL, legacy_metadata.get("exact_replay")),
            input_snapshot_ids=coerce_snapshot_ids(
                legacy_metadata.get("input_snapshot_ids")
            ),
            input_snapshot_fingerprint=cast(
                _OPTIONAL_STR, legacy_metadata.get("input_snapshot_fingerprint")
            ),
            run_context=legacy_metadata.get("run_context"),
        )

    def to_dict(self) -> JsonDict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of checkpoint metadata.
        """
        result: JsonDict = {"records_processed": self.records_processed}
        optional_values: tuple[tuple[str, object | None], ...] = (
            ("dq_contract_compatibility_hash", self.dq_contract_compatibility_hash),
            ("dq_policy_hash", self.dq_policy_hash),
            ("dq_rule_bundle_version", self.dq_rule_bundle_version),
            ("pipeline_name", self.pipeline_name),
            ("run_type", self.run_type),
            ("pipeline_version", self.pipeline_version),
            ("effective_config_hash", self.effective_config_hash),
            ("effective_config_artifact_id", self.effective_config_artifact_id),
            ("execution_fingerprint", self.execution_fingerprint),
            ("composite_run_identity", self.composite_run_identity),
            ("manifest_id", self.manifest_id),
            ("contract_ref", self.contract_ref),
            ("contract_version", self.contract_version),
            ("exact_replay", self.exact_replay),
            ("input_snapshot_ids", list(self.input_snapshot_ids)),
            ("input_snapshot_fingerprint", self.input_snapshot_fingerprint),
            ("run_context", self.run_context),
        )
        for key, value in optional_values:
            if is_empty_checkpoint_metadata_value(value):
                continue
            result[key] = value
        return result

    @staticmethod
    def from_dict(data: JsonDict) -> CheckpointMetadata:
        """Create CheckpointMetadata from dictionary.

        Args:
            data: Dictionary with checkpoint metadata.

        Returns:
            CheckpointMetadata instance.
        """
        return CheckpointMetadata(
            records_processed=data.get("records_processed", 0),
            dq_contract_compatibility_hash=data.get("dq_contract_compatibility_hash"),
            dq_policy_hash=data.get("dq_policy_hash"),
            dq_rule_bundle_version=data.get("dq_rule_bundle_version"),
            pipeline_name=cast(_OPTIONAL_STR, data.get("pipeline_name")),
            run_type=cast(_OPTIONAL_STR, data.get("run_type")),
            pipeline_version=data.get("pipeline_version"),
            effective_config_hash=data.get("effective_config_hash"),
            effective_config_artifact_id=data.get("effective_config_artifact_id"),
            execution_fingerprint=data.get("execution_fingerprint"),
            composite_run_identity=cast(
                _OPTIONAL_STR,
                data.get("composite_run_identity")
                or extract_run_context_anchor(data, "composite_run_identity"),
            ),
            manifest_id=cast(
                _OPTIONAL_STR,
                data.get("manifest_id")
                or extract_run_context_anchor(data, "manifest_id"),
            ),
            contract_ref=cast(_OPTIONAL_STR, data.get("contract_ref")),
            contract_version=cast(_OPTIONAL_STR, data.get("contract_version")),
            exact_replay=cast(_OPTIONAL_BOOL, data.get("exact_replay")),
            input_snapshot_ids=coerce_snapshot_ids(data.get("input_snapshot_ids")),
            input_snapshot_fingerprint=cast(
                _OPTIONAL_STR, data.get("input_snapshot_fingerprint")
            ),
            run_context=data.get("run_context"),
        )

    def checkpoint_execution_identity_payload(self) -> JsonDict:
        """Return the canonical checkpoint execution-identity fallback payload.

        This payload mirrors the canonical execution identity contract used by
        manifest persistence, but only includes the checkpoint-resident anchors
        that remain available during resume validation.
        """

        snapshot_fingerprint = (
            self.input_snapshot_fingerprint
            if self.input_snapshot_fingerprint is not None
            else compute_input_snapshot_identity_fingerprint(
                list(self.input_snapshot_ids)
            )
        )
        normalized_payload = normalize_execution_identity_payload(
            {
                "pipeline_name": self.pipeline_name,
                "run_type": self.run_type,
                "pipeline_version": self.pipeline_version,
                "effective_config_hash": self.effective_config_hash,
                "dq_contract_compatibility_hash": self.dq_contract_compatibility_hash,
                "contract_ref": self.contract_ref,
                "contract_version": self.contract_version,
                "effective_config_artifact_id": self.effective_config_artifact_id,
                "exact_replay": self.exact_replay,
                "input_snapshot_fingerprint": snapshot_fingerprint,
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


__all__ = [
    "CheckpointCompatibilityResult",
    "CheckpointMetadata",
]
