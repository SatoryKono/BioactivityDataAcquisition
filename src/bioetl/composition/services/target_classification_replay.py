"""Restore pinned target configuration before generic runner assembly."""

from __future__ import annotations
from collections.abc import Callable
from typing import TYPE_CHECKING, overload
from bioetl.composition.bootstrap.assembly.storage import hydrate_target_runtime_config
from bioetl.composition.services.target_classification_config import (
    resolve_target_runtime_config,
)
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    _resolve_replay_parent_manifest,
)
from bioetl.infrastructure.config.pipeline_config_api import PipelineYamlConfig

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings


@overload
def restore_target_replay_config(
    *, ctx: PipelineRunContext, settings: Settings, current_config: PipelineYamlConfig
) -> PipelineYamlConfig: ...


@overload
def restore_target_replay_config(
    *, ctx: PipelineRunContext, settings: Settings, current_config: object
) -> object: ...


def restore_target_replay_config(
    *, ctx: PipelineRunContext, settings: Settings, current_config: object
) -> object:
    """Restore the saved target profile rather than consulting a newer default."""
    if ctx.pipeline_name != "chembl_target" or not bool(
        getattr(ctx, "exact_replay", False)
    ):
        return current_config

    if not isinstance(current_config, PipelineYamlConfig):
        return current_config
    has_parent = bool(
        getattr(ctx, "replay_of_manifest_id", None)
        or getattr(ctx, "replay_of_run_id", None)
    )
    if not has_parent and not current_config.target_classification.to_domain().enabled:
        return current_config
    parent = _resolve_replay_parent_manifest(ctx=ctx, settings=settings)
    if parent.pipeline_name != "chembl_target":
        raise ValueError("target replay parent pipeline mismatch")
    if not parent.resolved_config:
        raise ValueError("target replay parent has no pinned resolved configuration")

    return hydrate_target_runtime_config(parent.resolved_config)


def load_target_aware_pipeline_config(
    pipeline_name: str,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    validate_pk_contract_fn: Callable[[PipelineYamlConfig], None],
    ctx: PipelineRunContext | None = None,
    settings: Settings | None = None,
) -> PipelineYamlConfig:
    yaml_config = load_pipeline_config_fn(pipeline_name)
    if pipeline_name == "chembl_target":
        if ctx is not None and settings is not None:
            yaml_config = restore_target_replay_config(
                ctx=ctx, settings=settings, current_config=yaml_config
            )
        yaml_config = resolve_target_runtime_config(yaml_config)
    validate_pk_contract_fn(yaml_config)
    return yaml_config
