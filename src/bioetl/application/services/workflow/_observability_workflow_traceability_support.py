"""Traceability section helpers for observability workflow dossiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)
from bioetl.application.services.export_lineage.audit_inspection_service import (
    AuditInspectionResult,
)
from bioetl.application.services.workflow._observability_trace_support import (
    build_trace_ids,
)
from bioetl.application.services.workflow._observability_trace_support import (
    trace_identifiers_available as _trace_identifiers_available,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )


def trace_identifiers_enabled(tracer: object | None) -> bool:
    """Проверить, что tracer может предоставить correlation identifiers."""
    return _trace_identifiers_available(tracer)


def build_traceability_section(
    *,
    run_id: str,
    run_manifest: RunManifestInspectionResult | None,
    lineage: LineageRunExplanationResult | None,
    audit: AuditInspectionResult,
    trace_identifiers_enabled: bool,
) -> dict[str, object]:
    """Собрать нейтральные traceability facts для workflow dossier."""
    diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
    identity_graph = run_manifest.identity_graph if run_manifest is not None else {}
    trace_ids = build_trace_ids(
        run_id=run_id,
        diagnostics=diagnostics,
        trace_identifiers_available=trace_identifiers_enabled,
    )
    traceability = {
        "audit_entries_count": len(audit.entries),
        "identity_graph_complete": diagnostics.get("identity_graph_complete"),
        "correlation_anchor_gaps": diagnostics.get("correlation_anchor_gaps"),
        "lineage_fragment_ids": diagnostics.get("lineage_fragment_ids")
        or (list(lineage.fragment_ids) if lineage is not None else []),
        "artifact_refs": diagnostics.get("artifact_refs", []),
        "trace_ids": trace_ids,
        "trace_identifiers_available": bool(trace_ids),
        "persistence_profile": diagnostics.get("persistence_profile"),
        "replay_capability": identity_graph.get("replay_capability")
        or diagnostics.get("replay_capability"),
    }
    composite_projection = diagnostics.get("composite_dossier_projection")
    if composite_projection is not None:
        traceability["composite_projection"] = composite_projection
    return traceability
