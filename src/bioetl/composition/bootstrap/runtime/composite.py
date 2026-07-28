"""Bootstrap facade for composite pipeline execution."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError as _ValidationError

from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    CompositeBootstrapPlan as _CompositeBootstrapPlan,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    bootstrap_runtime_basics_impl as _bootstrap_runtime_basics_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_composite_bootstrap_plan_impl as _build_composite_bootstrap_plan_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_runner_factories_impl as _build_runner_factories_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_support_services_impl as _build_support_services_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    create_composite_runner_from_plan_impl as _create_composite_runner_from_plan_impl,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    load_composite_config_impl as _load_runtime_composite_config_impl,
)
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    _load_field_group_registry,
)
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    bootstrap_runtime_basics_facade as _bootstrap_runtime_basics_facade,
)
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    build_runner_factories_facade as _build_runner_factories_facade,
)
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    build_support_services_facade as _build_support_services_facade,
)
from bioetl.composition.bootstrap.runtime.pipeline import (
    apply_runtime_compatibility_patches,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.infrastructure.config.composite_config_api import (
    DEFAULT_COMPOSITE_CONFIG_DIR,
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_config_path as _resolve_composite_config_path_impl,
)
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_gold_schema as _resolve_composite_gold_schema_impl,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_runner",
    "load_composite_config",
]

ValidationError = _ValidationError

def __getattr__(name: str) -> object:
    if name == "CompositeRuntimeConfig":
        from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

        return CompositeRuntimeConfig
    if name == "create_composite_runner_service":
        from bioetl.composition.bootstrap.runtime.runner_assembly import (
            create_composite_runner_service,
        )

        return create_composite_runner_service
    if name == "_create_dq_report_service":
        from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
            _create_dq_report_service,
        )

        return _create_dq_report_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def _resolve_composite_gold_schema(composite_name: str) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    return _resolve_composite_gold_schema_impl(
        composite_name,
        schema_registry=DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
    )

def _resolve_composite_config_path(name: str) -> Path:
    """Resolve composite config path from canonical composites directory."""
    return _resolve_composite_config_path_impl(
        name,
        config_dir=DEFAULT_COMPOSITE_CONFIG_DIR,
        configs_root=resolve_configs_root(),
    )

def load_composite_config(name: str) -> CompositeConfig:
    """Load and validate composite pipeline configuration from YAML."""
    return _load_runtime_composite_config_impl(
        name,
        resolve_config_path_fn=_resolve_composite_config_path,
        validate_payload=validate_composite_config_payload,
    )

def _bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap."""
    return _bootstrap_runtime_basics_facade(
        config=config,
        run_id=run_id,
        bootstrap_runtime_basics_impl=_bootstrap_runtime_basics_impl,
    )

def _build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases."""

    factories: tuple[
        Callable[[], PipelineRunner],
        Callable[[str, pl.DataFrame], PipelineRunner],
        Callable[[str, pl.DataFrame], PipelineRunner],
    ] = _build_runner_factories_facade(
        config=config,
        runtime=runtime,
        logger=logger,
        build_runner_factories_impl=_build_runner_factories_impl,
    )
    return factories

def _build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade."""

    return _build_support_services_facade(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        build_support_services_impl=_build_support_services_impl,
        resolve_gold_schema_fn=_resolve_composite_gold_schema,
        load_field_group_registry_fn=_load_field_group_registry,
    )

def _build_composite_bootstrap_plan(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
) -> _CompositeBootstrapPlan:
    """Resolve declarative bootstrap plan for the composite runner."""
    return _build_composite_bootstrap_plan_impl(
        config=config,
        runtime=runtime,
        run_id=run_id,
        bootstrap_runtime_basics_fn=_bootstrap_runtime_basics,
        build_runner_factories_fn=_build_runner_factories,
        build_support_services_fn=_build_support_services,
    )

def _create_composite_runner_from_plan(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    plan: _CompositeBootstrapPlan,
) -> CompositePipelineRunner:
    """Create the final composite runner from the resolved bootstrap plan."""
    from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
        create_composite_runner as _create_composite_runner_builder_impl,
    )
    from bioetl.composition.bootstrap.runtime.runner_assembly import (
        create_composite_runner_service,
    )

    return _create_composite_runner_from_plan_impl(
        config=config,
        runtime=runtime,
        plan=plan,
        create_composite_runner_builder_fn=_create_composite_runner_builder_impl,
        runner_factory=create_composite_runner_service,
    )

def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Create a ``CompositePipelineRunner`` with all dependencies."""
    apply_runtime_compatibility_patches()
    plan = _build_composite_bootstrap_plan(
        config=config, runtime=runtime, run_id=run_id
    )
    return _create_composite_runner_from_plan(config=config, runtime=runtime, plan=plan)
