"""Materialize control-plane validation fixtures outside Grafana tooling."""

from __future__ import annotations

import json
from pathlib import Path


def materialize_trust_validation_fixture_matrix(
    *,
    out: Path,
    matrix: dict[str, dict[str, dict[str, object]]],
    panel_map: dict[int, str],
    fixture_run_id: object,
) -> dict[str, object]:
    """Write the bounded Trust fixture matrix and return its index."""
    out.mkdir(parents=True, exist_ok=True)
    index: dict[str, object] = {
        "schema_version": 1,
        "issue": "#8576",
        "related_issue": "#8578",
        "contract": "control_plane_validation_evidence_v1",
        "panel_map": panel_map,
        "fixture_run_id": str(fixture_run_id),
        "fixture_pipeline": "chembl_activity",
        "fixture_run_type": "incremental",
        "states": {
            "populated": "OK check rows for selected exact run (operator-readable).",
            "valid_empty_or_unknown": (
                "Scope unresolved / evidence absent; UNKNOWN, not green."
            ),
            "zero_failures": (
                "failure-reasons only: exact run, zero failed events (counts=0)."
            ),
            "backend_error": "Source read/parse failure as ERROR row (HTTP 200 body).",
            "service_unavailable": (
                "Service missing; HTTP 503 body for QUERY_ERROR path."
            ),
            "empty_rows": "Synthetic rows=[] for Infinity noValue visual path.",
            "aggregate_scope_unknown": (
                "checkpoint only: aggregate scope needs exact pipeline."
            ),
        },
        "endpoints": {},
    }
    endpoints: dict[str, object] = {}
    for endpoint, states in matrix.items():
        ep_dir = out / endpoint
        ep_dir.mkdir(parents=True, exist_ok=True)
        ep_index: dict[str, object] = {}
        for state, payload in states.items():
            path = ep_dir / f"{state}.json"
            path.write_text(
                json.dumps(payload, indent=2, default=str, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            http_status = 503 if state == "service_unavailable" else 200
            if isinstance(payload.get("http_status"), int):
                http_status = int(payload["http_status"])
            raw_rows = payload.get("rows")
            rows = raw_rows if isinstance(raw_rows, list) else []
            ep_index[state] = {
                "path": path.as_posix(),
                "status": payload.get("status"),
                "row_count": len(rows),
                "http_status": http_status,
            }
            print(f"wrote {path} status={payload.get('status')} rows={len(rows)}")
        endpoints[endpoint] = ep_index
    index["endpoints"] = endpoints
    (out / "INDEX.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return index


__all__ = ["materialize_trust_validation_fixture_matrix"]
