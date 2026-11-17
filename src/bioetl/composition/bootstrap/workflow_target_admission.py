"""Admit workflow target mutations without importing CLI bootstrap."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationSpec,
)
from bioetl.composition.factories.dq.composite_validation import (
    resolve_target_table_paths,
)
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

    @property
    def bounded_destructive(self) -> bool:
        return self.destructive and self.bounded


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
    return WorkflowTargetAdmission(
        required or any(item.required for item in admissions),
        any(item.pending_writes for item in admissions),
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


def _has_pending_writes(
    writers: tuple[_PipelineIntent, ...], transforms: tuple[TransformStepConfig, ...]
) -> bool:
    return bool(writers) or any(not _verification_only(step) for step in transforms)


def _validate_upstream_profile(
    profile: str, risky: tuple[_PipelineIntent, ...]
) -> None:
    if profile == "V31" and risky:
        raise ValueError(
            "bounded destructive upstream cannot replace the reference cohort of an existing V31 target"
        )


def _validate_existing_transforms(
    profile: str,
    config: WorkflowConfig,
    transforms: tuple[TransformStepConfig, ...],
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    target: PipelineYamlConfig,
    settings: Settings,
) -> None:
    if profile == "V31":
        for step in transforms:
            _validate_target_transform(config, step, intents, paths, target, settings)


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
                _resolved_pipeline_paths(settings, yaml_config),
                bool(options.dry_run),
                (options.run_type or "incremental") in {"backfill", "rebuild"},
                _bounded_pipeline(yaml_config, options.to_mapping()),
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
            "cached_bronze_path",
            "cached_bronze_date",
        )
    )


def _bounded_pipeline(config: PipelineYamlConfig, options: dict[str, object]) -> bool:
    yaml_subset = config.input_filter.enabled and not options.get("ignore_yaml_filter")
    return (
        _bounded_options(options)
        or bool(options.get("use_cached_bronze"))
        or yaml_subset
    )


def _resolved_pipeline_paths(
    settings: Settings, config: PipelineYamlConfig
) -> tuple[Path, Path]:
    silver, gold = resolve_target_table_paths(settings, config)
    return silver.resolve(), gold.resolve()


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


def _transform_path(settings: Settings, layer: str, table: str) -> Path:
    base = settings.gold_path if layer == "gold" else settings.silver_path
    return Path(
        resolve_delta_table_path(
            base_path=str(base), table_name=table, flat_structure=False
        )
    ).resolve()


def _pending_pipeline_writers(
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    plan: WorkflowMutationSpec,
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
    settings: Settings,
    paths: tuple[Path, Path],
    plan: WorkflowMutationSpec,
) -> tuple[TransformStepConfig, ...]:
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


def _bounded_destructive_upstream(
    config: WorkflowConfig,
    settings: Settings,
    intents: tuple[_PipelineIntent, ...],
    transforms: tuple[TransformStepConfig, ...],
    plan: WorkflowMutationSpec,
    paths: tuple[Path, Path],
) -> tuple[_PipelineIntent, ...]:
    upstream = _reference_producers(config, settings, intents, transforms, paths)
    active = (
        item
        for item in intents
        if item.step.step_id in plan.pending_step_ids and not item.dry_run
    )
    return tuple(
        item
        for item in active
        if item.step.step_id in upstream and item.bounded_destructive
    )


def _reference_producers(
    config: WorkflowConfig,
    settings: Settings,
    intents: tuple[_PipelineIntent, ...],
    transforms: tuple[TransformStepConfig, ...],
    paths: tuple[Path, Path],
) -> set[str]:
    producers = _target_reference_producers(intents, paths)
    for step in transforms:
        producers.update(
            _transform_reference_producers(config, settings, intents, step)
        )
    return producers


def _target_reference_producers(
    intents: tuple[_PipelineIntent, ...], paths: tuple[Path, Path]
) -> set[str]:
    return {
        item.step.reference_cohort.step_id
        for item in intents
        if item.step.pipeline_name == "chembl_target"
        and bool(set(item.paths).intersection(paths))
        and item.step.reference_cohort is not None
    }


def _transform_reference_producers(
    config: WorkflowConfig,
    settings: Settings,
    intents: tuple[_PipelineIntent, ...],
    step: TransformStepConfig,
) -> set[str]:
    values = step.config or {}
    if values.get("reconciliation_mode", "complete-reference") == "selected-snapshot":
        return set()
    reference = _declared_transform_path(settings, values, "reference")
    ancestors = _ancestors(config, step.step_id)
    return {
        item.step.step_id
        for item in intents
        if item.step.step_id in ancestors and reference in item.paths
    }


def _declared_transform_path(
    settings: Settings, values: Mapping[str, object], role: str
) -> Path | None:
    table = values.get(role + "_table")
    if not isinstance(table, str):
        return None
    return _transform_path(settings, str(values.get(role + "_layer", "silver")), table)


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
        silver_path=paths[0], gold_path=paths[1], mode=target.target_classification.mode
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


__all__ = [
    "WorkflowTargetAdmission",
    "validate_workflow_target_mutations",
]
