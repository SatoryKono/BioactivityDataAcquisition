"""Trace-link helpers for observability workflow dossiers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from bioetl.application.services.audit_inspection_service import AuditInspectionResult
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionResult,
)

TRACE_DRILLDOWN_PATH = "/a/grafana-exploretraces-app/"
TRACE_DRILLDOWN_DEFAULT_FROM = "now-24h"
TRACE_DRILLDOWN_DEFAULT_TO = "now"
TRACE_WINDOW_PADDING = timedelta(minutes=5)


def trace_links_enabled(tracer: object | None) -> bool:
    if tracer is None:
        return False
    return getattr(tracer, "is_noop", False) is not True


def build_trace_ids(
    *,
    run_id: str,
    diagnostics: dict[str, object],
    trace_links_available: bool,
) -> list[str]:
    explicit_trace_ids = diagnostics.get("trace_ids")
    if isinstance(explicit_trace_ids, list):
        normalized = [
            value.strip()
            for value in explicit_trace_ids
            if isinstance(value, str) and value.strip()
        ]
        if normalized:
            return list(dict.fromkeys(normalized))
    if trace_links_available and run_id:
        return [run_id]
    return []


def resolve_manifest_provider(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    provider = getattr(run_manifest.manifest, "provider", None)
    return str(provider) if provider not in {None, ""} else None


def resolve_manifest_run_type(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    run_type = getattr(run_manifest.manifest, "run_type", None)
    run_type_value = getattr(run_type, "value", None)
    if isinstance(run_type_value, str):
        run_type = run_type_value
    return str(run_type) if run_type not in {None, ""} else None


def build_trace_urls(
    *,
    run_id: str,
    pipeline_name: str | None,
    provider: str | None,
    run_type: str | None,
    run_manifest: RunManifestInspectionResult | None,
    audit: AuditInspectionResult,
) -> list[str]:
    query = build_traceql_query(
        run_id=run_id,
        pipeline_name=pipeline_name,
        provider=provider,
        run_type=run_type,
    )
    if query is None:
        return []
    from_value, to_value = build_trace_time_window(
        run_manifest=run_manifest,
        audit=audit,
    )
    params = urlencode(
        {
            "from": from_value,
            "to": to_value,
            "datasource": "tempo",
            "queryType": "traceqlSearch",
            "query": query,
        }
    )
    return [f"{TRACE_DRILLDOWN_PATH}?{params}"]


def build_traceql_query(
    *,
    run_id: str,
    pipeline_name: str | None,
    provider: str | None,
    run_type: str | None,
) -> str | None:
    if not run_id:
        return None
    filters = [f'span."bioetl.run_id" = "{run_id}"']
    if pipeline_name:
        filters.append(f'span."bioetl.pipeline" = "{pipeline_name}"')
    if run_type:
        filters.append(f'span."bioetl.run_type" = "{run_type}"')
    if provider:
        filters.append(f'span."bioetl.provider" = "{provider}"')
    return "{ " + " && ".join(filters) + " }"


def build_trace_time_window(
    *,
    run_manifest: RunManifestInspectionResult | None,
    audit: AuditInspectionResult,
) -> tuple[str, str]:
    timestamps: list[datetime] = []
    manifest_created_at = (
        getattr(run_manifest.manifest, "created_at", None)
        if run_manifest is not None
        else None
    )
    normalized_manifest_time = normalize_datetime(manifest_created_at)
    if normalized_manifest_time is not None:
        timestamps.append(normalized_manifest_time)
    for entry in audit.entries:
        normalized_entry_time = normalize_datetime(entry.timestamp)
        if normalized_entry_time is not None:
            timestamps.append(normalized_entry_time)
    if not timestamps:
        return (TRACE_DRILLDOWN_DEFAULT_FROM, TRACE_DRILLDOWN_DEFAULT_TO)
    start = min(timestamps) - TRACE_WINDOW_PADDING
    end = max(timestamps) + TRACE_WINDOW_PADDING
    return (str(int(start.timestamp() * 1000)), str(int(end.timestamp() * 1000)))


def normalize_datetime(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
