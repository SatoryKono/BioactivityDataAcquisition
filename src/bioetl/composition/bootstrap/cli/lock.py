"""Bootstrap functions for lock CLI operations.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from bioetl.application.services.ops.lock_service import LockService
from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationSpec,
)
from bioetl.composition.bootstrap.cli.noop import (
    _PipelineIntent,
    _ancestors,
    _bounded_destructive_upstream,
    _bounded_pipeline,
    _has_pending_writes,
    _declared_transform_path,
    _pending_pipeline_writers,
    _resolved_pipeline_paths,
    _target_transforms,
    _transform_path,
    _validate_upstream_profile,
    _verification_only,
    create_noop_logger,
)
from bioetl.composition.factories.services.port_factories import create_lock
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.workflow_config import (
    TransformStepConfig,
    WorkflowConfig,
)
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
    get_target_table_profile,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest
    from bioetl.domain.workflow import WorkflowRunOptionsConfig

__all__ = [
    "WorkflowTargetAdmission",
    "bootstrap_lock_service",
    "resolve_workflow_target_config",
    "resolve_workflow_target_replay_config",
    "validate_workflow_target_mutations",
]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Uses the same lock port factory as runtime service wiring
    (:func:`create_lock`). Today that is the local in-process
    ``MemoryLock`` adapter; lock list/release therefore operate on
    the process-local lock table. A durable inter-process adapter is not yet
    part of the product surface — when one is introduced it must be
    registered through ``create_lock`` so CLI and runtime stay aligned.

    Returns:
        LockService configured for the current environment.
    """
    lock_port = create_lock()
    noop_logger = create_noop_logger()

    return LockService(lock_port=lock_port, logger=noop_logger)


PipelineConfigLoader = Callable[[str], PipelineYamlConfig]


@dataclass(frozen=True, slots=True)
class WorkflowTargetAdmission:
    """Separate dependency verification from admission of pending target writes."""

    required: bool
    pending_writes: bool


def validate_workflow_target_mutations(
    config: WorkflowConfig,
    target: PipelineYamlConfig,
    settings: Settings,
    plan: WorkflowMutationSpec,
    load_pipeline_config: PipelineConfigLoader,
) -> WorkflowTargetAdmission:
    """Validate writes before execution; runtime FK ownership checks remain required."""
    intents = _pipeline_intents(config, target, settings, load_pipeline_config)
    admissions = [
        _validate_bundle(config, target, settings, plan, intents, paths)
        for paths in _target_bundles(target, settings)
    ]
    required = any(item.step.pipeline_name == "chembl_target" for item in intents)
    pending_writes = any(item.pending_writes for item in admissions)
    if pending_writes and not required:
        # A transform or alias writing the target has no historical target parent.
        target.target_classification.to_domain().require_active()
    return WorkflowTargetAdmission(
        required or any(item.required for item in admissions), pending_writes
    )


def _validate_bundle(
    config: WorkflowConfig,
    target: PipelineYamlConfig,
    settings: Settings,
    plan: WorkflowMutationSpec,
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
) -> WorkflowTargetAdmission:
    writers = _pending_pipeline_writers(intents, paths, plan)
    transforms = _target_transforms(config, settings, paths, plan)
    risky = _bounded_destructive_upstream(
        config, settings, intents, transforms, plan, paths
    )
    if not (writers or transforms or risky):
        return WorkflowTargetAdmission(False, False)
    profile = get_target_table_profile(silver_path=paths[0], gold_path=paths[1])
    _validate_upstream_profile(profile, risky)
    if writers:
        _validate_pipeline_writers(writers, paths, target, profile)
    _validate_existing_transforms(
        profile, config, transforms, intents, paths, target, settings
    )
    return WorkflowTargetAdmission(True, _has_pending_writes(writers, transforms))


def _validate_existing_transforms(
    profile: str,
    config: WorkflowConfig,
    transforms: tuple[TransformStepConfig, ...],
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    target: PipelineYamlConfig,
    settings: Settings,
) -> None:
    if profile in {"V31", "V32"}:
        for step in transforms:
            _validate_target_transform(config, step, intents, paths, target, settings)


def _pipeline_intents(
    config: WorkflowConfig,
    target: PipelineYamlConfig,
    settings: Settings,
    loader: PipelineConfigLoader,
) -> tuple[_PipelineIntent, ...]:
    result = []
    for step in config.pipeline_steps:
        options = config.defaults.merged_with(step.run_options)
        yaml_config = (
            target
            if step.pipeline_name == "chembl_target"
            else loader(step.pipeline_name)
        )
        result.append(
            _PipelineIntent(
                step,
                _resolved_pipeline_paths(settings, yaml_config),
                bool(options.dry_run),
                (options.run_type or "incremental") in {"backfill", "rebuild"},
                _bounded_pipeline(yaml_config, options.to_mapping()),
            )
        )
    return tuple(result)


def _target_bundles(
    target: PipelineYamlConfig, settings: Settings
) -> tuple[tuple[Path, Path], ...]:
    domain = yaml_config_to_domain(target)
    direct = _resolved_pipeline_paths(settings, target)
    transforms = (
        _transform_path(settings, "silver", domain.effective_silver_table),
        _transform_path(settings, "gold", domain.effective_gold_table),
    )
    return tuple(dict.fromkeys((direct, transforms)))


def _validate_pipeline_writers(
    writers: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    target: PipelineYamlConfig,
    profile: str,
) -> None:
    if profile in {"V31", "V32"} and any(
        item.step.pipeline_name != "chembl_target" for item in writers
    ):
        raise ValueError(
            "unclassified writer cannot mutate an existing V31 target destination"
        )
    assert_target_table_compatibility(
        silver_path=paths[0],
        gold_path=paths[1],
        mode=target.target_classification.mode,
        destructive=any(item.destructive for item in writers),
        table_contract=target.target_classification.to_domain().contract_version,
    )


def _validate_target_transform(
    config: WorkflowConfig,
    step: TransformStepConfig,
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    target: PipelineYamlConfig,
    settings: Settings,
) -> None:
    values = step.config or {}
    mode = values.get("reconciliation_mode", "complete-reference")
    if (
        step.transform_name != "reconcile_foreign_keys"
        or values.get("action") != "delete_orphans"
    ):
        raise ValueError(
            "target mutation requires a declared supported workflow transform"
        )
    if _verification_only(step):
        return  # The canonical adapter either verifies closure or raises before mutation.
    assert_target_table_compatibility(
        silver_path=paths[0],
        gold_path=paths[1],
        mode=target.target_classification.mode,
        table_contract=target.target_classification.to_domain().contract_version,
    )
    upstream = _ancestors(config, step.step_id)
    if mode == "selected-snapshot":
        _require_scoped_producers(step, intents, upstream, settings)


def _require_scoped_producers(
    step: TransformStepConfig,
    intents: tuple[_PipelineIntent, ...],
    upstream: frozenset[str],
    settings: Settings,
) -> None:
    values = step.config or {}
    if values.get("source_scope") != "current_run":
        raise ValueError("selected-snapshot target mutation requires current_run scope")
    if not all(
        _has_bound_producer(settings, values, role, intents, upstream)
        for role in ("source", "reference")
    ):
        raise ValueError(
            "selected-snapshot target mutation requires both bound workflow producers"
        )


def _has_bound_producer(
    settings: Settings,
    values: Mapping[str, object],
    role: str,
    intents: tuple[_PipelineIntent, ...],
    upstream: frozenset[str],
) -> bool:
    path = _declared_transform_path(settings, values, role)
    index = int(values.get(role + "_layer", "silver") == "gold")
    return any(
        item.step.step_id in upstream and item.paths[index] == path for item in intents
    )


def resolve_workflow_target_replay_config(
    config: WorkflowConfig,
    current: PipelineYamlConfig,
    settings: Settings,
    *,
    load_parent: Callable[..., RunManifest],
    hydrate_config: Callable[[Mapping[str, object]], PipelineYamlConfig],
) -> PipelineYamlConfig:
    """Require every target step to use the same resolved classification inputs."""
    selected: PipelineYamlConfig | None = None
    for step in config.pipeline_steps:
        if step.pipeline_name != "chembl_target":
            continue
        candidate = _resolve_step_replay_config(
            config.defaults.merged_with(step.run_options),
            current,
            settings,
            load_parent=load_parent,
            hydrate_config=hydrate_config,
        )
        candidate = resolve_target_classification_profile(
            candidate
        ).resolved_yaml_config
        if (
            selected is not None
            and selected.target_classification != candidate.target_classification
        ):
            raise ValueError(
                "workflow target steps require conflicting classification dependencies"
            )
        selected = candidate
    return selected if selected is not None else current


def _resolve_step_replay_config(
    options: WorkflowRunOptionsConfig,
    current: PipelineYamlConfig,
    settings: Settings,
    *,
    load_parent: Callable[..., RunManifest],
    hydrate_config: Callable[[Mapping[str, object]], PipelineYamlConfig],
) -> PipelineYamlConfig:
    """Restore a persisted replay parent while retaining normal workflow defaults."""
    if not options.exact_replay:
        current.target_classification.to_domain().require_active()
        return current
    parent = load_parent(ctx=options, settings=settings)
    if parent.pipeline_name != "chembl_target" or not parent.resolved_config:
        raise ValueError("target replay parent has no matching pinned configuration")
    return hydrate_config(parent.resolved_config)


def resolve_workflow_target_config(
    stored: object,
    *,
    load_config: Callable[[str], PipelineYamlConfig],
    hydrate_config: Callable[[Mapping[str, object]], PipelineYamlConfig],
) -> PipelineYamlConfig:
    """Restore a pinned dependency or resolve the normal workflow target config."""
    if isinstance(stored, Mapping):
        payload = stored.get("target_config")
        if not isinstance(payload, Mapping):
            raise ValueError("stored workflow target dependency has no configuration")
        target = hydrate_config(payload)
    else:
        target = load_config("chembl_target")
    return resolve_target_classification_profile(target).resolved_yaml_config
