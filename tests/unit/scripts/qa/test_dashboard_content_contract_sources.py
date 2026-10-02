"""Dashboard datasource reuse must retain the underlying evidence provenance."""

import pytest

from scripts.engineering.qa.generate_dashboard_content_contract import (
    _resolved_evidence_source,
)


pytestmark = pytest.mark.unit


def test_verdict_reuse_keeps_ops_http_provenance():
    source = {
        "id": 9002,
        "datasource": "BioETL Ops HTTP",
        "targets": [{"url": "/ops/observability/selected-run-status?run_id=r1"}],
    }
    verdict = {
        "id": 9604,
        "datasource": {"uid": "-- Dashboard --"},
        "targets": [{"panelId": 9002}],
    }
    assert _resolved_evidence_source(verdict, {9002: source}) == "ops_http"


def test_broken_dashboard_source_is_rejected():
    verdict = {
        "id": 9604,
        "datasource": {"uid": "-- Dashboard --"},
        "targets": [{"panelId": 9002}],
    }
    with pytest.raises(ValueError, match="source missing"):
        _resolved_evidence_source(verdict, {})


def test_cyclic_dashboard_source_is_rejected():
    verdict = {
        "id": 9604,
        "datasource": {"uid": "-- Dashboard --"},
        "targets": [{"panelId": 9604}],
    }
    with pytest.raises(ValueError, match="cycle"):
        _resolved_evidence_source(verdict, {9604: verdict})
