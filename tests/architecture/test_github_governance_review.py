from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "scripts" / "engineering" / "repo" / "github_settings_review.py"
POLICY_PATH = ROOT / "configs" / "quality" / "github_governance_policy.json"


def _load_tool():
    spec = importlib.util.spec_from_file_location("github_settings_review", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = _load_tool()

pytestmark = pytest.mark.architecture


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _passing_snapshot() -> dict:
    policy = _policy()
    labels = [
        {
            "name": name,
            "description": "",
            "color": "ededed",
            "classification": "canonical",
            "replacement": None,
        }
        for name in policy["labels"]["automation_required"]
    ]
    return {
        "generated_at": "2026-08-30T12:00:00+00:00",
        "settings": {
            "has_wiki": False,
            "allow_squash_merge": True,
            "allow_merge_commit": False,
            "allow_rebase_merge": False,
            "secret_scanning": "enabled",
            "secret_scanning_validity_checks": "enabled",
            "secret_scanning_non_provider_patterns": "disabled",
        },
        "rulesets": [
            # Live GET 2026-09-10T02:53:01+03:00: ruleset main is active (#10267).
            {"name": "main", "enforcement": "active"}
        ],
        "actions_permissions": {
            "available": True,
            "payload": {
                "sha_pinning_required": True,
                "allowed_actions": "selected",
            },
        },
        "actions_selected": {
            "available": True,
            "payload": {
                "github_owned_allowed": True,
                "verified_allowed": False,
                "patterns_allowed": TOOL.selected_actions_patterns(),
            },
        },
        "environments": [
            *[
                {
                    "name": name,
                    "protection_rules": [{"type": "required_reviewers"}],
                    "deployment_branch_policy": {
                        "protected_branches": False,
                        "custom_branch_policies": True,
                    },
                }
                for name in policy["protected_environments"]
            ],
            *[
                {
                    "name": name,
                    "protection_rules": [{"type": "required_reviewers"}],
                    "deployment_branch_policy": {
                        "protected_branches": False,
                        "custom_branch_policies": True,
                    },
                    "deployment_branch_policies": [
                        {"name": f"{name}/**", "type": "branch"}
                    ],
                    "secret_count": 0,
                }
                for name in policy.get("agent_runtime_environments") or []
            ],
        ],
        "dependabot": {
            "alerts": {"enabled": True},
            "security_updates": {"enabled": True},
        },
        "codeql": {
            "advanced_workflow_exists": True,
            "default_setup": {
                "available": True,
                "payload": {"state": "not-configured"},
            },
            "hosted_default_workflows": [],
        },
        "codeowners": {"exists": True, "path": ".github/CODEOWNERS"},
        "issue_intake": {
            "forms": sorted(
                policy["issue_intake"]["primary_forms"]
                + policy["issue_intake"]["specialized_forms"]
            ),
            "config_exists": True,
        },
        "labels": {"items": labels},
    }


def test_captured_subprocess_output_uses_utf8() -> None:
    assert TOOL._CAPTURED_TEXT["encoding"] == "utf-8"
    assert TOOL._CAPTURED_TEXT["errors"] == "replace"
    assert TOOL._CAPTURED_TEXT["text"] is True


def test_client_rejects_mutating_gh_surfaces() -> None:
    with pytest.raises(TOOL.GitHubReviewError):
        TOOL.ReadOnlyGitHubClient.assert_read_only(
            ["api", "repos/owner/repo", "-X", "PATCH"]
        )
    with pytest.raises(TOOL.GitHubReviewError):
        TOOL.ReadOnlyGitHubClient.assert_read_only(["issue", "create"])
    with pytest.raises(TOOL.GitHubReviewError):
        TOOL._git_head(ROOT, "--output=unexpected")


def test_cli_paths_are_confined_but_explicit_runner_temp_is_supported(
    tmp_path: Path,
) -> None:
    assert TOOL.REPO_ROOT == ROOT
    with pytest.raises(ValueError):
        TOOL.resolve_cli_path(ROOT.parent / "outside-policy.json", root=ROOT)

    external_output = tmp_path / "github-settings-review.json"
    assert (
        TOOL.resolve_output_path(external_output, root=ROOT)
        == external_output.resolve()
    )


def test_unused_github_environments_are_not_required_protection_surfaces() -> None:
    protected = set(_policy()["protected_environments"])
    unused = set(_policy()["unused_environments"])
    agent_runtime = set(_policy()["agent_runtime_environments"])
    assert "ghcr-publish" in protected
    assert "observability-render-host" in protected
    assert unused == {"staging"}
    assert agent_runtime == {"copilot"}
    assert protected.isdisjoint(unused)
    assert protected.isdisjoint(agent_runtime)
    assert unused.isdisjoint(agent_runtime)


def test_agent_runtime_environment_requires_protected_copilot() -> None:
    now = datetime(2026, 9, 11, tzinfo=UTC)
    passing = TOOL.evaluate_snapshot(_passing_snapshot(), _policy(), now=now)
    by_id = {item["id"]: item for item in passing["controls"]}
    assert by_id["GH-ENV-003"]["status"] == "pass"

    missing = _passing_snapshot()
    missing["environments"] = [
        item for item in missing["environments"] if item["name"] != "copilot"
    ]
    drifted_missing = TOOL.evaluate_snapshot(missing, _policy(), now=now)
    by_id = {item["id"]: item for item in drifted_missing["controls"]}
    assert drifted_missing["overall"] == "drift"
    assert by_id["GH-ENV-003"]["status"] == "drift"
    assert "missing=['copilot']" in by_id["GH-ENV-003"]["evidence"]

    unprotected = _passing_snapshot()
    for item in unprotected["environments"]:
        if item["name"] == "copilot":
            item["protection_rules"] = []
            item["deployment_branch_policy"] = None
            item["deployment_branch_policies"] = [{"name": "main", "type": "branch"}]
            item["secret_count"] = 1
    drifted_unprotected = TOOL.evaluate_snapshot(unprotected, _policy(), now=now)
    by_id = {item["id"]: item for item in drifted_unprotected["controls"]}
    assert by_id["GH-ENV-003"]["status"] == "drift"
    assert "unprotected=['copilot']" in by_id["GH-ENV-003"]["evidence"]
    assert "copilot:main" in by_id["GH-ENV-003"]["evidence"]
    assert "secrets=['copilot=1']" in by_id["GH-ENV-003"]["evidence"]


def test_unknown_labels_are_retained_by_default() -> None:
    classification, replacement = TOOL._classification(
        "project-specific-label",
        canonical={"bug"},
        aliases={"docs": "documentation"},
        deprecated={"obsolete"},
    )
    assert classification == "retained"
    assert replacement is None


def test_evaluation_maps_drift_to_existing_issues() -> None:
    snapshot = _passing_snapshot()
    snapshot["settings"]["has_wiki"] = True
    snapshot["labels"]["items"] = []

    result = TOOL.evaluate_snapshot(
        snapshot,
        _policy(),
        now=datetime(2026, 8, 30, tzinfo=UTC),
    )
    by_id = {item["id"]: item for item in result["controls"]}

    assert result["overall"] == "drift"
    assert by_id["GH-WIKI-001"]["known_issue"] == 9787
    assert by_id["GH-WIKI-001"]["status"] == "drift"
    assert by_id["GH-LABELS-001"]["known_issue"] == 9787
    assert result["automation_mutated_github"] is False


def test_disabled_rulesets_are_gh_ruleset_001_drift() -> None:
    """Disabled rulesets fail GH-RULESET-001 even after #10267 activation."""
    snapshot = _passing_snapshot()
    snapshot["rulesets"] = [
        {"name": "main", "enforcement": "disabled"},
        {"name": "root-hygiene-required-check", "enforcement": "disabled"},
    ]
    result = TOOL.evaluate_snapshot(
        snapshot,
        _policy(),
        now=datetime(2026, 9, 10, tzinfo=UTC),
    )
    by_id = {item["id"]: item for item in result["controls"]}

    assert result["overall"] == "drift"
    assert by_id["GH-RULESET-001"]["status"] == "drift"
    assert "active rulesets: none" in by_id["GH-RULESET-001"]["evidence"]


def test_passing_snapshot_is_conformant_and_default_setup_drift_is_detected() -> None:
    now = datetime(2026, 8, 30, tzinfo=UTC)
    passing = TOOL.evaluate_snapshot(_passing_snapshot(), _policy(), now=now)
    assert passing["overall"] == "conformant"
    assert {
        item["id"]
        for item in passing["controls"]
        if item["id"].startswith("GH-CODEQL-")
    } == {
        "GH-CODEQL-001",
        "GH-CODEQL-002",
    }

    snapshot = _passing_snapshot()
    snapshot["codeql"]["default_setup"]["payload"]["state"] = "configured"
    drifted = TOOL.evaluate_snapshot(snapshot, _policy(), now=now)
    by_id = {item["id"]: item for item in drifted["controls"]}
    assert drifted["overall"] == "drift"
    assert by_id["GH-CODEQL-002"]["status"] == "drift"
    assert "state=configured" in by_id["GH-CODEQL-002"]["evidence"]


def test_supply_chain_controls_detect_validity_and_allowlist_drift() -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    passing = TOOL.evaluate_snapshot(_passing_snapshot(), _policy(), now=now)
    by_id = {item["id"]: item for item in passing["controls"]}
    assert by_id["GH-SECRET-002"]["status"] == "pass"
    assert by_id["GH-SECRET-003"]["status"] == "pass"
    assert by_id["GH-ACTIONS-002"]["status"] == "pass"
    assert by_id["GH-ACTIONS-003"]["status"] == "pass"
    assert by_id["GH-ENV-002"]["status"] == "pass"
    assert by_id["GH-ENV-003"]["status"] == "pass"

    snapshot = _passing_snapshot()
    snapshot["settings"]["secret_scanning_validity_checks"] = "disabled"
    snapshot["actions_permissions"]["payload"]["allowed_actions"] = "all"
    snapshot["environments"] = [
        *snapshot["environments"],
        {
            "name": "staging",
            "protection_rules": [],
            "deployment_branch_policy": None,
        },
    ]
    drifted = TOOL.evaluate_snapshot(snapshot, _policy(), now=now)
    by_id = {item["id"]: item for item in drifted["controls"]}
    assert drifted["overall"] == "drift"
    assert by_id["GH-SECRET-002"]["status"] == "drift"
    assert by_id["GH-ACTIONS-002"]["status"] == "drift"
    assert by_id["GH-ACTIONS-003"]["status"] == "drift"
    assert by_id["GH-ENV-002"]["status"] == "drift"
    assert "present=['staging']" in by_id["GH-ENV-002"]["evidence"]
    assert by_id["GH-ENV-003"]["status"] == "pass"


def test_policy_and_workflow_preserve_read_only_contract() -> None:
    policy = _policy()
    by_id = {item["id"]: item for item in policy["controls"]}
    assert by_id["GH-SECRET-002"]["known_issue"] == 10310
    assert by_id["GH-ENV-002"]["known_issue"] is None
    assert by_id["GH-ENV-003"]["known_issue"] is None
    assert by_id["GH-ENV-003"]["check"] == "agent_runtime_environment_protected"
    canonical = set(policy["labels"]["canonical"])
    assert set(policy["labels"]["aliases"].values()) <= canonical
    assert policy["migration"]["delete_not_before"] == "2026-11-30"

    workflow = (
        ROOT / ".github" / "workflows" / "github-settings-quarterly-review.yml"
    ).read_text(encoding="utf-8")
    assert "issues: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "1 1,4,7,10" in workflow
    assert "--fail-on-drift" not in workflow
    job_header = workflow.split("    steps:", 1)[0]
    assert "runner.temp" not in job_header
    assert "$RUNNER_TEMP/github-settings-review.json" in workflow
    assert "python -m scripts.engineering.repo github-settings-review" in workflow
    assert "python -m scripts.engineering.repo.github_settings_review" not in workflow
    assert "python scripts/engineering/repo/github_settings_review.py" not in workflow
    assert ".github/tooling/github_settings_review.py" not in workflow


def test_issue_forms_and_automation_use_canonical_labels() -> None:
    policy = _policy()
    intake = policy["issue_intake"]
    form_names = {
        path.name
        for path in (ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.y*ml")
        if path.name != "config.yml"
    }
    assert form_names == set(intake["primary_forms"] + intake["specialized_forms"])
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").is_file()

    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert '- "ci"' not in dependabot
    assert '- "ci/cd"' in dependabot
