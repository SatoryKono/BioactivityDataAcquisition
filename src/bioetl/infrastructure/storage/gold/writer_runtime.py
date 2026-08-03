"""Runtime services resolution for Gold writer."""

from __future__ import annotations

from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)

__all__ = ["_resolve_runtime_services"]


def _resolve_runtime_services(
    *,
    runtime_services: GoldWriterRuntimeServices | None,
) -> GoldWriterRuntimeServices:
    """Return grouped Gold runtime services, building defaults when omitted."""
    return runtime_services or build_gold_writer_runtime_services(
        csv_exporter=None,
        tracing=None,
        metrics=None,
        audit=None,
        metadata_writer=None,
        metadata_coordinator=None,
        lineage_store=None,
    )
