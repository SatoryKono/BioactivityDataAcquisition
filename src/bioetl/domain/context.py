"""Domain execution context objects.

The runtime model is intentionally split:
- ``PipelineRunContext`` carries launch-time execution parameters used to
  assemble and start a pipeline run.
- ``PipelineContext`` carries in-run processing state used by record, batch,
  and write paths after launch-time resolution is complete.

Control-plane provenance is modeled separately via
``bioetl.domain.control_plane.run_manifest.RunManifest`` and must not be folded
back into a universal runtime manifest object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bioetl.domain.context_cached_bronze import CachedBronzeContext
from bioetl.domain.context_filtering import InputFilterContext, VacuumSettings
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BatchID, ExecutionContext, RunID, RunType
from bioetl.domain.types.contract_identity import (
    ContractIdentity,
    DQContractCompatibility,
)

__all__ = [
    "CachedBronzeContext",
    "InputFilterContext",
    "MISSING_RUNTIME_TIMESTAMP",
    "PipelineContext",
    "PipelineRunContext",
    "VacuumSettings",
    "current_utc_time",
]


MISSING_RUNTIME_TIMESTAMP = datetime(1970, 1, 1, tzinfo=UTC)
"""Deterministic sentinel for compatibility-only direct context construction."""


def current_utc_time() -> datetime:
    """Return the sanctioned domain UTC timestamp source."""
    return datetime.now(UTC)


def _normalize_correlation_value(value: object | None) -> str | None:
    """Normalize one optional correlation field to a non-empty string."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_dq_contract_alignment(
    contract_identity: ContractIdentity,
    dq_contract_compatibility: DQContractCompatibility | None,
) -> list[str]:
    """Return DQ alignment issues between contract identity and DQ compatibility."""
    if dq_contract_compatibility is None:
        return []
    issues: list[str] = []
    checks = (
        (
            "DQ policy ref mismatch between contract identity and DQ compatibility",
            contract_identity.dq_policy_ref,
            dq_contract_compatibility.policy_ref,
        ),
        (
            "Rule bundle version mismatch between contract identity and DQ compatibility",
            contract_identity.rule_bundle_version,
            dq_contract_compatibility.rule_bundle_version,
        ),
    )
    for message, expected, actual in checks:
        if expected is None or expected == actual:
            continue
        issues.append(message)
    return issues


def _validate_manifest_contract_alignment(
    contract_identity: ContractIdentity,
    manifest_id: str | None,
) -> list[str]:
    """Return manifest-level contract alignment issues."""
    if manifest_id is None:
        return []
    if contract_identity.contract_ref:
        return []
    return ["Contract identity missing contract reference"]


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """In-run processing context for record, batch, and write execution paths."""

    run_id: RunID
    run_type: RunType
    logger: LoggerPort
    started_at: datetime = field(default=MISSING_RUNTIME_TIMESTAMP)
    source_batch_id: BatchID | None = None
    replay_timestamp_anchor: datetime | None = None
    pipeline_name: str | None = None

    @classmethod
    def create(
        cls,
        run_id: RunID,
        run_type: RunType,
        logger: LoggerPort,
        started_at: datetime | None = None,
        source_batch_id: BatchID | None = None,
        replay_timestamp_anchor: datetime | None = None,
        pipeline_name: str | None = None,
    ) -> PipelineContext:
        """Create a new PipelineContext with explicit timestamp ownership.

        Args:
            run_id: Unique identifier for the pipeline run.
            run_type: Type of run (incremental, backfill, rebuild).
            logger: Structured logger port for pipeline-level logging.
            started_at: UTC start timestamp captured by the caller. When omitted,
                the compatibility constructor carries a deterministic sentinel.
            replay_timestamp_anchor: Optional deterministic timestamp used for
                replay-facing artifacts that must not drift between exact replays.
            pipeline_name: Optional pipeline name for context identification.

        Returns:
            New PipelineContext instance with all fields set.
        """
        return cls(
            run_id=run_id,
            run_type=run_type,
            logger=logger,
            started_at=(
                started_at if started_at is not None else MISSING_RUNTIME_TIMESTAMP
            ),
            source_batch_id=source_batch_id,
            replay_timestamp_anchor=replay_timestamp_anchor,
            pipeline_name=pipeline_name,
        )

    def bind_logger(
        self,
        **kwargs: Any,  # Any: structlog-compatible key=value pairs
    ) -> PipelineContext:
        """Bind additional context to the logger.

        Args:
            **kwargs: Key-value pairs to bind to the structured logger (structlog-compatible).

        Returns:
            New PipelineContext with the bound logger; all other fields unchanged.
        """
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
            started_at=self.started_at,
            source_batch_id=self.source_batch_id,
            replay_timestamp_anchor=self.replay_timestamp_anchor,
        )

    def with_source_batch_id(self, source_batch_id: BatchID | None) -> PipelineContext:
        """Return a new context with batch lineage set for the active transform path."""
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=self.logger,
            started_at=self.started_at,
            source_batch_id=source_batch_id,
            replay_timestamp_anchor=self.replay_timestamp_anchor,
        )


@dataclass(frozen=True, slots=True)
class PipelineRunContext:
    """Launch/execution descriptor used to configure and start a pipeline run."""

    pipeline_name: str
    run_id: RunID
    run_type: RunType
    started_at: datetime = field(default=MISSING_RUNTIME_TIMESTAMP)
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    contract_identity: ContractIdentity | None = None
    dq_contract_compatibility: DQContractCompatibility | None = None

    resume: bool = False
    dry_run: bool = False
    vacuum: VacuumSettings = field(default_factory=VacuumSettings)
    input_filter: InputFilterContext = field(
        default_factory=InputFilterContext.disabled
    )
    cached_bronze: CachedBronzeContext = field(
        default_factory=CachedBronzeContext.disabled
    )
    exact_replay: bool = False

    limit: int | None = None
    query: str | None = None
    start_offset: int | None = None
    log_level: str = "INFO"
    ignore_yaml_filter: bool = False
    skip_gold: bool = False
    tracing_enabled_override: bool | None = None
    execution_context: ExecutionContext = ExecutionContext.ISOLATED

    @property
    def has_input_filter(self) -> bool:
        """Check if input filtering is enabled."""
        return bool(self.input_filter.enabled)

    @property
    def has_cached_bronze(self) -> bool:
        """Check if cached Bronze mode is enabled."""
        return bool(self.cached_bronze.enabled)

    @property
    def vacuum_enabled_override(self) -> bool | None:
        """Return the explicit vacuum override, if one was provided."""
        enabled = self.vacuum.enabled
        return None if enabled is None else bool(enabled)

    def log_correlation_fields(self) -> dict[str, str]:
        """Return the mandatory bound logging fields for one pipeline run.

        The application-layer logging contract requires:
        - ``run_id`` always
        - ``pipeline`` and ``pipeline_name`` always
        - ``manifest_id`` when available
        """
        fields = {
            "run_id": str(self.run_id),
            "pipeline": self.pipeline_name,
            "pipeline_name": self.pipeline_name,
        }
        manifest_id = _normalize_correlation_value(self.manifest_id)
        if manifest_id is not None:
            fields["manifest_id"] = manifest_id
        return fields

    def validate_contract_consistency(self) -> list[str]:
        """Validate contract identity consistency across runtime components.

        Returns:
            list[str]: List of consistency issues, empty if all valid
        """
        if self.contract_identity is None:
            return []
        issues = _validate_dq_contract_alignment(
            contract_identity=self.contract_identity,
            dq_contract_compatibility=self.dq_contract_compatibility,
        )
        issues.extend(
            _validate_manifest_contract_alignment(
                contract_identity=self.contract_identity,
                manifest_id=self.manifest_id,
            )
        )
        return issues
