"""Domain types for checkpoint metadata with DQ contract compatibility.

Extends checkpoint metadata to include Data Quality contract information
for resume compatibility validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class CheckpointMetadata:
    """Extended checkpoint metadata with DQ contract compatibility information.

    Attributes:
        records_processed: Count of records processed so far.
        dq_contract_compatibility_hash: Hash of DQ contract for compatibility checking.
        dq_policy_hash: Hash of DQ policy configuration.
        dq_rule_bundle_version: Version of DQ rule bundle.
        pipeline_version: Version of the pipeline configuration.
        effective_config_hash: Canonical effective-config hash for execution identity.
        effective_config_artifact_id: Effective-config artifact reference for provenance.
        execution_fingerprint: Stable execution identity fingerprint.
        run_context: Additional run context information.
    """

    records_processed: int
    dq_contract_compatibility_hash: str | None = None
    dq_policy_hash: str | None = None
    dq_rule_bundle_version: str | None = None
    pipeline_version: str | None = None
    effective_config_hash: str | None = None
    effective_config_artifact_id: str | None = None
    execution_fingerprint: str | None = None
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
            pipeline_version=legacy_metadata.get("pipeline_version"),
            effective_config_hash=legacy_metadata.get("effective_config_hash"),
            effective_config_artifact_id=legacy_metadata.get(
                "effective_config_artifact_id"
            ),
            execution_fingerprint=legacy_metadata.get("execution_fingerprint"),
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
            ("pipeline_version", self.pipeline_version),
            ("effective_config_hash", self.effective_config_hash),
            ("effective_config_artifact_id", self.effective_config_artifact_id),
            ("execution_fingerprint", self.execution_fingerprint),
            ("run_context", self.run_context),
        )
        for key, value in optional_values:
            if value:
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
            pipeline_version=data.get("pipeline_version"),
            effective_config_hash=data.get("effective_config_hash"),
            effective_config_artifact_id=data.get("effective_config_artifact_id"),
            execution_fingerprint=data.get("execution_fingerprint"),
            run_context=data.get("run_context"),
        )


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
