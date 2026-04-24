"""RunContext value object for pipeline execution context.

Provides an immutable container for run-time context that is shared
across all Medallion layers. This ensures consistency of run_id,
timestamps, and pipeline identification across Bronze, Silver, and Gold.

Implements RULES.md §1 - Domain Layer value objects (frozen dataclass).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from typing import cast

from bioetl.domain.types import RunID, RunType

__all__ = [
    "RunContext",
    "RunContextCreateInput",
]


@dataclass(frozen=True, slots=True)
class RunContextCreateInput:
    """Typed input bundle for ``RunContext.create``."""

    run_id: RunID
    run_type: RunType
    started_at: datetime
    provider: str
    entity: str
    transform_version: str | None = None
    transform_steps: tuple[str, ...] = ()
    pipeline_version: str | None = None
    git_commit: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    manifest_id: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    execution_fingerprint: str | None = None


_RUN_CONTEXT_REQUIRED_FIELDS = (
    "run_id",
    "run_type",
    "started_at",
    "provider",
    "entity",
)
_RUN_CONTEXT_OPTIONAL_DEFAULTS: dict[str, object] = {
    "transform_version": None,
    "transform_steps": (),
    "pipeline_version": None,
    "git_commit": None,
    "config_hash": None,
    "resolved_config_hash": None,
    "effective_config_hash": None,
    "manifest_id": None,
    "contract_ref": None,
    "contract_version": None,
    "contract_schema_hash": None,
    "dq_policy_ref": None,
    "rule_bundle_version": None,
    "dq_contract_compatibility_hash": None,
    "effective_config_artifact_id": None,
    "execution_fingerprint": None,
}


def _resolve_create_input_value(
    *,
    field_name: str,
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> object:
    if field_name in overrides:
        return overrides[field_name]
    if field_name in _RUN_CONTEXT_OPTIONAL_DEFAULTS and inputs is None:
        return _RUN_CONTEXT_OPTIONAL_DEFAULTS[field_name]
    if inputs is None:
        raise TypeError(
            f"RunContext.create() missing required argument: '{field_name}'"
        )
    return getattr(inputs, field_name)


def _coerce_run_context_create_input(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> RunContextCreateInput:
    _ensure_required_create_input_fields(inputs, overrides)
    return RunContextCreateInput(
        run_id=cast(
            RunID,
            _resolve_create_input_value(
                field_name="run_id",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        run_type=cast(
            RunType,
            _resolve_create_input_value(
                field_name="run_type",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        started_at=cast(
            datetime,
            _resolve_create_input_value(
                field_name="started_at",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        provider=cast(
            str,
            _resolve_create_input_value(
                field_name="provider",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        entity=cast(
            str,
            _resolve_create_input_value(
                field_name="entity",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        transform_version=cast(
            str | None,
            _resolve_create_input_value(
                field_name="transform_version",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        transform_steps=tuple(
            cast(
                tuple[str, ...] | None,
                _resolve_create_input_value(
                    field_name="transform_steps",
                    inputs=inputs,
                    overrides=overrides,
                ),
            )
            or ()
        ),
        pipeline_version=cast(
            str | None,
            _resolve_create_input_value(
                field_name="pipeline_version",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        git_commit=cast(
            str | None,
            _resolve_create_input_value(
                field_name="git_commit",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        config_hash=cast(
            str | None,
            _resolve_create_input_value(
                field_name="config_hash",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        resolved_config_hash=cast(
            str | None,
            _resolve_create_input_value(
                field_name="resolved_config_hash",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        effective_config_hash=cast(
            str | None,
            _resolve_create_input_value(
                field_name="effective_config_hash",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        manifest_id=cast(
            str | None,
            _resolve_create_input_value(
                field_name="manifest_id",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        contract_ref=cast(
            str | None,
            _resolve_create_input_value(
                field_name="contract_ref",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        contract_version=cast(
            str | None,
            _resolve_create_input_value(
                field_name="contract_version",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        contract_schema_hash=cast(
            str | None,
            _resolve_create_input_value(
                field_name="contract_schema_hash",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        dq_policy_ref=cast(
            str | None,
            _resolve_create_input_value(
                field_name="dq_policy_ref",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        rule_bundle_version=cast(
            str | None,
            _resolve_create_input_value(
                field_name="rule_bundle_version",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        dq_contract_compatibility_hash=cast(
            str | None,
            _resolve_create_input_value(
                field_name="dq_contract_compatibility_hash",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        effective_config_artifact_id=cast(
            str | None,
            _resolve_create_input_value(
                field_name="effective_config_artifact_id",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
        execution_fingerprint=cast(
            str | None,
            _resolve_create_input_value(
                field_name="execution_fingerprint",
                inputs=inputs,
                overrides=overrides,
            ),
        ),
    )


def _ensure_required_create_input_fields(
    inputs: RunContextCreateInput | None,
    overrides: dict[str, object],
) -> None:
    for field_name in _RUN_CONTEXT_REQUIRED_FIELDS:
        _resolve_create_input_value(
            field_name=field_name,
            inputs=inputs,
            overrides=overrides,
        )


@dataclass(frozen=True, slots=True)
class RunContext:
    """Immutable context for a pipeline run.

    Contains all information needed to create consistent metadata across
    all Medallion layers. Created once at pipeline start and passed to
    MetadataCoordinator.

    Attributes:
        run_id: Unique identifier for the pipeline run (UUID).
        run_type: Type of run (incremental, backfill, rebuild).
        started_at: UTC timestamp when the run started.
        pipeline_name: Full pipeline name (e.g., 'chembl_activity').
        provider: Data provider name (e.g., 'chembl').
        entity: Entity type (e.g., 'activity').
        transform_version: Optional semver version of transform (e.g., '1.0.0').
        transform_steps: Tuple of transform step names applied.
        pipeline_version: Pipeline version for reproducibility (e.g., '1.0.0').
        git_commit: Git commit hash for reproducibility.
        config_hash: SHA256 hash of pipeline configuration for change detection.
        resolved_config_hash: SHA256 hash of resolved declarative configuration.
        effective_config_hash: SHA256 hash of final effective execution configuration.
        manifest_id: Optional control-plane manifest identifier linked to the run.
        dq_contract_compatibility_hash: SHA256 hash of DQ contract compatibility for reproducibility.
        effective_config_artifact_id: Reference to the effective config artifact for this run.
        execution_fingerprint: Canonical execution identity fingerprint from the run manifest.

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> context = RunContext(
        ...     run_id=RunID(uuid4()),
        ...     run_type=RunType.INCREMENTAL,
        ...     started_at=datetime.now(UTC),
        ...     pipeline_name="chembl_activity",
        ...     provider="chembl",
        ...     entity="activity",
        ...     transform_version="1.0.0",
        ...     transform_steps=("normalize_values", "add_metadata"),
        ...     pipeline_version="1.0.0",
        ...     git_commit="abc123",
        ...     config_hash="sha256:...",
        ... )
    """

    run_id: RunID
    run_type: RunType
    started_at: datetime
    pipeline_name: str
    provider: str
    entity: str
    transform_version: str | None = None
    transform_steps: tuple[str, ...] = ()
    pipeline_version: str | None = None
    git_commit: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    manifest_id: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    # Data Quality integration
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    execution_fingerprint: str | None = None

    def __post_init__(self) -> None:
        """Validate run context after initialization."""
        if self.started_at.tzinfo is None:
            raise ValueError(
                "started_at must be timezone-aware (UTC). "
                "Use datetime.now(UTC) or datetime(..., tzinfo=timezone.utc)."
            )

        if not self.pipeline_name:
            raise ValueError("pipeline_name cannot be empty")

        if not self.provider:
            raise ValueError("provider cannot be empty")

        if not self.entity:
            raise ValueError("entity cannot be empty")

    @classmethod
    def create(
        cls,
        inputs: RunContextCreateInput | None = None,
        **overrides: object,
    ) -> RunContext:
        """Factory method to create RunContext with derived pipeline name."""
        create_input = _coerce_run_context_create_input(inputs, overrides)
        return cls(
            run_id=create_input.run_id,
            run_type=create_input.run_type,
            started_at=create_input.started_at,
            pipeline_name=f"{create_input.provider}_{create_input.entity}",
            provider=create_input.provider,
            entity=create_input.entity,
            transform_version=create_input.transform_version,
            transform_steps=create_input.transform_steps,
            pipeline_version=create_input.pipeline_version,
            git_commit=create_input.git_commit,
            config_hash=create_input.config_hash,
            resolved_config_hash=create_input.resolved_config_hash,
            effective_config_hash=create_input.effective_config_hash,
            manifest_id=create_input.manifest_id,
            contract_ref=create_input.contract_ref,
            contract_version=create_input.contract_version,
            contract_schema_hash=create_input.contract_schema_hash,
            dq_policy_ref=create_input.dq_policy_ref,
            rule_bundle_version=create_input.rule_bundle_version,
            dq_contract_compatibility_hash=create_input.dq_contract_compatibility_hash,
            effective_config_artifact_id=create_input.effective_config_artifact_id,
            execution_fingerprint=create_input.execution_fingerprint,
        )
