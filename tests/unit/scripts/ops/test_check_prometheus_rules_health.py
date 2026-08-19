"""Unit tests for partial Prometheus rule failure detection."""

from __future__ import annotations

from pathlib import Path

import json
from urllib.parse import parse_qs, urlsplit

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


def test_check_rules_health_uses_promql_safe_rule_group_regex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries: list[str] = []

    def fake_fetch(url: str, *, timeout: float) -> dict[str, object]:
        del timeout
        if url.endswith("/api/v1/rules"):
            return {"status": "success", "data": {"groups": []}}

        query = parse_qs(urlsplit(url).query)["query"][0]
        queries.append(query)
        return {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        }

    monkeypatch.setattr(mod, "_fetch_json", fake_fetch)

    report = mod.check_rules_health(prometheus_url="http://127.0.0.1:9090")

    assert report.ok is True
    assert len(queries) == 2
    assert all("[.]yml" in query for query in queries)
    assert all(r"\.yml" not in query for query in queries)


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


def test_compare_expr_parity_accepts_matching_live_rules() -> None:
    tracked = {
        "bioetl_provider_current_status": (
            "(x) or (bioetl_provider_health_check_provider_universe_15m * 0 + 3)",
        ),
        "bioetl_provider_current_status_info": ("info",),
        "bioetl_control_plane_telemetry_missing_5m": ("missing",),
        "bioetl_control_plane_current_status_trusted": ("trusted",),
        "bioetl_dq_current_status": ("dq",),
        "bioetl_l0_status": ("l0",),
    }
    issues = mod.compare_expr_parity(tracked=tracked, live=tracked)
    assert issues == []


def test_compare_expr_parity_flags_nan_division_fallback() -> None:
    tracked = {
        "bioetl_provider_current_status": ("universe * 0 + 3",),
        "bioetl_provider_current_status_info": ("info",),
        "bioetl_control_plane_telemetry_missing_5m": ("missing",),
        "bioetl_control_plane_current_status_trusted": ("trusted",),
        "bioetl_dq_current_status": ("dq",),
        "bioetl_l0_status": ("l0",),
    }
    live = dict(tracked)
    live["bioetl_provider_current_status"] = ("(x * 0) / (x * 0)",)
    issues = mod.compare_expr_parity(tracked=tracked, live=live)
    assert any("division" in item for item in issues)
    assert any("drift" in item for item in issues)


def test_check_rules_health_expr_parity_skips_when_prometheus_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(url: str, *, timeout: float):
        del url, timeout
        raise OSError("prometheus down")

    monkeypatch.setattr(mod, "_fetch_json", fake_fetch)
    report = mod.check_rules_health(
        prometheus_url="http://127.0.0.1:9090",
        expr_parity=True,
        skip_if_unreachable=True,
    )
    assert report.ok is True
    assert report.expr_parity_skipped is True
    assert report.skipped_unreachable is True


def test_check_rules_health_expr_parity_detects_live_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    yaml_text = """groups:
  - name: bioetl_provider
    rules:
      - record: bioetl_provider_current_status
        expr: universe * 0 + 3
      - record: bioetl_provider_current_status_info
        expr: info
      - record: bioetl_control_plane_telemetry_missing_5m
        expr: missing
      - record: bioetl_control_plane_current_status_trusted
        expr: trusted
      - record: bioetl_dq_current_status
        expr: dq
      - record: bioetl_l0_status
        expr: l0
"""
    (rules_dir / "bioetl.yml").write_text(yaml_text, encoding="utf-8")

    def fake_fetch(url: str, *, timeout: float):
        del timeout
        if url.endswith("/api/v1/rules"):
            return {
                "status": "success",
                "data": {
                    "groups": [
                        {
                            "file": "bioetl.yml",
                            "name": "bioetl_provider",
                            "rules": [
                                {
                                    "name": "bioetl_provider_current_status",
                                    "type": "recording",
                                    "health": "ok",
                                    "lastError": "",
                                    "query": "(x * 0) / (x * 0)",
                                }
                            ],
                        }
                    ]
                },
            }
        return {
            "status": "success",
            "data": {"resultType": "vector", "result": [{"value": [0, "0"]}]},
        }

    monkeypatch.setattr(mod, "_fetch_json", fake_fetch)
    report = mod.check_rules_health(
        prometheus_url="http://127.0.0.1:9090",
        expr_parity=True,
        rules_dir=rules_dir,
    )
    assert report.ok is False
    assert report.expr_parity_checked is True
    assert report.expr_parity_issues


def test_load_tracked_recording_exprs_includes_provider_unknown_fallback() -> None:
    tracked = mod.load_tracked_recording_exprs(mod.DEFAULT_RULES_DIR)
    exprs = " ".join(tracked["bioetl_provider_current_status"])
    assert "* 0 + 3" in exprs
    assert "/" not in exprs


def test_tracked_rules_bundle_sha256_is_stable() -> None:
    first = mod.tracked_rules_bundle_sha256(mod.DEFAULT_RULES_DIR)
    second = mod.tracked_rules_bundle_sha256(mod.DEFAULT_RULES_DIR)
    assert first == second
    assert len(first) == 64

