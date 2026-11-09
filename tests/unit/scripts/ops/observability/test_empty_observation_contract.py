"""Empty event observations require independent source and scope evidence."""

from urllib.parse import parse_qs, urlsplit

import pytest

from scripts.ops.observability.grafana._empty_observation_contract import qualify_empty

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "gap",
    [None, "down", "scope", "metadata", "annotation", "gauge", "warnings", "infos"],
)
def test_empty_event_contract_fails_closed_on_missing_witness(gap):
    def fetch(url, **_kwargs):
        params = parse_qs(urlsplit(url).query)
        if "metadata" in url:
            family = params["metric"][0]
            return {
                "status": "success",
                "warnings": ["partial metadata"] if gap == "warnings" else [],
                "infos": ["metadata notice"] if gap == "infos" else [],
                "data": {}
                if gap == "metadata"
                else {family: [{"type": "gauge" if gap == "gauge" else "counter"}]},
            }
        assert params["time"] == ["2026-11-09T11:30:00+00:00"]
        query = params["query"][0]
        rows = [
            {"metric": {"job": job}, "value": [1, "0" if gap == "down" else "1"]}
            for job in ("bioetl", "pushgateway", "prometheus")
        ]
        if not query.startswith("up{"):
            rows = (
                []
                if gap == "scope"
                else [{"metric": {"pipeline": "test"}, "value": [1, "1"]}]
            )
        return {
            "status": "success",
            "warnings": ["partial"] if gap == "annotation" else [],
            "data": {"resultType": "vector", "result": rows},
        }

    accepted, evidence = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=107,
        expr="sum(increase(bioetl_audit_write_events_total[1h]))",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
        as_of="2026-11-09T11:30:00+00:00",
    )
    assert accepted is (gap is None)
    assert evidence


@pytest.mark.parametrize("panel_id", [205, 999])
def test_panels_without_qualified_empty_contract_cannot_bypass_review(panel_id):
    accepted, evidence = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=panel_id,
        expr="absent_metric",
        base_url="http://prometheus",
        fetch=lambda *_a, **_k: pytest.fail(
            "unregistered panel must not query witnesses"
        ),
        substitute=lambda value: value,
        timeout=1,
    )
    assert not accepted
    assert not evidence


@pytest.mark.parametrize(
    "workflow, expected", [(".*", True), ("named_workflow", False)]
)
def test_standalone_witness_does_not_excuse_concrete_workflow(workflow, expected):
    def fetch(url, **_kwargs):
        query = parse_qs(urlsplit(url).query)["query"][0]
        rows = [{"metric": {}, "value": [1, "1"]}]
        if query.startswith("up{"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=9701,
        expr="bioetl_workflow_scope_input_status",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value.replace("$workflow", workflow),
        timeout=1,
    )
    assert accepted is expected


@pytest.mark.parametrize(
    "gap",
    [
        None,
        "unhealthy",
        "missing",
        "alerting",
        "error",
        "warnings",
        "infos",
        "unhealthy-sibling",
    ],
)
def test_empty_alert_list_requires_healthy_recording_rule(gap):
    def fetch(url, **_kwargs):
        endpoint = urlsplit(url).path
        if endpoint.endswith("metadata"):
            pytest.fail("metadata must not substitute a recording rule")
        if endpoint.endswith("rules"):
            rule = {
                "name": "bioetl_incident_alert_priority",
                "type": "alerting" if gap == "alerting" else "recording",
                "health": "err" if gap == "unhealthy" else "ok",
            }
            rules = [] if gap == "missing" else [rule]
            if gap == "unhealthy-sibling":
                rules.insert(0, {**rule, "health": "err"})
            return {
                "status": "error" if gap == "error" else "success",
                "warnings": ["partial"] if gap == "warnings" else [],
                "infos": ["notice"] if gap == "infos" else [],
                "data": {"groups": [{"rules": rules}]},
            }
        query = parse_qs(urlsplit(url).query)["query"][0]
        rows = [{"metric": {}, "value": [1, "1"]}]
        if query.startswith("up{job=~"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=2005,
        expr="bioetl_incident_alert_priority",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
    )
    assert accepted is (gap is None)
