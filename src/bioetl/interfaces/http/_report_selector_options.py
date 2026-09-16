"""Supplement selector catalogs with identity-checked persisted run reports."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.run_reports.query import list_pipeline_reports
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.interfaces.http.report_root_config import configured_report_root
from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_payload

_FIELDS = {
    "workflow": "workflow_id",
    "pipeline": "pipeline_name",
    "run_type": "run_type",
    "run_id": "run_id",
    "run_status": "status",
    "provider": "provider",
}
_ALL = {"", "All", "all", "$__all", ".*"}


def supplement_report_options(
    payload: dict[str, object],
    *,
    dimension: str,
    response_shape: str,
    scopes: dict[str, tuple[str, ...]],
    root: Path | None = None,
) -> dict[str, object]:
    """Append genuine report identities; empty/error responses are never fabricated."""
    if dimension not in _FIELDS:
        return payload
    root = configured_report_root(root=root)
    entries = list_pipeline_reports(
        root=root, limit=None, store=create_run_report_store()
    )
    raw_items = payload.get("items", [])
    items = list(raw_items) if isinstance(raw_items, list) else []
    seen = {item.get("value") if isinstance(item, dict) else item for item in items}
    for entry in sorted(entries, key=lambda item: item.started_at or "", reverse=True):
        pipelines = set(scopes.get("pipeline", ())) - _ALL
        run_ids = set(scopes.get("run_id", ())) - _ALL
        if (pipelines and entry.owner not in pipelines) or (
            run_ids and entry.run_id not in run_ids
        ):
            continue
        report = load_pipeline_run_report_payload(
            run_id=entry.run_id,
            pipeline_name=entry.owner,
            root=root,
        )
        if report is None:
            raise ValueError("Persisted selector report is unreadable or unsupported")
        identity = report.get("identity")
        if not isinstance(identity, dict):
            raise ValueError("Persisted selector report has no identity")
        if (
            identity.get("run_id") != entry.run_id
            or identity.get("pipeline_name") != entry.owner
        ):
            raise ValueError(
                "Persisted selector report identity does not match its path"
            )
        if any(
            allowed and identity.get(_FIELDS[name]) not in allowed
            for name, values in scopes.items()
            if (allowed := set(values) - _ALL)
        ):
            continue
        value = identity.get(_FIELDS[dimension])
        if not isinstance(value, str) or not value or value in seen:
            continue
        seen.add(value)
        label = value
        if dimension == "run_id":
            label = (
                f"{identity.get('started_at', 'UNKNOWN')} · {entry.owner} · "
                f"{identity.get('status', 'unknown')} · {value}"
            )
        items.append(
            {"text": label, "value": value} if response_shape == "options" else value
        )
    return {**payload, "items": items}
