"""HTTP record-payload classification tests for the Grafana live auditor."""

from __future__ import annotations

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject

pytestmark = pytest.mark.repo_backed


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
