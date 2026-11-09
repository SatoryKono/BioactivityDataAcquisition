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
    "workflow, mixed, expected",
    [(".*", False, True), ("named_workflow", False, False), (".*", True, False)],
)
def test_standalone_witness_must_cover_the_entire_scope(workflow, mixed, expected):
    def fetch(url, **_kwargs):
        query = parse_qs(urlsplit(url).query)["query"][0]
        rows = [
            {
                "metric": {"pipeline": "uniprot", "run_type": "incremental"},
                "value": [1, "1"],
            }
        ]
        if mixed and query.startswith(
            "bioetl_runtime_pipeline_run_type_universe_scoped"
        ):
            rows.append(
                {
                    "metric": {"pipeline": "chembl", "run_type": "incremental"},
                    "value": [1, "1"],
                }
            )
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


@pytest.mark.parametrize(
    "gap", [None, "failed_dependency", "missing_dependency", "active_signal"]
)
def test_ranked_evidence_needs_healthy_dependencies_and_no_active_witness(gap):
    def fetch(url, **_kwargs):
        if urlsplit(url).path.endswith("rules"):
            names = [
                "bioetl_incident_ranked_evidence",
                "bioetl_incident_ranked_runtime",
                "bioetl_incident_ranked_provider",
                "bioetl_incident_ranked_dq",
            ]
            if gap == "missing_dependency":
                names.remove("bioetl_incident_ranked_runtime")
            rules = [
                {
                    "name": name,
                    "type": "recording",
                    "health": (
                        "err"
                        if gap == "failed_dependency"
                        and name == "bioetl_incident_ranked_runtime"
                        else "ok"
                    ),
                }
                for name in names
            ]
            return {"status": "success", "data": {"groups": [{"rules": rules}]}}
        query = parse_qs(urlsplit(url).query)["query"][0]
        if query.startswith("up{"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        elif query.startswith("bioetl_runtime_pipeline_run_type_universe_scoped"):
            rows = [{"metric": {"pipeline": "test"}, "value": [1, "1"]}]
        else:
            rows = [
                {"metric": {}, "value": [1, "1" if gap == "active_signal" else "0"]}
            ]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=2010,
        expr="bioetl_incident_ranked_evidence",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
    )
    assert accepted is (gap is None)
