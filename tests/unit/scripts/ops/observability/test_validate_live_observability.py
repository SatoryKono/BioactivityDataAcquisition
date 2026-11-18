# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for live observability diagnostic validators."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
from collections.abc import Callable
from urllib.error import HTTPError

import pytest

from scripts.ops.observability import validate_live_observability as vlo


pytestmark = pytest.mark.unit


def _ready_payload() -> dict[str, object]:
    return {
        "runtime_source_id": "a" * 64,
        "run_manifest_port": True,
        "run_ledger_port": True,
        "workflow_manifest_port": True,
        "checkpoint_port": True,
        "validation_evidence_service": True,
    }


def _fake_dashboard_api(
    monkeypatch: pytest.MonkeyPatch,
    *,
    profile: str = "native",
    missing_uid: str | None = None,
    transform: Callable[[dict[str, Any]], object] | None = None,
) -> None:
    def fetch(url: str, *args: object) -> object:
        if "/api/search" in url:
            return [
                {"uid": uid}
                for uid in sorted(vlo.EXPECTED_BIOETL_DASHBOARD_UIDS)
                if uid != missing_uid
            ] + [{"uid": "unrelated-dashboard"}]
        uid = url.rsplit("/", 1)[-1]
        payload = json.loads(
            (vlo.DASHBOARD_PROFILES[profile] / f"{uid}.json").read_text(
                encoding="utf-8"
            )
        )
        return {"dashboard": transform(payload) if transform else payload}

    monkeypatch.setattr(vlo, "_fetch_json", fetch)


class _FakeResponse:
    def __init__(self, body: bytes, *, code: int = 200) -> None:
        self._body = body
        self.code = code

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_check_prometheus_health_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vlo,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"Prometheus is Healthy.\n"),
    )

    result = vlo.check_prometheus_health("http://prometheus:9090", 1.0)

    assert result.status == "pass"
    assert result.details is not None
    assert result.details["url"] == "http://prometheus:9090/-/healthy"
    assert "Healthy" in result.details["response"]


def test_check_prometheus_health_unexpected_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"NotReady"),
    )

    result = vlo.check_prometheus_health("http://prometheus:9090", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["response"] == "NotReady"


def test_check_prometheus_health_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            "http://prometheus:9090/-/healthy", 503, "down", hdrs=None, fp=None
        )

    monkeypatch.setattr(vlo, "urlopen", _raise)

    result = vlo.check_prometheus_health("http://prometheus:9090", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["url"] == "http://prometheus:9090/-/healthy"
    assert "error" in result.details


def test_check_prometheus_targets_malformed_and_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = iter(
        [
            {"status": "error", "error": "boom"},
            {
                "status": "success",
                "data": {
                    "activeTargets": [
                        {
                            "health": "up",
                            "labels": {"job": "bioetl", "instance": "a"},
                        },
                        {
                            "health": "down",
                            "labels": {"job": "node", "instance": "b"},
                            "lastError": "connection refused",
                        },
                    ]
                },
            },
        ]
    )

    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: next(payloads),
    )

    bad = vlo.check_prometheus_targets("http://prometheus:9090", 1.0)
    assert bad.status == "fail"
    assert bad.details is not None
    assert bad.details["api_response"]["status"] == "error"

    partial = vlo.check_prometheus_targets("http://prometheus:9090", 1.0)
    assert partial.status == "fail"
    assert partial.details is not None
    assert partial.details["up_targets"] == 1
    assert partial.details["down_targets"] == 1
    assert partial.details["down_targets_details"][0]["last_error"] == (
        "connection refused"
    )


def test_load_repo_environment_preserves_process_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, bool]] = []

    def fake_load_dotenv(*, dotenv_path: object, override: bool) -> None:
        calls.append((dotenv_path, override))
        monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-repo-env")

    for name in (
        "GF_SECURITY_ADMIN_PASSWORD",
        "GRAFANA_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(vlo, "load_dotenv", fake_load_dotenv)

    vlo._load_repo_environment()

    assert calls == [(vlo.REPO_ENV_PATH, False)]
    assert vlo.resolve_grafana_password() == "from-repo-env"


def test_resolve_grafana_password_prefers_grafana_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAFANA_PASSWORD", "from-grafana")
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-gf")
    assert vlo.resolve_grafana_password() == "from-grafana"


def test_resolve_grafana_password_falls_back_to_gf_security(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GRAFANA_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "from-gf")
    assert vlo.resolve_grafana_password() == "from-gf"


def test_resolve_grafana_password_has_no_committed_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GRAFANA_PASSWORD", raising=False)
    monkeypatch.delenv("GF_SECURITY_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("GRAFANA_ADMIN_PASSWORD", raising=False)
    assert vlo.resolve_grafana_password() == ""
    assert vlo.DEFAULT_GRAFANA_PASSWORD == ""


def test_check_grafana_datasources_fails_without_password() -> None:
    result = vlo.check_grafana_datasources("http://grafana:3000", "admin", "", 1.0)
    assert result.status == "fail"
    assert result.details is not None
    assert result.details["error"] == "missing_grafana_password"


def test_check_grafana_datasources_requires_ops_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: [
            {"name": "Prometheus", "uid": "prometheus"},
        ],
    )
    result = vlo.check_grafana_datasources(
        "http://grafana:3000", "admin", "secret", 1.0
    )
    assert result.status == "partial"
    assert result.details is not None
    assert result.details["has_prometheus"] is True
    assert result.details["has_ops_http"] is False


def test_check_grafana_datasources_passes_with_prometheus_and_ops_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fetch(url: str, *args: object) -> object:
        if "/proxy/uid/" in url:
            return _ready_payload()
        return [
            {"name": "Prometheus", "uid": "prometheus"},
            {
                "name": "BioETL Ops HTTP",
                "uid": "bioetl-ops-http",
                "type": "yesoreyeram-infinity-datasource",
            },
        ]

    monkeypatch.setattr(vlo, "_fetch_json", fetch)
    result = vlo.check_grafana_datasources(
        "http://grafana:3000", "admin", "secret", 1.0
    )
    assert result.status == "pass"
    assert result.details is not None
    assert result.details["has_ops_http"] is True
    assert result.details["ops_http_ready"] is True


@pytest.mark.parametrize(
    ("ops_name", "ops_uid"),
    [
        (vlo.EXPECTED_OPS_HTTP_DATASOURCE_NAME, "stale-ops-http"),
        ("Stale Ops HTTP", vlo.EXPECTED_OPS_HTTP_DATASOURCE_UID),
    ],
)
def test_check_grafana_datasources_requires_matching_ops_identity(
    monkeypatch: pytest.MonkeyPatch,
    ops_name: str,
    ops_uid: str,
) -> None:
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args, **kwargs: [
            {"name": "Prometheus", "uid": "prometheus"},
            {
                "name": ops_name,
                "uid": ops_uid,
                "type": "yesoreyeram-infinity-datasource",
            },
        ],
    )

    result = vlo.check_grafana_datasources(
        "http://grafana:3000", "admin", "secret", 1.0
    )

    assert result.status == "partial"
    assert result.details is not None
    assert result.details["has_ops_http"] is False


def test_check_grafana_datasources_rejects_wrong_ops_plugin_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args: [
            {"name": "Prometheus", "uid": "prometheus"},
            {"name": "BioETL Ops HTTP", "uid": "bioetl-ops-http", "type": "prometheus"},
        ],
    )
    result = vlo.check_grafana_datasources("http://grafana:3000", "admin", "secret", 1)
    assert result.status != "pass"
    assert result.details is not None
    assert result.details["has_ops_http"] is False


def test_check_grafana_datasources_http_auth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise HTTPError(
            "http://grafana:3000/api/datasources",
            401,
            "unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(vlo, "_fetch_json", _raise)

    result = vlo.check_grafana_datasources("http://grafana:3000", "admin", "bad", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["code"] == 401


def test_check_grafana_dashboards_fails_without_password_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_fetch(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"unexpected Grafana request: {args}, {kwargs}")

    monkeypatch.setattr(vlo, "_fetch_json", fail_fetch)

    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "   ", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["error"] == "missing_grafana_password"


def test_check_grafana_dashboards_accepts_shipped_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_dashboard_api(monkeypatch)

    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1.0)

    assert result.status == "pass"
    assert result.details is not None
    assert result.details["expected_bioetl_dashboards"] == 5
    assert result.details["missing_bioetl_dashboard_uids"] == []
    assert "5 shipped UIDs expected" in result.message


def test_expected_dashboard_uids_match_shipped_models() -> None:
    dashboard_root = Path(vlo.__file__).resolve().parents[3] / "grafana/dashboards"
    shipped_uids = {
        json.loads(path.read_text(encoding="utf-8"))["uid"]
        for path in dashboard_root.glob("*.json")
    }
    assert vlo.EXPECTED_BIOETL_DASHBOARD_UIDS == shipped_uids


def test_check_grafana_dashboards_reports_missing_shipped_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_uid = "bioetl-run-explorer-v1"
    _fake_dashboard_api(monkeypatch, missing_uid=missing_uid)

    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1.0)

    assert result.status == "fail"
    assert result.details is not None
    assert result.details["missing_bioetl_dashboard_uids"] == [missing_uid]


def test_validation_result_serializes_diagnostic_fields() -> None:
    result = vlo.ValidationResult(
        check_name="prometheus_health",
        status="fail",
        message="down",
        details={"url": "http://x/-/healthy", "error": "timeout"},
    )
    report = vlo.ValidationReport(
        prometheus_url="http://prom",
        grafana_url="http://grafana",
        timestamp=result.timestamp,
        results=[result],
        summary={"fail": 1},
    )
    payload = json.loads(json.dumps(vlo.asdict(report)))

    assert payload["results"][0]["details"]["url"] == "http://x/-/healthy"
    assert payload["results"][0]["details"]["error"] == "timeout"
    assert payload["summary"] == {"fail": 1}


def _targets() -> list[dict[str, Any]]:
    import yaml

    config = yaml.safe_load(
        (vlo.REPO_ROOT / "grafana/prometheus.yml").read_text(encoding="utf-8")
    )
    return [
        {"health": "up", "labels": {"job": item["job_name"]}}
        for item in config["scrape_configs"]
    ]


@pytest.mark.parametrize("case", ["empty", "missing", "unknown", "down", "all_up"])
def test_targets_require_configured_jobs_and_up_health(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    targets = _targets()
    if case == "empty":
        targets = []
    elif case == "missing":
        targets.pop()
    elif case in {"unknown", "down"}:
        targets[0]["health"] = case
    monkeypatch.setattr(
        vlo,
        "_fetch_json",
        lambda *args: {"status": "success", "data": {"activeTargets": targets}},
    )
    result = vlo.check_prometheus_targets("http://prometheus:9090", 1)
    assert (result.status == "pass") is (case == "all_up")
    assert result.details is not None
    if case in {"empty", "missing"}:
        assert result.details["missing_jobs"]
    elif case in {"unknown", "down"}:
        assert result.details["down_targets_details"][0]["health"] == case


@pytest.mark.parametrize("count", [None, "0", "NaN", "+Inf", "17"])
def test_metrics_require_current_samples_not_retained_names(
    monkeypatch: pytest.MonkeyPatch, count: str | None
) -> None:
    def fetch(url: str, *args: object) -> object:
        if "/label/" in url:
            return {"status": "success", "data": ["bioetl_old_total"]}
        assert "count%28" in url
        return {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"value": [100, count]}] if count is not None else [],
            },
        }

    monkeypatch.setattr(vlo, "_fetch_json", fetch)
    result = vlo.check_prometheus_metrics("http://prometheus:9090", 1)
    assert (result.status == "pass") is (count == "17")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "error"},
        {"status": "success", "data": {"resultType": "scalar", "result": [100, "3"]}},
    ],
)
def test_metrics_reject_malformed_or_failed_current_query(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> None:
    responses = iter(
        [{"status": "success", "data": ["prometheus_build_info"]}, payload]
    )
    monkeypatch.setattr(vlo, "_fetch_json", lambda *args: next(responses))
    assert vlo.check_prometheus_metrics("http://prometheus:9090", 1).status == "fail"


@pytest.mark.parametrize("case", ["healthy", "empty", "drift", "skipped", "failed"])
def test_rules_require_nonempty_healthy_rules_and_sentinel_parity(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from scripts.ops.observability import check_prometheus_rules_health as rules

    report = rules.HealthReport(
        ok=True,
        prometheus_url="http://prometheus:9090",
        bioetl_groups=1,
        bioetl_rules=6,
        issues=[],
        evaluation_failures_10m=0,
        iterations_missed_10m=0,
        query_errors=[],
        expr_parity_checked=True,
        tracked_rules_sha256="source-digest",
    )
    if case == "empty":
        report = replace(report, bioetl_groups=0, bioetl_rules=0)
    elif case == "drift":
        report = replace(report, ok=False, expr_parity_issues=["expression changed"])
    elif case == "skipped":
        report = replace(report, expr_parity_checked=False, expr_parity_skipped=True)
    elif case == "failed":
        report = replace(report, ok=False, query_errors=["unreachable"])

    def check(**kwargs: Any) -> rules.HealthReport:
        assert kwargs["expr_parity"] is True
        assert kwargs["skip_if_unreachable"] is False
        return report

    monkeypatch.setattr(rules, "check_rules_health", check)
    result = vlo.check_prometheus_rules_health("http://prometheus:9090", 1)
    assert (result.status == "pass") is (case == "healthy")
    assert result.details is not None
    assert result.details["tracked_rules_sha256"] == "source-digest"
    assert result.details["expr_parity_issues"] == report.expr_parity_issues


@pytest.mark.parametrize("profile", ["native", "adaptive"])
def test_dashboard_models_match_explicit_profile(
    monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    _fake_dashboard_api(monkeypatch, profile=profile)
    result = vlo.check_grafana_dashboards(
        "http://grafana:3000", "admin", "secret", 1, dashboard_profile=profile
    )
    assert result.status == "pass"
    assert result.details is not None
    assert result.details["dashboard_profile"] == profile


def test_dashboard_profile_is_never_inferred_from_uids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_dashboard_api(monkeypatch, profile="adaptive")
    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1)
    assert result.status == "fail"
    assert result.details is not None
    assert result.details["mismatched_dashboard_uids"]


def test_dashboard_fallback_notices_with_shipped_uids_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_dashboard_api(
        monkeypatch,
        transform=lambda model: {
            "uid": model["uid"],
            "panels": [{"title": "Ops HTTP not provisioned", "type": "text"}],
        },
    )
    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1)
    assert result.status == "fail"
    assert result.details is not None
    assert len(result.details["mismatched_dashboard_uids"]) == 5


def test_dashboard_database_versions_do_not_cause_model_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def alter_volatile(model: dict[str, Any]) -> dict[str, Any]:
        model.update(id=9999, version=9999)
        model["panels"][0]["pluginVersion"] = "new-server-version"
        return model

    _fake_dashboard_api(monkeypatch, transform=alter_volatile)
    assert (
        vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1).status
        == "pass"
    )


@pytest.mark.parametrize(
    "field", ["targets", "transformations", "templating", "links", "options"]
)
def test_dashboard_behavior_drift_fails(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    def alter_behavior(model: dict[str, Any]) -> dict[str, Any]:
        model = deepcopy(model)
        if field in {"templating", "links"}:
            model[field] = {"changed": True}
        else:
            model["panels"][0][field] = [{"changed": True}]
        return model

    _fake_dashboard_api(monkeypatch, transform=alter_behavior)
    assert (
        vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1).status
        == "fail"
    )


@pytest.mark.parametrize("model", [None, {}, {"uid": "wrong", "panels": []}])
def test_dashboard_malformed_models_fail(
    monkeypatch: pytest.MonkeyPatch, model: object
) -> None:
    _fake_dashboard_api(monkeypatch, transform=lambda _: model)
    assert (
        vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1).status
        == "fail"
    )


@pytest.mark.parametrize(
    "ready",
    [
        {},
        {"runtime_source_id": "unmanaged"},
        {**_ready_payload(), "run_ledger_port": False},
    ],
)
def test_datasource_configuration_alone_does_not_prove_ops_ready(
    monkeypatch: pytest.MonkeyPatch, ready: dict[str, object]
) -> None:
    def fetch(url: str, *args: object) -> object:
        if "/proxy/uid/" in url:
            return ready
        return [
            {"name": "Prometheus", "uid": "prometheus"},
            {
                "name": "BioETL Ops HTTP",
                "uid": "bioetl-ops-http",
                "type": "yesoreyeram-infinity-datasource",
            },
        ]

    monkeypatch.setattr(vlo, "_fetch_json", fetch)
    assert (
        vlo.check_grafana_datasources(
            "http://grafana:3000", "admin", "secret", 1
        ).status
        == "fail"
    )


def test_dashboard_model_http_error_is_not_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fetch(url: str, *args: object) -> object:
        if "/api/search" in url:
            return [{"uid": uid} for uid in vlo.EXPECTED_BIOETL_DASHBOARD_UIDS]
        raise HTTPError(url, 404, "not found", hdrs=None, fp=None)

    monkeypatch.setattr(vlo, "_fetch_json", fetch)
    result = vlo.check_grafana_dashboards("http://grafana:3000", "admin", "secret", 1)
    assert result.status == "fail"
    assert result.details is not None
    assert result.details["code"] == 404


@pytest.mark.parametrize("profile", ["native", "adaptive"])
def test_run_validation_forwards_explicit_profile_and_preserves_summary(
    monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    def passed(*args: object, **kwargs: object) -> vlo.ValidationResult:
        return vlo.ValidationResult("stub", "pass", "passed")

    for name in (
        "check_prometheus_health",
        "check_prometheus_targets",
        "check_prometheus_metrics",
        "check_prometheus_query",
        "check_prometheus_rules_health",
        "check_grafana_health",
        "check_grafana_datasources",
    ):
        monkeypatch.setattr(vlo, name, passed)

    def dashboard(*args: object, **kwargs: object) -> vlo.ValidationResult:
        assert kwargs["dashboard_profile"] == profile
        return passed()

    monkeypatch.setattr(vlo, "check_grafana_dashboards", dashboard)
    report = vlo.run_validation(
        "http://prometheus:9090",
        "http://grafana:3000",
        "admin",
        "secret",
        1,
        dashboard_profile=profile,
    )
    assert report.summary == {
        "total_checks": 8,
        "passed": 8,
        "failed": 0,
        "partial": 0,
        "success_rate": "100.0%",
    }


@pytest.mark.parametrize("profile_args", [[], ["--dashboard-profile", "adaptive"]])
def test_cli_dashboard_profile_reaches_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile_args: list[str]
) -> None:
    monkeypatch.setattr(vlo, "_load_repo_environment", lambda: None)
    monkeypatch.setattr(
        "sys.argv",
        ["validate_live_observability", "--output-dir", str(tmp_path), *profile_args],
    )

    def validate(**kwargs: Any) -> vlo.ValidationReport:
        assert kwargs["dashboard_profile"] == ("adaptive" if profile_args else "native")
        return vlo.ValidationReport(
            "http://prometheus:9090",
            "http://grafana:3000",
            "test",
            [],
            {"failed": 0, "partial": 0},
        )

    monkeypatch.setattr(vlo, "run_validation", validate)
    with pytest.raises(SystemExit) as exited:
        vlo.main()
    assert exited.value.code == 0
    assert len(list(tmp_path.glob("validation-report-*.json"))) == 1


def test_direct_script_help_bootstraps_repository_imports(tmp_path: Path) -> None:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, str(Path(vlo.__file__).resolve()), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--prometheus-url" in result.stdout
