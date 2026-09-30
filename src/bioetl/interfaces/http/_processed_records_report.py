"""Exact-run accounting from the persisted pipeline report, never current metrics."""

from bioetl.interfaces.http.processed_records_table import (
    PROCESSED_RECORDS_ROW_SPECS,
    build_processed_records_table_payload,
)
from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_payload


def saved_report_records(
    *, pipeline: str, run_id: str, run_type: str | None
) -> dict[str, object] | None:
    """Return accounting only when the saved identity matches the whole scope."""
    report = load_pipeline_run_report_payload(run_id=run_id, pipeline_name=pipeline)
    if not isinstance(report, dict):
        return None
    identity = report.get("identity")
    if not isinstance(identity, dict) or (
        identity.get("run_id"),
        identity.get("pipeline_name"),
    ) != (run_id, pipeline):
        return None
    selected_types = {
        part.strip()
        for part in (run_type or "").split(",")
        if part.strip() and part.strip() not in {"All", "$__all", ".*"}
    }
    if selected_types and identity.get("run_type") not in selected_types:
        return None
    layers = report.get("layers")
    if not isinstance(layers, dict):
        layers = {}
    values = {}
    for spec in PROCESSED_RECORDS_ROW_SPECS:
        key = spec.metric.removeprefix("bioetl_processed_records_").removesuffix(
            "_current"
        )
        raw = layers.get("bronze_records" if key == "bronze" else key)
        values[spec.metric] = raw if type(raw) in (int, float) and raw >= 0 else None
    payload = build_processed_records_table_payload(
        metric_values=values,
        pipeline=pipeline,
        run_type=run_type,
    )
    payload.update(source="saved_pipeline_run_report", run_id=run_id)
    return payload
