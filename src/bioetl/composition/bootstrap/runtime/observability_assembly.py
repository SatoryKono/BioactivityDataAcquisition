"""Assembly helpers for runtime observability bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.observability import ObservabilityBundle

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.runtime.observability_bundle import (
        _ObservabilityComponents,
    )
    from bioetl.infrastructure.config import Settings


def create_observability_bundle(
    components: _ObservabilityComponents,
) -> ObservabilityBundle:
    """Create the public bundle object from resolved component ports."""
    return ObservabilityBundle(
        logger=components.logger,
        metrics=components.metrics,
        tracer=components.tracer,
        audit=components.audit,
        dq_monitor=components.dq_monitor,
    )


def settings_control_plane(settings: Settings) -> object | None:
    pipeline_settings = getattr(settings, "pipeline", None)
    return getattr(pipeline_settings, "control_plane", None)


def run_observability_preflight(
    *,
    components: _ObservabilityComponents,
    settings: Settings,
    preflight_validator: Callable[..., None],
    control_plane: object | None,
    yaml_config: object | None,
    skip_gold: bool,
) -> None:
    """Validate observability readiness using one normalized control-plane view."""
    preflight_validator(
        tracer=components.tracer,
        metrics=components.metrics,
        environment=settings.env,
        logger=components.logger,
        allow_noop_in_prod=settings.observability.allow_noop_observability_in_prod,
        audit=components.audit,
        audit_required=bool(getattr(settings.observability, "audit_enabled", False)),
        control_plane=control_plane,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )
