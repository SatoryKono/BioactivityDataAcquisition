#!/usr/bin/env python3
"""Preview or apply metadata updates for the docs-sync issue pack.

Usage:
    python -m scripts.engineering.repo sync-docs-issues --help
    python scripts/engineering/repo/sync_docs_issues.py
    python scripts/engineering/repo/sync_docs_issues.py --apply --create-milestone

By default, the script runs in dry-run mode and prints the labels, milestone,
and comments it would apply to the documentation-sync issue set.

Real writes require ``--apply`` and a GitHub token in
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
DEFAULT_TOKEN_ENV: Final[str] = "GITHUB_PERSONAL_ACCESS_TOKEN"
DEFAULT_MILESTONE_TITLE: Final[str] = "Documentation Sync Foundations"
DEFAULT_MILESTONE_DESCRIPTION: Final[str] = (
    "Foundational work to stabilize documentation verification, unify the "
    "published verification entrypoint, add a recurring code-sync watchlist, "
    "and clarify reports governance."
)
MAX_HTTP_RETRIES: Final[int] = 4
RETRYABLE_HTTP_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {429, 500, 502, 503, 504}
)
DEFAULT_RETRY_DELAY_SECONDS: Final[float] = 1.5


@dataclass(frozen=True)
class IssueUpdate:
    """Target issue mutation for the docs-sync package."""

    number: int
    title: str
    labels: tuple[str, ...]
    comment: str


@dataclass(frozen=True)
class MilestoneRecord:
    """GitHub milestone metadata."""

    number: int
    title: str
    url: str


def _build_issue_updates() -> list[IssueUpdate]:
    return [
        IssueUpdate(
            number=2637,
            title="docs: stabilize uv docs verification and add CI gate",
            labels=(
                "documentation",
                "ci/cd",
                "developer-experience",
                "python:uv",
                "priority:high",
                "codex",
            ),
            comment=(
                "Suggested execution order anchor for this workstream:\n\n"
                "1. #2637\n"
                "2. #2638\n"
                "3. #2640\n"
                "4. #2639\n\n"
                "This issue should land first because the other doc-sync tasks "
                "benefit from a stable verification gate and reproducible `uv` "
                "docs toolchain."
            ),
        ),
        IssueUpdate(
            number=2638,
            title="docs: make docs-verification guide the single published entrypoint",
            labels=("documentation", "enhancement", "priority:high", "codex"),
            comment=(
                "Suggested dependency/order note:\n\n"
                "- Follow #2637 first to avoid documenting a verification flow "
                "that still fails in practice.\n"
                "- Once this issue lands, #2640 can extend the guide with the "
                "recurring watchlist.\n"
                "- #2639 can then align reports governance to the published "
                "verification boundary."
            ),
        ),
        IssueUpdate(
            number=2640,
            title="docs: add live code-sync watchlist for recurring documentation audits",
            labels=("documentation", "enhancement", "priority:medium", "codex"),
            comment=(
                "Suggested dependency/order note:\n\n"
                "- Depends conceptually on #2638, because the watchlist should "
                "extend the canonical `docs-verification.md` entrypoint rather "
                "than create a parallel workflow."
            ),
        ),
        IssueUpdate(
            number=2639,
            title="docs: define lightweight governance model for reports directory",
            labels=("documentation", "cleanup", "priority:medium", "codex"),
            comment=(
                "Suggested dependency/order note:\n\n"
                "- Best tackled after #2638 and #2640, so the governance model "
                "for `reports/**` can reference the canonical published "
                "verification flow and the new live code-sync watchlist.\n"
                "- This issue can start earlier in parallel if the work is "
                "limited to taxonomy and boundary wording."
            ),
        ),
    ]


def _require_token(token_env: str) -> str:
    token = os.getenv(token_env, "").strip()
    if not token:
        raise ValueError(f"Missing GitHub token in environment variable: {token_env}")
    return token


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


def _github_request(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, object] | None = None,
) -> tuple[Any, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "bioetl-docs-sync-issue-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

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
                charset = response.headers.get_content_charset("utf-8")
                raw = response.read().decode(charset)
                body = json.loads(raw) if raw else None
                return body, dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            charset = exc.headers.get_content_charset("utf-8")
            raw = exc.read().decode(charset)
            detail = raw
            try:
                parsed = json.loads(raw)
                detail = json.dumps(parsed, ensure_ascii=True)
            except json.JSONDecodeError:
                pass

            if exc.code in RETRYABLE_HTTP_STATUS_CODES and attempt < MAX_HTTP_RETRIES:
                delay = _resolve_retry_delay_seconds(
                    retry_after=exc.headers.get("Retry-After"),
                    attempt=attempt,
                )
                print(
                    f"[WARN] GitHub API {method} {url} returned {exc.code}; "
                    f"retrying in {delay:.1f}s (attempt {attempt}/{MAX_HTTP_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue

            raise RuntimeError(f"GitHub API {method} {url} failed: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < MAX_HTTP_RETRIES:
                delay = _resolve_retry_delay_seconds(
                    retry_after=None,
                    attempt=attempt,
                )
                print(
                    f"[WARN] GitHub API {method} {url} failed with network error "
                    f"{exc.reason!r}; retrying in {delay:.1f}s "
                    f"(attempt {attempt}/{MAX_HTTP_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            raise RuntimeError(
                f"GitHub API {method} {url} failed with network error: {exc.reason!r}"
            ) from exc


def _milestones_api_url(owner: str, repo: str) -> str:
    return f"{API_BASE}/repos/{owner}/{repo}/milestones"


def _issue_api_url(owner: str, repo: str, number: int) -> str:
    return f"{API_BASE}/repos/{owner}/{repo}/issues/{number}"


def _issue_comments_api_url(owner: str, repo: str, number: int) -> str:
    return f"{API_BASE}/repos/{owner}/{repo}/issues/{number}/comments"


def _find_milestone(
    *,
    owner: str,
    repo: str,
    token: str,
    title: str,
) -> MilestoneRecord | None:
    page = 1
    while True:
        query = urllib.parse.urlencode({"state": "all", "per_page": 100, "page": page})
        payload, _headers = _github_request(
            method="GET",
            url=f"{_milestones_api_url(owner, repo)}?{query}",
            token=token,
        )
        if not isinstance(payload, list) or not payload:
            return None
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("title") != title:
                continue
            number = item.get("number")
            html_url = item.get("html_url")
            if isinstance(number, int) and isinstance(html_url, str):
                return MilestoneRecord(number=number, title=title, url=html_url)
        page += 1


def _create_milestone(
    *,
    owner: str,
    repo: str,
    token: str,
    title: str,
    description: str,
) -> MilestoneRecord:
    payload, _headers = _github_request(
        method="POST",
        url=_milestones_api_url(owner, repo),
        token=token,
        payload={"title": title, "description": description},
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected milestone response for '{title}'")
    number = payload.get("number")
    html_url = payload.get("html_url")
    if not isinstance(number, int) or not isinstance(html_url, str):
        raise RuntimeError(f"Incomplete milestone response for '{title}'")
    return MilestoneRecord(number=number, title=title, url=html_url)


def _ensure_milestone(
    *,
    owner: str,
    repo: str,
    token: str,
    title: str,
    description: str,
    create_missing: bool,
) -> MilestoneRecord | None:
    existing = _find_milestone(owner=owner, repo=repo, token=token, title=title)
    if existing is not None:
        return existing
    if not create_missing:
        return None
    return _create_milestone(
        owner=owner,
        repo=repo,
        token=token,
        title=title,
        description=description,
    )


def _patch_issue(
    *,
    owner: str,
    repo: str,
    token: str,
    issue: IssueUpdate,
    milestone_number: int | None,
) -> None:
    payload: dict[str, object] = {"labels": list(issue.labels)}
    if milestone_number is not None:
        payload["milestone"] = milestone_number
    _github_request(
        method="PATCH",
        url=_issue_api_url(owner, repo, issue.number),
        token=token,
        payload=payload,
    )


def _post_comment(
    *,
    owner: str,
    repo: str,
    token: str,
    issue: IssueUpdate,
) -> None:
    _github_request(
        method="POST",
        url=_issue_comments_api_url(owner, repo, issue.number),
        token=token,
        payload={"body": issue.comment},
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or apply metadata updates for the docs-sync issue pack."
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    parser.add_argument(
        "--issue",
        action="append",
        type=int,
        dest="issues",
        help="Limit updates to the specified issue number. Repeatable.",
    )
    parser.add_argument(
        "--milestone-title",
        default=DEFAULT_MILESTONE_TITLE,
        help="Milestone title to attach to the issue pack.",
    )
    parser.add_argument(
        "--milestone-description",
        default=DEFAULT_MILESTONE_DESCRIPTION,
        help="Milestone description used when creating the milestone.",
    )
    parser.add_argument(
        "--create-milestone",
        action="store_true",
        help="Create the milestone when it does not already exist.",
    )
    parser.add_argument(
        "--skip-milestone",
        action="store_true",
        help="Do not attempt to resolve or set milestone metadata.",
    )
    parser.add_argument(
        "--skip-comments",
        action="store_true",
        help="Do not post execution-order comments.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply labels/milestone/comments instead of showing a dry-run preview.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a compact JSON summary instead of prose output.",
    )
    return parser.parse_args(argv)


def _select_updates(
    updates: list[IssueUpdate], selected_numbers: list[int] | None
) -> list[IssueUpdate]:
    if not selected_numbers:
        return updates
    selected = set(selected_numbers)
    return [item for item in updates if item.number in selected]


def _print_dry_run(
    *,
    owner: str,
    repo: str,
    updates: list[IssueUpdate],
    milestone_title: str | None,
    skip_comments: bool,
) -> None:
    print("[DRY-RUN] Docs-sync issue metadata plan\n")
    print(f"Repository: {owner}/{repo}")
    if milestone_title is not None:
        print(f"Milestone: {milestone_title}")
    else:
        print("Milestone: <skipped>")
    print()
    for issue in updates:
        print(f"=== #{issue.number} {issue.title} ===")
        print(f"Labels: {', '.join(issue.labels)}")
        if skip_comments:
            print("Comment: <skipped>")
        else:
            print("Comment:")
            print(issue.comment)
        print()


def _print_json_payload(
    *,
    owner: str,
    repo: str,
    updates: list[IssueUpdate],
    milestone_title: str | None,
    skip_comments: bool,
) -> None:
    payload = {
        "owner": owner,
        "repo": repo,
        "milestone_title": milestone_title,
        "skip_comments": skip_comments,
        "issues": [
            {
                "number": issue.number,
                "title": issue.title,
                "labels": list(issue.labels),
                "comment": None if skip_comments else issue.comment,
            }
            for issue in updates
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    updates = _select_updates(_build_issue_updates(), args.issues)
    if not updates:
        raise ValueError("No matching docs-sync issues selected.")

    milestone_title = None if args.skip_milestone else args.milestone_title
    if not args.apply:
        if args.json:
            _print_json_payload(
                owner=args.owner,
                repo=args.repo,
                updates=updates,
                milestone_title=milestone_title,
                skip_comments=args.skip_comments,
            )
        else:
            _print_dry_run(
                owner=args.owner,
                repo=args.repo,
                updates=updates,
                milestone_title=milestone_title,
                skip_comments=args.skip_comments,
            )
        return len(updates)

    token = _require_token(args.token_env)
    milestone: MilestoneRecord | None = None
    mutation_count = 0
    if not args.skip_milestone:
        milestone = _ensure_milestone(
            owner=args.owner,
            repo=args.repo,
            token=token,
            title=args.milestone_title,
            description=args.milestone_description,
            create_missing=args.create_milestone,
        )
        mutation_count += 1

    for issue in updates:
        _patch_issue(
            owner=args.owner,
            repo=args.repo,
            token=token,
            issue=issue,
            milestone_number=None if milestone is None else milestone.number,
        )
        mutation_count += 1
        if not args.skip_comments:
            _post_comment(
                owner=args.owner,
                repo=args.repo,
                token=token,
                issue=issue,
            )
            mutation_count += 1

    if args.json:
        payload = {
            "owner": args.owner,
            "repo": args.repo,
            "milestone": None
            if milestone is None
            else {
                "number": milestone.number,
                "title": milestone.title,
                "url": milestone.url,
            },
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "labels": list(issue.labels),
                    "comment_posted": not args.skip_comments,
                }
                for issue in updates
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("Applied docs-sync issue updates:")
        if milestone is None:
            print("- Milestone: <not set>")
        else:
            print(
                f"- Milestone: {milestone.title} (#{milestone.number}, {milestone.url})"
            )
        for issue in updates:
            print(f"- #{issue.number} {issue.title}")
            print(f"  Labels: {', '.join(issue.labels)}")
            if args.skip_comments:
                print("  Comment: <skipped>")
            else:
                print("  Comment: posted")
    return mutation_count


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
