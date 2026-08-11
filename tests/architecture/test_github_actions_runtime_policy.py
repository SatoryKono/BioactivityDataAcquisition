# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guardrails for GitHub Actions supply-chain policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from scripts.engineering.repo import check_github_actions_runtime_policy as policy

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "contract-tests.yml"
CODERABBIT_WORKFLOW = ROOT / ".github" / "workflows" / "coderabbit.yml"
NIGHTLY_REPLAY_WORKFLOW = ROOT / ".github" / "workflows" / "nightly-replay-parity.yml"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
GITHUB_POLICY = ROOT / "docs" / "00-project" / "governance" / "05-github-policy.md"
ALWAYS_ON_REQUIRED_CHECKS = {
    "checks-complete": ROOT / ".github" / "workflows" / "import-linter.yml",
    "root-hygiene": ROOT / ".github" / "workflows" / "root-hygiene.yml",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def test_runtime_policy_scans_workflows_and_composite_actions() -> None:
    scanned = {path.relative_to(ROOT).as_posix() for path in policy.iter_yaml_files()}

    assert ".github/workflows/contract-tests.yml" in scanned
    assert ".github/workflows/labeler.yml" in scanned
    assert ".github/actions/setup-python-uv/action.yml" in scanned


def test_runtime_policy_rejects_mutable_external_action_refs() -> None:
    violation = policy._validate_allowed_uses_ref(
        "actions/github-script@v7", "actions/github-script"
    )

    assert violation is not None
    assert "full 40-character SHA" in violation


def test_runtime_policy_parses_standard_step_uses_entries() -> None:
    parsed = policy._parsed_uses_reference("      - uses: actions/checkout@v4")

    assert parsed == ("actions/checkout@v4", "actions/checkout")


def test_repository_actions_refs_satisfy_runtime_policy() -> None:
    assert not policy._collect_uses_violations()


def test_github_policy_python_version_claims_match_workflows() -> None:
    tests_workflow = _load_yaml(TESTS_WORKFLOW)
    release_workflow = _load_yaml(RELEASE_WORKFLOW)
    test_matrix = tests_workflow["jobs"]["test-matrix"]["strategy"]["matrix"]
    release_matrix = release_workflow["jobs"]["test-install"]["strategy"]["matrix"]
    policy_doc = GITHUB_POLICY.read_text(encoding="utf-8")

    assert test_matrix["python-version"] == ["3.12"]
    assert len(test_matrix["test-group"]) == 6
    assert release_matrix["python-version"] == ["3.13"]
    assert "full test matrix (Python 3.12, 6 groups)" in policy_doc
    assert "Build and test on Python 3.13" in policy_doc
    assert "2. Test Install  → Python 3.13" in policy_doc


def test_ruleset_required_checks_materialize_on_every_pr() -> None:
    policy_doc = GITHUB_POLICY.read_text(encoding="utf-8")
    required_section = policy_doc.split(
        "### Final always-on required-check set", maxsplit=1
    )[1].split("### Path-scoped core checks", maxsplit=1)[0]

    for check_name, workflow_path in ALWAYS_ON_REQUIRED_CHECKS.items():
        workflow = _load_yaml(workflow_path)
        triggers = workflow.get("on", workflow.get(True))
        assert isinstance(triggers, dict)
        assert "pull_request" in triggers
        pull_request = triggers["pull_request"]
        assert pull_request is None or not {
            "paths",
            "paths-ignore",
        }.intersection(pull_request)
        assert check_name in workflow["jobs"]
        assert f"`{check_name}`" in required_section

    for path_scoped_check in (
        "coverage-verify",
        "schema-governance-status",
        "detect-secrets",
        "commit-lint",
        "type-check",
    ):
        assert f"`{path_scoped_check}`" not in required_section


def test_runtime_policy_rejects_mutable_docker_image_tags() -> None:
    violation = policy._validate_allowed_uses_ref(
        "docker://codiumai/pr-agent:latest",
        "docker://codiumai/pr-agent:latest",
    )

    assert violation is not None
    assert "immutable ref" in violation


def test_runtime_policy_accepts_approved_docker_image_digest() -> None:
    image = "docker://codiumai/pr-agent"
    digest = next(iter(policy.ALLOWED_DOCKER_IMAGES[image]))

    assert policy._validate_allowed_uses_ref(f"{image}@{digest}", image) is None


def test_runtime_policy_rejects_unrecognized_external_actions() -> None:
    violation = policy._validate_allowed_uses_ref(
        "example/action@0123456789abcdef0123456789abcdef01234567",
        "example/action",
    )

    assert violation is not None
    assert "unrecognized external action" in violation


def test_runtime_policy_accepts_only_approved_sha_refs() -> None:
    allowed = next(iter(policy.ALLOWED_USES["actions/github-script"]))

    assert (
        policy._validate_allowed_uses_ref(
            f"actions/github-script@{allowed}",
            "actions/github-script",
        )
        is None
    )


def test_runtime_policy_allows_cache_restore_and_save_subactions() -> None:
    cache_sha = next(iter(policy.ALLOWED_USES["actions/cache"]))

    assert (
        policy._validate_allowed_uses_ref(
            f"actions/cache/restore@{cache_sha}", "actions/cache/restore"
        )
        is None
    )
    assert (
        policy._validate_allowed_uses_ref(
            f"actions/cache/save@{cache_sha}", "actions/cache/save"
        )
        is None
    )


def test_contract_tests_workflow_uses_least_privilege_issue_permissions() -> None:
    workflow = _load_yaml(CONTRACT_TESTS_WORKFLOW)
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])

    assert workflow["permissions"] == {"contents": "read"}
    assert jobs["contract-tests"]["permissions"] == {
        "contents": "read",
        "issues": "write",
    }
    assert jobs["notify-success"]["permissions"] == {"contents": "read"}


def test_contract_tests_workflow_declares_boolean_dispatch_input() -> None:
    workflow = _load_yaml(CONTRACT_TESTS_WORKFLOW)
    triggers = cast(dict[str, Any], workflow.get("on", workflow.get(True)))
    dispatch = cast(dict[str, Any], triggers["workflow_dispatch"])
    inputs = cast(dict[str, dict[str, Any]], dispatch["inputs"])

    assert inputs["skip_slow"]["type"] == "boolean"


def test_nightly_replay_checksums_use_run_root_relative_paths() -> None:
    workflow = NIGHTLY_REPLAY_WORKFLOW.read_text(encoding="utf-8")

    assert "cd .artifacts/nightly-replay/determinism/run1" in workflow
    assert "cd .artifacts/nightly-replay/determinism/run2" in workflow
    assert workflow.count("find . -type f -print0 | sort -z | xargs -0 sha256sum") == 2
    assert "find .artifacts/nightly-replay/determinism/run1 -type f" not in workflow
    assert "find .artifacts/nightly-replay/determinism/run2 -type f" not in workflow


def test_coderabbit_installer_guard_ignores_documentation_comments() -> None:
    workflow = CODERABBIT_WORKFLOW.read_text(encoding="utf-8")

    assert "sed '/^[[:space:]]*#/d' \"${install_script}\"" in workflow
    assert "Install script nests a remote pipe-to-shell; refusing" in workflow
