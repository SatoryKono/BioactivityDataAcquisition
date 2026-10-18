"""Partition completeness and fail-closed scheduling regressions."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from scripts.engineering.ci.generated_artifact_checks import proven_deferral
from scripts.engineering.dev.pytest_artifact_selection import (
    ROOT,
    load_manifest,
    validate_selectors,
)

pytestmark = pytest.mark.unit


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


def test_real_daily_caller_and_command_partition_are_complete() -> None:
    manifest = load_manifest()
    nightly = yaml.safe_load((ROOT / manifest["daily_workflow"]).read_text())
    assert nightly[True]["schedule"] == [{"cron": "0 3 * * *"}]
    assert nightly["jobs"]["tests"]["with"]["generated-artifacts"] is True
    daily = nightly["jobs"]["generated-artifact-daily"]
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
    pr = (ROOT / ".github/workflows/pr-required.yml").read_text()
    assert "BIOETL_ARTIFACT_TEST_SELECTION: ci" in pr
    assert "generated_artifact_checks ci" in pr
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
    report = tmp_path / "validators.json"
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
