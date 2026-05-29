"""Public seam for runtime runner-builder control-plane helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._runner_control_plane_policy import (
    resolve_control_plane_flags,
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)

__all__ = [
    "bind_manifest_logger_context",
    "resolve_control_plane_flags",
    "resolve_required_artifact_lineage_layers",
    "validate_required_persistence_profile",
]


class _LoggerBindableObservability(Protocol):
    logger: object


def bind_manifest_logger_context[RunnerInputsT](
    inputs: RunnerInputsT,
    manifest_id: str,
) -> RunnerInputsT:
    """Bind ``manifest_id`` into runtime observability when available."""
    observability = getattr(inputs, "observability", None)
    rebound_observability = _rebind_observability_logger(
        observability=observability,
        manifest_id=manifest_id,
    )
    if rebound_observability is observability:
        return inputs
    if not isinstance(rebound_observability, ObservabilityBundle):
        return inputs
    try:
        return cast(
            "RunnerInputsT",
            replace(inputs, observability=rebound_observability),
        )
    except (TypeError, AttributeError):
        return inputs


def _rebind_observability_logger(
    *,
    observability: object,
    manifest_id: str,
) -> object:
    """Return observability with ``manifest_id`` bound to its logger context."""
    bind_fn = getattr(observability, "bind", None)
    if callable(bind_fn):
        return bind_fn(manifest_id=manifest_id)

    logger = getattr(observability, "logger", None)
    logger_bind = getattr(logger, "bind", None)
    if not callable(logger_bind):
        return observability

    typed_observability = cast("_LoggerBindableObservability", observability)
    try:
        typed_observability.logger = logger_bind(manifest_id=manifest_id)
    except (AttributeError, TypeError):
        return observability
    return observability
