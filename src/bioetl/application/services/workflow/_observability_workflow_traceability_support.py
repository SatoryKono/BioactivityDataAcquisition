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
    build_trace_urls,
    resolve_manifest_provider,
    resolve_manifest_run_type,
    resolve_primary_composite_run_id,
)
from bioetl.application.services.workflow._observability_trace_support import (
    trace_links_enabled as _trace_links_enabled,
)
from bioetl.application.services.workflow._observability_workflow_lookup_support import (
    resolve_pipeline_name,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )


def trace_links_enabled(tracer: object | None) -> bool:
    return _trace_links_enabled(tracer)


def build_traceability_section(
    *,
    run_id: str,
    run_manifest: RunManifestInspectionResult | None,
    lineage: LineageRunExplanationResult | None,
    audit: AuditInspectionResult,
    trace_links_enabled: bool,
) -> dict[str, object]:
    diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
    identity_graph = run_manifest.identity_graph if run_manifest is not None else {}
    provider = resolve_manifest_provider(run_manifest)
    run_type = resolve_manifest_run_type(run_manifest)
    composite_run_id = resolve_primary_composite_run_id(diagnostics)
    trace_urls = (
        build_trace_urls(
            run_id=run_id,
            pipeline_name=resolve_pipeline_name(run_manifest),
            provider=provider,
            run_type=run_type,
            composite_run_id=composite_run_id,
            run_manifest=run_manifest,
            audit=audit,
        )
        if trace_links_enabled
        else []
    )
    trace_ids = build_trace_ids(
        run_id=run_id,
        diagnostics=diagnostics,
        trace_links_available=bool(trace_urls),
    )
    traceability = {
        "audit_entries_count": len(audit.entries),
        "identity_graph_complete": diagnostics.get("identity_graph_complete"),
        "correlation_anchor_gaps": diagnostics.get("correlation_anchor_gaps"),
        "lineage_fragment_ids": diagnostics.get("lineage_fragment_ids")
        or (list(lineage.fragment_ids) if lineage is not None else []),
        "artifact_refs": diagnostics.get("artifact_refs", []),
        "trace_ids": trace_ids,
        "trace_urls": trace_urls,
        "trace_links_available": bool(trace_urls),
        "persistence_profile": diagnostics.get("persistence_profile"),
        "replay_capability": identity_graph.get("replay_capability")
        or diagnostics.get("replay_capability"),
    }
    composite_projection = diagnostics.get("composite_dossier_projection")
    if composite_projection is not None:
        traceability["composite_projection"] = composite_projection
    return traceability
