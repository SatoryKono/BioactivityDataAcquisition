"""Unit tests for partial Prometheus rule failure detection."""

from __future__ import annotations

import json

import pytest

from scripts.ops.observability import check_prometheus_rules_health as mod

pytestmark = pytest.mark.unit


def test_collect_rule_issues_flags_last_error() -> None:
    payload = {
        "status": "success",
        "data": {
            "groups": [
                {
                    "file": "/etc/prometheus/rules/bioetl_observability.yml",
                    "name": "bioetl_runtime_dashboard_recording",
                    "rules": [
                        {
                            "name": "bioetl_runtime_current_status",
                            "type": "recording",
                            "health": "ok",
                            "lastError": "",
                        },
                        {
                            "name": "broken_record",
                            "type": "recording",
                            "health": "err",
                            "lastError": "many-to-many matching not allowed",
                        },
                    ],
                },
                {
                    "file": "/etc/prometheus/rules/other.yml",
                    "name": "unrelated",
                    "rules": [
                        {
                            "name": "x",
                            "health": "err",
                            "lastError": "ignored non-bioetl",
                        }
                    ],
                },
            ]
        },
    }
    issues, groups, rules_n = mod.collect_rule_issues(payload)
    assert groups == 1
    assert rules_n == 2
    assert len(issues) == 1
    assert issues[0].rule == "broken_record"
    assert "many-to-many" in issues[0].last_error


def test_check_rules_health_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(url: str, *, timeout: float):
        del timeout
        if url.endswith("/api/v1/rules"):
            return {
                "status": "success",
                "data": {
                    "groups": [
                        {
                            "file": "bioetl_observability.yml",
                            "name": "g",
                            "rules": [
                                {
                                    "name": "r",
                                    "health": "ok",
                                    "lastError": "",
                                }
                            ],
                        }
                    ]
                },
            }
        if "evaluation_failures" in url:
            return {
                "status": "success",
                "data": {"resultType": "vector", "result": [{"value": [0, "0"]}]},
            }
        if "iterations_missed" in url:
            return {
                "status": "success",
                "data": {"resultType": "vector", "result": [{"value": [0, "0"]}]},
            }
        raise AssertionError(url)

    monkeypatch.setattr(mod, "_fetch_json", fake_fetch)
    report = mod.check_rules_health(prometheus_url="http://127.0.0.1:9090")
    assert report.ok is True
    assert report.bioetl_rules == 1
    assert report.issues == []


def test_check_rules_health_fails_on_metric_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(url: str, *, timeout: float):
        del timeout
        if url.endswith("/api/v1/rules"):
            return {"status": "success", "data": {"groups": []}}
        if "evaluation_failures" in url:
            return {
                "status": "success",
                "data": {"resultType": "vector", "result": [{"value": [0, "3"]}]},
            }
        if "iterations_missed" in url:
            return {
                "status": "success",
                "data": {"resultType": "vector", "result": [{"value": [0, "0"]}]},
            }
        raise AssertionError(url)

    monkeypatch.setattr(mod, "_fetch_json", fake_fetch)
    report = mod.check_rules_health(prometheus_url="http://127.0.0.1:9090")
    assert report.ok is False
    assert report.evaluation_failures_10m == 3.0


def test_main_json_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        mod,
        "check_rules_health",
        lambda **_k: mod.HealthReport(
            ok=False,
            prometheus_url="http://127.0.0.1:9090",
            bioetl_groups=1,
            bioetl_rules=2,
            issues=[
                mod.RuleIssue(
                    group="g",
                    file="bioetl.yml",
                    rule="r",
                    kind="recording",
                    health="err",
                    last_error="boom",
                )
            ],
            evaluation_failures_10m=1.0,
            iterations_missed_10m=0.0,
            query_errors=[],
        ),
    )
    code = mod.main(["--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["issues"][0]["last_error"] == "boom"
