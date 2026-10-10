"""Behavioral contracts for the isolated CircleCI migration preparation."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import sys

import pytest
import yaml

from scripts.engineering.ci.pr_gate import evaluate_results, load_catalog

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]


def _config():
    document = yaml.compose((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    _assert_unique_keys(document)
    return yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))


def _assert_unique_keys(node):
    """Do not silently accept YAML that CircleCI's compiler rejects."""
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for key, value in node.value:
            assert key.value not in seen, (
                f"Duplicate YAML key {key.value!r} at line {key.start_mark.line + 1}"
            )
            seen.add(key.value)
            _assert_unique_keys(value)
    elif isinstance(node, yaml.SequenceNode):
        for value in node.value:
            _assert_unique_keys(value)


def test_circleci_config_rejects_duplicate_nested_keys():
    document = yaml.compose(
        "jobs:\n  test:\n    environment: {}\n    environment: {}\n"
    )
    with pytest.raises(AssertionError, match="Duplicate YAML key 'environment'"):
        _assert_unique_keys(document)


def test_circleci_heredocs_escape_compiler_interpolation():
    source = (ROOT / ".circleci/config.yml").read_text(encoding="utf-8")
    assert not re.search(r"(?<!\\)<<[ \t]*['\"]", source)


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
            {
                "not": {
                    "equal": [
                        "scheduled_pipeline",
                        "<< pipeline.trigger_source >>",
                    ]
                }
            },
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
            {
                "not": {
                    "equal": [
                        "scheduled_pipeline",
                        "<< pipeline.trigger_source >>",
                    ]
                }
            },
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
    pytest_arguments = arguments[arguments.index("pytest") + 1 :]
    selector = pytest_arguments[pytest_arguments.index("-m") + 1]
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


def test_native_schedules_do_not_select_opt_in_lanes():
    config = _config()
    excluded = {
        "not": {"equal": ["scheduled_pipeline", "<< pipeline.trigger_source >>"]}
    }
    kept = {
        "pr-gate",
        "router-bridge-events",
        "retained-actions-online",
        "rf023-closeout",
    }
    for name, workflow in config["workflows"].items():
        if not isinstance(workflow, dict):
            continue
        when = workflow.get("when")
        if name in kept:
            assert "scheduled_pipeline" not in str(when)
            continue
        assert excluded in when["and"]


def test_mutation_preserves_targets_and_manual_main_backup():
    config = _config()
    workflow = config["workflows"]["mutation"]
    assert workflow["when"] == {
        "and": [
            {"equal": ["mutation", "<< pipeline.parameters.ci-lane >>"]},
            {"equal": ["main", "<< pipeline.git.branch >>"]},
            {
                "not": {
                    "equal": [
                        "scheduled_pipeline",
                        "<< pipeline.trigger_source >>",
                    ]
                }
            },
        ]
    }
    assert {"equal": ["scheduled_pipeline", "<< pipeline.trigger_source >>"]} not in (
        workflow["when"]["and"]
    )
    legacy = yaml.safe_load(
        (ROOT / ".github/workflows/mutation-testing.yml").read_text(encoding="utf-8")
    )["jobs"]["mutation-testing"]["strategy"]["matrix"]["target"]
    actual = [entry["mutation-testing"] for entry in workflow["jobs"]]
    assert len(actual) == len(legacy) == 4
    for old, new in zip(legacy, actual, strict=True):
        assert new["target"] == old["id"]
        assert new["source-path"] == old["paths_to_mutate"]
        # A replacement may include additional existing tests, never drop the legacy set.
        assert (ROOT / old["tests_dir"]).is_relative_to(ROOT / new["tests-dir"])
        assert new["threshold"] == old["threshold"]
    # Manual API backup stays available: the lane does not require a schedule.
    assert {"equal": ["schedule", "<< pipeline.trigger_source >>"]} not in (
        workflow["when"]["and"]
    )
    # Control-plane callers and regression tests also live outside its subdirectory.
    control_plane = next(
        job for job in actual if job["target"] == "application-control-plane"
    )
    selected_root = ROOT / control_plane["tests-dir"]
    for caller_test in (
        "tests/unit/application/services/test_run_manifest_service.py",
        "tests/unit/application/services/test_control_plane_service_seams.py",
        "tests/unit/application/test_issue_10469_stream_a_lt75_control_plane.py",
    ):
        assert (ROOT / caller_test).is_relative_to(selected_root)


@pytest.mark.parametrize(
    "stats,expected",
    [
        ({"killed": 6, "survived": 4, "timeout": 0}, 0),
        ({"killed": 5, "survived": 4, "timeout": 1}, 0),
        ({"killed": 5, "survived": 5, "timeout": 0}, 1),
        ({"killed": 0, "survived": 0, "timeout": 0}, 1),
        ({"killed": -1, "survived": 0, "timeout": 2}, 1),
        ({"killed": "invalid", "survived": 0, "timeout": 0}, 1),
        ({"killed": 1}, 1),
        (None, 1),
    ],
)
def test_mutation_score_rejects_invalid_missing_or_insufficient_evidence(
    tmp_path, monkeypatch, stats, expected
):
    import subprocess

    command = next(
        step["run"]["command"]
        for step in _config()["jobs"]["mutation-testing"]["steps"]
        if isinstance(step, dict)
        and step.get("run", {}).get("name") == "Check mutation score threshold"
    )
    script = command.split("python - \\<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
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


def test_relocated_router_verifiers_trigger_both_ci_event_filters():
    import fnmatch
    import shlex

    paths = (
        "scripts/ops/observability/grafana/router_rootfs.py",
        "scripts/ops/observability/grafana/router_managed_image.py",
        "scripts/ops/__main__.py",
        "tests/unit/scripts/ops/test_router_rootfs.py",
        "tests/unit/scripts/ops/test_router_managed_image.py",
    )
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/router-v7-bridge.yml").read_text(encoding="utf-8")
    )
    events = workflow.get("on", workflow.get(True))
    source = (ROOT / ".circleci/config.yml").read_text(encoding="utf-8")
    command = next(
        line.strip()
        for line in source.splitlines()
        if 'git diff --name-only "$base"...HEAD' in line
    )
    words = shlex.split(command)
    filters = words[words.index("--") + 1 : words.index(">")]
    assert "pull_request" not in events
    assert "push" not in events
    for path in paths:
        assert any(fnmatch.fnmatchcase(path, pattern) for pattern in filters), path
    assert not any(
        fnmatch.fnmatchcase("docs/unrelated.md", pattern) for pattern in filters
    )

    circle_commands = yaml.safe_load(source)["jobs"]["router-bridge-tests"]["steps"]
    circle_runs = "\n".join(
        step["run"]["command"]
        for step in circle_commands
        if isinstance(step, dict) and "run" in step
    )
    github_runs = "\n".join(
        step.get("run", "")
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
    )
    for test_name in ("test_router_rootfs.py", "test_router_managed_image.py"):
        invocation = f"/usr/bin/python3 ../../../tests/unit/scripts/ops/{test_name}"
        assert invocation in circle_runs
        assert invocation in github_runs


def test_pr_gate_credit_cut_keeps_required_job_names():
    config = _config()
    pr_gate_jobs = config["workflows"]["pr-gate"]["jobs"]
    integration = next(
        job["test-integration"]
        for job in pr_gate_jobs
        if isinstance(job, dict) and "test-integration" in job
    )
    assert integration["matrix"]["parameters"]["test-group"] == [
        "integration|tests/integration/|-n 2",
        "security|tests/security/|-n auto --dist loadscope",
    ]
    fast = next(
        job["test-fast"]
        for job in pr_gate_jobs
        if isinstance(job, dict) and "test-fast" in job
    )
    assert [
        item.split("|", 1)[0] for item in fast["matrix"]["parameters"]["test-group"]
    ] == [
        "unit-domain",
        "unit-application",
        "unit-infrastructure",
        "unit-other",
    ]
    event_names = [
        next(iter(job)) if isinstance(job, dict) else job
        for job in config["workflows"]["router-bridge-events"]["jobs"]
    ]
    assert event_names == ["router-bridge-tests", "router-plugin-tests"]
    bridge_names = [
        next(iter(job)) if isinstance(job, dict) else job
        for job in config["workflows"]["router-bridge"]["jobs"]
    ]
    assert "router-host-build" in bridge_names
    complete = next(
        job["pr-gate-complete"]["requires"]
        for job in pr_gate_jobs
        if isinstance(job, dict) and "pr-gate-complete" in job
    )
    for name in (
        "provider-contract-drift",
        "e2e-matrix-replay",
        "test-integration",
        "test-fast",
        "docs-diagram-syntax",
        "docs-diagram-targeted",
        "docs-diagram-drift",
    ):
        assert name in complete

    def keys(steps):
        return [next(iter(step)) if isinstance(step, dict) else step for step in steps]

    e2e_steps = config["jobs"]["e2e-matrix-replay"]["steps"]
    provider_steps = config["jobs"]["provider-contract-drift"]["steps"]
    e2e_keys = keys(e2e_steps)
    provider_keys = keys(provider_steps)
    assert e2e_keys.index("halt-unless-pr-gate-paths") < e2e_keys.index(
        "setup-python-uv"
    )
    assert provider_keys.index("halt-unless-pr-gate-paths") < provider_keys.index(
        "setup-python-uv"
    )
    e2e_halt = next(
        step["halt-unless-pr-gate-paths"]
        for step in e2e_steps
        if isinstance(step, dict) and "halt-unless-pr-gate-paths" in step
    )
    provider_halt = next(
        step["halt-unless-pr-gate-paths"]
        for step in provider_steps
        if isinstance(step, dict) and "halt-unless-pr-gate-paths" in step
    )
    assert "tests/e2e" in e2e_halt["pathspecs"]
    assert "tests/contract" in provider_halt["pathspecs"]

    def halt_params(job_name: str) -> dict[str, str]:
        steps = config["jobs"][job_name]["steps"]
        return next(
            step["halt-unless-pr-gate-paths"]
            for step in steps
            if isinstance(step, dict) and "halt-unless-pr-gate-paths" in step
        )

    for job_name in ("arch-tests", "duplication", "security-scans"):
        job_keys = keys(config["jobs"][job_name]["steps"])
        assert job_keys.index("halt-unless-pr-gate-paths") < job_keys.index(
            "setup-python-uv"
        )
    docker_keys = keys(config["jobs"]["docker-build"]["steps"])
    assert docker_keys.index("halt-unless-pr-gate-paths") < docker_keys.index(
        "check-gate"
    )
    assert docker_keys.index("halt-unless-pr-gate-paths") < docker_keys.index(
        "setup_remote_docker"
    )
    arch_paths = halt_params("arch-tests")["pathspecs"]
    assert "src/bioetl" in arch_paths
    assert "tests/architecture" in arch_paths
    assert "configs/**/*.yaml" in arch_paths
    assert ".circleci/config.yml" not in arch_paths
    duplication_paths = halt_params("duplication")["pathspecs"]
    assert ".jscpd.json" in duplication_paths
    assert "duplication_complexity_exemptions.yaml" in duplication_paths
    security_paths = halt_params("security-scans")["pathspecs"]
    assert "pyproject.toml" in security_paths
    assert ".gitleaks.toml" in security_paths
    assert ".secrets.baseline" in security_paths
    docker_paths = halt_params("docker-build")["pathspecs"]
    assert "Dockerfile.bioetl" in docker_paths
    assert "docker.yml" in docker_paths
    for name in ("arch-tests", "duplication", "security-scans", "docker-build"):
        assert name in complete
    docs_steps = config["jobs"]["docs-diagrams"]["steps"]
    classify_at = next(
        index
        for index, step in enumerate(docs_steps)
        if isinstance(step, dict)
        and step.get("run", {}).get("name", "").startswith("Classify diagram")
    )
    assert keys(docs_steps).index("setup-python-uv") > classify_at
    assert "uv run" not in docs_steps[classify_at]["run"]["command"]
    halt_run = config["commands"]["halt-unless-pr-gate-paths"]["steps"][0]["run"]
    halt = halt_run["command"]
    assert '!= "pr-gate"' in halt
    assert "circleci-agent step halt" in halt
    assert (
        halt_run["environment"]["BIOETL_HALT_PATHSPECS"] == "<< parameters.pathspecs >>"
    )
    assert "<< parameters.pathspecs >>" not in halt
    assert '"${pathspec_args[@]}"' in halt
