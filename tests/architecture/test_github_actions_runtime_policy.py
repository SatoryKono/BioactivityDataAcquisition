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

from collections.abc import Iterator
from pathlib import Path
import subprocess
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
DOCS_WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
GITHUB_POLICY = ROOT / "docs" / "00-project" / "governance" / "05-github-policy.md"
ALWAYS_ON_REQUIRED_CHECKS = {
    "checks-complete": ROOT / ".github" / "workflows" / "import-linter.yml",
    "root-hygiene": ROOT / ".github" / "workflows" / "root-hygiene.yml",
}
UPLOAD_ARTIFACT_PREFIX = "actions/upload-artifact@"
MAX_ARTIFACT_RETENTION_DAYS = 30


def _load_yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def _iter_upload_artifact_steps(node: object) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        uses = node.get("uses")
        if isinstance(uses, str) and uses.startswith(UPLOAD_ARTIFACT_PREFIX):
            yield node
        for value in node.values():
            yield from _iter_upload_artifact_steps(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_upload_artifact_steps(value)


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


def test_upload_artifacts_have_bounded_explicit_retention() -> None:
    violations: list[str] = []

    for workflow_path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for step in _iter_upload_artifact_steps(_load_yaml(workflow_path)):
            step_name = str(step.get("name", "unnamed upload-artifact step"))
            with_config = step.get("with")
            retention = (
                with_config.get("retention-days")
                if isinstance(with_config, dict)
                else None
            )
            if not isinstance(retention, int) or not (
                1 <= retention <= MAX_ARTIFACT_RETENTION_DAYS
            ):
                violations.append(
                    f"{workflow_path.name}::{step_name}: retention-days must be "
                    f"1..{MAX_ARTIFACT_RETENTION_DAYS}, got {retention!r}"
                )

    assert not violations, "\n".join(violations)


def test_always_upload_artifacts_skip_cancelled_runs() -> None:
    violations: list[str] = []

    for workflow_path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for step in _iter_upload_artifact_steps(_load_yaml(workflow_path)):
            condition = step.get("if")
            if (
                isinstance(condition, str)
                and "always()" in condition
                and "!cancelled()" not in condition
            ):
                violations.append(
                    f"{workflow_path.name}::{step.get('name', 'unnamed')}: "
                    "always() upload must include !cancelled()"
                )

    assert not violations, "\n".join(violations)


@pytest.mark.parametrize(
    ("workflow_name", "artifact_name"),
    [
        ("duplication-complexity.yml", "duplication-complexity-reports"),
        ("type-checking.yml", "type-checking-reports"),
    ],
)
def test_heavy_diagnostics_are_failure_only_and_path_scoped(
    workflow_name: str,
    artifact_name: str,
) -> None:
    workflow_path = ROOT / ".github" / "workflows" / workflow_name
    matching_steps = [
        step
        for step in _iter_upload_artifact_steps(_load_yaml(workflow_path))
        if isinstance(step.get("with"), dict)
        and step["with"].get("name") == artifact_name
    ]

    assert len(matching_steps) == 1
    step = matching_steps[0]
    assert "failure()" in str(step.get("if", ""))
    assert "!cancelled()" in str(step.get("if", ""))
    assert str(step["with"].get("path", "")).strip() not in {"reports", "reports/"}


def test_docs_workflow_is_tracked_and_not_gitignored() -> None:
    relative_path = DOCS_WORKFLOW.relative_to(ROOT).as_posix()

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative_path],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", relative_path],
        cwd=ROOT,
        check=False,
    )

    assert DOCS_WORKFLOW.is_file()
    assert tracked.returncode == 0, tracked.stderr
    assert ignored.returncode == 1


def test_github_policy_python_version_claims_match_workflows() -> None:
    tests_workflow = _load_yaml(TESTS_WORKFLOW)
    release_workflow = _load_yaml(RELEASE_WORKFLOW)
    test_matrix = tests_workflow["jobs"]["test-matrix"]["strategy"]["matrix"]
    release_matrix = release_workflow["jobs"]["test-install"]["strategy"]["matrix"]
    policy_doc = GITHUB_POLICY.read_text(encoding="utf-8")

    assert test_matrix["python-version"] == ["3.13"]
    assert len(test_matrix["test-group"]) == 6
    assert release_matrix["python-version"] == ["3.13"]
    assert "full test matrix (Python 3.13, 6 groups)" in policy_doc
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

    assert "cli.coderabbit.ai/install.sh" not in workflow
    assert "sha256sum -c" in workflow
    assert (
        "0b47cb4de75188c0184f290d8d6818a793a9528e8f79cf660c6a65f225b045c1" in workflow
    )
    assert "CODERABBIT_CLI_VERSION" in workflow
    assert "coderabbit-linux-x64.zip" in workflow


def test_runtime_policy_rejects_coderabbit_mutable_installer() -> None:
    sample = "curl -fsSL https://cli.coderabbit.ai/install.sh | bash\n"
    violations = policy.remote_download_violations_in_text(
        sample,
        rel_path="fixture.yml",
    )

    assert any("forbidden mutable installer" in item for item in violations)
    assert any("pipe-to-shell" in item for item in violations)


def test_runtime_policy_requires_pinned_coderabbit_zip_digest() -> None:
    url = "https://cli.coderabbit.ai/releases/0.7.5/coderabbit-linux-x64.zip"
    digest = "0b47cb4de75188c0184f290d8d6818a793a9528e8f79cf660c6a65f225b045c1"
    missing = policy.remote_download_violations_in_text(
        f"curl -fsSL {url} -o archive.zip\n",
        rel_path="fixture.yml",
    )
    pinned = policy.remote_download_violations_in_text(
        f"curl -fsSL {url} -o archive.zip\necho {digest}  archive.zip | sha256sum -c -\n",
        rel_path="fixture.yml",
    )

    assert any("missing pinned sha256" in item for item in missing)
    assert pinned == []


def test_release_publish_requires_same_sha_quality_gates() -> None:
    release = _load_yaml(RELEASE_WORKFLOW)
    security = _load_yaml(ROOT / ".github/workflows/security.yml")
    jobs = release["jobs"]
    on_field = security.get("on") or security.get(True) or {}

    assert "workflow_call" in on_field
    assert jobs["security-gate"]["uses"] == "./.github/workflows/security.yml"
    step_runs = " ".join(
        str(step.get("run", "")) for step in jobs["release-tests"]["steps"]
    )
    assert "pytest" in step_runs
    for publish in ("publish-testpypi", "publish-pypi"):
        needs = jobs[publish]["needs"]
        assert "security-gate" in needs
        assert "release-tests" in needs
        assert "test-install" in needs


def _step_uses(workflow: dict[str, Any], job_name: str) -> list[str]:
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])
    return [
        str(step.get("uses", ""))
        for step in jobs[job_name]["steps"]
        if isinstance(step, dict)
    ]


def test_dependency_review_workflow_is_pr_scoped_and_sha_pinned() -> None:
    workflow_path = ROOT / ".github/workflows/dependency-review.yml"
    workflow = _load_yaml(workflow_path)
    triggers = cast(dict[str, Any], workflow.get("on", workflow.get(True)))
    pull_request = triggers["pull_request"]
    uses = _step_uses(workflow, "dependency-review")
    review_sha = next(iter(policy.ALLOWED_USES["actions/dependency-review-action"]))
    checkout_sha = "3d3c42e5aac5ba805825da76410c181273ba90b1"

    assert workflow["permissions"] == {"contents": "read"}
    assert set(triggers) == {"pull_request"}
    assert "uv.lock" in pull_request["paths"]
    assert "pyproject.toml" in pull_request["paths"]
    assert f"actions/checkout@{checkout_sha}" in uses
    assert f"actions/dependency-review-action@{review_sha}" in uses
    review_step = next(
        step
        for step in workflow["jobs"]["dependency-review"]["steps"]
        if str(step.get("uses", "")).startswith("actions/dependency-review-action@")
    )
    assert review_step["with"]["fail-on-severity"] == "high"


def test_security_workflow_runs_gitleaks_and_osv_scanner() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/security.yml")
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])
    gitleaks_sha = next(iter(policy.ALLOWED_USES["gitleaks/gitleaks-action"]))
    osv_sha = next(
        iter(policy.ALLOWED_USES["google/osv-scanner-action/osv-scanner-action"])
    )
    gitleaks_env = jobs["gitleaks"]["steps"][1]["env"]
    osv_step = next(
        step
        for step in jobs["osv-scanner"]["steps"]
        if str(step.get("uses", "")).startswith(
            "google/osv-scanner-action/osv-scanner-action@"
        )
    )
    osv_gate = " ".join(
        str(step.get("run", "")) for step in jobs["osv-scanner"]["steps"]
    )
    pip_audit_run = " ".join(
        str(step.get("run", "")) for step in jobs["pip-audit"]["steps"]
    )

    assert "gitleaks" in jobs
    assert "osv-scanner" in jobs
    assert f"gitleaks/gitleaks-action@{gitleaks_sha}" in _step_uses(
        workflow, "gitleaks"
    )
    assert jobs["gitleaks"]["steps"][0]["with"]["fetch-depth"] == 0
    assert gitleaks_env["GITLEAKS_CONFIG"] == ".gitleaks.toml"
    assert gitleaks_env["GITLEAKS_ENABLE_COMMENTS"] == "false"
    assert f"google/osv-scanner-action/osv-scanner-action@{osv_sha}" in _step_uses(
        workflow, "osv-scanner"
    )
    assert osv_step.get("continue-on-error") is True
    assert "--lockfile=uv.lock" in str(osv_step["with"]["scan-args"])
    assert "--format=json" in str(osv_step["with"]["scan-args"])
    assert "--osv-json osv-results.json" in osv_gate
    assert "PYSEC-2026-3721" in pip_audit_run
    assert not (ROOT / "osv-scanner.toml").exists()


def test_codeql_workflow_is_python_only_and_sha_pinned() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/codeql.yml")
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])
    init_sha = next(iter(policy.ALLOWED_USES["github/codeql-action/init"]))
    analyze_sha = next(iter(policy.ALLOWED_USES["github/codeql-action/analyze"]))
    init_step = next(
        step
        for step in jobs["analyze"]["steps"]
        if str(step.get("uses", "")).startswith("github/codeql-action/init@")
    )

    assert workflow["permissions"] == {"contents": "read"}
    assert jobs["analyze"]["permissions"] == {
        "contents": "read",
        "security-events": "write",
    }
    assert init_step["with"]["languages"] == "python"
    assert "matrix" not in jobs["analyze"]
    assert f"github/codeql-action/init@{init_sha}" in _step_uses(workflow, "analyze")
    assert f"github/codeql-action/analyze@{analyze_sha}" in _step_uses(
        workflow, "analyze"
    )


def test_scorecard_workflow_is_non_blocking_weekly_baseline() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/scorecard.yml")
    triggers = cast(dict[str, Any], workflow.get("on", workflow.get(True)))
    scorecard_sha = next(iter(policy.ALLOWED_USES["ossf/scorecard-action"]))
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])

    assert "pull_request" not in triggers
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers
    assert f"ossf/scorecard-action@{scorecard_sha}" in _step_uses(workflow, "analysis")
    upload = next(
        step
        for step in jobs["analysis"]["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    assert upload["with"]["retention-days"] == 30
    assert "!cancelled()" in str(upload.get("if", ""))


def test_syft_sbom_is_generated_on_release_and_ghcr_push() -> None:
    release = _load_yaml(RELEASE_WORKFLOW)
    docker = _load_yaml(ROOT / ".github/workflows/docker.yml")
    sbom_sha = next(iter(policy.ALLOWED_USES["anchore/sbom-action"]))
    release_uses = _step_uses(release, "build")
    docker_uses = _step_uses(docker, "docker-push")
    release_assets = release["jobs"]["create-github-release-assets"]
    asset_files = str(release_assets["steps"][-1]["with"]["files"])

    assert f"anchore/sbom-action@{sbom_sha}" in release_uses
    assert f"anchore/sbom-action@{sbom_sha}" in docker_uses
    assert "bioetl-dist-sbom" in " ".join(
        str(step.get("with", {})) for step in release_assets["steps"]
    )
    assert "sbom/**" in asset_files


def test_zizmor_workflow_is_path_filtered_and_sha_pinned() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/zizmor.yml")
    triggers = cast(dict[str, Any], workflow.get("on", workflow.get(True)))
    zizmor_sha = next(iter(policy.ALLOWED_USES["zizmorcore/zizmor-action"]))
    zizmor_step = next(
        step
        for step in workflow["jobs"]["zizmor"]["steps"]
        if str(step.get("uses", "")).startswith("zizmorcore/zizmor-action@")
    )
    labeler = (ROOT / ".github/workflows/labeler.yml").read_text(encoding="utf-8")
    zizmor_config = (ROOT / ".github/zizmor.yml").read_text(encoding="utf-8")

    assert set(triggers) == {"pull_request"}
    assert ".github/workflows/**" in triggers["pull_request"]["paths"]
    assert ".github/actions/**" in triggers["pull_request"]["paths"]
    assert zizmor_step["uses"] == f"zizmorcore/zizmor-action@{zizmor_sha}"
    assert zizmor_step["with"]["min-severity"] == "high"
    assert zizmor_step["with"]["min-confidence"] == "high"
    assert zizmor_step["with"]["version"] == "1.29.0"
    assert "pull_request_target" in labeler
    assert "does not checkout untrusted PR HEAD" in labeler
    assert ".github/workflows/labeler.yml" in zizmor_config


def test_osv_high_critical_gate_ignores_medium_and_fails_high() -> None:
    medium = {
        "results": [
            {
                "packages": [
                    {
                        "package": {"name": "pip", "version": "26.1.2"},
                        "vulnerabilities": [
                            {
                                "id": "PYSEC-2026-3721",
                                "database_specific": {"severity": "MEDIUM"},
                                "severity": [{"score": 6.5}],
                            }
                        ],
                    }
                ]
            }
        ]
    }
    high = {
        "results": [
            {
                "packages": [
                    {
                        "package": {"name": "demo", "version": "1.0"},
                        "vulnerabilities": [
                            {
                                "id": "GHSA-high",
                                "database_specific": {"severity": "HIGH"},
                            }
                        ],
                    }
                ]
            }
        ]
    }

    vector_medium = {
        "results": [
            {
                "packages": [
                    {
                        "package": {"name": "pip", "version": "26.1.2"},
                        "vulnerabilities": [
                            {
                                "id": "PYSEC-2026-3721",
                                "severity": [
                                    {
                                        "type": "CVSS_V3",
                                        "score": (
                                            "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:N"
                                        ),
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ]
    }

    assert policy.collect_blocking_osv_findings(medium) == []
    assert policy.collect_blocking_osv_findings(vector_medium) == []
    assert policy.collect_blocking_osv_findings(high) == ["GHSA-high HIGH demo==1.0"]


def test_security_policy_lists_canonical_supply_chain_scanners() -> None:
    security_md = (ROOT / ".github/SECURITY.md").read_text(encoding="utf-8")

    for needle in (
        "Dependency review",
        "Gitleaks",
        "OSV-Scanner",
        "CodeQL",
        "OpenSSF Scorecard",
        "Syft SBOM",
        "zizmor",
    ):
        assert needle in security_md
