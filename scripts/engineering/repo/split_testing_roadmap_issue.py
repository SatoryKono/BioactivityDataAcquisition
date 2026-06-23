#!/usr/bin/env python3
"""Create or preview the #2511 testing-roadmap child issues.

Usage:
    python -m scripts.engineering.repo split-testing-roadmap --help
    python scripts/engineering/repo/split_testing_roadmap_issue.py
    python scripts/engineering/repo/split_testing_roadmap_issue.py --apply --comment-parent

By default, the script runs in dry-run mode and prints the issue bodies plus the
parent follow-up comment. Real writes require ``--apply`` and a GitHub token in
``GITHUB_PERSONAL_ACCESS_TOKEN`` (or another env var via ``--token-env``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Final

API_BASE: Final[str] = "https://api.github.com"
DEFAULT_OWNER: Final[str] = "SatoryKono"
DEFAULT_REPO: Final[str] = "BioactivityDataAcquisition"
DEFAULT_PARENT_ISSUE: Final[int] = 2511
DEFAULT_TOKEN_ENV: Final[str] = "GITHUB_PERSONAL_ACCESS_TOKEN"
MAX_HTTP_RETRIES: Final[int] = 4
RETRYABLE_HTTP_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {429, 500, 502, 503, 504}
)
DEFAULT_RETRY_DELAY_SECONDS: Final[float] = 1.5


@dataclass(frozen=True)
class IssueTemplate:
    """Immutable issue template definition."""

    title: str
    body: str
    track_summary: str


@dataclass(frozen=True)
class IssueRecord:
    """Existing or newly created GitHub issue."""

    number: int
    title: str
    url: str
    state: str


def _build_child_issue_templates(parent_issue: int) -> list[IssueTemplate]:
    parent_ref = f"#{parent_issue}"
    return [
        IssueTemplate(
            title="Unit Test Standards Baseline for Pure Transformation Logic",
            body=(
                "## Summary\n\n"
                f"Split out the unit-test standards track from {parent_ref} into "
                "an executable issue focused on defining and applying a baseline "
                "standard for pure transformation logic.\n\n"
                "## Why\n\n"
                "The parent roadmap issue is intentionally broad. This child issue "
                "isolates the unit-testing slice so it can be implemented and "
                "verified independently.\n\n"
                "## Scope\n\n"
                "- Define the expected structure and quality bar for unit tests "
                "around pure transformation logic.\n"
                "- Document baseline expectations for deterministic "
                "inputs/outputs, edge cases, and failure cases.\n"
                "- Add or tighten targeted coverage in a small set of high-value "
                "transformation modules rather than chasing blanket coverage.\n"
                "- Make the preferred execution path for these tests explicit in "
                "local and CI workflows.\n\n"
                "## Edge Cases to Cover First\n\n"
                "- Empty inputs\n"
                "- Malformed inputs\n"
                "- Unicode handling where relevant\n"
                "- Null or missing-value handling where relevant\n\n"
                "## Out of Scope\n\n"
                "- Blanket repository-wide coverage targets\n"
                "- Integration or VCR workflows\n"
                "- Provider contract drift automation\n"
                "- Broad data validation gates\n\n"
                "## Acceptance Criteria\n\n"
                "- [ ] Unit-test expectations for pure transformation logic are "
                "documented.\n"
                "- [ ] A small set of high-value transformation modules is "
                "brought up to the new baseline.\n"
                "- [ ] Edge-case expectations are explicitly covered for the "
                "selected modules.\n"
                "- [ ] The implementation fits the current testing and "
                "governance model.\n\n"
                "## Parent\n\n"
                f"- Split out of {parent_ref}\n"
            ),
            track_summary=(
                "Unit-test baseline for pure transformation logic, focused on "
                "determinism and edge-case coverage."
            ),
        ),
        IssueTemplate(
            title="Integration and VCR Policy Tightening for Supported Pipelines",
            body=(
                "## Summary\n\n"
                f"Split out the integration and cassette-governance track from "
                f"{parent_ref} into a focused issue covering integration, e2e, "
                "and VCR execution policy.\n\n"
                "## Why\n\n"
                "The repository already has integration and VCR coverage, but the "
                "remaining work is mostly about tightening conventions and making "
                "supported execution paths explicit.\n\n"
                "## Scope\n\n"
                "- Clarify integration and e2e expectations for supported "
                "pipeline families.\n"
                "- Define and document fixture and cassette expectations.\n"
                "- Make the supported local and CI execution paths explicit.\n"
                "- Tighten governance around when cassettes should be refreshed, "
                "reviewed, or treated as stale.\n\n"
                "## Out of Scope\n\n"
                "- Full replay system redesign\n"
                "- Blanket rewrite of all existing cassettes in one pass\n"
                "- Provider contract drift automation\n"
                "- Broad schema validation rollout\n\n"
                "## Acceptance Criteria\n\n"
                "- [ ] Integration and e2e expectations are documented for the "
                "intended scope.\n"
                "- [ ] Fixture and cassette handling rules are explicit and "
                "actionable.\n"
                "- [ ] Local and CI execution paths are documented and aligned "
                "with the current toolchain.\n"
                "- [ ] The resulting policy can be extended incrementally without "
                "reworking the full test stack.\n\n"
                "## Parent\n\n"
                f"- Split out of {parent_ref}\n"
            ),
            track_summary=(
                "Integration, e2e, and VCR policy tightening for supported "
                "pipeline families."
            ),
        ),
        IssueTemplate(
            title="Provider Contract Drift Checks MVP for External Schemas and Fields",
            body=(
                "## Summary\n\n"
                f"Split out the provider contract-drift track from {parent_ref} "
                "into a small executable MVP for detecting high-signal external "
                "schema or field drift.\n\n"
                "## Why\n\n"
                "The parent roadmap identifies contract drift as a real risk "
                "area, but it is too broad to execute as a roadmap item alone. "
                "This issue narrows the work to a minimal, high-value CI check.\n\n"
                "## Scope\n\n"
                "- Identify one or a small set of providers where schema or "
                "field drift risk is highest.\n"
                "- Define a lightweight baseline for expected fields or payload "
                "shape.\n"
                "- Add focused checks that flag drift with readable diagnostics.\n"
                "- Keep the implementation small enough to extend incrementally "
                "provider by provider.\n\n"
                "## Out of Scope\n\n"
                "- Full platform-wide contract testing framework\n"
                "- Broad compatibility governance across every layer\n"
                "- Full consumer notification workflows\n"
                "- Gold-layer compatibility checks already covered separately by "
                "#2516\n\n"
                "## Acceptance Criteria\n\n"
                "- [ ] At least one high-risk provider is covered by a focused "
                "drift check.\n"
                "- [ ] Drift produces readable diagnostics in test or CI output.\n"
                "- [ ] The baseline and extension path are documented.\n"
                "- [ ] The implementation aligns with the current testing and "
                "governance model.\n\n"
                "## Parent\n\n"
                f"- Split out of {parent_ref}\n\n"
                "## Related\n\n"
                "- Complements #2516 rather than replacing it\n"
            ),
            track_summary=(
                "Focused provider contract drift checks for external schemas or "
                "field-shape changes."
            ),
        ),
    ]


def _track_summary_for_title(title: str) -> str:
    for template in _build_child_issue_templates(DEFAULT_PARENT_ISSUE):
        if template.title == title:
            return template.track_summary
    return "Roadmap slice."


def _build_parent_comment(*, parent_issue: int, child_issues: list[IssueRecord]) -> str:
    lines = [
        "Split the testing roadmap into executable child issues so the parent "
        "can stay roadmap-shaped while implementation moves in smaller slices.",
        "",
        "Created or confirmed child issues:",
        "",
    ]
    for issue in child_issues:
        lines.append(f"- #{issue.number} {issue.title}")
        lines.append(f"  Scope: {_track_summary_for_title(issue.title)}")

    lines.extend(
        [
            "",
            "Existing related work kept as linked tracks:",
            "",
            "- #2594 Pandera Schema Drift Checks for Selected Pipelines",
            "- #2516 Gold Schema Compatibility CI Gate (ADR-036 MVP)",
            "",
            f"Parent roadmap remains #{parent_issue}.",
        ]
    )
    return "\n".join(lines)


def _require_token(token_env: str) -> str:
    token = os.getenv(token_env, "").strip()
    if not token:
        raise ValueError(f"Missing GitHub token in environment variable: {token_env}")
    return token


def _request_headers(
    token: str, payload: dict[str, object] | None
) -> tuple[dict[str, str], bytes | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "bioetl-testing-roadmap-splitter",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is None:
        return headers, None

    headers["Content-Type"] = "application/json"
    return headers, json.dumps(payload).encode("utf-8")


def _decode_response_body(response: Any) -> Any:
    charset = response.headers.get_content_charset("utf-8")
    raw = response.read().decode(charset)
    return json.loads(raw) if raw else None


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    charset = exc.headers.get_content_charset("utf-8")
    raw = exc.read().decode(charset)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    return json.dumps(parsed, ensure_ascii=True)


def _maybe_retry_http_error(
    *,
    exc: urllib.error.HTTPError,
    attempt: int,
    method: str,
    url: str,
) -> bool:
    if exc.code not in RETRYABLE_HTTP_STATUS_CODES or attempt >= MAX_HTTP_RETRIES:
        return False

    retry_after = exc.headers.get("Retry-After")
    delay = _resolve_retry_delay_seconds(
        retry_after=retry_after,
        attempt=attempt,
    )
    print(
        f"[WARN] GitHub API {method} {url} returned {exc.code}; retrying in {delay:.1f}s "
        f"(attempt {attempt}/{MAX_HTTP_RETRIES})",
        file=sys.stderr,
    )
    time.sleep(delay)
    return True


def _maybe_retry_url_error(
    *,
    exc: urllib.error.URLError,
    attempt: int,
    method: str,
    url: str,
) -> bool:
    if attempt >= MAX_HTTP_RETRIES:
        return False

    delay = _resolve_retry_delay_seconds(
        retry_after=None,
        attempt=attempt,
    )
    print(
        f"[WARN] GitHub API {method} {url} failed with network error {exc.reason!r}; retrying in {delay:.1f}s "
        f"(attempt {attempt}/{MAX_HTTP_RETRIES})",
        file=sys.stderr,
    )
    time.sleep(delay)
    return True


def _github_request(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, object] | None = None,
) -> tuple[Any, dict[str, str]]:
    headers, data = _request_headers(token, payload)

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(request) as response:
                body = _decode_response_body(response)
                return body, dict(response.headers.items())
        except urllib.error.HTTPError as exc:  # pragma: no cover - CLI path
            if _maybe_retry_http_error(
                exc=exc, attempt=attempt, method=method, url=url
            ):
                continue
            detail = _http_error_detail(exc)
            raise RuntimeError(f"GitHub API {method} {url} failed: {detail}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - CLI path
            if _maybe_retry_url_error(exc=exc, attempt=attempt, method=method, url=url):
                continue
            raise RuntimeError(
                f"GitHub API {method} {url} failed with network error: {exc.reason!r}"
            ) from exc


def _resolve_retry_delay_seconds(
    *,
    retry_after: str | None,
    attempt: int,
) -> float:
    if retry_after is not None:
        try:
            parsed = float(retry_after)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return DEFAULT_RETRY_DELAY_SECONDS * attempt


def _list_repo_issues(owner: str, repo: str, token: str) -> list[IssueRecord]:
    issues: list[IssueRecord] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"state": "all", "per_page": 100, "page": page})
        url = f"{API_BASE}/repos/{owner}/{repo}/issues?{query}"
        payload, _headers = _github_request(method="GET", url=url, token=token)
        if not isinstance(payload, list) or not payload:
            break
        for item in payload:
            if not isinstance(item, dict) or "pull_request" in item:
                continue
            number = item.get("number")
            title = item.get("title")
            html_url = item.get("html_url")
            state = item.get("state")
            if (
                isinstance(number, int)
                and isinstance(title, str)
                and isinstance(html_url, str)
                and isinstance(state, str)
            ):
                issues.append(
                    IssueRecord(number=number, title=title, url=html_url, state=state)
                )
        page += 1
    return issues


def _find_existing_issue(
    issues: list[IssueRecord], *, title: str
) -> IssueRecord | None:
    for issue in issues:
        if issue.title == title:
            return issue
    return None


def _create_issue(
    *,
    owner: str,
    repo: str,
    token: str,
    template: IssueTemplate,
) -> IssueRecord:
    url = f"{API_BASE}/repos/{owner}/{repo}/issues"
    payload, _headers = _github_request(
        method="POST",
        url=url,
        token=token,
        payload={"title": template.title, "body": template.body},
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected GitHub response for issue '{template.title}'")

    number = payload.get("number")
    title = payload.get("title")
    html_url = payload.get("html_url")
    state = payload.get("state")
    if (
        not isinstance(number, int)
        or not isinstance(title, str)
        or not isinstance(html_url, str)
        or not isinstance(state, str)
    ):
        raise RuntimeError(f"Incomplete GitHub response for issue '{template.title}'")

    return IssueRecord(number=number, title=title, url=html_url, state=state)


def _post_parent_comment(
    *,
    owner: str,
    repo: str,
    parent_issue: int,
    token: str,
    body: str,
) -> None:
    url = f"{API_BASE}/repos/{owner}/{repo}/issues/{parent_issue}/comments"
    _payload, _headers = _github_request(
        method="POST",
        url=url,
        token=token,
        payload={"body": body},
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or preview the #2511 testing-roadmap child issues."
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--parent-issue", type=int, default=DEFAULT_PARENT_ISSUE)
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing child issues in GitHub instead of dry-run preview.",
    )
    parser.add_argument(
        "--comment-parent",
        action="store_true",
        help="Post the generated follow-up comment into the parent issue.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a compact JSON summary instead of prose output.",
    )
    return parser.parse_args(argv)


def _print_dry_run(*, templates: list[IssueTemplate], comment_body: str) -> None:
    print("[DRY-RUN] Prepared child issues:\n")
    for template in templates:
        print(f"=== {template.title} ===")
        print(template.body.strip())
        print()
    print("=== Parent Comment Preview ===")
    print(comment_body)


def _print_json_payload(
    *,
    owner: str,
    repo: str,
    parent_issue: int,
    child_issues: list[IssueRecord],
    comment_body: str,
) -> None:
    payload = {
        "owner": owner,
        "repo": repo,
        "parent_issue": parent_issue,
        "child_issues": [
            {
                "number": issue.number,
                "title": issue.title,
                "url": issue.url,
                "state": issue.state,
            }
            for issue in child_issues
        ],
        "parent_comment": comment_body,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    templates = _build_child_issue_templates(args.parent_issue)

    if not args.apply:
        child_issues = [
            IssueRecord(number=0, title=item.title, url="", state="planned")
            for item in templates
        ]
        comment_body = _build_parent_comment(
            parent_issue=args.parent_issue,
            child_issues=child_issues,
        )
        if args.json:
            _print_json_payload(
                owner=args.owner,
                repo=args.repo,
                parent_issue=args.parent_issue,
                child_issues=child_issues,
                comment_body=comment_body,
            )
        else:
            _print_dry_run(templates=templates, comment_body=comment_body)
        return len(child_issues)

    token = _require_token(args.token_env)
    existing_issues = _list_repo_issues(args.owner, args.repo, token)
    resolved_issues: list[IssueRecord] = []
    created_count = 0

    for template in templates:
        existing = _find_existing_issue(existing_issues, title=template.title)
        if existing is not None:
            resolved_issues.append(existing)
            continue
        created = _create_issue(
            owner=args.owner,
            repo=args.repo,
            token=token,
            template=template,
        )
        resolved_issues.append(created)
        created_count += 1

    comment_body = _build_parent_comment(
        parent_issue=args.parent_issue,
        child_issues=resolved_issues,
    )
    if args.comment_parent:
        _post_parent_comment(
            owner=args.owner,
            repo=args.repo,
            parent_issue=args.parent_issue,
            token=token,
            body=comment_body,
        )

    if args.json:
        _print_json_payload(
            owner=args.owner,
            repo=args.repo,
            parent_issue=args.parent_issue,
            child_issues=resolved_issues,
            comment_body=comment_body,
        )
    else:
        print("Prepared testing-roadmap child issues:")
        for issue in resolved_issues:
            print(f"- #{issue.number} {issue.title} ({issue.url})")
        if args.comment_parent:
            print(f"\nPosted follow-up comment to #{args.parent_issue}.")
        else:
            print(f"\nParent comment preview:\n\n{comment_body}")
    return created_count


def main(argv: list[str] | None = None) -> int:
    try:
        run(argv)
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
