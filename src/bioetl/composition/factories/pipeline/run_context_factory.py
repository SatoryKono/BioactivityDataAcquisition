"""Run-context assembly helpers for pipeline construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.run_context_contract_identity import (
    ContractIdentityResolver,
    NormalizedContractIdentity,
    resolve_contract_identity_for_runtime,
    resolve_contract_identity_snapshot,
    runtime_requires_strict_contract_identity,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_dependency_lock_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.value_objects.run_context import RunContext, RunContextCreateInput

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _get_transform_version(yaml_config: PipelineYamlConfig) -> str | None:
    """Extract transform version from resolved pipeline YAML config."""
    transform = getattr(yaml_config, "transform", None)
    version = getattr(transform, "version", None)
    return str(version) if version is not None else None


def _get_transform_steps(yaml_config: PipelineYamlConfig) -> tuple[str, ...]:
    """Extract transform steps from resolved pipeline YAML config."""
    transform = getattr(yaml_config, "transform", None)
    steps = getattr(transform, "steps", ())
    return tuple(str(step) for step in (steps or ()))


def _build_contract_identity_kwargs(
    contract_identity: NormalizedContractIdentity,
) -> dict[str, str | None]:
    """Map normalized contract identity tuples into ``RunContext`` keyword fields."""
    return {
        "contract_ref": contract_identity[0],
        "contract_version": contract_identity[1],
        "contract_schema_hash": contract_identity[2],
        "dq_policy_ref": contract_identity[3],
        "rule_bundle_version": contract_identity[4],
        "normalization_profile_ref": contract_identity[5],
        "normalization_profile_version": contract_identity[6],
        "normalization_profile_hash": contract_identity[7],
    }


@dataclass(frozen=True, slots=True)
class RunContextFactory:
    """Build ``RunContext`` for metadata coordinator wiring."""

    pipeline_name: str
    provider: str
    entity_type_extractor: Callable[[str], str | None]
    pipeline_version_getter: Callable[[PipelineYamlConfig], str] = get_pipeline_version
    git_commit_getter: Callable[[], str | None] = get_git_commit
    dependency_lock_hash_getter: Callable[[], str | None] = get_dependency_lock_hash
    config_hash_getter: Callable[[PipelineYamlConfig], str] = compute_config_hash
    transform_version_getter: Callable[[PipelineYamlConfig], str | None] = (
        _get_transform_version
    )
    transform_steps_getter: Callable[[PipelineYamlConfig], tuple[str, ...]] = (
        _get_transform_steps
    )
    contract_identity_resolver: ContractIdentityResolver = (
        resolve_contract_identity_snapshot
    )

    def create(
        self,
        *,
        run_id: RunID,
        runtime: RuntimeConfig,
        started_at: datetime,
        yaml_config: PipelineYamlConfig,
        manifest_id: str | None = None,
        execution_fingerprint: str | None = None,
        config_hash: str | None = None,
        resolved_config_hash: str | None = None,
        effective_config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
        exact_replay: bool | None = None,
        replay_of_run_id: str | None = None,
        replay_of_manifest_id: str | None = None,
        input_snapshot_fingerprint: str | None = None,
    ) -> RunContext:
        """Create metadata ``RunContext`` from runtime and resolved YAML."""
        entity = self.entity_type_extractor(self.pipeline_name) or self.pipeline_name
        strict_contract_identity = runtime_requires_strict_contract_identity(runtime)
        contract_identity = resolve_contract_identity_for_runtime(
            resolver=self.contract_identity_resolver,
            provider=self.provider,
            entity=entity,
            strict=strict_contract_identity,
        )
        resolved_hash = (
            self.config_hash_getter(yaml_config)
            if resolved_config_hash is None
            else resolved_config_hash
        )
        legacy_config_hash = config_hash if config_hash is not None else resolved_hash
        return RunContext.create(
            RunContextCreateInput(
                run_id=run_id,
                run_type=runtime.run_type,
                started_at=started_at,
                provider=self.provider,
                entity=entity,
                transform_version=self.transform_version_getter(yaml_config),
                transform_steps=self.transform_steps_getter(yaml_config),
                pipeline_version=self.pipeline_version_getter(yaml_config),
                git_commit=self.git_commit_getter(),
                dependency_lock_hash=self.dependency_lock_hash_getter(),
                config_hash=legacy_config_hash,
                resolved_config_hash=resolved_hash,
                effective_config_hash=effective_config_hash,
                manifest_id=manifest_id,
                execution_fingerprint=execution_fingerprint,
                dq_contract_compatibility_hash=dq_contract_compatibility_hash,
                effective_config_artifact_id=effective_config_artifact_id,
                exact_replay=(
                    bool(getattr(runtime, "exact_replay", False))
                    if exact_replay is None
                    else exact_replay
                ),
                required_persistence_profile=getattr(
                    runtime,
                    "required_persistence_profile",
                    None,
                ),
                replay_of_run_id=(
                    replay_of_run_id
                    if replay_of_run_id is not None
                    else getattr(runtime, "replay_of_run_id", None)
                ),
                replay_of_manifest_id=(
                    replay_of_manifest_id
                    if replay_of_manifest_id is not None
                    else getattr(runtime, "replay_of_manifest_id", None)
                ),
                input_snapshot_fingerprint=input_snapshot_fingerprint,
                **_build_contract_identity_kwargs(contract_identity),
            )
        )
