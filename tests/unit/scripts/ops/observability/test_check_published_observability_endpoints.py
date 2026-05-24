from __future__ import annotations

from typing import Any

from tests.helpers import assert_cli_succeeded, run_python_cli

from scripts.ops.observability import check_published_observability_endpoints as subject


def test_classify_diagnosis_flags_published_port_gap() -> None:
    diagnosis = subject._classify_diagnosis(
        subject.ProbeResult(ok=False, detail="connection reset by peer"),
        subject.ProbeResult(ok=True, status_code=0, detail="healthy"),
    )
    assert diagnosis == "published_port_unreachable_but_container_healthy"


def test_run_checks_collects_published_and_container_status() -> None:
    endpoint = subject.EndpointSpec(
        name="grafana",
        published_url="http://127.0.0.1:3000/api/health",
        container_name="bioetl-grafana",
        container_internal_url="http://127.0.0.1:3000/api/health",
        description="Grafana published API health",
    )

    def fake_http_probe(url: str, timeout_seconds: float) -> subject.ProbeResult:
        assert url == endpoint.published_url
        assert timeout_seconds == 1.5
        return subject.ProbeResult(ok=False, detail="connection reset by peer")

    def fake_container_probe(
        container_name: str,
        url: str,
        timeout_seconds: float,
    ) -> subject.ProbeResult:
        assert container_name == endpoint.container_name
        assert url == endpoint.container_internal_url
        assert timeout_seconds == 1.5
        return subject.ProbeResult(ok=True, status_code=0, detail='{"database":"ok"}')

    checks = subject.run_checks(
        endpoints=(endpoint,),
        timeout_seconds=1.5,
        http_probe=fake_http_probe,
        container_probe=fake_container_probe,
    )

    assert len(checks) == 1
    check = checks[0]
    assert check.diagnosis == "published_port_unreachable_but_container_healthy"
    assert not check.published_probe.ok
    assert check.container_probe is not None
    assert check.container_probe.ok


def test_main_json_renders_and_returns_nonzero_when_published_probe_fails(
    monkeypatch: Any, capsys: Any
) -> None:
    checks = [
        subject.EndpointCheck(
            name="grafana",
            published_url="http://127.0.0.1:3000/api/health",
            container_name="bioetl-grafana",
            container_internal_url="http://127.0.0.1:3000/api/health",
            description="Grafana published API health",
            published_probe=subject.ProbeResult(
                ok=False,
                detail="connection reset by peer",
            ),
            container_probe=subject.ProbeResult(
                ok=True,
                status_code=0,
                detail='{"database":"ok"}',
            ),
            diagnosis="published_port_unreachable_but_container_healthy",
        )
    ]

    monkeypatch.setattr(subject, "run_checks", lambda **_: checks)

    exit_code = subject.main(["--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "published_port_unreachable_but_container_healthy" in captured.out


def test_main_returns_zero_when_published_probe_is_healthy(
    monkeypatch: Any, capsys: Any
) -> None:
    checks = [
        subject.EndpointCheck(
            name="prometheus",
            published_url="http://127.0.0.1:9090/-/healthy",
            container_name="bioetl-prometheus",
            container_internal_url="http://127.0.0.1:9090/-/healthy",
            description="Prometheus published API health",
            published_probe=subject.ProbeResult(ok=True, status_code=200, detail="ok"),
            container_probe=None,
            diagnosis="published_healthy",
        )
    ]
    monkeypatch.setattr(subject, "run_checks", lambda **_: checks)

    exit_code = subject.main(["--skip-container-check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "prometheus: diagnosis=published_healthy published=ok container=skipped" in captured.out


def test_scripts_ops_router_exposes_check_observability_ports_help_smoke() -> None:
    result = run_python_cli(
        "-m",
        "scripts.ops",
        "check-observability-ports",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Check host-published Grafana/Prometheus-style endpoints" in result.stdout
    )
