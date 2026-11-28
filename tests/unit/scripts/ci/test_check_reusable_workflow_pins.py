"""Pin-checker contract tests for the PR coordinator.

Placement is the scripts-tooling lane (`tests/unit/scripts/`). The checker is
repo-side consistency only: these tests keep that limit explicit.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.engineering.repo import check_github_actions_runtime_policy as pins

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
COORDINATOR = ROOT / ".github" / "workflows" / "pr-required.yml"
REGISTRY = ROOT / "configs" / "quality" / "reusable_action_pins.yaml"
CHECKER = (
    ROOT / "scripts" / "engineering" / "repo" / "check_github_actions_runtime_policy.py"
)
PIN_ARGS = ["--pr-required-pins"]
SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
OTHER = "0000000000000000000000000000000000000001"
BUMP = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
BASE_REF = "ref: ${{ github.event.pull_request.base.sha || github.sha }}"
REUSABLE = "SatoryKono/BioactivityDataAcquisition/.github/workflows/example.yml"


def _dump(path: Path, payload: object) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _registry(
    path: Path, action_path: str = "actions/checkout", sha: str = SHA
) -> None:
    _dump(path, {"pins": [{"path": action_path, "sha": sha}]})


def _step_workflow(path: Path, uses: object) -> None:
    _dump(path, {"jobs": {"test": {"steps": [{"uses": uses}]}}})


def _job_workflow(path: Path, uses: object) -> None:
    _dump(path, {"jobs": {"called": {"uses": uses}}})


def test_secret_expression_in_uses_is_not_logged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _step_workflow(workflow, "something/${{ secrets.TOKEN }}")

    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)

    captured = capsys.readouterr()
    assert "secrets." not in captured.err
    assert "TOKEN" not in captured.err
    assert "[redacted-diagnostic]" in captured.err


def test_verified_pin_bump_passes(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry, sha=BUMP)
    _step_workflow(workflow, f"actions/checkout@{BUMP}")
    assert pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_step_ref_retarget_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _step_workflow(workflow, f"actions/checkout@{OTHER}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_step_path_retarget_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _step_workflow(workflow, f"actions/upload-artifact@{SHA}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


@pytest.mark.parametrize("ref", ["v3", "main", "refs/heads/main"])
def test_tag_or_branch_ref_fails(tmp_path: Path, ref: str) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _step_workflow(workflow, f"actions/checkout@{ref}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_job_level_pin_bump_passes(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry, action_path=REUSABLE, sha=BUMP)
    _job_workflow(workflow, f"{REUSABLE}@{BUMP}")
    assert pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_job_level_ref_retarget_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry, action_path=REUSABLE, sha=SHA)
    _job_workflow(workflow, f"{REUSABLE}@{OTHER}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_job_level_path_retarget_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry, action_path=REUSABLE, sha=SHA)
    other = "SatoryKono/BioactivityDataAcquisition/.github/workflows/other.yml"
    _job_workflow(workflow, f"{other}@{SHA}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_job_level_branch_ref_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry, action_path=REUSABLE, sha=SHA)
    _job_workflow(workflow, f"{REUSABLE}@main")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_reusable_file_existence_is_not_trust(tmp_path: Path) -> None:
    workflow_file = tmp_path / ".github" / "workflows" / "example.yml"
    workflow_file.parent.mkdir(parents=True)
    workflow_file.write_text("name: example\n", encoding="utf-8")
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "caller.yaml"
    _registry(registry, action_path=REUSABLE, sha=SHA)
    _job_workflow(workflow, f"{REUSABLE}@{OTHER}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


@pytest.mark.parametrize(
    "uses",
    [
        "actions/checkout",
        "docker://alpine:3.20",
        1,
        None,
        {"path": "actions/checkout"},
        "  actions/checkout@" + SHA,
    ],
)
def test_malformed_step_uses_fail(tmp_path: Path, uses: object) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _step_workflow(workflow, uses)
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_empty_and_wrong_shape_yaml_fail(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    _registry(registry)
    empty = tmp_path / "empty.yaml"
    empty.write_text("\n", encoding="utf-8")
    listed = tmp_path / "list.yaml"
    listed.write_text("- just-a-list\n", encoding="utf-8")
    missing_jobs = tmp_path / "no-jobs.yaml"
    _dump(missing_jobs, {"name": "broken"})
    null_jobs = tmp_path / "null-jobs.yaml"
    null_jobs.write_text("jobs:\n", encoding="utf-8")
    null_steps = tmp_path / "null-steps.yaml"
    _dump(null_steps, {"jobs": {"test": {"steps": None}}})
    for path in (empty, listed, missing_jobs, null_jobs, null_steps):
        assert not pins.check_pins(registry, [path], repo_root=tmp_path)


def test_missing_paths_and_empty_workflow_list_fail(tmp_path: Path) -> None:
    missing_registry = tmp_path / "absent.yaml"
    workflow = tmp_path / "workflow.yaml"
    _step_workflow(workflow, f"actions/checkout@{SHA}")
    assert not pins.check_pins(missing_registry, [workflow], repo_root=tmp_path)
    registry = tmp_path / "registry.yaml"
    _registry(registry)
    assert not pins.check_pins(
        registry, [tmp_path / "missing.yaml"], repo_root=tmp_path
    )
    assert not pins.check_pins(registry, [], repo_root=tmp_path)


@pytest.mark.parametrize(
    "payload",
    [
        ["not-a-mapping"],
        {"pins": {"path": "actions/checkout"}},
        {"pins": ["not-a-mapping"]},
        {"pins": [{"sha": SHA}]},
        {"pins": [{"path": "actions/checkout", "sha": "v1"}]},
        {
            "pins": [
                {"path": "actions/checkout", "sha": SHA},
                {"path": "actions/checkout", "sha": OTHER},
            ]
        },
        {
            "pins": [
                {"path": "actions/checkout", "sha": SHA},
                {"path": "actions/checkout", "sha": SHA},
            ]
        },
    ],
)
def test_malformed_or_duplicate_registry_fails(tmp_path: Path, payload: object) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _dump(registry, payload)
    _step_workflow(workflow, f"actions/checkout@{SHA}")
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


def test_local_action_manifest_existence_does_not_bind_content(tmp_path: Path) -> None:
    action_dir = tmp_path / ".github" / "actions" / "demo"
    action_dir.mkdir(parents=True)
    manifest = action_dir / "action.yml"
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _step_workflow(workflow, "./.github/actions/demo")
    first = "name: one\nruns: {using: composite, steps: []}\n"
    second = "name: two\nruns: {using: composite, steps: []}\n"
    manifest.write_text(first, encoding="utf-8")
    assert pins.check_pins(registry, [workflow], repo_root=tmp_path)
    manifest.write_text(second, encoding="utf-8")
    assert pins.check_pins(registry, [workflow], repo_root=tmp_path)
    assert first != second


def test_local_action_yaml_suffix_passes_and_escape_fails(tmp_path: Path) -> None:
    action_dir = tmp_path / ".github" / "actions" / "demo"
    action_dir.mkdir(parents=True)
    (action_dir / "action.yaml").write_text("name: demo\n", encoding="utf-8")
    registry = tmp_path / "registry.yaml"
    allowed = tmp_path / "allowed.yaml"
    escaped = tmp_path / "escaped.yaml"
    outside = tmp_path / "outside.yaml"
    missing = tmp_path / "missing.yaml"
    _registry(registry)
    _step_workflow(allowed, "./.github/actions/demo")
    _step_workflow(escaped, "./.github/actions/../workflows/example.yml")
    _step_workflow(outside, "../.github/actions/demo")
    _step_workflow(missing, "./.github/actions/missing")
    assert pins.check_pins(registry, [allowed], repo_root=tmp_path)
    assert not pins.check_pins(registry, [escaped], repo_root=tmp_path)
    assert not pins.check_pins(registry, [outside], repo_root=tmp_path)
    assert not pins.check_pins(registry, [missing], repo_root=tmp_path)


DOCKER_LANE_PIN = (
    "SatoryKono/BioactivityDataAcquisition/.github/workflows/docker.yml"
    "@cfc518a21c94eba702157209946b38cd21a9ce7a"
)
DOCS_LANE_PIN = (
    "SatoryKono/BioactivityDataAcquisition/.github/workflows/docs.yml"
    "@cfc518a21c94eba702157209946b38cd21a9ce7a"
)


def test_current_coordinator_job_level_calls_match_registry() -> None:
    """Coordinator reusable calls stay pinned to registry SHAs (docker + docs)."""
    document = yaml.safe_load(COORDINATOR.read_text(encoding="utf-8"))
    jobs = document["jobs"]
    assert isinstance(jobs, dict)
    reusable = {
        name: str(job["uses"])
        for name, job in jobs.items()
        if isinstance(job, dict) and "uses" in job
    }
    assert reusable == {
        "docs-lane": DOCS_LANE_PIN,
        "docker-lane": DOCKER_LANE_PIN,
    }
    for name, job in jobs.items():
        assert isinstance(job, dict)
        if name in reusable:
            assert "steps" not in job, name
            continue
        assert "uses" not in job, name
        assert isinstance(job.get("steps"), list)
    assert pins.check_pins(
        REGISTRY,
        [COORDINATOR],
        repo_root=ROOT,
        enforce_allowed_uses=True,
    )


def test_registry_sha_outside_allowed_uses_fails(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry, sha=OTHER)
    _step_workflow(workflow, f"actions/checkout@{OTHER}")
    assert pins.check_pins(registry, [workflow], repo_root=tmp_path)
    assert not pins.check_pins(
        registry,
        [workflow],
        repo_root=tmp_path,
        enforce_allowed_uses=True,
    )


def test_osv_entry_point_does_not_import_yaml_at_module_scope() -> None:
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            assert "yaml" not in names
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "yaml"


def test_fast_governance_hosts_the_checker_after_setup() -> None:
    text = COORDINATOR.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    classify = document["jobs"]["classify-changes"]["steps"]
    fast = document["jobs"]["fast-governance"]["steps"]
    aggregate = document["jobs"]["pr-gate-complete"]["steps"]
    assert text.count(BASE_REF) == 2
    assert classify[0]["with"]["ref"] == (
        "${{ github.event.pull_request.base.sha || github.sha }}"
    )
    assert aggregate[0]["with"]["ref"] == (
        "${{ github.event.pull_request.base.sha || github.sha }}"
    )
    assert "ref" not in fast[0].get("with", {})
    names = [step.get("name") for step in fast]
    assert names.index("Set up Python + uv") < names.index(
        "Checkout default branch for pin gate"
    )
    assert names.index("Checkout default branch for pin gate") < names.index(
        "Check reusable workflow pins"
    )
    assert names.index("Check reusable workflow pins") < names.index(
        "Remove default-branch pin gate checkout"
    )
    assert names.index("Remove default-branch pin gate checkout") < names.index(
        "Validate repository root allowlist"
    )
    remove_gate = fast[names.index("Remove default-branch pin gate checkout")]
    assert remove_gate["if"] == "always()"
    assert "rm -rf" in remove_gate["run"]
    pin_gate = fast[names.index("Checkout default branch for pin gate")]
    assert pin_gate["with"]["persist-credentials"] is False
    assert pin_gate["with"]["fetch-depth"] == 1
    assert pin_gate["with"]["ref"] == "${{ github.event.repository.default_branch }}"
    assert pin_gate["with"]["path"] == ".gha-default-branch-pin-gate"
    assert pin_gate["with"]["sparse-checkout"] == "scripts/engineering/repo"
    assert pin_gate["with"]["sparse-checkout-cone-mode"] is True
    pin_step = fast[names.index("Check reusable workflow pins")]
    assert "${RUNNER_TEMP}/check_github_actions_runtime_policy.py" in pin_step["run"]
    assert ".gha-default-branch-pin-gate" in pin_step["run"]
    assert 'rm -rf "${gate}"' in pin_step["run"]
    assert "--pr-required-pins --check" in pin_step["run"]
    assert (
        "python scripts/engineering/repo/check_github_actions_runtime_policy.py"
        not in pin_step["run"]
    )
    assert "if" not in pin_step
    assert all(step.get("name") != "Check reusable workflow pins" for step in classify)


def test_disabled_pin_step_is_outside_the_checker(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    _registry(registry)
    _dump(
        workflow,
        {
            "jobs": {
                "fast-governance": {"steps": [{"uses": f"actions/checkout@{OTHER}"}]}
            }
        },
    )
    loaded = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    runs = [
        str(step.get("run", "")) for step in loaded["jobs"]["fast-governance"]["steps"]
    ]
    assert all("check_github_actions_runtime_policy.py" not in run for run in runs)
    assert not pins.check_pins(registry, [workflow], repo_root=tmp_path)


@pytest.mark.subprocess_backed
def test_same_named_and_simultaneous_substitution_are_not_enforcement(
    tmp_path: Path,
) -> None:
    hostile_sha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    registry = tmp_path / "registry.yaml"
    workflow = tmp_path / "workflow.yaml"
    substitute = tmp_path / "check_github_actions_runtime_policy.py"
    _dump(registry, {"pins": [{"path": "hostile/action", "sha": hostile_sha}]})
    _dump(
        workflow,
        {
            "jobs": {
                "fast-governance": {
                    "steps": [
                        {
                            "run": (
                                "python check_github_actions_runtime_policy.py "
                                "--pr-required-pins --check"
                            )
                        },
                        {"uses": f"hostile/action@{hostile_sha}"},
                    ]
                }
            }
        },
    )
    substitute.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    substituted = subprocess.run(
        [sys.executable, str(substitute)],
        check=False,
        cwd=tmp_path,
    )
    trusted = tmp_path / "trusted.yaml"
    _registry(trusted)
    assert substituted.returncode == 0
    assert not pins.check_pins(trusted, [workflow], repo_root=tmp_path)


@pytest.mark.subprocess_backed
def test_cli_exit_codes(tmp_path: Path) -> None:
    success = subprocess.run(
        [sys.executable, str(CHECKER), *PIN_ARGS, "--check"],
        check=False,
        cwd=ROOT,
    )
    failure = subprocess.run(
        [sys.executable, str(CHECKER), *PIN_ARGS, "--check"],
        check=False,
        cwd=tmp_path,
    )
    default_still_checks = subprocess.run(
        [sys.executable, str(CHECKER), *PIN_ARGS],
        check=False,
        cwd=tmp_path,
    )
    usage = subprocess.run(
        [sys.executable, str(CHECKER), *PIN_ARGS, "--nope"],
        check=False,
        cwd=ROOT,
    )
    assert success.returncode == 0
    assert failure.returncode == 1
    assert default_still_checks.returncode == 1
    assert usage.returncode == 2


@pytest.mark.subprocess_backed
def test_actual_pinned_docker_workflow_preserves_sarif_comparison() -> None:
    """Validate the called immutable workflow, not a newer unexecuted local file.

    This repo-backed Class-lane contract requires its existing full-history
    checkout. Git may lazily obtain the historical blob in a blob-filtered clone;
    it never changes a branch, index, worktree file, or remote ref.
    """
    caller = yaml.safe_load(COORDINATOR.read_text(encoding="utf-8"))
    uses = caller["jobs"]["docker-lane"]["uses"]
    path, revision = uses.rsplit("@", 1)
    assert path == (
        "SatoryKono/BioactivityDataAcquisition/.github/workflows/docker.yml"
    )
    assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision)
    result = subprocess.run(
        ["git", "show", f"{revision}:.github/workflows/docker.yml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, "Pinned workflow blob requires full Git history"
    pinned_workflow = yaml.safe_load(result.stdout)
    caller_permissions = caller["jobs"]["docker-lane"]["permissions"]
    permission_levels = {"none": 0, "read": 1, "write": 2}
    # GitHub validates every nested job, including skipped publish jobs.
    for job in pinned_workflow["jobs"].values():
        for scope, requested in job.get("permissions", {}).items():
            assert (
                permission_levels[requested]
                <= permission_levels[caller_permissions.get(scope, "none")]
            ), (scope, requested)
    steps = pinned_workflow["jobs"]["docker-build"]["steps"]
    uploads = [
        step
        for step in steps
        if str(step.get("uses", "")).startswith("github/codeql-action/upload-sarif@")
    ]
    assert len(uploads) == 3
    assert {step["with"].get("category") for step in uploads} == {
        ".github/workflows/docker.yml:docker-build",
        ".github/workflows/main-integrity.yml:docker-build",
        ".github/workflows/pr-required.yml:docker-build",
    }
    for step in uploads:
        assert step["with"]["sarif_file"] == "reports/security/trivy-results.sarif"
        assert step["with"]["wait-for-processing"] is True
        assert not step.get("continue-on-error", False)
