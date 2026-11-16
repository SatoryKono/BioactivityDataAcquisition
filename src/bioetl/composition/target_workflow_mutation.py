"""Admit declared target mutations using pending steps and actual destinations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationPlan,
)
from bioetl.composition.factories.storage.target_paths import resolve_target_table_paths
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.delta.table_ops import resolve_delta_table_path
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
    get_target_table_profile,
)

PipelineConfigLoader = Callable[[str], PipelineYamlConfig]


@dataclass(frozen=True, slots=True)
class _PipelineIntent:
    step: WorkflowStepConfig
    paths: tuple[Path, Path]
    dry_run: bool
    destructive: bool
    bounded: bool


@dataclass(frozen=True, slots=True)
class WorkflowTargetAdmission:
    required: bool
    pending_writes: bool


def workflow_target_relevant(config: WorkflowConfig) -> bool:
    """Include transform-only writes; reference-only reads need no classification."""
    for step in config.steps:
        if (
            isinstance(step, WorkflowStepConfig)
            and step.pipeline_name == "chembl_target"
        ):
            return True
        if (
            isinstance(step, TransformStepConfig)
            and (step.config or {}).get("source_table") == "chembl.target"
        ):
            return True
    return False


def validate_workflow_target_mutations(
    config: WorkflowConfig,
    target: PipelineYamlConfig,
    settings: Settings,
    plan: WorkflowMutationPlan,
    load_pipeline_config: PipelineConfigLoader,
) -> WorkflowTargetAdmission:
    """Validate writes before execution; runtime FK ownership checks remain required."""
    intents = _pipeline_intents(config, target, settings, load_pipeline_config)
    bundles = _target_bundles(target, settings)
    required = any(item.step.pipeline_name == "chembl_target" for item in intents)
    pending_writes = False
    for paths in bundles:
        writers = _pending_pipeline_writers(intents, paths, plan)
        transforms = _target_transforms(config, target, settings, paths, plan)
        if not (required or writers or transforms):
            continue
        required = True
        pending_writes = (
            pending_writes
            or bool(writers)
            or any(not _verification_only(step) for step in transforms)
        )
        profile = get_target_table_profile(silver_path=paths[0], gold_path=paths[1])
        if writers:
            _validate_pipeline_writers(writers, paths, target, profile)
        if profile != "V31":
            continue
        if (
            writers
            or transforms
            or any(item.step.pipeline_name == "chembl_target" for item in intents)
        ):
            _reject_bounded_destructive_upstream(config, intents, transforms, plan)
        for step in transforms:
            _validate_target_transform(config, step, intents, paths, target)
    return WorkflowTargetAdmission(required, pending_writes)


def _verification_only(step: TransformStepConfig) -> bool:
    values = step.config or {}
    return (
        values.get("require_closed_cohort") is True
        and values.get("reconciliation_mode", "complete-reference")
        == "complete-reference"
    )


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
                resolve_target_table_paths(settings, yaml_config),
                bool(options.dry_run),
                (options.run_type or "incremental") in {"backfill", "rebuild"},
                _bounded_options(options.to_mapping()),
            )
        )
    return tuple(result)


def _bounded_options(options: dict[str, object]) -> bool:
    return any(
        options.get(name) is not None
        for name in (
            "limit",
            "start_offset",
            "input_csv",
            "filter_ids",
            "multi_filter_ids",
        )
    )


def _target_bundles(
    target: PipelineYamlConfig, settings: Settings
) -> tuple[tuple[Path, Path], ...]:
    domain = yaml_config_to_domain(target)
    direct = resolve_target_table_paths(settings, target)
    transforms = (
        _transform_path(settings, "silver", domain.effective_silver_table),
        _transform_path(settings, "gold", domain.effective_gold_table),
    )
    return tuple(dict.fromkeys((direct, transforms)))


def _transform_path(settings: Settings, layer: str, table: str) -> Path:
    base = settings.gold_path if layer == "gold" else settings.silver_path
    return Path(
        resolve_delta_table_path(
            base_path=str(base), table_name=table, flat_structure=False
        )
    )


def _pending_pipeline_writers(
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    plan: WorkflowMutationPlan,
) -> tuple[_PipelineIntent, ...]:
    return tuple(
        item
        for item in intents
        if item.step.step_id in plan.pending_step_ids
        and not item.dry_run
        and bool(set(item.paths).intersection(paths))
    )


def _validate_pipeline_writers(
    writers: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    target: PipelineYamlConfig,
    profile: str,
) -> None:
    if profile == "V31" and any(
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
    )


def _target_transforms(
    config: WorkflowConfig,
    target: PipelineYamlConfig,
    settings: Settings,
    paths: tuple[Path, Path],
    plan: WorkflowMutationPlan,
) -> tuple[TransformStepConfig, ...]:
    del target
    if config.defaults.dry_run:
        return ()
    return tuple(
        step
        for step in config.steps
        if isinstance(step, TransformStepConfig)
        and step.step_id in plan.pending_step_ids
        and _transform_writes_paths(step, settings, paths)
    )


def _transform_writes_paths(
    step: TransformStepConfig, settings: Settings, paths: tuple[Path, Path]
) -> bool:
    values = step.config or {}
    source = values.get("source_table")
    if not isinstance(source, str):
        return False
    if step.transform_name in {"summarize_upstream_outputs", "reconcile_rows"}:
        return False
    layer = str(values.get("mutation_layer") or values.get("source_layer", "silver"))
    return _transform_path(settings, layer, source) in paths


def _ancestors(config: WorkflowConfig, step_id: str) -> frozenset[str]:
    definitions = {step.step_id: step for step in config.steps}
    pending = list(definitions[step_id].depends_on)
    found: set[str] = set()
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(definitions[current].depends_on)
    return frozenset(found)


def _reject_bounded_destructive_upstream(
    config: WorkflowConfig,
    intents: tuple[_PipelineIntent, ...],
    transforms: tuple[TransformStepConfig, ...],
    plan: WorkflowMutationPlan,
) -> None:
    affected = {
        item.step.step_id
        for item in intents
        if item.step.pipeline_name == "chembl_target"
    }
    affected.update(step.step_id for step in transforms)
    upstream = (
        set().union(*(_ancestors(config, step_id) for step_id in affected))
        if affected
        else set()
    )
    if any(
        item.step.step_id in upstream
        and item.step.step_id in plan.pending_step_ids
        and item.destructive
        and item.bounded
        and not item.dry_run
        for item in intents
    ):
        raise ValueError(
            "bounded destructive upstream cannot replace the reference cohort of an existing V31 target"
        )


def _validate_target_transform(
    config: WorkflowConfig,
    step: TransformStepConfig,
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    target: PipelineYamlConfig,
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
    if values.get("require_closed_cohort") is True and mode == "complete-reference":
        return  # The canonical adapter either verifies closure or raises before mutation.
    assert_target_table_compatibility(
        silver_path=paths[0], gold_path=paths[1], mode=target.target_classification.mode
    )
    upstream = _ancestors(config, step.step_id)
    if mode == "selected-snapshot":
        _require_scoped_producers(step, intents, upstream)
    elif (
        any(item.bounded and item.step.step_id in upstream for item in intents)
        and values.get("source_scope", "all_current") != "current_run"
    ):
        raise ValueError(
            "bounded complete-reference target mutation requires a bound current-run source scope"
        )


def _require_scoped_producers(
    step: TransformStepConfig,
    intents: tuple[_PipelineIntent, ...],
    upstream: frozenset[str],
) -> None:
    values = step.config or {}
    if values.get("source_scope") != "current_run":
        raise ValueError("selected-snapshot target mutation requires current_run scope")
    producers = {
        item.step.pipeline_name.replace("_", ".", 1)
        for item in intents
        if item.step.step_id in upstream
    }
    if (
        values.get("source_table") not in producers
        or values.get("reference_table") not in producers
    ):
        raise ValueError(
            "selected-snapshot target mutation requires both bound workflow producers"
        )
