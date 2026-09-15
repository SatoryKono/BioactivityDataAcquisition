"""Query mode and historical evidence regressions for the live panel auditor."""

from urllib.parse import parse_qs, urlsplit

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as audit

pytestmark = pytest.mark.repo_backed


@pytest.mark.parametrize(
    ("flags", "expected_paths"),
    [
        ({}, ["/api/v1/query_range"]),
        ({"instant": False, "range": True}, ["/api/v1/query_range"]),
        ({"instant": True}, ["/api/v1/query"]),
        ({"instant": True, "range": False}, ["/api/v1/query"]),
        ({"instant": True, "range": True}, ["/api/v1/query", "/api/v1/query_range"]),
    ],
)
def test_target_mode_controls_requests_and_preserves_range_evidence(
    monkeypatch,
    flags,
    expected_paths,
):
    calls = []

    def fetch(url, **_kwargs):
        calls.append(url)
        if urlsplit(url).path.endswith("query_range"):
            return {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"pipeline": "chembl_assay"},
                            "values": [[1000, "2"], [1300, "3"]],
                        },
                    ],
                },
            }
        return {"status": "success", "data": {"resultType": "vector", "result": []}}

    monkeypatch.setattr(audit, "_fetch_json", fetch)
    spec = audit.PanelAuditSpec(
        "bioetl-dq-v2", 11, "Duration", "prometheus", "prometheus_query", "A", False
    )
    monkeypatch.setattr(audit, "effective_panel_specs", lambda: (spec,))
    config = audit._parse_args(["--range-from", "1000000", "--range-to", "1600000"])
    result = audit._audit_prometheus_panel(
        spec,
        {
            "type": "timeseries",
            "targets": [{"refId": "A", "expr": "duration", **flags}],
        },
        config,
    )
    assert [urlsplit(url).path for url in calls] == expected_paths
    for url in calls:
        query = parse_qs(urlsplit(url).query)
        if urlsplit(url).path.endswith("query_range"):
            assert float(query["start"][0]) == 1000
            assert float(query["end"][0]) == 1600
            assert float(query["step"][0]) > 0
        else:
            assert float(query["time"][0]) == 1600
    if len(calls) == 2:
        assert result.classification == "mixed_query_results"
        assert len(result.query_requests) == 2
        assert audit.semantic_gate_evidence([result])["status"] == "review_required"
    elif expected_paths[0].endswith("query_range"):
        assert result.classification == "nonzero_result"
        assert result.response["data"]["result"][0]["values"][0] == [1000, "2"]
    else:
        assert result.classification == "empty_result"


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], "empty_result"),
        ([[1, "0"], [2, "0"]], "zero_result"),
        ([[1, "0"], [2, "4"]], "nonzero_result"),
        ([[1, "NaN"]], "nonfinite_result"),
        ([[1, "+Inf"]], "nonfinite_result"),
        ([[1, "bad"]], "invalid_shape"),
        ([[1]], "invalid_shape"),
    ],
)
def test_matrix_samples_receive_numeric_and_shape_validation(values, expected):
    payload = {
        "status": "success",
        "data": {"resultType": "matrix", "result": [{"values": values}]},
    }
    assert audit._classify_prometheus_payload(payload)[0] == expected


def test_matrix_annotation_requires_review():
    payload = {
        "status": "success",
        "infos": ["histogram repaired"],
        "data": {
            "resultType": "matrix",
            "result": [{"values": [[1, "0.5"]]}],
        },
    }
    assert audit._classify_prometheus_payload(payload)[0] == "annotated_result"


@pytest.mark.parametrize(
    "result",
    [
        None,
        [{"values": None}],
        [{"histograms": [[1, {}]]}],
        [{"values": [[1, "2"]], "histograms": [[2, {}]]}],
        [None],
    ],
)
def test_malformed_or_unsupported_matrix_is_not_empty_success(result):
    assert (
        audit._classify_prometheus_payload(
            {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": result,
                },
            }
        )[0]
        == "invalid_shape"
    )


@pytest.mark.parametrize("step", ["0", "-1", "nan", "inf"])
def test_invalid_range_step_is_rejected(step):
    with pytest.raises(SystemExit):
        audit._parse_args(["--prometheus-step-seconds", step])


def test_both_mode_preserves_first_response_when_second_request_fails(monkeypatch):
    payload = {"status": "success", "data": {"resultType": "vector", "result": []}}

    def fetch(url, **_kwargs):
        if urlsplit(url).path.endswith("query_range"):
            raise OSError("range endpoint unavailable")
        return payload

    monkeypatch.setattr(audit, "_fetch_json", fetch)
    spec = audit.PanelAuditSpec(
        "bioetl-dq-v2", 11, "Duration", "prometheus", "prometheus_query", "A", False
    )
    result = audit._audit_prometheus_panel(
        spec,
        {
            "targets": [
                {"refId": "A", "expr": "duration", "instant": True, "range": True}
            ]
        },
        audit._parse_args([]),
    )
    assert result.classification == "blocked_unavailable"
    assert len(result.query_requests) == 2
    assert result.query_requests[0]["response"] == payload
    assert result.query_requests[1]["mode"] == "range"
    assert "range endpoint unavailable" in result.query_requests[1]["detail"]
