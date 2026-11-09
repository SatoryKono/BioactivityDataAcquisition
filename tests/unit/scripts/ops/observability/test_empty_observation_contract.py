"""Empty event observations require independent source and scope evidence."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject

from scripts.ops.observability.grafana._empty_observation_contract import (
    _STANDALONE_DEPENDENCIES,
    _WORKFLOW_INPUT_DEPENDENCIES,
    _alert_history_available,
    qualify_empty,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "gap", [None, "missing-rule", "bad-rule", "outage", "one-sample", "query-error"]
)
def test_empty_alert_history_requires_rules_and_observed_service(gap, monkeypatch):
    monkeypatch.setattr(
        "scripts.ops.observability.grafana._empty_observation_contract._expected_alert_names",
        lambda: {"ExampleAlert"},
    )

    def request(*_args):
        rules = (
            []
            if gap == "missing-rule"
            else [
                {
                    "name": "ExampleAlert",
                    "type": "alerting",
                    "health": "err" if gap == "bad-rule" else "ok",
                }
            ]
        )
        return {"status": "success", "data": {"groups": [{"rules": rules}]}}

    def vector(query):
        if gap == "query-error":
            return None
        value = "1" if query.startswith("min_") or gap == "one-sample" else "20"
        if query.startswith("min_") and gap == "outage":
            value = "0"
        return [{"metric": {}, "value": [1, value]}]

    assert _alert_history_available(
        'ALERTS{alertstate="firing"} or (ALERTS{alertstate="pending"} * 2)',
        vector,
        request,
    ) is (gap is None)


@pytest.mark.parametrize(
    "gap",
    [
        None,
        "down",
        "scope",
        "metadata",
        "annotation",
        "gauge",
        "warnings",
        "infos",
        "single-sample",
        "sample-query-error",
    ],
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
        if query.startswith("count_over_time("):
            assert (
                query
                == 'count_over_time(bioetl_audit_write_events_total{operation="commit"}[1h])'
            )
            return {
                "status": "error" if gap == "sample-query-error" else "success",
                "data": {
                    "resultType": "vector",
                    "result": [{"metric": {}, "value": [1, "1"]}]
                    if gap == "single-sample"
                    else [],
                },
            }
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
        expr='sum(increase(bioetl_audit_write_events_total{operation="commit"}[1h]))',
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
    "workflow, mixed, gap, expected",
    [
        (".*", False, None, True),
        ("named_workflow", False, None, False),
        (".*", True, None, False),
        (".*", False, "missing", False),
        (".*", False, "unhealthy", False),
    ],
)
def test_standalone_witness_must_cover_the_entire_scope(workflow, mixed, gap, expected):
    def fetch(url, **_kwargs):
        if urlsplit(url).path.endswith("rules"):
            rules = [
                {
                    "name": name,
                    "type": "recording",
                    "health": "err"
                    if gap == "unhealthy" and name == "bioetl_workflow_scope_universe"
                    else "ok",
                }
                for name in _STANDALONE_DEPENDENCIES | _WORKFLOW_INPUT_DEPENDENCIES
                if gap != "missing" or name != "bioetl_workflow_scope_universe"
            ]
            return {"status": "success", "data": {"groups": [{"rules": rules}]}}
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
        "unhealthy-alert",
        "missing-alert",
    ],
)
def test_empty_alert_list_requires_healthy_alerting_and_recording_rules(
    gap, monkeypatch
):
    monkeypatch.setattr(
        "scripts.ops.observability.grafana._empty_observation_contract._expected_alert_names",
        lambda: {"BioETLPipelineRunFailed"},
    )

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
            if gap != "missing-alert":
                rules.append(
                    {
                        "name": "BioETLPipelineRunFailed",
                        "type": "alerting",
                        "health": "err" if gap == "unhealthy-alert" else "ok",
                    }
                )
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


@pytest.mark.parametrize(
    "gap",
    [
        None,
        "missing-operand",
        "active-dq",
        "lazy-event",
        "single-sample",
        "raw-query-error",
        "active-operand",
    ],
)
def test_dq_empty_requires_all_operands_and_no_active_signal(gap):
    metric = "bioetl_runtime_alert_condition_dq_hard_fail_15m"

    def fetch(url, **_kwargs):
        if urlsplit(url).path.endswith("metadata"):
            family = parse_qs(urlsplit(url).query)["metric"][0]
            return {
                "status": "success",
                "data": {}
                if gap == "missing-operand"
                else {family: [{"type": "counter"}]},
            }
        if urlsplit(url).path.endswith("rules"):
            return {
                "status": "success",
                "data": {
                    "groups": [
                        {
                            "rules": [
                                {"name": metric, "type": "recording", "health": "ok"}
                            ]
                        }
                    ]
                },
            }
        query = parse_qs(urlsplit(url).query)["query"][0]
        rows = [{"metric": {}, "value": [1, "0"]}]
        if query.startswith("up{job=~"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        elif query.startswith(metric) and gap in {
            "missing-operand",
            "lazy-event",
            "single-sample",
            "raw-query-error",
        }:
            rows = []
        elif query.startswith(metric) and gap == "active-operand":
            rows = [{"metric": {}, "value": [1, "1"]}]
        elif query.startswith("count_over_time("):
            if gap == "raw-query-error":
                return {"status": "error"}
            rows = [{"metric": {}, "value": [1, "1"]}] if gap == "single-sample" else []
        elif query.startswith("bioetl_dq_current_status") and gap == "active-dq":
            rows = [{"metric": {}, "value": [1, "2"]}]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=4,
        expr=f"sum({metric})",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
    )
    assert accepted is (gap in {None, "lazy-event"})


@pytest.mark.parametrize("resets, expected", [("0", True), ("1", False), (None, False)])
def test_empty_histogram_rejects_resets_and_failed_reset_queries(resets, expected):
    metric = "bioetl_checkpoint_save_duration_seconds"

    def fetch(url, **_kwargs):
        params = parse_qs(urlsplit(url).query)
        if "metadata" in url:
            return {"status": "success", "data": {metric: [{"type": "histogram"}]}}
        query = params["query"][0]
        rows = [{"metric": {}, "value": [1, "6"]}]
        if query.startswith("up{job=~"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        if query.startswith("changes("):
            if resets is None:
                return {"status": "error"}
            rows = [{"metric": {}, "value": [1, resets]}]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=105,
        expr=f"increase({metric}_bucket[1h]) unless (changes({metric}_created[1h]) > 0)",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
    )
    assert accepted is expected


@pytest.mark.parametrize(
    "gap",
    [
        None,
        "no-reset",
        "single-sample",
        "missing-buckets",
        "query-error",
        "wrong-panel",
    ],
)
@pytest.mark.parametrize(
    "panel_id,family,labels",
    [
        (105, "bioetl_checkpoint_save_duration_seconds", "pipeline, operation"),
        (207, "bioetl_phase_duration_seconds", "phase, status"),
        (239, "bioetl_pipeline_duration_seconds", "stage, status, run_type"),
    ],
)
def test_reviewed_generation_gap_requires_reset_and_complete_raw_evidence(
    gap, panel_id, family, labels
):

    def fetch(url, **_kwargs):
        params = parse_qs(urlsplit(url).query)
        if "metadata" in url:
            return {"status": "success", "data": {family: [{"type": "histogram"}]}}
        query = params["query"][0]
        rows = [{"metric": {}, "value": [1, "10"]}]
        if query.startswith("up{"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        elif query.startswith("changes("):
            if gap == "query-error":
                return {"status": "error"}
            rows = [{"metric": {}, "value": [1, "0" if gap == "no-reset" else "1"]}]
        elif query.startswith("count_over_time(") and "_bucket" in query:
            rows = (
                []
                if gap == "missing-buckets"
                else [
                    {
                        "metric": {},
                        "value": [1, "1" if gap == "single-sample" else "10"],
                    }
                ]
            )
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=106 if gap == "wrong-panel" else panel_id,
        expr=f"histogram_quantile(0.5, sum by (le, {labels}) (increase({family}_bucket[24h])) unless on ({labels}) (sum by ({labels}) (changes({family}_created[24h]) > 0)))",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
        historical_reset=True,
    )
    assert accepted is (gap is None)


@pytest.mark.parametrize(
    "gap", [None, "missing-operand", "active-signal", "unknown-health"]
)
@pytest.mark.parametrize(
    "panel_id, metric, witness",
    [
        (
            4,
            "bioetl_runtime_alert_condition_dq_hard_fail_15m",
            "bioetl_dq_current_status",
        ),
        (
            259,
            "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m",
            "bioetl_provider_current_status",
        ),
    ],
)
def test_conditions_empty_requires_all_operands_and_no_active_signal(
    gap, panel_id, metric, witness
):

    def fetch(url, **_kwargs):
        if urlsplit(url).path.endswith("metadata"):
            return {"status": "success", "data": {}}
        if urlsplit(url).path.endswith("rules"):
            return {
                "status": "success",
                "data": {
                    "groups": [
                        {
                            "rules": [
                                {"name": metric, "type": "recording", "health": "ok"}
                            ]
                        }
                    ]
                },
            }
        query = parse_qs(urlsplit(url).query)["query"][0]
        rows = [{"metric": {}, "value": [1, "0"]}]
        if query.startswith("up{job=~"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        elif query.startswith(metric) and gap == "missing-operand":
            rows = []
        elif query.startswith(witness) and gap == "active-signal":
            rows = [{"metric": {}, "value": [1, "2"]}]
        elif query.startswith(witness) and gap == "unknown-health":
            rows = [{"metric": {}, "value": [1, "3"]}]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=panel_id,
        expr=f"sum({metric})",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
    )
    assert accepted is (gap is None or (panel_id == 259 and gap == "unknown-health"))


@pytest.mark.parametrize("raw_count, expected", [(None, True), (1, False), (2, False)])
def test_empty_runtime_error_rate_requires_no_raw_error_observations(
    raw_count, expected
):
    def fetch(url, **_kwargs):
        endpoint = urlsplit(url).path
        if endpoint.endswith("rules"):
            rule = {
                "name": "bioetl_runtime_error_rate_30m",
                "type": "recording",
                "health": "ok",
            }
            return {"status": "success", "data": {"groups": [{"rules": [rule]}]}}
        if endpoint.endswith("metadata"):
            return {
                "status": "success",
                "data": {"bioetl_errors_total": [{"type": "counter"}]},
            }
        query = parse_qs(urlsplit(url).query)["query"][0]
        rows = [{"metric": {}, "value": [1, "1"]}]
        if query.startswith("up{job=~"):
            rows = [
                {"metric": {"job": job}, "value": [1, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        elif query.startswith("count_over_time"):
            assert (
                query
                == 'count_over_time(bioetl_errors_total{pipeline=~"$pipeline"}[30m])'
            )
            rows = (
                []
                if raw_count is None
                else [{"metric": {}, "value": [1, str(raw_count)]}]
            )
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=220,
        expr='bioetl_runtime_error_rate_30m{pipeline=~"$pipeline"}',
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
    )
    assert accepted is expected


@pytest.mark.parametrize("proved", [True, False])
def test_generation_gap_review_keeps_warning_and_requires_evidence(proved, monkeypatch):
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-incident-v1",
        panel_id=105,
        title="Checkpoint latency",
        source_kind="prometheus",
        semantic_kind="prometheus_query",
        target_ref_id="A",
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))
    monkeypatch.setattr(
        audit_subject,
        "_collect_empty_witnesses",
        lambda *_args, historical_reset=False, **_kwargs: (
            historical_reset and proved,
            [],
        ),
    )
    classification, detail = audit_subject._qualify_empty_panel(
        spec, audit_subject._parse_args([]), "guarded histogram", [], "No estimate"
    )
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=105,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="ok",
        classification=classification,
        detail=detail,
        query_preview="guarded histogram",
        target_ref_id="A",
    )
    gate = audit_subject.semantic_gate_evidence([result])
    assert gate["status"] == ("pass" if proved else "review_required")
    if proved:
        assert "WARN" in detail
        assert gate["panel_outcomes"][0]["decision"] == "pass_reviewed"


@pytest.mark.parametrize("early_sample", [False, True])
def test_empty_range_checks_samples_before_the_last_step(early_sample):
    family = "bioetl_shutdown_started_total"
    bounds = {"start": "0", "end": "3600", "step": "60"}

    def fetch(url, **_kwargs):
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        if parsed.path.endswith("metadata"):
            return {"status": "success", "data": {family: [{"type": "counter"}]}}
        query = params["query"][0]
        if query.startswith("count_over_time"):
            assert parsed.path == "/api/v1/query_range"
            assert {key: params[key][0] for key in bounds} == bounds
            rows = [{"metric": {}, "values": [[60, "1"]]}] if early_sample else []
            return {
                "status": "success",
                "data": {"resultType": "matrix", "result": rows},
            }
        rows = [{"metric": {}, "value": [3600, "1"]}]
        if query.startswith("up{job=~"):
            rows = [
                {"metric": {"job": job}, "value": [3600, "1"]}
                for job in ("bioetl", "pushgateway", "prometheus")
            ]
        return {"status": "success", "data": {"resultType": "vector", "result": rows}}

    accepted, _ = qualify_empty(
        dashboard_uid="bioetl-incident-v1",
        panel_id=209,
        expr=f"increase({family}[5m])",
        base_url="http://prometheus",
        fetch=fetch,
        substitute=lambda value: value,
        timeout=1,
        range_bounds=bounds,
    )
    assert accepted is not early_sample


@pytest.mark.parametrize(
    "counts, expected", [([1, 2], True), ([1], False), ([2], True)]
)
def test_historical_boundary_requires_later_samples_for_each_series(counts, expected):
    from scripts.ops.observability.grafana._empty_observation_contract import (
        _event_samples_sufficient,
    )

    rows = [
        {"metric": {"pipeline": "p"}, "value": [i, str(n)]}
        for i, n in enumerate(counts)
    ]
    assert _event_samples_sufficient(rows, require_reset=True) is expected
    assert _event_samples_sufficient(rows, require_reset=False) is all(
        n >= 2 for n in counts
    )
    rows.append({"metric": {"pipeline": "other"}, "value": [0, "1"]})
    assert not _event_samples_sufficient(rows, require_reset=True)
