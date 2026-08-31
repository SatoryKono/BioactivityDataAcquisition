"""Regression tests for the unified governance artifact refresh command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa import refresh_governance_artifacts as refresh

pytestmark = pytest.mark.unit


def test_check_routes_every_governed_artifact_through_fail_closed_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *, check: bool = True) -> int:
        assert check is True
        calls.append(cmd[1:])
        return 0

    monkeypatch.setattr(refresh, "_run", fake_run)

    refresh._run_check_only()

    assert calls == [
        [
            "-m",
            "scripts.engineering.qa.report_source_tree_manifest",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa.report_module_coverage_inventory",
            "--check",
            "--allow-missing-coverage-xml",
        ],
        [
            "-m",
            "scripts.engineering.qa.generate_architecture_dependency_map",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa.report_test_governance_audit",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa.report_hotspot_family_baseline",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa.report_dead_code_inventory",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa.report_live_residual_snapshot",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
            "--check",
        ],
        [
            "-m",
            "scripts.engineering.qa",
            "report-debt-governance-gates",
            "--check",
        ],
        [
            "-m",
            "pytest",
            "tests/architecture/test_module_coverage_inventory_freshness.py::"
            "test_module_coverage_inventory_source_tree_hash_is_current",
            "tests/architecture/test_quality_debt_scorecard.py::"
            "test_debt_scorecard_hotspot_family_metrics_match_committed_baseline",
            "-q",
            "--tb=no",
        ],
    ]


def test_run_propagates_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=23),
    )

    with pytest.raises(SystemExit) as exc_info:
        refresh._run(["generator", "--check"])

    assert exc_info.value.code == 23


def test_refresh_propagates_generator_failure_before_later_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_subprocess_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(cmd)
        return SimpleNamespace(
            returncode=(
                41
                if "scripts.engineering.qa.report_architecture_quality_scorecard" in cmd
                else 0
            )
        )

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(
        refresh,
        "_sync_scorecard_hotspot_metrics_from_baseline",
        lambda: None,
    )

    with pytest.raises(SystemExit) as exc_info:
        refresh._run_refresh()

    assert exc_info.value.code == 41
    assert not any(
        "scripts.engineering.qa.report_config_surface_backlog" in cmd for cmd in calls
    )



def test_refresh_updates_remote_main_baseline_before_debt_rollup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], *, check: bool = True) -> int:
        assert check is True
        calls.append(cmd[1:])
        return 0

    monkeypatch.setattr(refresh, "_run", fake_run)
    monkeypatch.setattr(
        refresh,
        "_sync_scorecard_hotspot_metrics_from_baseline",
        lambda: None,
    )

    refresh._run_refresh()

    remote_main_index = calls.index(
        [
            "-m",
            "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
            "--update",
        ]
    )
    debt_rollup_index = calls.index(
        [
            "-m",
            "scripts.engineering.qa",
            "report-debt-governance-gates",
            "--update",
        ]
    )
    assert remote_main_index < debt_rollup_index

def test_scorecard_sync_fails_when_required_input_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(refresh, "ROOT", tmp_path)

    with pytest.raises(FileNotFoundError, match="hotspot-family-baseline.json"):
        refresh._sync_scorecard_hotspot_metrics_from_baseline()


def test_scorecard_budget_sync_is_shrink_only() -> None:
    family: dict[str, object] = {
        "bounded_growth_budgets": {
            "files_ge_250_loc": 4,
            "max_internal_fan_in": 2,
        }
    }
    measured: dict[str, object] = {
        "bounded_growth_budgets": {
            "files_ge_250_loc": 3,
            "max_internal_fan_in": 5,
        }
    }

    changed = refresh._ratchet_family_budgets(family, measured)

    assert changed == 1
    assert family["bounded_growth_budgets"] == {
        "files_ge_250_loc": 3,
        "max_internal_fan_in": 2,
    }


def test_atomic_writer_uses_utf8_lf_and_replaces_target(tmp_path: Path) -> None:
    target = tmp_path / "scorecard.yaml"
    target.write_text("stale\r\n", encoding="utf-8", newline="")

    refresh._write_text_atomically(target, "owner: architecture\nvalue: тест\n")

    assert target.read_bytes() == "owner: architecture\nvalue: тест\n".encode()
    assert list(tmp_path.iterdir()) == [target]
