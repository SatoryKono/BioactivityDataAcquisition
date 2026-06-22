"""Owner-only runtime-context assembly for composite support services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_wiring_api import EnrichmentCrossValidator
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    bind_manifest_logger,
    build_composite_control_plane_bundle,
)
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.composition.bootstrap.runtime.composite_control_plane_bundle import (
        CompositeControlPlaneBundle,
    )
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class CompositeSupportRuntimeContext:
    """Resolved runtime collaborators shared across composite support builders."""

    control_plane_bundle: CompositeControlPlaneBundle
    logger: LoggerPort
    delta_reader: DeltaReader
    field_group_registry: FieldGroupRegistry | None
    cross_validator: EnrichmentCrossValidator | None


def resolve_composite_support_runtime_context(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    load_field_group_registry: Callable[[str, LoggerPort], FieldGroupRegistry | None],
) -> CompositeSupportRuntimeContext:
    """Resolve shared logger/control-plane/reader context for support assembly."""
    control_plane_bundle = build_composite_control_plane_bundle(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )
    logger = bind_manifest_logger(
        infra_context.logger,
        control_plane_bundle.manifest_id,
    )
    delta_reader = DeltaReader(
        base_path=str(Path(infra_context.settings.data_dir) / "output"),
        logger=logger,
    )
    field_group_registry = load_field_group_registry(config.name, logger)
    cross_validator = None
    if config.cross_validation.enabled:
        cross_validator = EnrichmentCrossValidator(
            config=config.cross_validation,
            logger=logger,
        )
    return CompositeSupportRuntimeContext(
        control_plane_bundle=control_plane_bundle,
        logger=logger,
        delta_reader=delta_reader,
        field_group_registry=field_group_registry,
        cross_validator=cross_validator,
    )


__all__ = [
    "CompositeSupportRuntimeContext",
    "resolve_composite_support_runtime_context",
]
