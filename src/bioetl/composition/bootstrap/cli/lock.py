"""Bootstrap functions for lock CLI operations.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from bioetl.application.services.ops.lock_service import LockService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.services.port_factories import create_lock

__all__ = ["bootstrap_lock_service"]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Uses the same lock port factory as runtime service wiring
    (:func:`create_lock`). Today that is the local in-process
    ``MemoryLock`` adapter; lock list/release therefore operate on the
    process-local lock table. A durable inter-process adapter is not yet
    part of the product surface — when one is introduced it must be
    registered through ``create_lock`` so CLI and runtime stay aligned.

    Returns:
        LockService configured for the current environment.
    """
    lock_port = create_lock()
    noop_logger = create_noop_logger()

    return LockService(lock_port=lock_port, logger=noop_logger)


from collections.abc import Callable, Mapping
from pathlib import Path

from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationSpec,
)
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
)

PipelineConfigLoader = Callable[[str], PipelineYamlConfig]


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


from bioetl.composition.bootstrap.cli.lineage import (
    _PipelineIntent,
    _transform_path,
    _verification_only,
)
