"""Local scope selection and receipts cannot replace fresh protected checks."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.engineering.repo import scoped_checks as checks

pytestmark = pytest.mark.unit


@pytest.mark.skipif(os.name != "nt", reason="Native Windows wrapper qualification")
def test_windows_pretest_without_bash_is_error():
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell is not None
    script = Path(checks.__file__).parents[1] / "dev/pretest_guardrails.ps1"
    # Only command discovery is replaced; no Bash script or service executes.
    code = (
        "function Get-Command { return $null }; & '"
        + str(script).replace("'", "''")
        + "'; exit $LASTEXITCODE"
    )
    result = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-Command", code],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2
    assert "Required bash is unavailable" in result.stderr


@pytest.mark.parametrize(
    "path,required,excluded",
    [
        ("docs/guide.md", "docs-cleanup-inventory", "dashboard-static-gates"),
        (
            "scripts/ai/junie/junie-mirror-contract.json",
            "runtime-parity",
            "dashboard-static-gates",
        ),
        (".pre-commit-config.yaml", "dashboard-first-window", "dashboard-static-gates"),
        ("src/bioetl/example.py", "module-coverage-source", "runtime-parity"),
        (".devin/agents/DEVIN-RUNTIME.md", "runtime-parity", "dashboard-static-gates"),
        ("grafana/dashboards/example.json", "dashboard-static-gates", "runtime-parity"),
        (
            "tests/integration/_grafana_test_support.py",
            "dashboard-static-gates",
            "runtime-parity",
        ),
    ],
)
def test_scope_preserves_owner_gates(tmp_path, path, required, excluded):
    ids = {check.id for check in checks.select_checks(tmp_path, [path])}
    assert required in ids
    assert excluded not in ids
    if path.startswith(("docs/", "src/", "tests/", "grafana/")):
        assert "dashboard-first-window" in ids  # DASH-FIT-004 remains global.


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 181])
def test_invalid_deadline_cannot_start_checks(tmp_path, timeout):
    with pytest.raises(ValueError, match="deadline"):
        checks.validate(tmp_path, timeout=timeout)


def test_missing_dependency_returns_error(tmp_path):
    result = checks._execute(
        checks.Check("missing", (str(tmp_path / "does-not-exist"),)),
        tmp_path,
        tmp_path,
        5,
    )
    assert result["status"] == "ERROR"
    assert result["returncode"] is None


def test_exhausted_deadline_never_runs_child(tmp_path, monkeypatch):
    monkeypatch.setattr(
        checks, "run_owned", lambda *args, **kwargs: pytest.fail("child started")
    )
    result = checks._execute(checks.Check("late", ("fixture",)), tmp_path, tmp_path, 0)
    assert result["status"] == "ERROR"


def test_plan_does_not_claim_execution_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checks, "validate_repo", lambda root: root)
    monkeypatch.setattr(
        checks.receipts, "snapshot", lambda *args, **kwargs: {"base_sha": "a" * 40}
    )
    monkeypatch.setattr(
        checks,
        "build_plan",
        lambda *args: {
            "unknown": [],
            "checks": [],
            "base_sha": "a" * 40,
        },
    )
    assert checks.main(["plan", "--repo", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PLANNED"
    assert result["execution_status"] == "NOT_RUN"
    assert result["ci_acceptance"] is False


def test_unknown_surface_never_qualifies_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checks, "validate_repo", lambda root: root)
    monkeypatch.setattr(checks, "build_plan", lambda *args: {"unknown": ["foreign"]})
    assert (
        checks.main(["receipt", "--repo", str(tmp_path), "--receipt", "missing"]) == 2
    )
    assert json.loads(capsys.readouterr().out)["status"] == "ERROR"


@pytest.mark.parametrize("core_status", ["PASS", "ERROR", "FAIL"])
def test_reuse_always_runs_fresh_core_and_stops_on_failure(
    tmp_path, monkeypatch, core_status
):
    static = checks.Check("static", ("fixture",), cacheable=True)
    fresh = checks.Check("fresh", ("fixture",))
    monkeypatch.setattr(
        checks,
        "build_plan",
        lambda *args: {
            "unknown": [],
            "checks": [static, fresh],
            "base_sha": "a" * 40,
        },
    )
    monkeypatch.setattr(checks, "resolve_revision", lambda *args: "a" * 40)
    monkeypatch.setattr(
        checks.receipts,
        "snapshot",
        lambda *args, **kwargs: {"state": "same", "base_sha": "a" * 40},
    )
    monkeypatch.setattr(
        checks.receipts, "receipt_directory", lambda *args: tmp_path / "receipts"
    )
    monkeypatch.setattr(
        checks.receipts, "validate_receipt", lambda *args, **kwargs: {"status": "PASS"}
    )
    written = []

    def write_receipt(*args):
        written.append(args)
        return Path("observation.json")

    monkeypatch.setattr(checks.receipts, "write_receipt", write_receipt)
    monkeypatch.setattr(
        checks, "_core_checks", lambda *args: [checks.Check("tree", ("fixture",))]
    )
    executed = []

    def execute(check, *args):
        executed.append(check.id)
        status = core_status if check.id == "tree" else "PASS"
        return checks._row(check, status, 0 if status == "PASS" else 2, 1)

    monkeypatch.setattr(checks, "_execute", execute)
    result = checks.validate(tmp_path, reuse=Path("cache.json"))
    assert executed == (["tree", "fresh"] if core_status == "PASS" else ["tree"])
    assert (
        result["status"] == core_status
        if core_status == "PASS"
        else result["status"] == "ERROR"
    )
    assert result["runtime_admission"] is False
    assert len(written) == 1  # Only a new observation, never a renewed cache TTL.
    assert result["cache_receipt"] == ("cache.json" if core_status == "PASS" else None)


def test_state_change_after_checks_does_not_write_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(
        checks,
        "build_plan",
        lambda *args: {
            "unknown": [],
            "checks": [],
            "base_sha": "a" * 40,
        },
    )
    states = iter(
        [
            {"state": "before", "base_sha": "a" * 40},
            {"state": "before", "base_sha": "a" * 40},
            {"state": "after", "base_sha": "a" * 40},
        ]
    )
    monkeypatch.setattr(
        checks.receipts, "snapshot", lambda *args, **kwargs: next(states)
    )
    monkeypatch.setattr(
        checks.receipts, "receipt_directory", lambda *args: tmp_path / "receipts"
    )
    monkeypatch.setattr(checks, "_core_checks", lambda *args: [])
    monkeypatch.setattr(
        checks.receipts,
        "write_receipt",
        lambda *args: pytest.fail("stale receipt written"),
    )
    assert checks.validate(tmp_path)["reason"] == "state_changed_during_checks"


def test_state_change_during_planning_cannot_start_old_checks(tmp_path, monkeypatch):
    states = iter(
        [
            {"base_sha": "a" * 40, "state": "before"},
            {"base_sha": "a" * 40, "state": "after"},
        ]
    )
    monkeypatch.setattr(
        checks.receipts, "snapshot", lambda *args, **kwargs: next(states)
    )
    monkeypatch.setattr(checks, "build_plan", lambda *args: {"base_sha": "a" * 40})
    monkeypatch.setattr(
        checks, "_execute", lambda *args: pytest.fail("old selection executed")
    )
    with pytest.raises(ValueError, match="state changed during planning"):
        checks.validate(tmp_path)
