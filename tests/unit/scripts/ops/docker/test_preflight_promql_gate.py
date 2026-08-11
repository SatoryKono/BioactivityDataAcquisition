"""Preflight PromQL syntax gate findings."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ops.runtime.docker import docker_runtime_preflight as preflight

pytestmark = pytest.mark.unit


def test_promql_gate_flags_missing_expr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules = tmp_path / "grafana" / "prometheus-rules"
    rules.mkdir(parents=True)
    (rules / "bad.yml").write_text(
        "groups:\n- name: g\n  rules:\n  - alert: A\n    expr: ''\n",
        encoding="utf-8",
    )
    import scripts.engineering.qa.check_prometheus_rules as real_mod

    monkeypatch.setattr(
        real_mod,
        "list_shipped_rule_files",
        lambda d: sorted(d.glob("*.yml")),
    )
    monkeypatch.setattr(
        real_mod,
        "validate_rule_expr_presence",
        lambda _f: [
            f"{next(rules.glob('*.yml')).as_posix()} alert=A: missing or empty expr"
        ],
    )
    monkeypatch.setattr(
        real_mod,
        "check_rules_syntax",
        lambda *_a, **_k: {
            "ok": True,
            "runner": "local",
            "returncode": 0,
            "command": [],
            "stdout": "",
            "stderr": "",
            "rules_files": [],
        },
    )
    findings = preflight._findings_prometheus_rules_promql(tmp_path)
    assert any(f.code == "MONITORING_RULE_EXPR_MISSING" for f in findings)


def test_promql_gate_tool_missing_is_warning_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules = tmp_path / "grafana" / "prometheus-rules"
    rules.mkdir(parents=True)
    (rules / "ok.yml").write_text(
        "groups:\n- name: g\n  rules:\n  - record: x\n    expr: up\n",
        encoding="utf-8",
    )
    import scripts.engineering.qa.check_prometheus_rules as real_mod

    monkeypatch.setattr(
        real_mod,
        "list_shipped_rule_files",
        lambda d: sorted(d.glob("*.yml")),
    )
    monkeypatch.setattr(real_mod, "validate_rule_expr_presence", lambda _f: [])
    monkeypatch.setattr(
        real_mod,
        "check_rules_syntax",
        lambda *_a, **_k: {
            "ok": False,
            "runner": "none",
            "returncode": 127,
            "command": [],
            "stdout": "",
            "stderr": "promtool missing",
            "rules_files": ["ok.yml"],
        },
    )
    monkeypatch.delenv("BIOETL_REQUIRE_PROMTOOL", raising=False)
    findings = preflight._findings_prometheus_rules_promql(tmp_path)
    assert any(
        f.code == "MONITORING_PROMQL_TOOL_MISSING" and f.severity == "warning"
        for f in findings
    )


def test_promql_gate_syntax_error_is_hard_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules = tmp_path / "grafana" / "prometheus-rules"
    rules.mkdir(parents=True)
    (rules / "ok.yml").write_text(
        "groups:\n- name: g\n  rules:\n  - record: x\n    expr: up\n",
        encoding="utf-8",
    )
    import scripts.engineering.qa.check_prometheus_rules as real_mod

    monkeypatch.setattr(
        real_mod,
        "list_shipped_rule_files",
        lambda d: sorted(d.glob("*.yml")),
    )
    monkeypatch.setattr(real_mod, "validate_rule_expr_presence", lambda _f: [])
    monkeypatch.setattr(
        real_mod,
        "check_rules_syntax",
        lambda *_a, **_k: {
            "ok": False,
            "runner": "local",
            "returncode": 1,
            "command": ["promtool", "check", "rules"],
            "stdout": "",
            "stderr": "parse error",
            "rules_files": ["ok.yml"],
        },
    )
    findings = preflight._findings_prometheus_rules_promql(tmp_path)
    assert any(
        f.code == "MONITORING_PROMQL_SYNTAX" and f.severity == "error" for f in findings
    )
