from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.engineering.qa import __main__ as qa_router
from scripts.engineering.qa import check_prometheus_rules


pytestmark = pytest.mark.unit


def test_prometheus_toolchain_compatibility_is_pinned_to_supported_series() -> None:
    assert check_prometheus_rules.PROMETHEUS_IMAGE == "prom/prometheus:v3.13.1"
    assert check_prometheus_rules.PROMETHEUS_COMPATIBILITY_SERIES == "3.13.x"
    assert check_prometheus_rules.PUSHGATEWAY_COMPATIBILITY_SERIES == "1.11.x"


def test_rule_test_coverage_is_measured_and_regression_guarded() -> None:
    coverage = check_prometheus_rules.collect_rule_test_coverage(
        rules_files=check_prometheus_rules.DEFAULT_RULES_FILES,
        test_file=check_prometheus_rules.TESTS_FILE,
    )

    assert coverage["alert_definitions"] == 53
    assert coverage["tested_alerts"] >= check_prometheus_rules.MIN_TESTED_ALERTS
    assert coverage["firing_alerts"] >= check_prometheus_rules.MIN_TESTED_ALERTS
    assert coverage["directly_tested_records"] >= (
        check_prometheus_rules.MIN_DIRECTLY_TESTED_RECORDS
    )
    assert len(coverage["control_plane_records"]) == 8
    assert coverage["untested_control_plane_records"] == []
    assert coverage["undefined_fixture_alerts"] == []
    assert check_prometheus_rules.validate_rule_test_coverage(coverage) == []


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
            "grafana/prometheus-rules/bioetl_control_plane_current_status.yml",
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
    assert commands[0][-2:] == [
        "grafana/prometheus-rules/bioetl_observability.yml",
        "grafana/prometheus-rules/bioetl_control_plane_current_status.yml",
    ]
    assert commands[1][-3:] == [
        "test",
        "rules",
        "grafana/prometheus-rules/tests/bioetl_observability.test.yml",
    ]


def test_check_prometheus_rules_rules_file_override_checks_selected_file(
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

    result = check_prometheus_rules.main(
        [
            "--rules-file",
            "grafana/prometheus-rules/bioetl_control_plane_current_status.yml",
        ]
    )

    assert result == 0
    assert commands[0] == [
        "/usr/bin/promtool",
        "check",
        "rules",
        "grafana/prometheus-rules/bioetl_control_plane_current_status.yml",
    ]
