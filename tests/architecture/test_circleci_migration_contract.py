"""Behavioral contracts for the isolated CircleCI migration preparation."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys

import pytest
import yaml

from scripts.engineering.ci.pr_gate import evaluate_results, load_catalog

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]


def _config():
    return yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))


def _default_branch_matrix(monkeypatch):
    steps = _config()["jobs"]["classify"]["steps"]
    command = next(
        step["run"]["command"]
        for step in steps
        if isinstance(step, dict) and "run" in step
    )
    script = command.split("import json, sys", 1)[1].split("EOF", 1)[0]
    script = "import json, sys" + script
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(sys, "argv", ["classifier", "a" * 40])
    output = StringIO()
    with redirect_stdout(output):
        exec(compile(script, "circleci-default-branch", "exec"), {})
    return json.loads(output.getvalue())


def test_default_branch_matrix_uses_catalog_without_codeql(monkeypatch):
    matrix = _default_branch_matrix(monkeypatch)
    catalog = load_catalog(ROOT / "configs/quality/github_required_checks.yaml")
    assert set(matrix["decisions"]) == {gate["id"] for gate in catalog["gates"]}
    assert "codeql" not in matrix["decisions"]
    assert matrix["config_version"] == catalog["version"]
    assert matrix["head_sha"] == "a" * 40
    assert all(row["decision"] == "required" for row in matrix["decisions"].values())


@pytest.mark.parametrize("state", ["failure", "cancelled", "skipped"])
def test_remaining_security_failure_blocks_aggregate(monkeypatch, state):
    matrix = _default_branch_matrix(monkeypatch)
    catalog = load_catalog(ROOT / "configs/quality/github_required_checks.yaml")
    results = {
        gate: {"required": "success", "not_applicable": "skipped"}
        for gate in matrix["decisions"]
    }
    assert (
        evaluate_results(
            catalog,
            matrix,
            results,
            expected_head_sha="a" * 40,
            observed_head_sha="a" * 40,
        )
        == []
    )
    results["security"]["required"] = state
    assert evaluate_results(
        catalog, matrix, results, expected_head_sha="a" * 40, observed_head_sha="a" * 40
    )


def test_legacy_coordinator_has_no_codeql_dependency():
    coordinator = yaml.safe_load(
        (ROOT / ".github/workflows/pr-required.yml").read_text(encoding="utf-8")
    )
    jobs = coordinator["jobs"]
    assert "codeql" not in jobs
    assert "codeql" not in jobs["classify-changes"]["outputs"]
    assert "codeql" not in jobs["pr-gate-complete"]["needs"]


def test_docs_kpi_is_opt_in_main_only_and_preserves_policy():
    config = _config()
    assert config["parameters"]["ci-lane"]["default"] == "pr-gate"
    workflows = config["workflows"]
    assert workflows["pr-gate"]["when"] == {
        "equal": ["pr-gate", "<< pipeline.parameters.ci-lane >>"]
    }
    docs = workflows["docs-kpi"]
    assert docs["when"] == {
        "and": [
            {"equal": ["docs-kpi", "<< pipeline.parameters.ci-lane >>"]},
            {"equal": ["main", "<< pipeline.git.branch >>"]},
        ]
    }
    assert docs["jobs"] == ["docs-kpi"]
    steps = config["jobs"]["docs-kpi"]["steps"]
    command = next(
        step["run"]["command"]
        for step in steps
        if isinstance(step, dict)
        and step.get("run", {}).get("name") == "Generate docs KPI report"
    )
    for required in [
        "--kpi-target-not-in-nav 120",
        "--hard-limit-not-in-nav 135",
        "--max-orphans 0",
        "--target-deadline 2026-12-31",
        "--fail-on-breach",
    ]:
        assert required in command
    assert any(
        step.get("store_artifacts", {}).get("path") == "reports/docs-kpi"
        for step in steps
        if isinstance(step, dict)
    )


def test_compose_placeholders_are_step_scoped_and_runtime_stays_strict():
    job = _config()["jobs"]["docker-build"]
    assert "environment" not in job
    validation = next(
        step["run"]
        for step in job["steps"]
        if isinstance(step, dict)
        and step.get("run", {}).get("name") == "docker compose config validation"
    )
    assert validation["environment"]["COMPOSE_DISABLE_ENV_FILE"] == "1"
    for key in [
        "NEO4J_PASSWORD",
        "GF_SECURITY_ADMIN_PASSWORD",
        "GF_RENDERING_RENDERER_TOKEN",
    ]:
        assert validation["environment"][key] == "ci-compose-validation-placeholder"
    assert "docker compose config --quiet" in validation["command"]
    assert (
        "docker compose -f docker-compose.monitoring.yml config --quiet"
        in validation["command"]
    )
    runtime = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    monitoring = (ROOT / "docker-compose.monitoring.yml").read_text(encoding="utf-8")
    assert "${NEO4J_PASSWORD:?" in runtime
    assert "${GF_SECURITY_ADMIN_PASSWORD:?" in monitoring
    assert "${GF_RENDERING_RENDERER_TOKEN:?" in monitoring
    for step in job["steps"]:
        if isinstance(step, dict) and "run" in step and step["run"] is not validation:
            assert "ci-compose-validation-placeholder" not in str(step)


@pytest.mark.parametrize(
    "lane",
    [
        "memory-retention",
        "performance",
        "replay-parity",
        "memory-freshness",
        "port-contracts",
        "skills-consistency",
        "github-settings-review",
    ],
)
def test_independent_lanes_are_opt_in_main_only(lane):
    config = _config()
    workflow = config["workflows"][lane]
    assert workflow["when"] == {
        "and": [
            {"equal": [lane, "<< pipeline.parameters.ci-lane >>"]},
            {"equal": ["main", "<< pipeline.git.branch >>"]},
        ]
    }
    assert len(workflow["jobs"]) == 1
    assert "docker-build" not in str(workflow["jobs"])
    assert "mutation" not in str(workflow["jobs"])
    assert "context" not in str(workflow["jobs"]) or lane == "github-settings-review"


def test_retention_and_skills_lanes_do_not_mutate_source():
    jobs = _config()["jobs"]
    for lane in ["memory-retention", "skills-consistency"]:
        commands = "\n".join(
            step["run"]["command"]
            for step in jobs[lane]["steps"]
            if isinstance(step, dict) and "run" in step
        )
        assert "--check" in commands
        assert "--sync" not in commands
        assert "git push" not in commands
    assert "prune --check --json" in str(jobs["memory-retention"])


def test_hypothesis_defaults_on_and_settings_context_is_separate():
    config = _config()
    assert config["parameters"]["include-hypothesis"]["default"] is True
    assert config["workflows"]["github-settings-review"]["jobs"] == [
        {"github-settings-review": {"context": "bioetl-github-read-only"}}
    ]


@pytest.mark.parametrize(
    ("markers", "selected"),
    [
        (set(), True),
        ({"architecture"}, True),
        ({"slow"}, False),
        ({"benchmark"}, False),
        ({"memory"}, False),
    ],
)
def test_architecture_selector_includes_ordinary_tests_and_excludes_heavy_ones(
    markers, selected
):
    import shlex
    from _pytest.mark.expression import Expression

    steps = _config()["jobs"]["arch-tests"]["steps"]
    command = next(
        step["run"]["command"]
        for step in steps
        if isinstance(step, dict) and "run" in step
    )
    arguments = shlex.split(command.replace("\\\n", " "))
    selector = arguments[arguments.index("-m") + 1]
    assert (
        Expression.compile(selector).evaluate(lambda name, **kwargs: name in markers)
        is selected
    )


def test_hotspot_report_dispatcher_accepts_cli_arguments():
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "scripts.engineering.qa", "report-hotspots", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--observations" in result.stdout


@pytest.mark.parametrize(
    "summary, expected",
    [
        ({"total": 1, "failed": 0}, 0),
        ({"total": 1, "failed": 1}, 1),
        ({"total": 0, "failed": 0}, 1),
        (None, 1),
    ],
)
def test_performance_gate_rejects_missing_empty_or_failing_evidence(
    tmp_path, summary, expected
):
    import shlex
    import subprocess

    steps = _config()["jobs"]["performance"]["steps"]
    command = next(
        step["run"]["command"]
        for step in steps
        if isinstance(step, dict)
        and step.get("run", {}).get("name")
        == "Reject missing or failing performance evidence"
    )
    arguments = shlex.split(command)
    script = arguments[arguments.index("-c") + 1]
    if summary is not None:
        path = tmp_path / "reports/performance/hotspot-degradation.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"summary": summary}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, capture_output=True, check=False
    )
    assert result.returncode == expected


@pytest.mark.parametrize("second, expected", [(b"same", 0), (b"changed", 1), (None, 1)])
def test_replay_checksums_reject_drift_and_empty_runs(tmp_path, second, expected):
    import shutil
    import subprocess

    bash = shutil.which("bash")
    if sys.platform == "win32":
        import os

        git_bash = (
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Git/bin/bash.exe"
        )
        bash = str(git_bash) if git_bash.is_file() else None
    if bash is None:
        pytest.skip("bash is required to execute the Linux CI checksum contract")
    roots = tmp_path / ".artifacts/nightly-replay"
    for lane in [
        "determinism/run1",
        "determinism/run2",
        "idempotency",
        "composite_resume",
    ]:
        (roots / lane).mkdir(parents=True)
    (roots / "determinism/run1/payload.json").write_bytes(b"same")
    if second is not None:
        (roots / "determinism/run2/payload.json").write_bytes(second)
    steps = _config()["jobs"]["replay-parity"]["steps"]
    command = next(
        step["run"]["command"]
        for step in steps
        if isinstance(step, dict)
        and step.get("run", {}).get("name")
        == "Compare nonempty replay checksum inventories"
    )
    result = subprocess.run(
        [bash, "-euo", "pipefail", "-c", command],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode == expected, result.stderr.decode(errors="replace")


def test_memory_freshness_preparation_does_not_get_write_context():
    job = _config()["jobs"]["memory-freshness"]
    assert "gh issue" not in str(job)
    assert "issues: write" not in str(job)
    assert "context" not in str(_config()["workflows"]["memory-freshness"])
