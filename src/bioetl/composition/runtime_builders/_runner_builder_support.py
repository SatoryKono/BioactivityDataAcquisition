"""Private helpers for runtime runner builder control-plane glue."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)


class _LoggerBindableObservability(Protocol):
    logger: object


def resolve_control_plane_flags(settings: object) -> tuple[bool, bool]:
    """Resolve control-plane feature flags for executable pipeline runs."""
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    if not manifest_enabled:
        raise RuntimeError(
            "Pipeline execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    return True, ledger_enabled


def bind_manifest_logger_context(
    inputs: _RunnerInputs,
    manifest_id: str,
) -> _RunnerInputs:
    """Bind ``manifest_id`` into runtime observability when available."""
    observability = getattr(inputs, "observability", None)
    rebound_observability = _rebind_observability_logger(
        observability=observability,
        manifest_id=manifest_id,
    )
    if rebound_observability is observability:
        return inputs
    if isinstance(inputs, _RunnerInputs):
        return replace(
            inputs,
            observability=cast("ObservabilityBundle", rebound_observability),
        )
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
