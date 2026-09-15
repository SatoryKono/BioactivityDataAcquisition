"""HTTP record-payload classification tests for the Grafana live auditor."""

from __future__ import annotations

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject

pytestmark = pytest.mark.repo_backed


@pytest.mark.parametrize(
    "semantic_kind",
    ["http_endpoint", "http_table", "http_summary", "http_records", "freshness"],
)
@pytest.mark.parametrize("required", [True, False])
@pytest.mark.parametrize("reason", ["capacity_exhausted", "deadline_exceeded"])
def test_live_audit_blocks_forensic_error_rows_over_http_200(
    monkeypatch: pytest.MonkeyPatch, semantic_kind: str, required: bool, reason: str
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=9416,
        title="Review Retention Compliance",
        source_kind="http",
        semantic_kind=semantic_kind,
        required=required,
    )
    payload = {
        "contract": "forensic_endpoint_error_v1",
        "status": "unavailable",
        "endpoint": "retention-compliance",
        "reason": reason,
        "retryable": True,
        "rows": [
            {"check": "endpoint_availability", "status": "ERROR", "reason": reason}
        ],
    }
    monkeypatch.setattr(
        audit_subject, "_fetch_json_with_optional_auth", lambda *args, **kwargs: payload
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))
    result = audit_subject._audit_http_panel(
        spec,
        {
            "targets": [
                {"url": "/ops/control-plane/retention-compliance?error_as_row=1"}
            ]
        },
        audit_subject._parse_args([]),
        app_base_url="http://127.0.0.1:8000",
    )
    assert result.status == "error"
    assert result.classification == "endpoint_execution_error"
    assert reason in result.detail
    assert result.response == payload
    assert audit_subject.semantic_gate_evidence([result])["blocking_count"] == 1


def test_live_audit_classifies_empty_filtered_records_by_row_count() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [], "total": 0, "limit": 50, "offset": 0}
    )

    assert classification == "zero_result"
    assert "zero rows" in detail


def test_live_audit_classifies_nonempty_filtered_records_by_row_count() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [{"payload_hash": "abc"}], "total": 1, "limit": 50, "offset": 0}
    )

    assert classification == "nonempty_result"
    assert "returned rows" in detail


def test_live_audit_rejects_filtered_records_total_items_drift() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [], "total": 1, "limit": 50, "offset": 0}
    )

    assert classification == "invalid_shape"
    assert "disagree" in detail
