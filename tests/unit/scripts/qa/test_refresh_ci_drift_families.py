"""Tests for refresh-ci-drift-families (no full governance refresh)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.engineering.qa import __main__ as qa_router
from scripts.engineering.qa import refresh_governance_artifacts as refresh

pytestmark = pytest.mark.unit


def test_router_exposes_ci_drift_families_command() -> None:
    spec = qa_router.COMMAND_SPECS["refresh-ci-drift-families"]
    assert spec.runner == "module"
    assert spec.target == "scripts.engineering.qa.refresh_governance_artifacts"
    assert spec.prefix_args == ("ci-drift-families",)


def test_ci_drift_families_requires_a_family_flag() -> None:
    with pytest.raises(SystemExit) as exc_info:
        refresh.run_ci_drift_families([])
    assert exc_info.value.code == 2


def test_check_runs_selected_families_in_canonical_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *, check: bool = True) -> int:
        assert check is True
        calls.append(cmd[1:])
        return 0

    monkeypatch.setattr(refresh, "_run", fake_run)
    monkeypatch.setattr(refresh, "_rebind_evidence_surface", lambda **_: 0)

    assert (
        refresh.run_ci_drift_families(
            [
                "--check",
                "--dataflow",
                "--telemetry",
                "--test-gov",
                "--flaky-fingerprint",
                "--evidence",
                "--remote-main",
            ]
        )
        == 0
    )

    assert calls == [
        ["-m", "scripts.engineering.qa.report_test_governance_audit", "--check"],
        [
            "-m",
            "scripts.engineering.qa",
            "report-flaky-test-burndown-review",
            "--check",
        ],
        [
            "-m",
            "pytest",
            "tests/architecture/test_test_telemetry_baseline.py",
            "tests/architecture/test_test_telemetry_governance.py",
            "-q",
            "--tb=short",
        ],
        [
            "-m",
            "scripts.engineering.qa",
            "report-architecture-debt-remote-main-baseline",
            "--check",
        ],
        [
            "-m",
            "scripts.diagrams",
            "generate-dataflows",
            "--pipeline",
            "chembl_activity",
            "--check",
        ],
    ]


def test_update_does_not_call_budget_ratchet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ratchet_calls: list[object] = []

    def fail_ratchet(*args: object, **kwargs: object) -> int:
        ratchet_calls.append((args, kwargs))
        return 0

    monkeypatch.setattr(refresh, "_ratchet_family_budgets", fail_ratchet)
    monkeypatch.setattr(refresh, "_run", lambda *args, **kwargs: 0)
    monkeypatch.setattr(refresh, "_rebind_evidence_surface", lambda **_: 0)

    assert refresh.run_ci_drift_families(["--update", "--test-gov", "--evidence"]) == 0
    assert ratchet_calls == []


def test_telemetry_update_requires_tests_run_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(refresh, "_run", lambda *args, **kwargs: 0)
    with pytest.raises(SystemExit, match="telemetry --update requires"):
        refresh.run_ci_drift_families(["--update", "--telemetry"])


def test_replace_current_evidence_hash_leaves_historical_records() -> None:
    registry = (
        "current_audit_id: current-id\n"
        "audits:\n"
        "  - id: current-id\n"
        "    evidence_surface_sha256: aaa111\n"
        "  - id: old-id\n"
        "    evidence_surface_sha256: aaa111\n"
    )
    updated = refresh._replace_current_evidence_hash(
        registry, current_id="current-id", old="aaa111", live="bbb222"
    )
    assert "  - id: current-id\n    evidence_surface_sha256: bbb222\n" in updated
    assert "  - id: old-id\n    evidence_surface_sha256: aaa111\n" in updated


def test_dataflow_rejects_unsafe_pipeline_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(refresh, "_run", lambda *args, **kwargs: 0)
    with pytest.raises(SystemExit, match="invalid --pipeline"):
        refresh.run_ci_drift_families(
            ["--check", "--dataflow", "--pipeline", "chembl; rm -rf /"]
        )


def test_telemetry_update_rejects_non_ancestor_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        refresh.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr=""),
    )
    with pytest.raises(SystemExit, match="ancestor of HEAD"):
        refresh.run_ci_drift_families(
            [
                "--update",
                "--telemetry",
                "--coverage-percent",
                "96.73",
                "--source-commit",
                "deadbeef",
                "--source-run-id",
                "1",
                "--source-run-url",
                "https://example.invalid/run/1",
            ]
        )


def test_telemetry_update_rejects_flag_like_source_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(refresh, "_run", lambda *args, **kwargs: 0)
    with pytest.raises(SystemExit, match="git object id"):
        refresh.run_ci_drift_families(
            [
                "--update",
                "--telemetry",
                "--coverage-percent",
                "96.73",
                "--source-commit=--output=/tmp/x",
                "--source-run-id",
                "1",
                "--source-run-url",
                "https://example.invalid/run/1",
            ]
        )


def test_run_rejects_shell_metacharacters_before_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        refresh.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    with pytest.raises(SystemExit, match="shell metacharacters"):
        refresh._run(["python", "-c", "print(1); rm -rf /"])
