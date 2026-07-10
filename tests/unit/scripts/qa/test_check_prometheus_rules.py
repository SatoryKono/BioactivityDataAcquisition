from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.engineering.qa import __main__ as qa_router
from scripts.engineering.qa import check_prometheus_rules


pytestmark = pytest.mark.unit


def test_router_exposes_check_prometheus_rules_command() -> None:
    spec = qa_router.COMMAND_SPECS["check-prometheus-rules"]
    assert spec.runner == "module"
    assert spec.target == "scripts.engineering.qa.check_prometheus_rules"


def test_check_prometheus_rules_fails_fast_when_promtool_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_prometheus_rules.shutil, "which", lambda _: None)

    result = check_prometheus_rules.main([])

    assert result == 127
    assert "promtool executable not found" in capsys.readouterr().err


def test_check_prometheus_rules_runs_check_and_test_vectors_locally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        check_prometheus_rules.shutil,
        "which",
        lambda name: "/usr/bin/promtool" if name == "promtool" else None,
    )

    def fake_run(command: list[str], check: bool) -> SimpleNamespace:
        commands.append(command)
        assert check is False
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(check_prometheus_rules.subprocess, "run", fake_run)

    result = check_prometheus_rules.main([])

    assert result == 0
    assert commands == [
        [
            "/usr/bin/promtool",
            "check",
            "rules",
            "grafana/prometheus-rules/bioetl_observability.yml",
        ],
        [
            "/usr/bin/promtool",
            "test",
            "rules",
            "grafana/prometheus-rules/tests/bioetl_observability.test.yml",
        ],
    ]


def test_check_prometheus_rules_docker_runner_uses_promtool_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(
        check_prometheus_rules.shutil,
        "which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )

    def fake_run(command: list[str], check: bool) -> SimpleNamespace:
        commands.append(command)
        assert check is False
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(check_prometheus_rules.subprocess, "run", fake_run)

    result = check_prometheus_rules.main(["--runner", "docker"])

    assert result == 0
    assert commands[0][0:3] == ["/usr/bin/docker", "run", "--rm"]
    assert "--entrypoint" in commands[0]
    assert "promtool" in commands[0]
    assert commands[0][-3:] == [
        "check",
        "rules",
        "grafana/prometheus-rules/bioetl_observability.yml",
    ]
    assert commands[1][-3:] == [
        "test",
        "rules",
        "grafana/prometheus-rules/tests/bioetl_observability.test.yml",
    ]
