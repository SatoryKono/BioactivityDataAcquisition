"""Launch-time pipeline run context value object."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from bioetl.domain.context_cached_bronze import CachedBronzeContext
from bioetl.domain.context_correlation import _normalize_correlation_value
from bioetl.domain.context_filtering import InputFilterContext, VacuumSettings
from bioetl.domain.context_time import (
    MISSING_RUNTIME_TIMESTAMP,
    resolve_context_started_at,
)
from bioetl.domain.context_validation import (
    _validate_contract_identity_completeness,
    _validate_dq_contract_alignment,
    _validate_manifest_contract_alignment,
)
from bioetl.domain.types import ExecutionContext, RunID, RunType
from bioetl.domain.types.contract_identity import (
    ContractIdentity,
    DQContractCompatibility,
)


def _resolve_vacuum_settings(vacuum: VacuumSettings | None) -> VacuumSettings:
    """Return explicit vacuum settings or the default disabled override."""
    return vacuum if vacuum is not None else VacuumSettings()


def _resolve_input_filter_context(
    input_filter: InputFilterContext | None,
) -> InputFilterContext:
    """Return explicit input-filter context or the disabled default."""
    return input_filter if input_filter is not None else InputFilterContext.disabled()


def _resolve_cached_bronze_context(
    cached_bronze: CachedBronzeContext | None,
) -> CachedBronzeContext:
    """Return explicit cached-Bronze context or the disabled default."""
    return (
        cached_bronze if cached_bronze is not None else CachedBronzeContext.disabled()
    )


def _build_pipeline_run_context_kwargs(
    raw: dict[str, object],
) -> dict[str, object]:
    """Normalize create() kwargs into constructor-ready PipelineRunContext fields."""
    payload = dict(raw)
    started_at = payload.pop("started_at", None)
    clock = payload.pop("clock", None)
    payload["started_at"] = resolve_context_started_at(
        started_at=started_at,  # type: ignore[arg-type]
        clock=clock,  # type: ignore[arg-type]
    )
    payload["vacuum"] = _resolve_vacuum_settings(payload.get("vacuum"))  # type: ignore[arg-type]
    payload["input_filter"] = _resolve_input_filter_context(
        payload.get("input_filter")  # type: ignore[arg-type]
    )
    payload["cached_bronze"] = _resolve_cached_bronze_context(
        payload.get("cached_bronze")  # type: ignore[arg-type]
    )
    return payload


@dataclass(frozen=True, slots=True)
class PipelineRunContext:
    """Launch/execution descriptor used to configure and start a pipeline run."""

    pipeline_name: str
    run_id: RunID
    run_type: RunType
    started_at: datetime = field(default=MISSING_RUNTIME_TIMESTAMP)
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    input_snapshot_fingerprint: str | None = None
    resume_run_id: str | None = None
    resume_manifest_id: str | None = None
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    source_fingerprint: str | None = None
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
    required_persistence_profile: str | None = None
    required_persistence_profile_opt_down: bool = False

    limit: int | None = None
    query: str | None = None
    start_offset: int | None = None
    log_level: str = "INFO"
    ignore_yaml_filter: bool = False
    skip_gold: bool = False
    tracing_enabled_override: bool | None = None
    debug_export_enabled: bool = False
    debug_export_formats: tuple[str, ...] = ()
    debug_export_dir: str | None = None
    workflow_id: str = "standalone"
    workflow_run_id: str | None = None
    workflow_name: str | None = None
    workflow_step_id: str | None = None
    execution_context: ExecutionContext = ExecutionContext.ISOLATED

    @classmethod
    def create(cls, **kwargs: object) -> PipelineRunContext:
        """Create a new PipelineRunContext with explicit timestamp ownership.

        Accepts the same keyword fields as ``PipelineRunContext`` plus optional
        ``started_at`` / ``clock`` resolution inputs used only at construction.
        """
        constructor = cast(Callable[..., PipelineRunContext], cls)
        return constructor(**_build_pipeline_run_context_kwargs(kwargs))

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
        """Return the mandatory bound logging fields for one pipeline run."""
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
        """Validate contract identity consistency across runtime components."""
        if self.contract_identity is None:
            return []
        issues = _validate_dq_contract_alignment(
            contract_identity=self.contract_identity,
            dq_contract_compatibility=self.dq_contract_compatibility,
        )
        issues.extend(
            _validate_contract_identity_completeness(
                contract_identity=self.contract_identity
            )
        )
        issues.extend(
            _validate_manifest_contract_alignment(
                contract_identity=self.contract_identity,
                manifest_id=self.manifest_id,
            )
        )
        return issues


__all__ = ["PipelineRunContext"]
