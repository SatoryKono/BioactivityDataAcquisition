"""Read-only, evidence-producing review of live GitHub repository settings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.common.repo_paths import (
    resolve_cli_path,
    resolve_output_path,
)

MUTATING_GH_ARGUMENTS = frozenset(
    {
        "-X",
        "--method",
        "-f",
        "-F",
        "--field",
        "--raw-field",
        "--input",
    }
)
READ_ONLY_GH_COMMANDS = frozenset({("api",), ("repo", "view")})
_GITHUB_DIRNAME = ".github"
ControlResult = tuple[bool | None, str]
_CAPTURED_TEXT = {
    "capture_output": True,
    "check": False,
    "encoding": "utf-8",
    "errors": "replace",
    "text": True,
}


class GitHubReviewError(RuntimeError):
    """Raised when the review cannot collect required public metadata."""


def _safe_error(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    message = lines[0] if lines else "GitHub API request failed"
    if "token" in message.casefold() or "credential" in message.casefold():
        return "GitHub authentication failed"
    return message[:240]


def _dotenv_tokens(repo_root: Path) -> list[str]:
    env_path = repo_root / ".env"
    if not env_path.is_file():
        return []
    accepted = {
        "GITHUB_TOKEN",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "GITHUB_CDX_PERSONAL_ACCESS_TOKEN",
    }
    tokens: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() not in accepted:
            continue
        token = value.strip().strip("'").strip('"')
        if token and token not in tokens:
            tokens.append(token)
    return tokens


class ReadOnlyGitHubClient:
    """Small gh wrapper that rejects mutating command surfaces."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        explicit = [
            os.environ.get("GH_TOKEN", ""),
            os.environ.get("GITHUB_TOKEN", ""),
        ]
        self._tokens = [
            token for token in [*explicit, *_dotenv_tokens(repo_root)] if token
        ]
        self._active_token: str | None = None

    @staticmethod
    def assert_read_only(args: Sequence[str]) -> None:
        if not args:
            raise GitHubReviewError("empty gh command")
        allowed = any(
            tuple(args[: len(prefix)]) == prefix for prefix in READ_ONLY_GH_COMMANDS
        )
        if not allowed:
            raise GitHubReviewError(
                f"mutating or unsupported gh command rejected: {args[0]}"
            )
        if any(argument in MUTATING_GH_ARGUMENTS for argument in args):
            raise GitHubReviewError("mutating gh api argument rejected")

    def _environment(self, token: str | None) -> dict[str, str]:
        environment = os.environ.copy()
        if token:
            environment["GH_TOKEN"] = token
        return environment

    def _authenticate(self) -> None:
        if self._active_token is not None:
            return
        candidates: list[str | None] = list(dict.fromkeys(self._tokens))
        if not candidates:
            candidates.append(None)
        for candidate in candidates:
            completed = subprocess.run(
                ["gh", "api", "user", "--silent"],
                cwd=self.repo_root,
                env=self._environment(candidate),
                **_CAPTURED_TEXT,
            )
            if completed.returncode == 0:
                self._active_token = candidate or ""
                return
        raise GitHubReviewError("no working GitHub credential is available")

    def run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        self.assert_read_only(args)
        self._authenticate()
        return subprocess.run(
            ["gh", *args],
            cwd=self.repo_root,
            env=self._environment(self._active_token),
            **_CAPTURED_TEXT,
        )

    def json(self, args: Sequence[str]) -> Any:
        completed = self.run(args)
        if completed.returncode != 0:
            raise GitHubReviewError(_safe_error(completed.stderr))
        if not completed.stdout.strip():
            return {}
        return json.loads(completed.stdout)

    def api_optional(self, endpoint: str) -> dict[str, Any]:
        completed = self.run(["api", endpoint])
        if completed.returncode != 0:
            return {
                "available": False,
                "reason": _safe_error(completed.stderr),
            }
        payload: Any = {}
        if completed.stdout.strip():
            payload = json.loads(completed.stdout)
        return {"available": True, "payload": payload}

    def api_enabled(self, endpoint: str) -> dict[str, Any]:
        completed = self.run(["api", endpoint, "--silent"])
        if completed.returncode == 0:
            return {
                "available": True,
                "enabled": True,
                "reason": "",
            }
        if "HTTP 404" in completed.stderr:
            return {
                "available": True,
                "enabled": False,
                "reason": "HTTP 404: setting is disabled or not configured",
            }
        return {
            "available": False,
            "enabled": None,
            "reason": _safe_error(completed.stderr),
        }

    def api_pages(self, endpoint: str, *, page_size: int = 100) -> list[Any]:
        collected: list[Any] = []
        for page in range(1, 101):
            separator = "&" if "?" in endpoint else "?"
            payload = self.json(
                [
                    "api",
                    f"{endpoint}{separator}per_page={page_size}&page={page}",
                ]
            )
            if not isinstance(payload, list):
                raise GitHubReviewError(f"expected list payload from {endpoint}")
            collected.extend(payload)
            if len(payload) < page_size:
                break
        return collected


def _git_head(repo_root: Path, source_ref: str = "HEAD") -> str:
    if (
        source_ref.startswith("-")
        or re.fullmatch(r"[A-Za-z0-9_./^~:-]+", source_ref) is None
    ):
        raise GitHubReviewError("invalid source git ref")
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", source_ref + "^{commit}"],
        cwd=repo_root,
        **_CAPTURED_TEXT,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _classification(
    name: str,
    *,
    canonical: set[str],
    aliases: dict[str, str],
    deprecated: set[str],
) -> tuple[str, str | None]:
    if name in canonical:
        return "canonical", None
    if name in aliases:
        return "deprecated", aliases[name]
    if name in deprecated:
        return "deprecated", None
    return "retained", None


def _workflow_health(runs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    normalized = list(runs)
    conclusions = Counter(
        str(run.get("conclusion") or run.get("status") or "unknown")
        for run in normalized
    )
    failures = [
        {
            "name": run.get("name"),
            "conclusion": run.get("conclusion"),
            "started_at": run.get("run_started_at"),
            "url": run.get("html_url"),
        }
        for run in normalized
        if run.get("conclusion") in {"failure", "timed_out", "cancelled"}
    ][:10]
    return {
        "sample_size": len(normalized),
        "conclusions": dict(sorted(conclusions.items())),
        "recent_non_successful": failures,
    }


def collect_snapshot(
    client: ReadOnlyGitHubClient,
    repo_root: Path,
    policy: dict[str, Any],
    *,
    now: datetime | None = None,
    source_git_ref: str = "HEAD",
) -> dict[str, Any]:
    generated_at = (now or datetime.now(UTC)).astimezone(UTC)
    identity = client.json(["repo", "view", "--json", "nameWithOwner,defaultBranchRef"])
    repository = identity["nameWithOwner"]
    repo_payload = client.json(["api", f"repos/{repository}"])
    rulesets = client.api_pages(f"repos/{repository}/rulesets")
    labels_payload = client.api_pages(f"repos/{repository}/labels")
    environments_payload = client.json(
        ["api", f"repos/{repository}/environments?per_page=100"]
    )
    runs_payload = client.json(["api", f"repos/{repository}/actions/runs?per_page=100"])

    label_policy = policy["labels"]
    canonical = set(label_policy["canonical"])
    aliases = dict(label_policy["aliases"])
    deprecated = set(label_policy["deprecated_without_replacement"])
    labels: list[dict[str, Any]] = []
    for item in labels_payload:
        classification, replacement = _classification(
            item["name"],
            canonical=canonical,
            aliases=aliases,
            deprecated=deprecated,
        )
        labels.append(
            {
                "name": item["name"],
                "description": item.get("description") or "",
                "color": item.get("color") or "",
                "classification": classification,
                "replacement": replacement,
            }
        )
    labels.sort(key=lambda item: item["name"].casefold())

    issue_template_dir = repo_root / _GITHUB_DIRNAME / "ISSUE_TEMPLATE"
    issue_files = sorted(
        path.name for path in issue_template_dir.iterdir() if path.is_file()
    )
    form_files = [
        name
        for name in issue_files
        if Path(name).suffix.casefold() in {".yml", ".yaml"} and name != "config.yml"
    ]
    codeowners_candidates = [
        repo_root / _GITHUB_DIRNAME / "CODEOWNERS",
        repo_root / "CODEOWNERS",
        repo_root / "docs" / "CODEOWNERS",
    ]
    codeowners_path = next(
        (path for path in codeowners_candidates if path.is_file()),
        None,
    )
    security_analysis = repo_payload.get("security_and_analysis") or {}
    default_branch_ref = identity.get("defaultBranchRef") or {}

    return {
        "schema_version": "1.0",
        "generated_at": generated_at.isoformat(),
        "source": {
            "git_head": _git_head(repo_root, source_git_ref),
            "git_ref": source_git_ref,
            "policy_sha256": _sha256(
                repo_root / "configs" / "quality" / "github_governance_policy.json"
            ),
            "tool_sha256": _sha256(Path(__file__).resolve()),
        },
        "repository": {
            "name_with_owner": repository,
            "default_branch": default_branch_ref.get("name")
            or repo_payload.get("default_branch"),
            "visibility": repo_payload.get("visibility"),
            "archived": repo_payload.get("archived"),
        },
        "settings": {
            "has_wiki": repo_payload.get("has_wiki"),
            "allow_squash_merge": repo_payload.get("allow_squash_merge"),
            "allow_merge_commit": repo_payload.get("allow_merge_commit"),
            "allow_rebase_merge": repo_payload.get("allow_rebase_merge"),
            "delete_branch_on_merge": repo_payload.get("delete_branch_on_merge"),
            "secret_scanning": (security_analysis.get("secret_scanning") or {}).get(
                "status"
            ),
            "secret_scanning_push_protection": (
                security_analysis.get("secret_scanning_push_protection") or {}
            ).get("status"),
        },
        "rulesets": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "enforcement": item.get("enforcement"),
                "target": item.get("target"),
            }
            for item in rulesets
        ],
        "actions_permissions": client.api_optional(
            f"repos/{repository}/actions/permissions"
        ),
        "environments": [
            {
                "name": item.get("name"),
                "protection_rules": item.get("protection_rules") or [],
                "deployment_branch_policy": item.get("deployment_branch_policy"),
            }
            for item in environments_payload.get("environments", [])
        ],
        "dependabot": {
            "alerts": client.api_enabled(f"repos/{repository}/vulnerability-alerts"),
            "security_updates": client.api_enabled(
                f"repos/{repository}/automated-security-fixes"
            ),
        },
        "codeql": {
            "advanced_workflow_exists": (
                repo_root / ".github" / "workflows" / "codeql.yml"
            ).is_file(),
            "default_setup": client.api_optional(
                f"repos/{repository}/code-scanning/default-setup"
            ),
        },
        "codeowners": {
            "exists": codeowners_path is not None,
            "path": (
                codeowners_path.relative_to(repo_root).as_posix()
                if codeowners_path
                else None
            ),
        },
        "issue_intake": {
            "files": issue_files,
            "forms": form_files,
            "config_exists": (issue_template_dir / "config.yml").is_file(),
        },
        "labels": {
            "count": len(labels),
            "classification_counts": dict(
                sorted(Counter(item["classification"] for item in labels).items())
            ),
            "items": labels,
        },
        "workflow_health": _workflow_health(runs_payload.get("workflow_runs", [])),
    }


def _optional_payload_value(container: dict[str, Any], key: str) -> Any:
    if not container.get("available"):
        return None
    payload = container.get("payload")
    return payload.get(key) if isinstance(payload, dict) else None


def _control_active_ruleset(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    active = [
        item["name"]
        for item in snapshot["rulesets"]
        if item.get("enforcement") == "active"
    ]
    return bool(active), f"active rulesets: {active or 'none'}"


def _control_sha_pinning_required(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    value = _optional_payload_value(
        snapshot["actions_permissions"], "sha_pinning_required"
    )
    if value is None:
        return None, f"sha_pinning_required={value}"
    return value is True, f"sha_pinning_required={value}"


def _control_protected_environments(
    snapshot: dict[str, Any], policy: dict[str, Any]
) -> ControlResult:
    by_name = {item["name"]: item for item in snapshot["environments"]}
    missing: list[str] = []
    unprotected: list[str] = []
    for name in policy["protected_environments"]:
        item = by_name.get(name)
        if item is None:
            missing.append(name)
        elif not item["protection_rules"] and not item["deployment_branch_policy"]:
            unprotected.append(name)
    evidence = f"missing={missing or 'none'}; unprotected={unprotected or 'none'}"
    return not missing and not unprotected, evidence


def _control_dependabot_security_updates(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    alerts = snapshot["dependabot"]["alerts"].get("enabled")
    updates = snapshot["dependabot"]["security_updates"].get("enabled")
    evidence = f"alerts={alerts}; security_updates={updates}"
    if alerts is None or updates is None:
        return None, evidence
    return alerts is True and updates is True, evidence


def _control_advanced_codeql(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    exists = snapshot["codeql"]["advanced_workflow_exists"]
    return exists, f"{_GITHUB_DIRNAME}/workflows/codeql.yml exists={exists}"


def _control_secret_scanning(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    value = snapshot["settings"]["secret_scanning"]
    if value is None:
        return None, f"secret_scanning={value}"
    return value == "enabled", f"secret_scanning={value}"


def _control_codeowners(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    value = snapshot["codeowners"]["exists"]
    return value, f"path={snapshot['codeowners']['path']}"


def _control_squash_only(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    settings = snapshot["settings"]
    value = (
        settings["allow_squash_merge"] is True
        and settings["allow_merge_commit"] is False
        and settings["allow_rebase_merge"] is False
    )
    evidence = (
        f"squash={settings['allow_squash_merge']}; "
        f"merge_commit={settings['allow_merge_commit']}; "
        f"rebase={settings['allow_rebase_merge']}"
    )
    return value, evidence


def _control_wiki_disabled(
    snapshot: dict[str, Any], _policy: dict[str, Any]
) -> ControlResult:
    value = snapshot["settings"]["has_wiki"]
    if value is None:
        return None, f"has_wiki={value}"
    return value is False, f"has_wiki={value}"


def _control_issue_forms(
    snapshot: dict[str, Any], policy: dict[str, Any]
) -> ControlResult:
    intake = policy["issue_intake"]
    expected = set(intake["primary_forms"] + intake["specialized_forms"])
    actual = set(snapshot["issue_intake"]["forms"])
    value = actual == expected and snapshot["issue_intake"]["config_exists"]
    evidence = (
        f"forms={sorted(actual)}; config_exists="
        f"{snapshot['issue_intake']['config_exists']}"
    )
    return value, evidence


def _control_automation_labels(
    snapshot: dict[str, Any], policy: dict[str, Any]
) -> ControlResult:
    actual = {item["name"] for item in snapshot["labels"]["items"]}
    missing = sorted(set(policy["labels"]["automation_required"]) - actual)
    return not missing, f"missing={missing or 'none'}"


_CONTROL_CHECKS: dict[
    str, Callable[[dict[str, Any], dict[str, Any]], ControlResult]
] = {
    "active_ruleset": _control_active_ruleset,
    "sha_pinning_required": _control_sha_pinning_required,
    "protected_environments": _control_protected_environments,
    "dependabot_security_updates": _control_dependabot_security_updates,
    "advanced_codeql": _control_advanced_codeql,
    "secret_scanning": _control_secret_scanning,
    "codeowners": _control_codeowners,
    "squash_only": _control_squash_only,
    "wiki_disabled": _control_wiki_disabled,
    "issue_forms": _control_issue_forms,
    "automation_labels": _control_automation_labels,
}


def _check_control(
    check: str,
    snapshot: dict[str, Any],
    policy: dict[str, Any],
) -> ControlResult:
    handler = _CONTROL_CHECKS.get(check)
    if handler is None:
        raise GitHubReviewError(f"unknown governance control: {check}")
    return handler(snapshot, policy)


def _control_status(passed: bool | None) -> str:
    if passed is True:
        return "pass"
    if passed is None:
        return "unavailable"
    return "drift"


def evaluate_snapshot(
    snapshot: dict[str, Any],
    policy: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    reviewed_at = (now or datetime.fromisoformat(snapshot["generated_at"])).astimezone(
        UTC
    )
    results: list[dict[str, Any]] = []
    for control in policy["controls"]:
        passed, evidence = _check_control(control["check"], snapshot, policy)
        status = _control_status(passed)
        due_date = (
            (reviewed_at + timedelta(days=control["due_days"])).date().isoformat()
        )
        known_issue = control.get("known_issue")
        if status == "pass":
            decision = "No action required."
        elif known_issue:
            decision = f"Track remediation in existing issue #{known_issue}."
        else:
            decision = "Owner must open a labelled follow-up issue manually."
        results.append(
            {
                "id": control["id"],
                "title": control["title"],
                "status": status,
                "evidence": evidence,
                "owner": control["owner"],
                "risk": control["risk"],
                "decision": decision,
                "known_issue": known_issue,
                "due_date": due_date,
            }
        )
    counts = Counter(item["status"] for item in results)
    return {
        "overall": "conformant"
        if counts.get("drift", 0) == 0 and counts.get("unavailable", 0) == 0
        else "drift",
        "counts": dict(sorted(counts.items())),
        "controls": results,
        "automation_mutated_github": False,
    }


def build_report(
    snapshot: dict[str, Any],
    policy: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "review": evaluate_snapshot(snapshot, policy, now=now),
        "snapshot": snapshot,
        "governance": {
            "owner": policy["owner"],
            "cadence": policy["cadence"],
            "migration": policy["migration"],
            "wiki": policy["wiki"],
        },
    }


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    snapshot = report["snapshot"]
    review = report["review"]
    lines = [
        "# GitHub settings review",
        "",
        f"- Repository: `{snapshot['repository']['name_with_owner']}`",
        f"- Discovered default branch: `{snapshot['repository']['default_branch']}`",
        f"- Generated: `{snapshot['generated_at']}`",
        f"- Git HEAD: `{snapshot['source']['git_head']}`",
        f"- Overall: **{review['overall']}**",
        "- Mutation posture: read-only; this automation did not change GitHub state.",
        "",
        "## Controls",
        "",
        "| ID | Status | Risk | Owner | Evidence | Decision | Due |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in review["controls"]:
        lines.append(
            "| {id} | {status} | {risk} | {owner} | {evidence} | {decision} | {due} |".format(
                id=_md(item["id"]),
                status=_md(item["status"]),
                risk=_md(item["risk"]),
                owner=_md(item["owner"]),
                evidence=_md(item["evidence"]),
                decision=_md(item["decision"]),
                due=_md(item["due_date"]),
            )
        )
    lines.extend(
        [
            "",
            "## Workflow health sample",
            "",
            f"- Runs sampled: {snapshot['workflow_health']['sample_size']}",
            f"- Conclusions: `{json.dumps(snapshot['workflow_health']['conclusions'], sort_keys=True)}`",
            "",
            "## Label inventory",
            "",
            f"- Total: {snapshot['labels']['count']}",
            f"- Classification counts: `{json.dumps(snapshot['labels']['classification_counts'], sort_keys=True)}`",
            "",
            "| Label | Classification | Replacement | Description |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in snapshot["labels"]["items"]:
        lines.append(
            f"| {_md(item['name'])} | {_md(item['classification'])} | "
            f"{_md(item['replacement'] or '')} | {_md(item['description'])} |"
        )
    lines.extend(
        [
            "",
            "## Escalation rule",
            "",
            "The workflow never opens or edits issues. For any drift without an existing issue, "
            "the accountable owner copies the control ID, evidence, risk, decision, and due date "
            "into a manually created `governance` issue and links this report.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise GitHubReviewError("unsupported GitHub governance policy schema")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("configs/quality/github_governance_policy.json"),
    )
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, required=True)
    parser.add_argument(
        "--source-git-ref",
        default="HEAD",
        help="Read-only git ref recorded as the reviewed source (default: HEAD).",
    )
    parser.add_argument("--fail-on-drift", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = resolve_cli_path(args.repo_root)
    policy_path = resolve_cli_path(args.policy, root=repo_root)
    policy = _load_policy(policy_path)
    client = ReadOnlyGitHubClient(repo_root)
    snapshot = collect_snapshot(
        client,
        repo_root,
        policy,
        source_git_ref=args.source_git_ref,
    )
    report = build_report(snapshot, policy)

    for output_path, content in (
        (args.json_out, json.dumps(report, indent=2, sort_keys=True) + "\n"),
        (args.markdown_out, render_markdown(report)),
    ):
        target = resolve_output_path(output_path, root=repo_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(tmp, target)

    sys.stdout.write(
        "GitHub governance review: "
        f"{report['review']['overall']} "
        f"({json.dumps(report['review']['counts'], sort_keys=True)})\n"
    )
    if args.fail_on_drift and report["review"]["overall"] != "conformant":
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GitHubReviewError, json.JSONDecodeError, OSError, ValueError) as error:
        sys.stderr.write(f"GitHub governance review failed: {error}\n")
        raise SystemExit(2) from error
