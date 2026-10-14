"""Regression tests for the unified governance artifact refresh command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa import refresh_governance_artifacts as refresh

pytestmark = pytest.mark.unit


def test_local_telemetry_refresh_uses_verified_manifest_only(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(refresh, "_run", lambda command: calls.append(command) or 0)
    args = SimpleNamespace(local_manifest=Path("complete/manifest.json"))
    assert refresh._run_telemetry(check_only=False, telemetry=args) == 0
    assert calls[0][1:] == [
        "-m",
        "scripts.engineering.ci.update_test_telemetry_baseline",
        "--local-manifest",
        str(args.local_manifest),
    ]


@pytest.mark.parametrize(
    "override",
    ["coverage_percent", "source_commit", "source_run_id", "source_run_url", "junit"],
)
def test_local_telemetry_refresh_rejects_ci_identity_overrides(
    monkeypatch, override
) -> None:
    calls = []
    monkeypatch.setattr(refresh, "_run", lambda command: calls.append(command) or 0)
    args = SimpleNamespace(local_manifest=Path("complete/manifest.json"))
    setattr(
        args,
        override,
        99.9
        if override == "coverage_percent"
        else ["lane.xml"]
        if override == "junit"
        else "invented",
    )
    with pytest.raises(SystemExit, match="must come from the manifest"):
        refresh._run_telemetry(check_only=False, telemetry=args)
    assert calls == []


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


@pytest.mark.parametrize("unmeasured", [0, 1])
def test_application_core_closeout_preserves_measurement_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unmeasured: int
) -> None:
    import json

    quality = tmp_path / "reports/quality"
    quality.mkdir(parents=True)
    path = quality / "issue-5272-application-core-coverage-closeout.json"
    initial = {
        "snapshot_date": "2026-08-17",
        "current_metrics": {"application_core_covered_line_percent": 99.86},
        "baseline_metrics": {"application_core_covered_line_percent": 49.09},
        "parent_epic_status": {"remaining_below_85_module_count": 0, "status": "open"},
        "current_binding_refresh": {"measured_head": "historical-head"},
    }
    path.write_text(json.dumps(initial), encoding="utf-8")
    inventory = {
        "source_tree_sha256": "current-source",
        "summary": {
            "status_counts": {"uncovered": 0},
            "unmeasured_module_count": unmeasured,
            "hotspot_family_coverage": {
                "application_core": {
                    "covered_line_percent": 99.79,
                    "status_counts": {"uncovered": 0},
                    "unmeasured_module_count": 0,
                }
            },
        },
        "modules": [{"coverage_percent": 95}, {"coverage_percent": None}],
    }
    (quality / "module-coverage-inventory.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )
    monkeypatch.setattr(refresh, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="differs from accepted inventory"):
        refresh._refresh_application_core_closeout(check_only=True)
    assert json.loads(path.read_text()) == initial
    refresh._refresh_application_core_closeout(check_only=False)
    updated = json.loads(path.read_text())
    assert updated["current_metrics"]["application_core_covered_line_percent"] == 99.79
    assert updated["previous_current_bindings"][0]["current_binding_refresh"] == {
        "measured_head": "historical-head"
    }
    assert "measured_head" not in updated["current_binding_refresh"]
    assert updated["status"] == (
        "current_inventory_regressed" if unmeasured else "validated_local_closeable"
    )
    original_bytes = path.read_bytes()
    refresh._refresh_application_core_closeout(check_only=False)
    refresh._refresh_application_core_closeout(check_only=True)
    assert path.read_bytes() == original_bytes

    # Identical measurements do not make a different source binding current.
    inventory["source_tree_sha256"] = "new-source-with-same-metrics"
    (quality / "module-coverage-inventory.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="differs from accepted inventory"):
        refresh._refresh_application_core_closeout(check_only=True)
    assert path.read_bytes() == original_bytes
    refresh._refresh_application_core_closeout(check_only=False)
    rebound = json.loads(path.read_text())
    assert rebound["current_metrics"] == updated["current_metrics"]
    assert (
        rebound["current_binding_refresh"]["source_tree_sha256"]
        == inventory["source_tree_sha256"]
    )
    assert (
        rebound["previous_current_bindings"][-1]["current_binding_refresh"]
        == (updated["current_binding_refresh"])
    )
    refresh._refresh_application_core_closeout(check_only=True)


@pytest.mark.parametrize("outcome", ["pass", "fail", "skip"])
def test_coverage_closeout_rebinds_only_after_executed_tests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, outcome: str
) -> None:
    import json

    quality = tmp_path / "reports/quality"
    quality.mkdir(parents=True)
    closeout = quality / "low-coverage-targeted-tests-6045.json"
    initial = {
        "module_coverage_inventory_source_tree_sha256": "old",
        "targeted_modules": [{"targeted_tests": ["tests/test_target.py"]}],
        "validation": [{"status": "pass", "tests": 1}],
    }
    closeout.write_text(json.dumps(initial), encoding="utf-8")
    (quality / "module-coverage-inventory.json").write_text(
        '{"source_tree_sha256": "new"}', encoding="utf-8"
    )
    monkeypatch.setattr(refresh, "ROOT", tmp_path)

    def run(command: list[str]) -> int:
        assert "tests/test_target.py" in command
        if outcome == "fail":
            raise SystemExit(1)
        skipped = 1 if outcome == "skip" else 0
        (quality / "low-coverage-6045-revalidation.xml").write_text(
            f'<testsuites><testsuite tests="1" skipped="{skipped}"/></testsuites>',
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(refresh, "_run", run)
    if outcome == "pass":
        refresh._refresh_targeted_coverage_closeout()
        assert (
            json.loads(closeout.read_text())[
                "module_coverage_inventory_source_tree_sha256"
            ]
            == "new"
        )
    else:
        with pytest.raises(SystemExit):
            refresh._refresh_targeted_coverage_closeout()
        assert json.loads(closeout.read_text()) == initial
