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
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa import __main__ as qa_router
from scripts.engineering.qa import check_prometheus_rules
import yaml


pytestmark = pytest.mark.unit


def test_prometheus_toolchain_compatibility_is_pinned_to_supported_series() -> None:
    assert check_prometheus_rules.PROMETHEUS_IMAGE == (
        "prom/prometheus:v3.13.1@sha256:"
        "3c42b892cf723fa54d2f262c37a0e1f80aa8c8ddb1da7b9b0df9455a35a7f893"
    )
    assert check_prometheus_rules.PROMETHEUS_COMPATIBILITY_SERIES == "3.13.x"
    assert check_prometheus_rules.PUSHGATEWAY_COMPATIBILITY_SERIES == "1.11.x"


def test_rule_test_coverage_is_measured_and_regression_guarded() -> None:
    coverage = check_prometheus_rules.collect_rule_test_coverage(
        rules_files=check_prometheus_rules.DEFAULT_RULES_FILES,
        test_file=check_prometheus_rules.TESTS_FILE,
    )

    assert (
        coverage["alert_definitions"]
        == check_prometheus_rules.EXPECTED_ALERT_DEFINITIONS
    )
    assert (
        coverage["record_definitions"]
        == check_prometheus_rules.EXPECTED_RECORD_DEFINITIONS
    )
    assert coverage["tested_alerts"] >= check_prometheus_rules.MIN_TESTED_ALERTS
    assert coverage["firing_alerts"] >= check_prometheus_rules.MIN_TESTED_ALERTS
    assert coverage["directly_tested_records"] >= (
        check_prometheus_rules.MIN_DIRECTLY_TESTED_RECORDS
    )
    assert len(coverage["control_plane_records"]) == 8
    assert coverage["untested_control_plane_records"] == []
    assert coverage["undefined_fixture_alerts"] == []
    assert check_prometheus_rules.validate_rule_test_coverage(coverage) == []


def test_rule_test_coverage_rejects_vacuous_expected_results(
    tmp_path: Path,
) -> None:
    fixture = yaml.safe_load(
        check_prometheus_rules.TESTS_FILE.read_text(encoding="utf-8")
    )
    for test_case in fixture["tests"]:
        for assertion in test_case.get("alert_rule_test", []):
            assertion["exp_alerts"] = []
        for assertion in test_case.get("promql_expr_test", []):
            assertion["exp_samples"] = []

    fixture_path = tmp_path / "vacuous-prometheus-rules.test.yml"
    fixture_path.write_text(
        yaml.safe_dump(fixture, sort_keys=False),
        encoding="utf-8",
    )
    coverage = check_prometheus_rules.collect_rule_test_coverage(
        rules_files=check_prometheus_rules.DEFAULT_RULES_FILES,
        test_file=fixture_path,
    )

    assert coverage["tested_alerts"] == check_prometheus_rules.MIN_TESTED_ALERTS
    assert coverage["firing_alerts"] == 0
    assert coverage["directly_tested_records"] == 0
    violations = check_prometheus_rules.validate_rule_test_coverage(coverage)
    assert "firing alert fixtures regressed below 36: 0" in violations
    assert "directly tested records regressed below 28: 0" in violations


def test_rule_test_coverage_rejects_new_untested_record(
    tmp_path: Path,
) -> None:
    rules = yaml.safe_load(
        check_prometheus_rules.OBSERVABILITY_RULES_FILE.read_text(encoding="utf-8")
    )
    record_name = "bioetl_uncovered_regression_probe"
    rules["groups"][0]["rules"].append({"record": record_name, "expr": "vector(1)"})
    rules_path = tmp_path / "bioetl_observability_with_uncovered_record.yml"
    rules_path.write_text(
        yaml.safe_dump(rules, sort_keys=False),
        encoding="utf-8",
    )

    coverage = check_prometheus_rules.collect_rule_test_coverage(
        rules_files=(
            rules_path,
            check_prometheus_rules.CONTROL_PLANE_RULES_FILE,
        ),
        test_file=check_prometheus_rules.TESTS_FILE,
    )

    expected = check_prometheus_rules.EXPECTED_RECORD_DEFINITIONS
    assert coverage["record_definitions"] == expected + 1
    assert record_name in coverage["untested_records"]
    assert (
        f"record definitions changed from baseline {expected}: {expected + 1}"
        in check_prometheus_rules.validate_rule_test_coverage(coverage)
    )


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

    def fake_run(
        command: list[str], check: bool = False, **kwargs: object
    ) -> SimpleNamespace:
        del kwargs
        commands.append(command)
        assert check is False
        return SimpleNamespace(returncode=0, stdout="", stderr="")

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

    def fake_run(
        command: list[str], check: bool = False, **kwargs: object
    ) -> SimpleNamespace:
        del kwargs
        commands.append(command)
        assert check is False
        return SimpleNamespace(returncode=0, stdout="", stderr="")

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

    def fake_run(
        command: list[str], check: bool = False, **kwargs: object
    ) -> SimpleNamespace:
        del kwargs
        commands.append(command)
        assert check is False
        return SimpleNamespace(returncode=0, stdout="", stderr="")

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
