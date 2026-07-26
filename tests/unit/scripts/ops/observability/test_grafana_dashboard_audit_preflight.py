"""Unit contracts for Grafana dashboard audit preflight readiness."""

from __future__ import annotations

import json

import pytest

from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight,
)

pytestmark = pytest.mark.unit


def test_forbidden_default_password_is_empty() -> None:
    assert preflight.DEFAULT_GRAFANA_PASSWORD == ""


def test_resolve_grafana_password_prefers_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GF_SECURITY_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_ADMIN_PASSWORD", raising=False)
    assert preflight._resolve_grafana_password() == ""

    monkeypatch.setenv("GRAFANA_PASSWORD", "from-grafana-password")
    assert preflight._resolve_grafana_password() == "from-grafana-password"

    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-gf-security")
    assert preflight._resolve_grafana_password() == "from-gf-security"


def test_main_fails_closed_without_credentials(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GF_SECURITY_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_SERVICE_ACCOUNT_TOKEN", raising=False)

    code = preflight.main(
        [
            "--json",
            "--skip-screenshot-check",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == preflight.EXIT_CREDENTIALS
    assert payload["checks"][0]["name"] == "credentials"
    assert payload["checks"][0]["status"] == "error"


def test_exit_code_mapping_is_distinct_per_failure_class() -> None:
    assert (
        preflight._exit_code_for_checks(
            [preflight.PreflightCheck("grafana", "error", "down")]
        )
        == preflight.EXIT_GRAFANA_HEALTH
    )
    assert (
        preflight._exit_code_for_checks(
            [preflight.PreflightCheck("grafana-render-auth", "error", "401")]
        )
        == preflight.EXIT_RENDER_AUTH
    )
    assert (
        preflight._exit_code_for_checks(
            [preflight.PreflightCheck("playwright-runtime", "error", "browser")]
        )
        == preflight.EXIT_PLAYWRIGHT
    )
    assert (
        preflight._exit_code_for_checks(
            [preflight.PreflightCheck("bioetl-prometheus-target", "error", "down")]
        )
        == preflight.EXIT_BIOETL_TARGET
    )


def test_bioetl_prometheus_target_check_requires_up_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _ok_targets(_url: str, _timeout: float) -> dict[str, object]:
        return {
            "data": {
                "activeTargets": [
                    {
                        "health": "down",
                        "scrapeUrl": "http://bioetl:8000/metrics",
                        "labels": {"job": "bioetl", "instance": "bioetl:8000"},
                        "lastError": "connection refused",
                    }
                ]
            }
        }

    monkeypatch.setattr(preflight, "_fetch_json", _ok_targets)
    check = preflight._check_bioetl_prometheus_target(
        prometheus_base_url="http://localhost:9090",
        timeout_seconds=1.0,
    )
    assert check.name == "bioetl-prometheus-target"
    assert check.status == "error"
    assert "not UP" in check.detail


def test_bioetl_prometheus_target_check_passes_when_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _ok_targets(_url: str, _timeout: float) -> dict[str, object]:
        return {
            "data": {
                "activeTargets": [
                    {
                        "health": "up",
                        "scrapeUrl": "http://bioetl:8000/metrics",
                        "labels": {"job": "bioetl", "instance": "bioetl:8000"},
                        "lastError": "",
                    }
                ]
            }
        }

    monkeypatch.setattr(preflight, "_fetch_json", _ok_targets)
    check = preflight._check_bioetl_prometheus_target(
        prometheus_base_url="http://localhost:9090",
        timeout_seconds=1.0,
    )
    assert check.status == "ok"
