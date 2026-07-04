"""Shared runtime, pipeline, and environment metadata builders."""

from __future__ import annotations

import platform
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Final

from bioetl import __version__ as BIOETL_VERSION
from bioetl.domain.models.metadata import (
    EnvironmentMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext

_RUN_TYPE_TO_ENUM: Final[dict[RunType, RunTypeEnum]] = {
    RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
    RunType.BACKFILL: RunTypeEnum.BACKFILL,
    RunType.REBUILD: RunTypeEnum.REBUILD,
}


class EnvironmentMetadataRuntimeService:
    """Process-lifetime cache for environment metadata."""

    _cached_environment: ClassVar[EnvironmentMetadata | None] = None

    @classmethod
    def get(cls) -> EnvironmentMetadata:
        """Return immutable process environment metadata."""
        if cls._cached_environment is None:
            cls._cached_environment = EnvironmentMetadata(
                hostname=socket.gethostname(),
                python_version=platform.python_version(),
                bioetl_version=BIOETL_VERSION,
            )
        return cls._cached_environment

    @classmethod
    def reset(cls) -> None:
        """Clear cached environment metadata for deterministic tests."""
        cls._cached_environment = None


@dataclass(slots=True)
class RunMetadataAssembler:
    """Assemble runtime and pipeline metadata from a run context."""

    run_context: RunContext
    environment_runtime_service: type[EnvironmentMetadataRuntimeService] = (
        EnvironmentMetadataRuntimeService
    )

    @property
    def run_type_enum(self) -> RunTypeEnum:
        """Map domain RunType to metadata RunTypeEnum."""
        return _RUN_TYPE_TO_ENUM[self.run_context.run_type]

    @property
    def environment_metadata(self) -> EnvironmentMetadata:
        """Return process environment metadata."""
        return self.environment_runtime_service.get()

    def build_runtime_metadata(
        self,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
        input_snapshot_fingerprint: str | None = None,
    ) -> RuntimeMetadata:
        """Build RuntimeMetadata with consistent run_id and run_type."""
        return RuntimeMetadata(
            run_id=str(self.run_context.run_id),
            manifest_id=self.run_context.manifest_id,
            run_type=self.run_type_enum,
            started_at_utc=started_at or self.run_context.started_at,
            completed_at_utc=completed_at,
            duration_seconds=duration_seconds,
            exact_replay=self.run_context.exact_replay,
            replay_of_run_id=self.run_context.replay_of_run_id,
            replay_of_manifest_id=self.run_context.replay_of_manifest_id,
            input_snapshot_fingerprint=(
                self.run_context.input_snapshot_fingerprint
                if input_snapshot_fingerprint is None
                else input_snapshot_fingerprint
            ),
        )

    def build_pipeline_metadata(self) -> PipelineMetadata:
        """Build PipelineMetadata with versioning from run context."""
        return PipelineMetadata(
            name=self.run_context.pipeline_name,
            provider=self.run_context.provider,
            entity=self.run_context.entity,
            version=self.run_context.pipeline_version or "1.0.0",
            git_commit=self.run_context.git_commit,
            dependency_lock_hash=self.run_context.dependency_lock_hash,
            config_hash=self.run_context.config_hash,
            resolved_config_hash=self.run_context.resolved_config_hash,
            effective_config_hash=self.run_context.effective_config_hash,
            effective_config_artifact_id=self.run_context.effective_config_artifact_id,
            execution_fingerprint=self.run_context.execution_fingerprint,
            contract_ref=self.run_context.contract_ref,
            contract_version=self.run_context.contract_version,
            contract_schema_hash=self.run_context.contract_schema_hash,
            dq_policy_ref=self.run_context.dq_policy_ref,
            rule_bundle_version=self.run_context.rule_bundle_version,
            normalization_profile_ref=self.run_context.normalization_profile_ref,
            normalization_profile_version=(
                self.run_context.normalization_profile_version
            ),
            normalization_profile_hash=self.run_context.normalization_profile_hash,
            dq_contract_compatibility_hash=(
                self.run_context.dq_contract_compatibility_hash
            ),
        )


__all__ = [
    "EnvironmentMetadataRuntimeService",
    "RunMetadataAssembler",
]
