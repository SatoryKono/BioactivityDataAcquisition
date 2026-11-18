"""Resolve workflow target replay inputs before mutation admission."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest
    from bioetl.domain.workflow import WorkflowConfig, WorkflowRunOptionsConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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
    if not options.exact_replay or not (
        options.replay_of_manifest_id or options.replay_of_run_id
    ):
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
