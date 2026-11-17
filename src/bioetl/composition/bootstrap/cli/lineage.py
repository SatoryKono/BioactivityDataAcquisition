"""Bootstrap functions for lineage CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.control_plane import (
    FileLineageStore,
    FileRunManifestStore,
)

__all__ = ["bootstrap_lineage_service"]


def bootstrap_lineage_service() -> LineageInspectionService:
    """Bootstrap lineage inspection service for CLI commands."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return LineageInspectionService(
        lineage_store=FileLineageStore(
            base_path=output_root / "lineage",
            metrics=metrics,
        ),
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
    )


from collections.abc import Callable
from dataclasses import dataclass

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


from bioetl.composition.bootstrap.cli.lock import (
    _bounded_destructive_upstream,
    _pending_pipeline_writers,
    _target_transforms,
    _validate_pipeline_writers,
    _validate_target_transform,
)
