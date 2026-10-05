"""Regression checks for fail-closed live acceptance."""

from __future__ import annotations

import pytest
import json
from pathlib import Path

from scripts.ops.observability.green_acceptance import Case, command, green_failures


pytestmark = pytest.mark.unit


def test_composite_children_cannot_substitute_parent_evidence(tmp_path):
    from scripts.ops.observability.green_acceptance import inspect_composite_parents

    folder = tmp_path / "output/control/run_manifest"
    folder.mkdir(parents=True)
    (folder / "parent.json").write_text(
        json.dumps(
            {
                "provider": "composite",
                "pipeline_name": "composite_activity",
                "run_id": "parent",
            }
        )
    )
    failures = inspect_composite_parents(
        Case("composite", "composite_activity"),
        tmp_path,
        [tmp_path / "pipeline/chembl_activity/child/pipeline-run-report.json"],
    )
    assert failures == ["composite_parent_report_missing:composite_activity"]


def test_matrix_covers_every_case_and_prepares_derived_inputs():
    from scripts.ops.observability.green_acceptance import discover

    root = Path(__file__).resolve().parents[5]
    cases = discover(root)
    assert len(cases) == 54
    target = next(
        case
        for case in cases
        if case.id == "pipeline-chembl_target_protein_classification"
    )
    assert set(target.prerequisites) == {
        "chembl_target",
        "chembl_target_component",
        "chembl_protein_class",
    }
    for prerequisite in target.prerequisites:
        args = command(Case("pipeline", prerequisite))
        assert args[args.index("--limit") + 1] == "1000"


def test_error_log_cannot_be_hidden_by_successful_exit():
    from scripts.ops.observability.green_acceptance import logged_errors

    assert logged_errors('{"level":"error","event":"write_failed"}') == [
        "error_log:write_failed"
    ]
    assert logged_errors('{"level":"info","event":"completed"}') == []


def test_composite_limit_alias_preserves_seed_limit():
    from bioetl.interfaces.cli.commands.run_composite import run_composite

    option = next(param for param in run_composite.params if param.name == "seed_limit")
    assert {"--seed-limit", "--limit"} <= set(option.opts)


@pytest.mark.parametrize("kind", ["pipeline", "workflow", "composite"])
def test_every_launch_has_limit_1000(kind):
    args = command(Case(kind, "chembl_assay"))
    assert args[args.index("--limit") + 1] == "1000"
    assert (
        args[args.index("--required-persistence-profile") + 1] == "degraded_observable"
    )


def test_all_green_passes():
    assert (
        green_failures(
            "success",
            {"saved_evidence_status": "OK", "replay_readiness_status": "OK"},
            {"verdict": "OK", "evidence_completeness": "COMPLETE"},
        )
        == []
    )


@pytest.mark.parametrize(
    "value", [None, "UNKNOWN", "INCOMPLETE", "N/A", "WARN", "ERROR", "QUERY ERROR"]
)
@pytest.mark.parametrize("field", ["saved_evidence_status", "replay_readiness_status"])
def test_non_green_evidence_fails(field, value):
    presentation = {
        "saved_evidence_status": "OK",
        "replay_readiness_status": "OK",
        field: value,
    }
    assert green_failures(
        "success", presentation, {"verdict": "OK", "evidence_completeness": "COMPLETE"}
    )


@pytest.mark.parametrize(
    "status", ["failed", "running", "partial", "shutdown", "unknown"]
)
def test_failed_execution_cannot_be_hidden_by_green_evidence(status):
    assert green_failures(
        status,
        {"saved_evidence_status": "OK", "replay_readiness_status": "OK"},
        {"verdict": "OK", "evidence_completeness": "COMPLETE"},
    )


@pytest.mark.parametrize("limit", [0, -1, True, "10", 1.5])
def test_invalid_limit_rejected_before_launch(limit):
    with pytest.raises(ValueError, match="positive integer"):
        command(Case("pipeline", "test"), limit)


@pytest.mark.parametrize("kind", ["pipeline", "composite", "workflow"])
@pytest.mark.parametrize("limit", [10, 100])
def test_explicit_limit_reaches_cli(kind, limit):
    args = command(Case(kind, "test"), limit)
    assert args[args.index("--limit") + 1] == str(limit)


@pytest.mark.parametrize("error", [OSError("setup failed"), KeyboardInterrupt()])
def test_setup_failure_and_cancellation_keep_terminal_receipt(
    tmp_path, monkeypatch, error
):
    import json
    from scripts.ops.observability import green_acceptance as runner

    monkeypatch.setattr(runner, "source_commit", lambda root: "pinned-sha")

    def fail(*args):
        raise error

    monkeypatch.setattr(runner, "_execute_case", fail)
    with pytest.raises(type(error)):
        runner.execute(
            Case("pipeline", "test"),
            tmp_path,
            tmp_path / "reports",
            tmp_path / "env",
            limit=10,
        )
    result = json.loads((tmp_path / "reports/pipeline-test/result.json").read_text())
    assert result["passed"] is False
    assert result["status"] == (
        "failed" if isinstance(error, Exception) else "interrupted"
    )
    assert result["started_at"] <= result["finished_at"]
    assert result["source_commit"] == result["source_commit_after"] == "pinned-sha"
    assert result["limit"] == 10


def test_changed_source_fails_otherwise_successful_case(tmp_path, monkeypatch):
    import json
    from scripts.ops.observability import green_acceptance as runner

    commits = iter(["before", "after"])
    monkeypatch.setattr(runner, "source_commit", lambda root: next(commits))
    monkeypatch.setattr(runner, "_execute_case", lambda *args: [])
    failures = runner.execute(
        Case("pipeline", "test"), tmp_path, tmp_path / "reports", tmp_path / "env"
    )
    assert failures == ["source_commit_changed"]
    result = json.loads((tmp_path / "reports/pipeline-test/result.json").read_text())
    assert result["passed"] is False


def campaign_stubs(monkeypatch):
    from scripts.ops.observability import green_acceptance as runner

    monkeypatch.setattr(runner, "input_fingerprints", lambda root: {"configs": "fixed"})
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    monkeypatch.setattr(runner, "source_commit", lambda root: "pinned-sha")
    monkeypatch.setattr(
        runner,
        "discover",
        lambda root: tuple(
            Case("composite", f"composite_{name}")
            for name in ("activity", "assay", "molecule", "target", "publication")
        ),
    )
    return runner


def test_campaign_is_ordered_pinned_and_not_final_acceptance(tmp_path, monkeypatch):
    import json

    runner = campaign_stubs(monkeypatch)
    launches = []

    def execute(case, root, output, env_file, **kwargs):
        assert (root / "reports/quality/green-acceptance.lock").is_file()
        launches.append((case.name, kwargs))
        return ["Provider WARN"] if case.name == "composite_assay" else []

    monkeypatch.setattr(runner, "execute", execute)
    output = tmp_path / "reports/campaign"
    assert runner.execute_campaign(tmp_path, output, tmp_path / "env") == [
        "composite-composite_assay:Provider WARN"
    ]
    assert [name for name, _ in launches] == [
        "composite_activity",
        "composite_assay",
        "composite_molecule",
        "composite_target",
    ]
    assert all(
        kwargs == {"limit": 10, "expected_source": "pinned-sha"}
        for _, kwargs in launches
    )
    receipt = json.loads((output / "campaign.json").read_text())
    assert receipt["local_checks_passed"] is False
    assert receipt["acceptance_status"] == "PENDING_HTTP_AND_OFFLINE_REPLAY"
    assert receipt["scope"] == {
        "issue": 11906,
        "composites": [name for name, _ in launches],
        "excluded": {"composite_publication": "Tracked separately in #11947"},
    }
    assert not (tmp_path / "reports/quality/green-acceptance.lock").exists()
    with pytest.raises(FileExistsError):
        runner.execute_campaign(tmp_path, output, tmp_path / "env")
    assert len(launches) == 4


@pytest.mark.parametrize("error", [KeyboardInterrupt(), OSError("setup")])
def test_campaign_cancel_records_unstarted_cases_and_releases_lease(
    tmp_path, monkeypatch, error
):
    import json

    runner = campaign_stubs(monkeypatch)

    def interrupt(*args, **kwargs):
        raise error

    monkeypatch.setattr(runner, "execute", interrupt)
    output = tmp_path / "reports/campaign"
    with pytest.raises(type(error)):
        runner.execute_campaign(tmp_path, output, tmp_path / "env")
    receipt = json.loads((output / "campaign.json").read_text())
    expected = "failed" if isinstance(error, Exception) else "interrupted"
    assert receipt["status"] == expected
    assert [row["status"] for row in receipt["cases"]] == [expected] + [
        "not_started"
    ] * 3
    assert receipt["local_checks_passed"] is False
    assert not (tmp_path / "reports/quality/green-acceptance.lock").exists()


def test_existing_campaign_lease_is_preserved(tmp_path, monkeypatch):
    runner = campaign_stubs(monkeypatch)
    lock = tmp_path / "reports/quality/green-acceptance.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("another-owner")
    with pytest.raises(FileExistsError):
        runner.execute_campaign(
            tmp_path, tmp_path / "reports/campaign", tmp_path / "env"
        )
    assert lock.read_text() == "another-owner"
    assert not (tmp_path / "reports/campaign").exists()


@pytest.mark.parametrize("outcome", [0, 7, "timeout", "cancel"])
def test_launch_receipts_and_owned_process_cleanup(tmp_path, monkeypatch, outcome):
    import io
    from unittest.mock import Mock
    from scripts.ops.observability import green_acceptance as runner

    process = Mock(pid=123, returncode=-9)
    process.poll.return_value = None
    if outcome == "timeout":
        process.wait.side_effect = [runner.subprocess.TimeoutExpired("fake", 12), -9]
    elif outcome == "cancel":
        process.wait.side_effect = [KeyboardInterrupt(), -9]
    else:
        process.wait.return_value = outcome
        process.poll.return_value = outcome
        process.returncode = outcome
    monkeypatch.setattr(runner.subprocess, "Popen", Mock(return_value=process))
    terminate = Mock()
    monkeypatch.setattr(runner.sys, "platform", "win32")
    monkeypatch.setattr(runner.subprocess, "run", terminate)
    receipt = {}
    if outcome == "cancel":
        with pytest.raises(KeyboardInterrupt):
            runner.run_launch(
                ["fake"],
                tmp_path,
                {},
                io.StringIO(),
                timeout_seconds=12,
                receipt=receipt,
            )
    else:
        failures = runner.run_launch(
            ["fake"], tmp_path, {}, io.StringIO(), timeout_seconds=12, receipt=receipt
        )
        assert failures == (
            []
            if outcome == 0
            else ["launch_timeout=12s"]
            if outcome == "timeout"
            else ["exit_code=7"]
        )
    assert receipt["pid"] == 123
    assert receipt["finished_at"] >= receipt["started_at"]
    assert (
        receipt["status"]
        == {0: "success", 7: "failed", "timeout": "timeout", "cancel": "interrupted"}[
            outcome
        ]
    )
    if outcome in ("timeout", "cancel"):
        assert terminate.call_args.args[0] == ["taskkill", "/PID", "123", "/T", "/F"]
    else:
        terminate.assert_not_called()


@pytest.mark.parametrize("outcome", ["timeout", "cancel"])
def test_launch_preserves_result_when_process_group_exits(
    tmp_path, monkeypatch, outcome
):
    import io
    from unittest.mock import Mock
    from scripts.ops.observability import green_acceptance as runner

    process = Mock(pid=123, returncode=0)
    process.poll.return_value = None
    original = (
        runner.subprocess.TimeoutExpired("fake", 12)
        if outcome == "timeout"
        else KeyboardInterrupt()
    )
    process.wait.side_effect = [original, 0]
    monkeypatch.setattr(runner.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(runner.sys, "platform", "linux")
    monkeypatch.setattr(runner.signal, "SIGKILL", 9, raising=False)
    terminate = Mock(side_effect=ProcessLookupError())
    monkeypatch.setattr(runner.os, "killpg", terminate, raising=False)
    receipt = {}
    if outcome == "cancel":
        with pytest.raises(KeyboardInterrupt) as raised:
            runner.run_launch(
                ["fake"],
                tmp_path,
                {},
                io.StringIO(),
                timeout_seconds=12,
                receipt=receipt,
            )
        assert raised.value is original
    else:
        assert runner.run_launch(
            ["fake"], tmp_path, {}, io.StringIO(), timeout_seconds=12, receipt=receipt
        ) == ["launch_timeout=12s"]
    terminate.assert_called_once_with(process.pid, runner.signal.SIGKILL)
    process.wait.assert_called_with(timeout=30)
    assert receipt["exit_code"] == 0
    assert receipt["status"] == ("timeout" if outcome == "timeout" else "interrupted")
    assert receipt["finished_at"] >= receipt["started_at"]


def test_launch_creation_error_has_terminal_receipt(tmp_path, monkeypatch):
    import io
    from unittest.mock import Mock
    from scripts.ops.observability import green_acceptance as runner

    monkeypatch.setattr(
        runner.subprocess, "Popen", Mock(side_effect=OSError("unavailable"))
    )
    receipt = {}
    with pytest.raises(OSError):
        runner.run_launch(["fake"], tmp_path, {}, io.StringIO(), receipt=receipt)
    assert receipt["status"] == "failed"
    assert receipt["error_type"] == "OSError"
    assert "finished_at" in receipt
    assert "pid" not in receipt


def test_campaign_rejects_xdist_before_reading_source(tmp_path, monkeypatch):
    runner = campaign_stubs(monkeypatch)
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    with pytest.raises(ValueError, match="sequential"):
        runner.execute_campaign(
            tmp_path, tmp_path / "reports/campaign", tmp_path / "env"
        )
    assert not (tmp_path / "reports").exists()


def test_successful_local_campaign_still_requires_external_acceptance(
    tmp_path, monkeypatch
):
    runner = campaign_stubs(monkeypatch)
    monkeypatch.setattr(runner, "execute", lambda *args, **kwargs: [])
    output = tmp_path / "reports/campaign"
    assert runner.execute_campaign(tmp_path, output, tmp_path / "env", limit=10) == []
    manifest = json.loads((output / "campaign.json").read_text())
    assert manifest["local_checks_passed"] is True
    assert manifest["acceptance_status"] == "PENDING_HTTP_AND_OFFLINE_REPLAY"


def test_case_uses_copied_configs_and_same_limit_for_prerequisites(
    tmp_path, monkeypatch
):
    from scripts.ops.observability import green_acceptance as runner
    import dotenv

    (tmp_path / "data/input").mkdir(parents=True)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/sentinel.yaml").write_text("copied: true")
    (tmp_path / "uv.lock").write_text("version = 1")
    monkeypatch.setattr(
        dotenv,
        "dotenv_values",
        lambda path: {"BIOETL_SEMANTICSCHOLAR_API_KEY": "not-used"},
    )
    launches = []

    def launch(args, folder, environment, log, **kwargs):
        assert Path(environment["BIOETL_CONFIGS_ROOT"]) == folder / "configs"
        assert (Path(environment["BIOETL_CONFIGS_ROOT"]) / "sentinel.yaml").is_file()
        assert environment["BIOETL_DATA_DIR"] == str(folder / "data")
        assert environment["BIOETL_SEMANTICSCHOLAR_API_KEY"] == ""
        launches.append(args)
        return []

    monkeypatch.setattr(runner, "run_launch", launch)
    monkeypatch.setattr(runner, "_runtime_policy", lambda *args: {"test_mode": False})
    folder = tmp_path / "reports/case"
    folder.mkdir(parents=True)
    receipt = {"processes": []}
    failures = runner._execute_case(
        Case("pipeline", "downstream", prerequisites=("upstream",)),
        tmp_path,
        folder,
        tmp_path / "unused-env",
        10,
        receipt,
    )
    assert "pipeline_reports_missing" in failures
    assert len(launches) == 2
    assert all(args[args.index("--limit") + 1] == "10" for args in launches)
    assert receipt["launch_timeout_seconds"] == [1800, 1800]
    assert receipt["runtime_policy"] == {"test_mode": False}


@pytest.mark.parametrize("dotenv_mode", [None, "true"])
def test_live_child_restores_production_http_and_durability(
    tmp_path, monkeypatch, dotenv_mode
):
    import dotenv
    from scripts.ops.observability import green_acceptance as runner

    root = Path(__file__).resolve().parents[5]
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setattr(
        dotenv, "dotenv_values", lambda _: {"BIOETL_TEST_MODE": dotenv_mode}
    )
    environment = runner._case_environment(root, tmp_path, tmp_path / "unused-env")
    environment["BIOETL_CONFIGS_ROOT"] = str(root / "configs")
    assert environment["BIOETL_TEST_MODE"] == "false"
    policy = runner._runtime_policy(tmp_path, environment)
    assert policy["test_mode"] is False
    assert policy["control_plane_fsync"] is True
    chembl = policy["providers"]["chembl"]
    assert chembl["timeout_seconds"] == 120
    assert chembl["read_timeout_seconds"] == 240
    assert chembl["retry_base_delay_seconds"] == 1
    assert chembl["retry_after_cap_seconds"] is None
    assert chembl["rate_per_second"] == 0.1
    assert chembl["circuit_recovery_seconds"] == 3000


def test_live_runtime_probe_rejects_test_mode(tmp_path, monkeypatch):
    import subprocess
    from scripts.ops.observability import green_acceptance as runner

    root = Path(__file__).resolve().parents[5]
    environment = runner._case_environment(root, tmp_path, tmp_path / "unused-env")
    environment["BIOETL_TEST_MODE"] = "true"
    with pytest.raises(subprocess.CalledProcessError) as error:
        runner._runtime_policy(tmp_path, environment)
    assert "live_acceptance_requires_production_runtime" in error.value.stderr


@pytest.mark.parametrize(
    "branch, dirty",
    [("main", ""), ("codex/pipeline-green-gates-test", " M src/file.py")],
)
def test_source_rejects_unsafe_branch_and_dirty_tree(
    tmp_path, monkeypatch, branch, dirty
):
    from unittest.mock import Mock
    from scripts.ops.observability import green_acceptance as runner

    monkeypatch.setattr(
        runner.subprocess, "check_output", Mock(side_effect=[branch, dirty])
    )
    with pytest.raises(ValueError):
        runner.source_commit(tmp_path)


def test_outside_output_rejected_before_creation(tmp_path, monkeypatch):
    from scripts.ops.observability import green_acceptance as runner

    root = tmp_path / "worktree"
    root.mkdir()
    monkeypatch.setattr(runner, "source_commit", lambda root: "sha")
    with pytest.raises(ValueError, match="inside"):
        runner.execute(
            Case("pipeline", "test"), root, tmp_path / "outside", tmp_path / "unused"
        )
    assert not (tmp_path / "outside").exists()


def test_input_fingerprint_binds_file_names_and_content(tmp_path):
    from scripts.ops.observability import green_acceptance as runner

    (tmp_path / "configs").mkdir()
    (tmp_path / "data/input").mkdir(parents=True)
    (tmp_path / "uv.lock").write_text("lock")
    item = tmp_path / "data/input/ids.csv"
    item.write_text("one")
    before = runner.input_fingerprints(tmp_path)
    item.write_text("two")
    changed = runner.input_fingerprints(tmp_path)
    assert before["data/input"] != changed["data/input"]
    item.rename(item.with_name("other.csv"))
    assert runner.input_fingerprints(tmp_path)["data/input"] != changed["data/input"]
    assert before["uv.lock"] == changed["uv.lock"]


@pytest.mark.parametrize("defect", [None, "missing", "wrong_run", "failed"])
def test_composite_child_coverage_binds_config_and_parent(tmp_path, defect):
    from scripts.ops.observability import green_acceptance as runner

    config = tmp_path / "configs/composites"
    config.mkdir(parents=True)
    (config / "assay.yaml").write_text(
        "composite:\n  seed:\n    pipeline: seed\n  enrichers:\n    - pipeline: optional_child\n      required: false\n"
    )
    paths = []
    for name in ("composite_assay", "seed", "optional_child"):
        path = tmp_path / "reports/pipeline" / name / "run" / "pipeline-run-report.json"
        path.parent.mkdir(parents=True)
        path.write_text("{}")
        paths.append(path)
    children = [
        {"pipeline_name": name, "run_id": "run", "status": "success"}
        for name in ("seed", "optional_child")
    ]
    if defect == "missing":
        paths.pop()
    elif defect == "wrong_run":
        children[1]["run_id"] = "another"
    elif defect == "failed":
        children[1]["status"] = "failed"
    paths[0].write_text(json.dumps({"io": {"child_runs": children}}))
    failures = runner.composite_report_coverage(
        Case("composite", "composite_assay"), tmp_path / "configs", paths
    )
    assert bool(failures) is (defect is not None)
