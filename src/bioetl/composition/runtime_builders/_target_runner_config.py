"""Resolve chembl_target YAML with pinned classification and replay restore."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.target_classification_init import (
    resolve_target_runtime_config,
)
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    restore_target_replay_config,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


__all__ = ["load_target_aware_pipeline_config"]
