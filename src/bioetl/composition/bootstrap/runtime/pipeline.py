# pyright: reportInvalidCast=false
# Host/cast bridge residual (PD3).
"""Main composition-root bootstrap for runtime pipeline execution."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.runtime.assembly import RuntimeBootstrapPhases
from bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases import (
    build_runtime_bootstrap_phases_with_registry,
    prepare_runtime_registry,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import resolve_configs_root
from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    require_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders.runner_builder import (
    build_pipeline_runner as _build_pipeline_runner,
)

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "RuntimeBootstrapPhases",
    "apply_runtime_compatibility_patches",
    "bootstrap_pipeline_runner",
    "build_runtime_bootstrap_phases",
]


def _coerce_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fail_fast_empty_explicit_cached_bronze(ctx: PipelineRunContext) -> None:
    """Reject explicit cached-Bronze replay before heavy runtime bootstrap work."""
    cached_bronze = getattr(ctx, "cached_bronze", None)
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return
    bronze_path = _coerce_optional_str(getattr(cached_bronze, "bronze_path", None))
    if bronze_path is None:
        return
    require_cached_bronze_input_snapshot_refs(
        bronze_root=Path(bronze_path),
        bronze_date=_coerce_optional_str(getattr(cached_bronze, "bronze_date", None)),
    )


def apply_runtime_compatibility_patches() -> bool:
    """Retained public bootstrap hook; no runtime compatibility patch is needed."""
    return False


def build_runtime_bootstrap_phases(
    *,
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None,
) -> RuntimeBootstrapPhases:
    """Resolve explicit runtime bootstrap phases before runner construction."""
    apply_runtime_compatibility_patches()
    effective_registry = prepare_runtime_registry(
        registry=registry, pipeline_name=ctx.pipeline_name
    )
    return build_runtime_bootstrap_phases_with_registry(
        registry=effective_registry,
        load_pipeline_config_fn=load_pipeline_config_fn,
        resolve_configs_root_fn=resolve_configs_root,
    )


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] | None = None,
) -> PipelineRunner:
    """Build one ready-to-run pipeline runner from runtime context and registry."""
    _fail_fast_empty_explicit_cached_bronze(ctx)
    apply_runtime_compatibility_patches()
    registry = prepare_runtime_registry(
        registry=registry, pipeline_name=ctx.pipeline_name
    )
    phases = build_runtime_bootstrap_phases_with_registry(
        registry=registry,
        load_pipeline_config_fn=load_pipeline_config_fn,
        resolve_configs_root_fn=resolve_configs_root,
    )
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerBuilderWiring,
    )

    wiring = RunnerBuilderWiring(
        factory=phases.factory_wiring, inputs=phases.input_wiring
    )
    runner = _build_pipeline_runner(ctx=ctx, registry=phases.registry, wiring=wiring)
    return cast("PipelineRunner", runner)
