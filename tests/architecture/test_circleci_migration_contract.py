"""Contracts retained on the GitHub Actions side of the CI migration."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys

import pytest
import yaml

from scripts.engineering.ci.pr_gate import (
    classify_changes,
    evaluate_results,
    load_catalog,
)

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]


def _workflow(name):
    return yaml.safe_load(
        (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
    )


def _events(workflow):
    return workflow.get("on", workflow.get(True))


@pytest.mark.parametrize("state", ["failure", "cancelled", "skipped"])
def test_remaining_security_failure_blocks_aggregate(state):
    catalog = load_catalog(ROOT / "configs/quality/github_required_checks.yaml")
    matrix = classify_changes(catalog, [], head_sha="a" * 40)
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
    jobs = _workflow("pr-required.yml")["jobs"]
    assert "codeql" not in jobs
    assert "codeql" not in jobs["classify-changes"]["outputs"]
    assert "codeql" not in jobs["pr-gate-complete"]["needs"]


def test_docs_kpi_preserves_policy():
    workflow = _workflow("docs-kpi-weekly.yml")
    assert "workflow_dispatch" in _events(workflow)
    steps = workflow["jobs"]["docs-kpi"]["steps"]
    command = next(
        step["run"] for step in steps if step.get("name") == "Generate docs KPI report"
    )
    for required in (
        "--kpi-target-not-in-nav 120",
        "--hard-limit-not-in-nav 135",
        "--max-orphans 0",
        "--target-deadline 2026-12-31",
        "--fail-on-breach",
    ):
        assert required in command
    assert any(
        "reports/docs-kpi" in step.get("with", {}).get("path", "") for step in steps
    )


def test_compose_placeholders_are_step_scoped_and_runtime_stays_strict():
    job = _workflow("docker.yml")["jobs"]["docker-compose-validate"]
    assert "env" not in job
    steps = job["steps"]
    normal = next(
        step
        for step in steps
        if step.get("name") == "Validate docker-compose.yml syntax"
    )
    monitoring = next(
        step
        for step in steps
        if step.get("name") == "Validate docker-compose.monitoring.yml syntax"
    )
    assert "docker compose config" in normal["run"]
    assert "docker compose -f docker-compose.monitoring.yml config" in monitoring["run"]
    assert normal["env"]["NEO4J_PASSWORD"] == "ci-compose-validation-placeholder"
    for key in (
        "NEO4J_PASSWORD",
        "GF_SECURITY_ADMIN_PASSWORD",
        "GF_RENDERING_RENDERER_TOKEN",
    ):
        assert monitoring["env"][key] == "ci-compose-validation-placeholder"
    assert "${NEO4J_PASSWORD:?" in (ROOT / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    source = (ROOT / "docker-compose.monitoring.yml").read_text(encoding="utf-8")
    assert "${GF_SECURITY_ADMIN_PASSWORD:?" in source
    assert "${GF_RENDERING_RENDERER_TOKEN:?" in source
    for step in steps:
        if step is not normal and step is not monitoring:
            assert "ci-compose-validation-placeholder" not in str(step)


def test_retention_lane_does_not_mutate_source():
    steps = _workflow("memory-retention.yml")["jobs"]["check-retention-policy"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "prune --check --json" in commands
    assert "--sync" not in commands
    assert "git push" not in commands


@pytest.mark.parametrize(
    "markers, selected",
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
    from _pytest.mark.expression import Expression

    steps = _workflow("pr-required.yml")["jobs"]["class-lane"]["steps"]
    command = next(step["run"] for step in steps if step.get("id") == "arch-pytest")
    args = shlex.split(command)
    selector = args[args.index("--parallel-marker") + 1]
    assert (
        Expression.compile(selector).evaluate(lambda name, **kwargs: name in markers)
        is selected
    )


def test_hotspot_report_dispatcher_accepts_cli_arguments():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.engineering.qa", "report-hotspots", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--observations" in result.stdout


def test_performance_benchmark_loads_vcs_guard_first():
    nightly = (ROOT / ".github/workflows/performance-nightly.yml").read_text(
        encoding="utf-8"
    )
    command = nightly.split("BIOETL_BENCHMARK_CALLER=performance-nightly", 1)[1]
    assert command.index("-p tests.benchmarks.benchmark_vcs_guard") < command.index(
        "-p benchmark"
    )


def test_memory_freshness_preparation_does_not_get_write_context():
    job = _workflow("memory-freshness.yml")["jobs"]["freshness"]
    assert job["permissions"] == {"contents": "read"}
    assert "gh issue" not in str(job)


@pytest.mark.parametrize("second,expected", [(b"same", 0), (b"changed", 1), (None, 0)])
def test_replay_checksums_reject_drift(tmp_path, monkeypatch, second, expected):
    import shutil

    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash is required for the GitHub Actions checksum script")
    roots = tmp_path / ".artifacts/nightly-replay"
    for lane in (
        "determinism/run1",
        "determinism/run2",
        "idempotency",
        "composite_resume",
    ):
        (roots / lane).mkdir(parents=True)
    (roots / "determinism/run1/payload.json").write_bytes(b"same")
    if second is None:
        # The existing GitHub workflow accepts two empty inventories.
        (roots / "determinism/run1/payload.json").unlink()
    else:
        (roots / "determinism/run2/payload.json").write_bytes(second)
    steps = _workflow("nightly-replay-parity.yml")["jobs"]["replay-parity"]["steps"]
    command = next(
        step["run"] for step in steps if step.get("name") == "Replay parity checksums"
    )
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    result = subprocess.run(
        [bash, "-euo", "pipefail", "-c", command],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode == expected, result.stderr.decode(errors="replace")


def test_mutation_workflow_preserves_targets_and_manual_dispatch():
    workflow = _workflow("mutation-testing.yml")
    assert "workflow_dispatch" in _events(workflow)
    targets = workflow["jobs"]["mutation-testing"]["strategy"]["matrix"]["target"]
    assert {target["id"] for target in targets} == {
        "domain",
        "application-control-plane",
        "application-export-manifests",
        "application-workflow-runner",
    }
    assert all(
        (ROOT / target["paths_to_mutate"]).exists()
        and (ROOT / target["tests_dir"]).exists()
        for target in targets
    )


@pytest.mark.parametrize(
    "stats,expected",
    [
        ({"killed": 6, "survived": 4, "timeout": 0}, 0),
        ({"killed": 5, "survived": 4, "timeout": 1}, 0),
        ({"killed": 5, "survived": 5, "timeout": 0}, 1),
        ({"killed": 0, "survived": 0, "timeout": 0}, 1),
        # Unlike the retired CircleCI check, the existing workflow accepts this.
        ({"killed": -1, "survived": 0, "timeout": 2}, 0),
        ({"killed": "invalid", "survived": 0, "timeout": 0}, 1),
        ({"killed": 1}, 1),
        (None, 1),
    ],
)
def test_mutation_score_rejects_invalid_missing_or_insufficient_evidence(
    tmp_path, monkeypatch, stats, expected
):
    steps = _workflow("mutation-testing.yml")["jobs"]["mutation-testing"]["steps"]
    command = next(
        step["run"]
        for step in steps
        if step.get("name") == "Check mutation score threshold"
    )
    script = command.split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    monkeypatch.setenv("MUTATION_TARGET", "domain")
    monkeypatch.setenv("MUTATION_SCORE_THRESHOLD", "60.0")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    if stats is not None:
        path = tmp_path / "reports/domain/mutmut-cicd-stats.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(stats), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, capture_output=True, check=False
    )
    assert result.returncode == expected, result.stderr.decode(errors="replace")


def test_router_manual_workflow_runs_relocated_verifiers():
    workflow = _workflow("router-v7-bridge.yml")
    assert "workflow_dispatch" in _events(workflow)
    runs = "\n".join(
        step.get("run", "")
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
    )
    for name in (
        "test_router_rootfs.py",
        "test_router_managed_image.py",
        "test_router_candidate.py",
    ):
        assert f"/usr/bin/python3 ../../../tests/unit/scripts/ops/{name}" in runs


def test_workflow_map_describes_manual_only_performance():
    text = (ROOT / "docs/05-operations/ci-workflow-map.md").read_text(encoding="utf-8")
    assert "Performance is manual-only" in text
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| `performance-nightly.yml` | manual")
    )
    assert "workflow_dispatch" in row
    assert "CircleCI lane removed" in row
    triggers = _events(_workflow("performance-nightly.yml"))
    assert "workflow_dispatch" in triggers
    assert "schedule" not in triggers
