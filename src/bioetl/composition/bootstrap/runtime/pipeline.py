"""Main composition-root bootstrap for runtime pipeline execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.runtime.assembly import (
    assemble_filter_config as _rf014_assembly_owner,
)
from bioetl.composition.bootstrap.runtime.compatibility import (
    apply_runtime_compatibility_patches,
)
from bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases import (
    build_bootstrap_runner_factory_wiring,
    build_bootstrap_runner_input_wiring,
    initialize_runtime_policy_sources,
    prepare_runtime_registry,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import (
    get_settings as _rf014_config_access_owner,
)
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner
from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = ["bootstrap_pipeline_runner"]

_RF014_HELPER_OWNER_IMPORTS = (_rf014_assembly_owner, _rf014_config_access_owner)


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None = None,
) -> PipelineRunner:
    """Build one ready-to-run pipeline runner from runtime context and registry."""
    apply_runtime_compatibility_patches()
    effective_registry = prepare_runtime_registry(
        registry=registry,
        pipeline_name=ctx.pipeline_name,
    )
    configs_root = resolve_configs_root()
    initialize_runtime_policy_sources(configs_root)

    return cast(
        "PipelineRunner",
        build_pipeline_runner(
            ctx=ctx,
            registry=effective_registry,
            factory_wiring=build_bootstrap_runner_factory_wiring(),
            input_wiring=build_bootstrap_runner_input_wiring(
                configs_root=configs_root,
                load_pipeline_config_fn=load_pipeline_config_fn,
            ),
        ),
    )
