"""Partition completeness and fail-closed scheduling regressions."""

from __future__ import annotations

import ast
import errno
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from scripts.engineering.ci.generated_artifact_checks import proven_deferral
from scripts.engineering.common.repo_paths import ensure_safe_cli_argv
from scripts.engineering.dev.pytest_artifact_selection import (
    ROOT,
    load_manifest,
    validate_selectors,
)

pytestmark = pytest.mark.unit


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    """Skip only unavailable symlink support/Windows privileges, not test failures."""
    try:
        link.symlink_to(target, target_is_directory=directory)
    except NotImplementedError:
        pytest.skip("Platform does not implement symlinks")
    except OSError as exc:
        unsupported = exc.errno in {errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}
        windows_privilege = getattr(exc, "winerror", None) == 1314 or (
            sys.platform == "win32" and exc.errno in {errno.EACCES, errno.EPERM}
        )
        if unsupported or windows_privilege:
            pytest.skip(f"Symlink creation is unsupported: {exc}")
        raise


def test_manifest_selectors_exist_and_do_not_cover_entire_modules() -> None:
    manifest = load_manifest()
    trees = {}
    for row in manifest["tests"]:
        path, *names = row["node"].split("::")
        if path not in trees:
            trees[path] = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        scope = trees[path]
        for name in names:
            matches = [
                node for node in scope.body if getattr(node, "name", None) == name
            ]
            assert len(matches) == 1, row["node"]
            scope = matches[0]
        assert isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
        assert "pytest.mark.generated_artifact" in {
            ast.unparse(d) for d in scope.decorator_list
        }


def test_reviewed_source_and_fixture_cases_stay_in_ci() -> None:
    nodes = {row["node"] for row in load_manifest()["tests"]}
    retained = {
        "tests/architecture/test_documentation_cleanup_inventory.py::test_documentation_cleanup_inventory_routed_in_registry",
        "tests/architecture/test_documentation_cleanup_inventory.py::test_ai_runtime_generated_mirrors_are_routed_in_registry",
        "tests/architecture/test_config_discrepancy_report_drift.py::test_config_matrix_uses_repository_canonical_lf_newlines",
        "tests/architecture/test_module_coverage_inventory.py::test_allow_missing_coverage_xml_preserves_existing_inventory_rows",
        "tests/architecture/test_composition_protocol_inventory.py::test_report_composition_protocol_inventory_check_cli",
        "tests/integration/ci/test_silver_gold_filter_parity.py::test_silver_gold_filter_parity_cli_check_round_trip",
    }
    assert nodes.isdisjoint(retained)
    closeout = [
        node
        for node in nodes
        if "test_tech_debt_issues_5933_5944_closeout.py::" in node
    ]
    assert len(closeout) == 4
    assert not any("5937" in node or "5938" in node for node in closeout)
    assert not any(
        node.startswith(
            "tests/unit/scripts/qa/test_report_flaky_test_burndown_review.py::"
        )
        for node in nodes
    )


def test_manifest_rejects_duplicate_or_module_wide_exemptions(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    row = {
        "node": "tests/test_a.py::test_a",
        "artifacts": ["a.json"],
        "reason": "reader",
    }
    for rows in (
        [row, row],
        [{**row, "node": "tests/test_a.py"}],
        [{**row, "artifacts": []}],
    ):
        path.write_text(
            json.dumps({"schema_version": 1, "tests": rows}), encoding="utf-8"
        )
        with pytest.raises(ValueError):
            load_manifest(path)


def test_deferral_requires_complete_nonempty_error_free_collection() -> None:
    node = "tests/test_a.py::test_a"
    payload = {
        "status": "deferred-to-daily",
        "selection": "ci",
        "pytest_exit_code": 5,
        "collection_errors": 0,
        "collected": [node],
        "deferred": [node],
        "selected": [],
        "other_deselected": [],
    }
    assert proven_deferral(payload, 5, {node})
    for changed in (
        {"collected": []},
        {"collection_errors": 1},
        {"selected": [node]},
        {"other_deselected": [node]},
        {"deferred": []},
        {"pytest_exit_code": 2},
        {"status": "failed"},
        {"selection": "daily"},
    ):
        assert not proven_deferral({**payload, **changed}, 5, {node})
    assert not proven_deferral(payload, 2, {node})
    assert not proven_deferral(payload, 5, set())


def test_real_pytest_partition_and_daily_missing_node_fail_closed(
    tmp_path: Path,
) -> None:
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nmarkers = generated_artifact: daily\n    slow: slow\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_cases.py").write_text(
        "import pytest\n@pytest.mark.generated_artifact\n@pytest.mark.slow\ndef test_artifact(): assert True\ndef test_source(): assert True\n",
        encoding="utf-8",
    )
    node = "tests/test_cases.py::test_artifact"
    manifest = {
        "schema_version": 1,
        "tests": [{"node": node, "artifacts": ["x"], "reason": "reader"}],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "conftest.py").write_text(
        "import sys, json\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from scripts.engineering.dev import pytest_artifact_selection as selection\n"
        "selection.load_manifest = lambda: json.loads(Path('manifest.json').read_text())\n"
        "original_validate = selection.validate_selectors\n"
        "selection.validate_selectors = lambda payload: original_validate(payload, Path.cwd())\n"
        "pytest_plugins = ['scripts.engineering.dev.pytest_artifact_selection']\n",
        encoding="utf-8",
    )

    def run(mode: str, *args: str):
        report = tmp_path / "report.json"
        report.unlink(missing_ok=True)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-c",
                str(tmp_path / "pytest.ini"),
                "--confcutdir",
                str(tmp_path),
                f"--artifact-selection={mode}",
                f"--artifact-selection-report={report}",
                *args,
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, json.loads(report.read_text()) if report.exists() else {}

    result, report = run("ci", "tests")
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["selected"] == ["tests/test_cases.py::test_source"]
    result, report = run("daily", "tests")
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["selected"] == [node]  # slow is included
    result, report = run("ci", node)
    assert result.returncode == 5
    assert proven_deferral(report, 5, {node})
    result, report = run("ci", "tests", "-k", "nonexistent")
    assert result.returncode == 5
    assert not proven_deferral(report, 5, {node})
    result, _ = run("daily", "tests", "-m", "not slow")
    assert result.returncode != 0
    assert "Daily artifact coverage is incomplete" in result.stderr
    source = (tests / "test_cases.py").read_text()
    (tests / "test_cases.py").write_text(
        source.replace("assert True", "assert False", 1)
    )
    result, report = run("daily", "tests")
    assert result.returncode == 1
    assert report["status"] == "failed"
    (tests / "test_cases.py").write_text(source)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "tests": []})
    )
    result, _ = run("ci", "tests")
    assert result.returncode != 0
    assert "Unmanifested generated_artifact test" in result.stderr
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tests / "test_broken.py").write_text(
        "raise RuntimeError('collection failed')\n", encoding="utf-8"
    )
    result, report = run("ci", "tests")
    assert result.returncode != 0
    assert not proven_deferral(report, result.returncode, {node})


def test_committed_generated_artifact_commands_pass_argv_guard() -> None:
    from scripts.engineering.ci import generated_artifact_checks as checks

    manifest = load_manifest()
    validate_selectors(manifest)
    files = sorted({row["node"].split("::", 1)[0] for row in manifest["tests"]})
    command = checks._pytest_command(
        "daily",
        ["-n", "0", "-q", "--tb=short", "--", *files],
    )
    assert "--artifact-selection=daily" in command
    assert all(path in command for path in files)
    for row in manifest["validators"]:
        if row["owner"] == "generated-artifact-daily":
            safe = ensure_safe_cli_argv([sys.executable, *row["argv"]])
            assert safe[0] == sys.executable
            assert safe[1:] == row["argv"]


def test_real_daily_caller_and_command_partition_are_complete() -> None:
    manifest = load_manifest()
    nightly = yaml.safe_load((ROOT / manifest["daily_workflow"]).read_text())
    assert nightly[True]["schedule"] == [{"cron": "0 3 * * *"}]
    assert "workflow_dispatch" in nightly[True]
    assert nightly["jobs"]["tests"]["with"]["generated-artifacts"] is True
    daily = nightly["jobs"]["generated-artifact-daily"]
    assert "needs" not in daily
    assert "if" not in daily
    assert "continue-on-error" not in daily
    commands = "\n".join(step.get("run", "") for step in daily["steps"])
    assert "daily --report" in commands and "validators --report" in commands
    assert "not slow" not in commands
    workflow = yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())
    assert (
        workflow[True]["workflow_call"]["inputs"]["generated-artifacts"]["default"]
        is False
    )
    conditional_steps = {
        (job_name, step["name"])
        for job_name, job in workflow["jobs"].items()
        for step in job.get("steps", [])
        if step.get("if") == "inputs.generated-artifacts"
    }
    assert conditional_steps == {
        (row["job"], row["step"])
        for row in manifest["validators"]
        if row["owner"] == "tests-nightly"
    }
    for row in manifest["validators"]:
        if row["owner"] == "tests-nightly":
            steps = workflow["jobs"][row["job"]]["steps"]
            step = next(step for step in steps if step.get("name") == row["step"])
            assert step["if"] == "inputs.generated-artifacts"
            assert step["run"] == row["command"]
    pr = (ROOT / ".github/workflows/pr-required.yml").read_text(encoding="utf-8")
    assert "BIOETL_ARTIFACT_TEST_SELECTION: ci" in pr
    # #12440 replaced the ci partition driver with the resilient runner.
    assert "scripts.engineering.ci.run_pytest_resilient" in pr
    assert "serial_or_bounded" not in pr
    assert '--parallel-marker "not serial"' in pr
    assert '--serial-marker "serial"' in pr
    assert "--prove-artifact-deferral" in pr
    assert '--fallback-addopts "-p no:xdist -q --tb=line"' in pr
    assert "cov-fail-under" not in pr
    assert "exit 5" not in pr


def test_stale_manifest_selector_fails_before_subset_selection(tmp_path: Path) -> None:
    path = tmp_path / "tests/test_removed.py"
    path.parent.mkdir()
    path.write_text("def test_source(): pass\n", encoding="utf-8")
    manifest = {"tests": [{"node": "tests/test_removed.py::test_old"}]}
    with pytest.raises(ValueError, match="Stale artifact manifest selector"):
        validate_selectors(manifest, tmp_path)


def test_docs_partition_keeps_source_checks_and_defers_only_generated_outputs(
    monkeypatch,
) -> None:
    from scripts.docs.checks import verify

    labels = []
    monkeypatch.setattr(
        verify, "_run_step", lambda label, argv: labels.append(label) or 0
    )
    assert verify.main(["--skip-build", "--defer-generated-artifacts"]) == 0
    assert labels == ["check-links", "check-drift", "check-docstrings"]
    labels.clear()
    assert verify.main(["--skip-build"]) == 0
    assert {
        "generate-dashboard-panel-inventory",
        "generate-cleanup-inventory",
        "generate-pipeline-normalization-matrix",
    } <= set(labels)


def test_daily_validator_failures_survive_and_do_not_suppress_remaining_checks(
    monkeypatch, tmp_path: Path
) -> None:
    from types import SimpleNamespace
    from scripts.engineering.ci import generated_artifact_checks as checks

    manifest = {
        "tests": [{"node": "tests/test_a.py::test_a"}],
        "validators": [
            {"id": "bad", "owner": "generated-artifact-daily", "argv": ["bad"]},
            {"id": "good", "owner": "generated-artifact-daily", "argv": ["good"]},
        ],
    }
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=1 if command[-1] == "bad" else 0)

    monkeypatch.setattr(checks, "load_manifest", lambda: manifest)
    monkeypatch.setattr(checks.subprocess, "run", run)
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    report = tmp_path / "reports/quality/generated-artifact-daily-validators.json"
    assert checks.main(["validators", "--report", str(report)]) == 1
    assert len(commands) == 2
    assert [row["exit_code"] for row in json.loads(report.read_text())] == [1, 0]


def test_source_governance_fetch_is_unconditional_and_precedes_both_modes():
    workflow = yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())
    steps = workflow["jobs"]["governance-preflight"]["steps"]
    checkout = next(step for step in steps if step["name"] == "Checkout code")
    assert checkout["with"]["fetch-depth"] == 0
    fetch = next(
        step
        for step in steps
        if step["name"] == "Prepare source-governance comparison baseline"
    )
    assert "if" not in fetch and "--depth" not in fetch["run"]
    assert "main:refs/remotes/origin/main" in fetch["run"]
    source = next(
        step
        for step in steps
        if step["name"] == "Validate debt-governance fail-fast gates"
    )
    daily = next(
        step
        for step in steps
        if step["name"] == "Validate full debt-governance generated evidence"
    )
    assert steps.index(fetch) < steps.index(source) < steps.index(daily)
    assert "if" not in source and "--source-only" in source["run"]
    assert (
        daily["if"] == "inputs.generated-artifacts"
        and "--source-only" not in daily["run"]
    )


def test_missing_comparison_ref_fails_instead_of_empty_changed_paths(tmp_path):
    from scripts.engineering.qa.debt_governance_gate_evaluators import (
        _collect_changed_paths,
    )

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    with pytest.raises(ValueError, match="Cannot collect changed paths"):
        _collect_changed_paths(tmp_path, changed_from_ref="refs/remotes/origin/main")


@pytest.mark.parametrize(
    "failure",
    [
        "debt_scorecard_budget_no_growth",
        "production_uuid4_seams",
        "dq_contract_registry_blocking_drift",
        "scripts_review_expiry_ratchet",
    ],
)
def test_source_debt_failures_survive_without_generated_inputs(monkeypatch, failure):
    from scripts.engineering.qa import report_debt_governance_gates as gates
    from scripts.engineering.qa import debt_governance_gate_report as cli
    from scripts.engineering.qa import debt_governance_gate_evaluators as evaluators

    def forbidden(*args, **kwargs):
        raise AssertionError("source mode read committed generated evidence")

    monkeypatch.setattr(gates, "_load_json", forbidden)
    monkeypatch.setattr(evaluators, "_load_json", forbidden)
    monkeypatch.setattr(
        gates, "_collect_changed_paths", lambda *a, **k: {"src/changed.py"}
    )
    monkeypatch.setattr(gates, "_debt_scorecard_gates", lambda: [])
    monkeypatch.setattr(
        gates,
        "_scripts_review_expiry_gate",
        lambda **k: gates.Gate(
            "scripts_review_expiry_ratchet",
            "fail" if failure == "scripts_review_expiry_ratchet" else "pass",
            "expired_review_by_count",
            2,
            1,
            "configs/quality/scripts_lifecycle_registry.json",
            "review",
        ),
    )
    monkeypatch.setattr(
        gates,
        "_debt_scorecard_budget_no_growth_gate",
        lambda **k: gates.Gate(
            "debt_scorecard_budget_no_growth",
            "fail" if failure == "debt_scorecard_budget_no_growth" else "pass",
            "count",
            1,
            0,
            "source",
            "fix",
        ),
    )
    monkeypatch.setattr(
        gates,
        "_load_yaml",
        lambda *a: {
            "policy": {"production_uuid4_budget": 0},
            "seams": ["bad"] if failure == "production_uuid4_seams" else [],
        },
    )
    monkeypatch.setattr(
        gates,
        "build_contract_registry_dq_diagnostics",
        lambda *a: {
            "blocking_issue_count": int(
                failure == "dq_contract_registry_blocking_drift"
            )
        },
    )
    payload = gates.build_source_payload(repo_root=ROOT, changed_from_ref="origin/main")
    assert payload["summary"]["failing_gates"] == [failure]
    assert (
        cli.main(["--source-only", "--check", "--changed-from-ref", "origin/main"]) == 1
    )
    with pytest.raises(SystemExit):
        gates._parse_args(["--source-only", "--check"])


def test_ordinary_observability_inventory_does_not_read_generated_reports(monkeypatch):
    from scripts.engineering.qa import (
        report_observability_metric_inventory as inventory,
    )

    original = Path.read_text

    def guarded(path, *args, **kwargs):
        if path.is_relative_to(ROOT / "reports"):
            raise AssertionError(
                f"ordinary metric inventory read generated report: {path}"
            )
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded)
    inventory._METRIC_INVENTORY_CACHE.clear()
    report = inventory.collect_metric_inventory(ROOT)
    assert report is not None
    workflow = yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())
    commands = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "report-observability-metric-inventory" in step.get("run", "")
    ]
    assert commands
    assert all("--typed-observability-views" not in command for command in commands)


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX bash/shebang receipt fixture"
)
@pytest.mark.parametrize("generated,scope", [("false", "source"), ("true", "full")])
def test_debt_receipt_records_executed_command_and_scope(tmp_path, generated, scope):
    import os

    workflow = yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())
    step = next(
        s
        for s in workflow["jobs"]["proof-or-stop-advisory"]["steps"]
        if s["name"] == "Normalize required producer receipts"
    )
    assert (
        step["env"]["DEBT_GENERATED_ARTIFACTS"] == "${{ inputs.generated-artifacts }}"
    )
    log = tmp_path / "calls.jsonl"
    uv = tmp_path / "uv"
    uv.write_text(
        f'#!{sys.executable}\nimport json,sys\nwith open({str(log)!r}, "a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n'
    )
    uv.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "DEBT_GENERATED_ARTIFACTS": generated,
        "GOVERNANCE_RESULT": "success",
        "QUALITY_RESULT": "success",
        "TEST_RESULTS": "success",
        "DOCS_RUNTIME_RC": "0",
        "PROOF_OR_STOP_RUN_ID": "run",
        "PROOF_OR_STOP_TASK_ID": "task",
        "PROOF_OR_STOP_CLAIM": "tested",
        "PROOF_OR_STOP_TRUST_TIER": "ci",
        "PROOF_OR_STOP_CI_RUN_ID": "123",
        "GITHUB_JOB": "proof",
    }
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    receipt = next(
        argv
        for argv in calls
        if argv[argv.index("--producer") + 1] == "debt_governance_gates"
    )
    command = receipt[receipt.index("--command") + 1]
    target_name = (
        "Validate debt-governance fail-fast gates"
        if scope == "source"
        else "Validate full debt-governance generated evidence"
    )
    executed = next(
        s["run"]
        for s in workflow["jobs"]["governance-preflight"]["steps"]
        if s["name"] == target_name
    )
    assert executed == "uv run --frozen --no-build " + command
    assert (
        receipt[receipt.index("--receipt-id") + 1]
        == f"debt_governance_gates-proof-{scope}"
    )
    assert ("--source-only" in command) == (scope == "source")


@pytest.mark.parametrize("mode", ["ci", "daily", "validators"])
@pytest.mark.parametrize(
    "attack", ["outside", "traversal", "wrong_name", "file_link", "parent_link"]
)
def test_runner_rejects_report_escape_before_any_effect(
    tmp_path, monkeypatch, mode, attack
):
    from scripts.engineering.ci import generated_artifact_checks as checks

    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "victim.json"
    outside.write_text("preserve")
    monkeypatch.setattr(checks, "ROOT", root)
    expected = root / "reports/quality" / checks.REPORT_NAMES[mode]
    expected.parent.mkdir(parents=True)
    supplied = expected
    if attack == "outside":
        supplied = outside
    elif attack == "traversal":
        supplied = root / "reports/quality/../../victim.json"
    elif attack == "wrong_name":
        supplied = expected.parent / "test-governance-current.json"
        supplied.write_text("preserve")
    elif attack == "file_link":
        _symlink_or_skip(expected, outside)
    else:
        expected.parent.rmdir()
        _symlink_or_skip(expected.parent, tmp_path, directory=True)
    monkeypatch.setattr(
        checks.subprocess,
        "run",
        lambda *a, **k: pytest.fail("subprocess before validation"),
    )
    with pytest.raises(SystemExit):
        checks.main([mode, "--report", str(supplied)])
    assert outside.read_text() == "preserve"
    if attack == "wrong_name":
        assert supplied.read_text() == "preserve"


@pytest.mark.parametrize(
    "option",
    [
        "-p",
        "-c",
        "--override-ini",
        "--rootdir",
        "--basetemp",
        "--junitxml",
        "--artifact-selection",
        "--report",
    ],
)
def test_runner_rejects_pytest_option_injection_before_deleting_report(
    tmp_path, monkeypatch, option
):
    from scripts.engineering.ci import generated_artifact_checks as checks

    monkeypatch.setattr(checks, "ROOT", tmp_path)
    (tmp_path / "tests").mkdir()
    report = tmp_path / "reports/quality/affected-test-partition.json"
    report.parent.mkdir(parents=True)
    report.write_text("old proof")
    monkeypatch.setattr(
        checks.subprocess,
        "run",
        lambda *a, **k: pytest.fail("injected command executed"),
    )
    with pytest.raises(SystemExit):
        checks.main(["ci", "--report", str(report), "--", "tests", option, "evil"])
    assert report.read_text() == "old proof"


@pytest.mark.parametrize("token", [";", "|", "&", ">", "<", "`", "$"])
def test_runner_rejects_shell_metacharacters_without_creating_targets(
    tmp_path, monkeypatch, token
):
    from scripts.engineering.ci import generated_artifact_checks as checks

    monkeypatch.setattr(checks, "ROOT", tmp_path)
    (tmp_path / "tests").mkdir()
    report = tmp_path / "reports/quality/affected-test-partition.json"
    report.parent.mkdir(parents=True)
    report.write_text("old proof")
    unsafe_name = f"bad{token}name.py"

    def reject_unsafe(method):
        def wrapped(self, *args, **kwargs):
            if self.name == unsafe_name:
                raise AssertionError(f"filesystem probe of unsafe target: {self.name}")
            return method(self, *args, **kwargs)

        return wrapped

    monkeypatch.setattr(Path, "exists", reject_unsafe(Path.exists))
    monkeypatch.setattr(Path, "is_symlink", reject_unsafe(Path.is_symlink))
    monkeypatch.setattr(Path, "resolve", reject_unsafe(Path.resolve))
    monkeypatch.setattr(
        checks.subprocess,
        "run",
        lambda *a, **k: pytest.fail("metacharacter command executed"),
    )
    with pytest.raises(SystemExit):
        checks.main(["ci", "--report", str(report), "--", f"tests/{unsafe_name}"])
    assert report.read_text() == "old proof"
    assert list((tmp_path / "tests").iterdir()) == []


def test_runner_keeps_targets_and_exit_codes_with_fixed_options(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts.engineering.ci import generated_artifact_checks as checks

    monkeypatch.setattr(checks, "ROOT", tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_cases.py").write_text("")
    target = "tests/test_cases.py::TestCases::test_source[value with spaces]"
    report = tmp_path / "reports/quality/affected-test-partition.json"
    report.parent.mkdir(parents=True)
    report.write_text("stale proof")
    commands = []

    def run(command, **kwargs):
        assert not report.exists()
        commands.append(command)
        return SimpleNamespace(returncode=5)

    monkeypatch.setattr(checks.subprocess, "run", run)
    assert (
        checks.main(["ci", "--report", str(report), "--", target, "-q", "--tb=line"])
        == 5
    )
    assert commands[0][-2:] == ["--", target]
    assert "-q" in commands[0] and "--tb=line" in commands[0]
    for target in ("../tests", "/tmp/tests", "@args.txt"):
        with pytest.raises(ValueError):
            checks.ci_pytest_arguments([target])


def test_runner_rejects_symlink_test_target(tmp_path, monkeypatch):
    from scripts.engineering.ci import generated_artifact_checks as checks

    monkeypatch.setattr(checks, "ROOT", tmp_path)
    (tmp_path / "tests").mkdir()
    _symlink_or_skip(tmp_path / "tests/link.py", tmp_path / "outside.py")
    with pytest.raises(ValueError, match="Symlink"):
        checks.ci_pytest_arguments(["tests/link.py"])


def test_docs_verify_preserves_failure_and_build_exit_codes(monkeypatch):
    from scripts.docs.checks import verify

    labels = []

    def fail_drift(label, argv):
        labels.append(label)
        return 7 if label == "check-drift" else 0

    monkeypatch.setattr(verify, "_run_step", fail_drift)
    assert verify.main(["--skip-build", "--defer-generated-artifacts"]) == 7
    assert labels == ["check-links", "check-drift"]
    monkeypatch.setattr(
        verify, "_run_step", lambda label, argv: 9 if label == "strict-build" else 0
    )
    monkeypatch.setattr(verify, "_require_docs_extra", lambda: 2)
    assert verify.main([]) == 2
    monkeypatch.setattr(verify, "_require_docs_extra", lambda: 0)
    assert verify.main([]) == 9


def test_source_checks_and_coverage_selection_survive_daily_partition():
    nodes = {row["node"] for row in load_manifest()["tests"]}
    retained = {
        "test_arch_s4_s9_gates.py::test_s8_domain_framework_import_ratchet",
        "test_domain_aggregate_classification.py::test_retired_batch_split_modules_are_absent",
        "test_tech_debt_issues_5553_5558_closeout.py::test_issue_5554_interfaces_do_not_import_control_plane_facade",
        "test_tech_debt_issues_6159_6169_closeout.py::test_issue_6163_live_source_hotspot_is_reduced",
        "test_public_surface_importer_census_governance.py::test_touched_twin_family_files_do_not_grow_private_imports",
    }
    for relative in retained:
        node = f"tests/architecture/{relative}"
        assert node not in nodes
        path, name = node.split("::")
        function = next(
            n
            for n in ast.parse((ROOT / path).read_text()).body
            if getattr(n, "name", None) == name
        )
        assert "pytest.mark.generated_artifact" not in {
            ast.unparse(d) for d in function.decorator_list
        }
    workflow = yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())
    assert workflow["env"]["BIOETL_ARTIFACT_TEST_SELECTION"] == "ci"
    for job in workflow["jobs"].values():
        assert "BIOETL_ARTIFACT_TEST_SELECTION" not in job.get("env", {})
        for step in job.get("steps", []):
            assert "BIOETL_ARTIFACT_TEST_SELECTION" not in step.get("env", {})
    steps = workflow["jobs"]["governance-preflight"]["steps"]
    baseline = next(
        i
        for i, step in enumerate(steps)
        if step["name"] == "Prepare source-governance comparison baseline"
    )
    twin = next(
        i
        for i, step in enumerate(steps)
        if "test_public_surface_importer_census_governance.py" in step.get("run", "")
    )
    assert baseline < twin
    inventory = next(
        s
        for s in steps
        if s["name"] == "Validate scripts inventory + lifecycle governance"
    )
    assert "--check" not in inventory["run"].split()
    daily = next(
        row for row in load_manifest()["validators"] if row["id"] == "scripts-inventory"
    )
    assert "--check" in daily["argv"]
    pr = yaml.safe_load(
        (ROOT / ".github/workflows/pr-required.yml").read_text(encoding="utf-8")
    )
    commands = [
        step.get("run", "")
        for job in pr["jobs"].values()
        for step in job.get("steps", [])
    ]
    assert any(
        "python -m scripts.docs passports check-source" in command
        for command in commands
    )


@pytest.mark.parametrize("new_importer", [False, True])
def test_twin_source_census_compares_base_ref_without_generated_reports(
    tmp_path, monkeypatch, new_importer
):
    from tests.architecture import (
        test_public_surface_importer_census_governance as gate,
    )

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "--initial-branch=main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Fixture")
    package = tmp_path / "src/bioetl/core"
    package.mkdir(parents=True)
    for name in ("__init__", "helper", "_helper"):
        (package / f"{name}.py").write_text("")
    (package.parent / "__init__.py").write_text("")
    git("add", ".")
    git("commit", "-m", "fixture base")
    git("checkout", "-b", "change")
    family = {
        "family_id": "fixture",
        "public_module": "bioetl.core.helper",
        "private_module": "bioetl.core._helper",
        "max_public_src_importers": 2,
        "max_private_src_importers": 2,
    }
    config = tmp_path / "ratchet.yaml"
    config.write_text(yaml.safe_dump({"families": [family]}))
    (package / "consumer.py").write_text(
        "import bioetl.core._helper\n" if new_importer else "value = 1\n"
    )
    git("add", ".")
    git("commit", "-m", "fixture change")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "TWIN_RATCHET", config)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    if new_importer:
        with pytest.raises(AssertionError, match="private src importers grew"):
            gate.test_touched_twin_family_files_do_not_grow_private_imports()
    else:
        gate.test_touched_twin_family_files_do_not_grow_private_imports()


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_twin_source_base_uses_event_commit_and_rejects_missing_base(
    tmp_path, monkeypatch, event
):
    from tests.architecture import (
        test_public_surface_importer_census_governance as gate,
    )

    payload = (
        {"before": "abc", "pull_request": {"base": {"sha": "abc"}}}
        if event == "pull_request"
        else {"before": "abc"}
    )
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    monkeypatch.setattr(
        gate, "_git_command", lambda *a: subprocess.CompletedProcess([], 0, "abc\n", "")
    )
    assert gate._resolve_merge_base(tmp_path) == "abc"
    monkeypatch.setattr(
        gate,
        "_git_command",
        lambda *a: subprocess.CompletedProcess([], 1, "", "missing"),
    )
    with pytest.raises(AssertionError, match="base commit is unavailable"):
        gate._resolve_merge_base(tmp_path)


@pytest.mark.parametrize(
    "value", ["unknown", "short --rootdir=/tmp", "-p", "", "short\n-p"]
)
def test_unknown_traceback_format_fails_before_any_effect(tmp_path, monkeypatch, value):
    from scripts.engineering.ci import generated_artifact_checks as checks

    monkeypatch.setattr(checks, "ROOT", tmp_path)
    (tmp_path / "tests").mkdir()
    report = tmp_path / "reports/quality/affected-test-partition.json"
    report.parent.mkdir(parents=True)
    report.write_text("preserve")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: pytest.fail("invalid tb executed")
    )
    with pytest.raises(ValueError, match="Unsupported pytest traceback"):
        checks.traceback_option(value)
    with pytest.raises(SystemExit):
        checks.main(["ci", "--report", str(report), "--", "tests", f"--tb={value}"])
    assert report.read_text() == "preserve"


@pytest.mark.parametrize("value", ["line", "short", "long", "auto", "native", "no"])
def test_traceback_formats_emit_closed_literal_options(value):
    from scripts.engineering.ci import generated_artifact_checks as checks

    assert checks.traceback_option(value) == "--tb=" + value


@pytest.mark.parametrize(
    "failure", ["unsupported", "windows_privilege", "not_implemented", "disk_full"]
)
def test_symlink_setup_skips_only_unsupported_creation(tmp_path, monkeypatch, failure):
    error = {
        "unsupported": OSError(errno.ENOTSUP, "unsupported"),
        "windows_privilege": OSError(errno.EPERM, "privilege not held"),
        "not_implemented": NotImplementedError("symlinks"),
        "disk_full": OSError(errno.ENOSPC, "disk full"),
    }[failure]
    if failure == "windows_privilege":
        error.winerror = 1314

    def create(*args, **kwargs):
        raise error

    monkeypatch.setattr(Path, "symlink_to", create)
    expected = OSError if failure == "disk_full" else pytest.skip.Exception
    with pytest.raises(expected):
        _symlink_or_skip(tmp_path / "link", tmp_path / "target")


def _runner_pass_result(name: str, return_code: int, tmp_path: Path):
    from scripts.engineering.ci.run_pytest_resilient import PassResult

    return PassResult(
        name=name,
        command=["pytest", name],
        return_code=return_code,
        output="",
        junit_path=tmp_path / f"junit_{name}.xml",
        log_path=tmp_path / f"{name}.log",
        failed_nodeids=[],
        worker_crash_detected=False,
        timed_out=False,
    )


def test_proven_deferral_requires_a_complete_selection_report(tmp_path, monkeypatch):
    from scripts.engineering.ci import run_pytest_resilient as runner

    node = "tests/test_a.py::test_a"
    payload = {
        "status": "deferred-to-daily",
        "selection": "ci",
        "pytest_exit_code": 5,
        "collection_errors": 0,
        "collected": [node],
        "deferred": [node],
        "selected": [],
        "other_deselected": [],
    }
    report = tmp_path / "artifact-selection-parallel.json"
    report.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.engineering.dev.pytest_artifact_selection.load_manifest",
        lambda: {"tests": [{"node": node}]},
    )
    result = _runner_pass_result("parallel", 5, tmp_path)
    assert runner._pass_is_proven_deferral(result, report)
    assert not runner._pass_is_proven_deferral(result, None)
    assert not runner._pass_is_proven_deferral(
        _runner_pass_result("parallel", 1, tmp_path), report
    )
    report.write_text(json.dumps({**payload, "selected": [node]}), encoding="utf-8")
    assert not runner._pass_is_proven_deferral(result, report)


def test_runner_runs_serial_marker_and_accepts_only_proven_deferral(
    tmp_path, monkeypatch
):
    from scripts.engineering.ci import run_pytest_resilient as runner

    calls: list[tuple[str, list[str]]] = []
    plan: dict[str, tuple[int, bool]] = {}

    def fake_run_pass(*, name, addopts=None, **kwargs):
        calls.append((name, list(addopts or [])))
        return_code, _proven = plan[name]
        return _runner_pass_result(name, return_code, tmp_path)

    def fake_proven(result, report):
        return plan[result.name][1]

    monkeypatch.setattr(runner, "_run_pass", fake_run_pass)
    monkeypatch.setattr(runner, "_pass_is_proven_deferral", fake_proven)

    def run(extra: list[str], outcomes: dict[str, tuple[int, bool]]):
        calls.clear()
        plan.clear()
        plan.update(outcomes)
        args = runner._create_parser().parse_args(
            [
                "--target",
                "tests/example.py",
                "--reports-dir",
                str(tmp_path / "reports"),
                *extra,
            ]
        )
        return runner._execute_passes(args), list(calls)

    code, seen = run([], {"parallel": (5, False), "serial": (0, False)})
    assert code == 0
    assert [name for name, _args in seen] == ["parallel", "serial"]
    assert not any(arg.startswith("--artifact-selection-report=") for arg in seen[0][1])

    code, seen = run(
        ["--no-fallback"],
        {"parallel": (1, False)},
    )
    assert code == 1
    assert [name for name, _args in seen] == ["parallel"]

    code, seen = run([], {"parallel": (5, False), "serial": (5, False)})
    assert code == 5
    assert [name for name, _args in seen] == ["parallel", "serial"]

    code, seen = run(
        ["--prove-artifact-deferral"],
        {
            "parallel": (5, False),
            "serial": (5, False),
            "deferral-proof": (5, True),
        },
    )
    assert code == 0
    assert [name for name, _args in seen] == ["parallel", "serial", "deferral-proof"]
    assert all(
        args is not None
        and any(arg.startswith("--artifact-selection-report=") for arg in args)
        for _name, args in seen
    )

    code, seen = run(
        ["--prove-artifact-deferral"],
        {
            "parallel": (5, False),
            "serial": (5, False),
            "deferral-proof": (5, False),
        },
    )
    assert code == 5
    assert [name for name, _args in seen] == ["parallel", "serial", "deferral-proof"]

    code, seen = run(
        ["--prove-artifact-deferral"],
        {"parallel": (5, True), "serial": (5, False)},
    )
    assert code == 0
    assert [name for name, _args in seen] == ["parallel", "serial"]

    code, seen = run(
        ["--prove-artifact-deferral"],
        {"parallel": (5, False), "serial": (5, True)},
    )
    assert code == 0
    assert [name for name, _args in seen] == ["parallel", "serial"]

    code, seen = run(
        ["--prove-artifact-deferral", "--skip-serial-pass"],
        {"parallel": (5, False)},
    )
    assert code == 5
    assert [name for name, _args in seen] == ["parallel"]
