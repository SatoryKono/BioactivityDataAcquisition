"""Extracted _coerce_named_runtime_bundle for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)

def _coerce_named_runtime_bundle(
    resolved_bundle: object,
) -> CompositeInfrastructureContext | None:
    field_names = (
        "run_id",
        "settings",
        "logger",
        "metrics",
        "tracer",
        "storage",
        "lock",
    )
    if not all(hasattr(resolved_bundle, field_name) for field_name in field_names):
        return None
    bundle = cast("CompositeInfrastructureContext", resolved_bundle)
    clock = bundle.clock if hasattr(bundle, "clock") else None
    return CompositeInfrastructureContext(
        run_id=bundle.run_id,
        settings=bundle.settings,
        logger=bundle.logger,
        metrics=bundle.metrics,
        tracer=bundle.tracer,
        storage=bundle.storage,
        lock=bundle.lock,
        clock=clock,
    )
