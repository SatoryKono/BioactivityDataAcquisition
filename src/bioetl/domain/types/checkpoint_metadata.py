"""Domain types for checkpoint metadata with DQ contract compatibility.

Extends checkpoint metadata to include Data Quality contract information
for resume compatibility validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from bioetl.domain.normalization import (
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
    normalize_execution_identity_payload,
)
from bioetl.domain.types import JsonDict


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
        manifest_id: Persisted run-manifest identifier for resume identity checks.
        contract_ref: Canonical contract reference for checkpoint compatibility.
        contract_version: Canonical contract version for checkpoint compatibility.
        exact_replay: Whether the checkpoint was created under exact-replay mode.
        input_snapshot_ids: Snapshot identities required for replay-safe resume.
        run_context: Additional run context information.
    """

    records_processed: int
    dq_contract_compatibility_hash: str | None = None
    dq_policy_hash: str | None = None
    dq_rule_bundle_version: str | None = None
    pipeline_name: str | None = None
    run_type: str | None = None
    pipeline_version: str | None = None
    effective_config_hash: str | None = None
    effective_config_artifact_id: str | None = None
    execution_fingerprint: str | None = None
    manifest_id: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    exact_replay: bool | None = None
    input_snapshot_ids: tuple[str, ...] = ()
    input_snapshot_fingerprint: str | None = None
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
            pipeline_name=cast("str | None", legacy_metadata.get("pipeline_name")),
            run_type=cast("str | None", legacy_metadata.get("run_type")),
            pipeline_version=legacy_metadata.get("pipeline_version"),
            effective_config_hash=legacy_metadata.get("effective_config_hash"),
            effective_config_artifact_id=legacy_metadata.get(
                "effective_config_artifact_id"
            ),
            execution_fingerprint=legacy_metadata.get("execution_fingerprint"),
            manifest_id=cast(
                "str | None",
                legacy_metadata.get("manifest_id")
                or _extract_manifest_id_from_run_context(legacy_metadata),
            ),
            contract_ref=cast("str | None", legacy_metadata.get("contract_ref")),
            contract_version=cast(
                "str | None",
                legacy_metadata.get("contract_version"),
            ),
            exact_replay=cast("bool | None", legacy_metadata.get("exact_replay")),
            input_snapshot_ids=_coerce_snapshot_ids(
                legacy_metadata.get("input_snapshot_ids")
            ),
            input_snapshot_fingerprint=cast(
                "str | None", legacy_metadata.get("input_snapshot_fingerprint")
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
            ("manifest_id", self.manifest_id),
            ("contract_ref", self.contract_ref),
            ("contract_version", self.contract_version),
            ("exact_replay", self.exact_replay),
            ("input_snapshot_ids", list(self.input_snapshot_ids)),
            ("input_snapshot_fingerprint", self.input_snapshot_fingerprint),
            ("run_context", self.run_context),
        )
        for key, value in optional_values:
            if _is_empty_checkpoint_metadata_value(value):
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
            pipeline_name=cast("str | None", data.get("pipeline_name")),
            run_type=cast("str | None", data.get("run_type")),
            pipeline_version=data.get("pipeline_version"),
            effective_config_hash=data.get("effective_config_hash"),
            effective_config_artifact_id=data.get("effective_config_artifact_id"),
            execution_fingerprint=data.get("execution_fingerprint"),
            manifest_id=cast(
                "str | None",
                data.get("manifest_id") or _extract_manifest_id_from_run_context(data),
            ),
            contract_ref=cast("str | None", data.get("contract_ref")),
            contract_version=cast("str | None", data.get("contract_version")),
            exact_replay=cast("bool | None", data.get("exact_replay")),
            input_snapshot_ids=_coerce_snapshot_ids(data.get("input_snapshot_ids")),
            input_snapshot_fingerprint=cast(
                "str | None", data.get("input_snapshot_fingerprint")
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
            else compute_input_snapshot_identity_fingerprint(list(self.input_snapshot_ids))
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
            key: value
            for key, value in normalized_payload.items()
            if value is not None
        }

    def checkpoint_execution_identity_fingerprint(self) -> str | None:
        """Return the deterministic checkpoint execution-identity fingerprint."""

        payload = self.checkpoint_execution_identity_payload()
        if not payload:
            return None
        return compute_execution_identity_fingerprint(payload)

    def runtime_anchor_payload(self) -> JsonDict:
        """Backward-compatible alias for checkpoint execution-identity payload."""

        return self.checkpoint_execution_identity_payload()

    def runtime_anchor_fingerprint(self) -> str | None:
        """Backward-compatible alias for checkpoint execution-identity fingerprint."""

        return self.checkpoint_execution_identity_fingerprint()


def _extract_manifest_id_from_run_context(data: JsonDict) -> str | None:
    """Backfill manifest_id from legacy run_context payloads when present."""
    run_context = data.get("run_context")
    if not isinstance(run_context, dict):
        return None
    manifest_id = run_context.get("manifest_id")
    if manifest_id is None:
        return None
    text = str(manifest_id).strip()
    return text or None


def _coerce_snapshot_ids(value: object | None) -> tuple[str, ...]:
    """Normalize persisted snapshot identifiers into a stable tuple."""
    if not isinstance(value, (list, tuple)):
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _is_empty_checkpoint_metadata_value(value: object | None) -> bool:
    """Return whether optional checkpoint metadata should be omitted from serialization."""
    if value is None or value == "":
        return True
    if isinstance(value, (tuple, list, dict)):
        return len(value) == 0
    return False


@dataclass(frozen=True, slots=True)
class CheckpointCompatibilityResult:
    """Result of checkpoint compatibility validation.

    Attributes:
        compatible: Whether checkpoint is compatible for resume.
        dq_compatible: Whether DQ contracts are compatible.
        pipeline_compatible: Whether pipeline versions are compatible.
        execution_identity_compatible: Whether execution identity is compatible.
        messages: List of compatibility messages.
    """

    compatible: bool
    dq_compatible: bool
    pipeline_compatible: bool
    messages: list[str]
    execution_identity_compatible: bool = True

    @staticmethod
    def compatible_result() -> CheckpointCompatibilityResult:
        """Create a compatible result.

        Returns:
            CheckpointCompatibilityResult indicating full compatibility.
        """
        return CheckpointCompatibilityResult(
            compatible=True,
            dq_compatible=True,
            pipeline_compatible=True,
            execution_identity_compatible=True,
            messages=["Checkpoint is compatible for resume"],
        )

    @staticmethod
    def incompatible_result(
        dq_compatible: bool = False,
        pipeline_compatible: bool = False,
        execution_identity_compatible: bool = False,
        messages: list[str] | None = None,
    ) -> CheckpointCompatibilityResult:
        """Create an incompatible result.

        Args:
            dq_compatible: Whether DQ contracts are compatible.
            pipeline_compatible: Whether pipeline versions are compatible.
            messages: List of incompatibility messages.

        Returns:
            CheckpointCompatibilityResult indicating incompatibility.
        """
        return CheckpointCompatibilityResult(
            compatible=False,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=execution_identity_compatible,
            messages=messages or [],
        )


__all__ = [
    "CheckpointCompatibilityResult",
    "CheckpointMetadata",
]
