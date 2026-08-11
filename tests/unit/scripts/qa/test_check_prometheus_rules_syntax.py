"""Unit tests for built-in PromQL rule syntax helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.engineering.qa import check_prometheus_rules as cpr

pytestmark = pytest.mark.unit


def test_list_shipped_rule_files_excludes_tests_dir(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_text("groups: []\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "t.yml").write_text("tests: []\n", encoding="utf-8")
    files = cpr.list_shipped_rule_files(tmp_path)
    assert [p.name for p in files] == ["a.yml"]


def test_validate_rule_expr_presence_flags_empty_expr(tmp_path: Path) -> None:
    path = tmp_path / "bad.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "groups": [
                    {
                        "name": "g",
                        "rules": [
                            {"alert": "X", "expr": ""},
                            {"record": "y", "expr": "up"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    violations = cpr.validate_rule_expr_presence([path])
    assert len(violations) == 1
    assert "alert=X" in violations[0]
    assert "empty expr" in violations[0]


def test_validate_rule_expr_presence_ok_for_shipped_rules() -> None:
    files = cpr.list_shipped_rule_files(Path("grafana/prometheus-rules"))
    assert files
    assert cpr.validate_rule_expr_presence(files) == []


def test_check_rules_syntax_local_missing_promtool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rule = tmp_path / "r.yml"
    rule.write_text(
        "groups:\n- name: g\n  rules:\n  - record: x\n    expr: up\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cpr.shutil, "which", lambda name: None)
    result = cpr.check_rules_syntax([rule], root=tmp_path, prefer="local")
    assert result["ok"] is False
    assert result["returncode"] == 127
    assert "promtool" in result["stderr"]


def test_check_rules_syntax_local_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rule = tmp_path / "r.yml"
    rule.write_text(
        "groups:\n- name: g\n  rules:\n  - record: x\n    expr: up\n",
        encoding="utf-8",
    )

    def fake_which(name: str) -> str | None:
        return "/usr/bin/promtool" if name == "promtool" else None

    def fake_run(command, **kwargs):
        del kwargs
        assert command[0] == "/usr/bin/promtool"
        assert command[1:3] == ["check", "rules"]
        return SimpleNamespace(returncode=0, stdout="SUCCESS\n", stderr="")

    monkeypatch.setattr(cpr.shutil, "which", fake_which)
    monkeypatch.setattr(cpr.subprocess, "run", fake_run)
    result = cpr.check_rules_syntax([rule], root=tmp_path, prefer="local")
    assert result["ok"] is True
    assert result["runner"] == "local"


def test_recording_identity_uniqueness_flags_same_labels(tmp_path: Path) -> None:
    path = tmp_path / "dup.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "groups": [
                    {
                        "name": "g",
                        "rules": [
                            {
                                "record": "bioetl_x",
                                "labels": {"reason": "a"},
                                "expr": "vector(1)",
                            },
                            {
                                "record": "bioetl_x",
                                "labels": {"reason": "a"},
                                "expr": "vector(2)",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    violations = cpr.validate_recording_rule_identity_uniqueness([path])
    assert len(violations) == 1
    assert "bioetl_x" in violations[0]
    assert "reason=a" in violations[0]


def test_recording_identity_uniqueness_allows_distinct_labels(tmp_path: Path) -> None:
    path = tmp_path / "ok.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "groups": [
                    {
                        "name": "g",
                        "rules": [
                            {
                                "record": "bioetl_x",
                                "labels": {"reason": "a"},
                                "expr": "vector(1)",
                            },
                            {
                                "record": "bioetl_x",
                                "labels": {"reason": "b"},
                                "expr": "vector(2)",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert cpr.validate_recording_rule_identity_uniqueness([path]) == []


def test_recording_identity_uniqueness_ok_for_shipped_rules() -> None:
    files = cpr.list_shipped_rule_files(Path("grafana/prometheus-rules"))
    assert cpr.validate_recording_rule_identity_uniqueness(files) == []


def test_check_rules_syntax_reports_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rule = tmp_path / "r.yml"
    rule.write_text(
        "groups:\n- name: g\n  rules:\n  - record: x\n    expr: up\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cpr.shutil,
        "which",
        lambda name: "/usr/bin/promtool" if name == "promtool" else None,
    )
    monkeypatch.setattr(
        cpr.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1, stdout="", stderr="parse error: unexpected"
        ),
    )
    result = cpr.check_rules_syntax([rule], root=tmp_path, prefer="local")
    assert result["ok"] is False
    assert "parse error" in result["stderr"]
