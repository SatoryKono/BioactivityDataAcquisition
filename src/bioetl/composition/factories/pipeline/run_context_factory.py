"""Run-context assembly helpers for pipeline construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.construction_types import (
    EntityTypeExtractor,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
    legacy_config_hash_from_resolved_config_hash,
    resolve_contract_identity,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_dependency_lock_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.value_objects.run_context import RunContext, RunContextCreateInput

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

_ContractIdentityTuple = tuple[str, ...]
_ContractIdentityResult = _ContractIdentityTuple | RunManifestContractIdentity
_NormalizedContractIdentity = tuple[
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
]
_ContractIdentityResolver = Callable[..., _ContractIdentityResult]


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


def _resolve_contract_identity_snapshot(
    provider: str,
    entity: str,
    *,
    strict: bool = False,
) -> _NormalizedContractIdentity:
    """Resolve contract identity through the manifest support seam."""
    return resolve_contract_identity(
        provider=provider,
        entity=entity,
        strict=strict,
    )


def _normalize_contract_identity_result(
    result: _ContractIdentityResult,
) -> _NormalizedContractIdentity:
    """Accept legacy tuples and canonical dataclass contract identity values."""
    if isinstance(result, RunManifestContractIdentity):
        return (
            result.contract_ref,
            result.contract_version,
            result.contract_schema_hash,
            result.dq_policy_ref,
            result.rule_bundle_version,
            result.normalization_profile_ref,
            result.normalization_profile_version,
            result.normalization_profile_hash,
        )
    if len(result) == 5:
        (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
        ) = result
        return (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
            None,
            None,
            None,
        )
    if len(result) == 8:
        return result  # type: ignore[return-value]
    raise RuntimeError(
        "Contract identity resolver must return either the legacy 5-field "
        "tuple, the canonical 8-field tuple, or RunManifestContractIdentity"
    )


def _runtime_requires_strict_contract_identity(runtime: RuntimeConfig) -> bool:
    """Return whether metadata RunContext must fail closed on partial identity."""
    if bool(getattr(runtime, "exact_replay", False)):
        return True
    profile = getattr(runtime, "required_persistence_profile", None)
    profile_value = getattr(profile, "value", profile)
    if profile_value is None:
        return False
    return str(profile_value).strip().lower() in STRICT_PERSISTENCE_PROFILES


def _resolve_contract_identity_for_runtime(
    *,
    resolver: _ContractIdentityResolver,
    provider: str,
    entity: str,
    strict: bool,
) -> _NormalizedContractIdentity:
    """Resolve identity while preserving legacy two-argument test doubles."""
    if strict:
        try:
            result = _normalize_contract_identity_result(
                resolver(provider, entity, strict=True)
            )
        except TypeError:
            result = _normalize_contract_identity_result(resolver(provider, entity))
        missing = [
            name
            for name, value in zip(
                (
                    "contract_version",
                    "contract_schema_hash",
                    "dq_policy_ref",
                    "rule_bundle_version",
                    "normalization_profile_ref",
                    "normalization_profile_version",
                    "normalization_profile_hash",
                ),
                result[1:],
                strict=True,
            )
            if value is None
        ]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(
                "Strict reproducibility contexts require complete contract "
                f"identity for '{result[0]}'; missing: {missing_text}"
            )
        return result
    return _normalize_contract_identity_result(resolver(provider, entity))


@dataclass(frozen=True, slots=True)
class RunContextFactory:
    """Build ``RunContext`` for metadata coordinator wiring."""

    pipeline_name: str
    provider: str
    entity_type_extractor: EntityTypeExtractor
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
    contract_identity_resolver: _ContractIdentityResolver = (
        _resolve_contract_identity_snapshot
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
        strict_contract_identity = _runtime_requires_strict_contract_identity(runtime)
        (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
            normalization_profile_ref,
            normalization_profile_version,
            normalization_profile_hash,
        ) = _resolve_contract_identity_for_runtime(
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
        legacy_config_hash = (
            config_hash
            if config_hash is not None
            else legacy_config_hash_from_resolved_config_hash(resolved_hash)
        )
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
                contract_ref=contract_ref,
                contract_version=contract_version,
                contract_schema_hash=contract_schema_hash,
                dq_policy_ref=dq_policy_ref,
                rule_bundle_version=rule_bundle_version,
                normalization_profile_ref=normalization_profile_ref,
                normalization_profile_version=normalization_profile_version,
                normalization_profile_hash=normalization_profile_hash,
                dq_contract_compatibility_hash=dq_contract_compatibility_hash,
                effective_config_artifact_id=effective_config_artifact_id,
                exact_replay=(
                    bool(getattr(runtime, "exact_replay", False))
                    if exact_replay is None
                    else exact_replay
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
            )
        )
