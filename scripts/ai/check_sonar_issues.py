#!/usr/bin/env python3
"""Check whether historical Sonar remediation GitHub issues still look relevant."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Final

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_REPO: Final[str] = "SatoryKono/BioactivityDataAcquisition"
DEFAULT_ISSUES_TO_CHECK: Final[tuple[int, ...]] = (2988, 2987, 2986, 2985)
EXPECTED_ISSUE_ERRORS: Final[tuple[type[Exception], ...]] = (
    requests.exceptions.RequestException,
    json.JSONDecodeError,
    KeyError,
    ValueError,
    IndexError,
)
ERROR_LABELS: Final[tuple[tuple[type[Exception], str], ...]] = (
    (requests.exceptions.RequestException, "Network error"),
    (json.JSONDecodeError, "JSON decode error"),
    (KeyError, "Missing expected field"),
    (ValueError, "Expected error"),
    (IndexError, "Expected error"),
)


def _github_headers(token: str | None, *, include_accept: bool = True) -> dict[str, str]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"token {token}"
    if include_accept:
        headers["Accept"] = "application/vnd.github.v3+json"
    return headers


def _issue_status_label(*, state: str, age_days: int, comments_count: int) -> str:
    if age_days > 30 and comments_count == 0:
        return "⚠️  STALE - No recent activity"
    if state == "closed":
        return "✅ COMPLETED"
    return "🔄 ACTIVE"


def _print_issue_summary(
    issue_number: int,
    issue: dict[str, object],
    *,
    comments_count: int,
) -> None:
    created_at = datetime.fromisoformat(str(issue["created_at"]).replace("Z", "+00:00"))
    age_days = (datetime.now(UTC) - created_at).days
    state = str(issue["state"])

    print(f'\n📋 Issue #{issue_number}: {issue["title"]}')
    print(f'Status: {"OPEN" if state == "open" else "CLOSED"}')
    print(f"Age: {age_days} days old")
    print(f"Comments: {comments_count}")
    print(f'Updated: {issue["updated_at"]}')
    print(f"Relevance: {_issue_status_label(state=state, age_days=age_days, comments_count=comments_count)}")

    body = str(issue.get("body", "") or "")
    if body:
        first_line = body.split("\n", 1)[0][:80]
        print(f"Content: {first_line}...")

    print(f'URL: {issue["html_url"]}')


def _fetch_issue(
    repo: str,
    github_token: str | None,
    issue_number: int,
) -> requests.Response:
    return requests.get(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}",
        headers=_github_headers(github_token),
        timeout=30,
    )


def _fetch_comments_count(
    repo: str,
    github_token: str | None,
    issue_number: int,
) -> int:
    comments_response = requests.get(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        headers=_github_headers(github_token, include_accept=False),
        timeout=30,
    )
    if comments_response.status_code != 200:
        return 0
    return len(comments_response.json())


def _load_issue_details(
    repo: str,
    github_token: str | None,
    issue_number: int,
) -> tuple[dict[str, object] | None, int]:
    response = _fetch_issue(repo, github_token, issue_number)
    if response.status_code != 200:
        return None, 0
    issue = response.json()
    comments_count = _fetch_comments_count(repo, github_token, issue_number)
    return issue, comments_count


def _report_issue_error(issue_number: int, exc: Exception) -> None:
    for error_type, label in ERROR_LABELS:
        if isinstance(exc, error_type):
            print(f"\n❌ {label} checking issue #{issue_number}: {exc}")
            return
    print(f"\n❌ Unexpected error checking issue #{issue_number}: {exc}")


def _is_expected_issue_error(exc: Exception) -> bool:
    return isinstance(exc, EXPECTED_ISSUE_ERRORS)


def _print_report_header() -> None:
    print("🔍 Analyzing Sonar Remediation Issues Relevance")
    print("=" * 60)


def _print_report_footer() -> None:
    print("\n" + "=" * 60)
    print("📊 SUMMARY ANALYSIS")
    print("=" * 60)
    print("These issues appear to be part of a structured Sonar remediation program.")
    print("The numbering suggests a wave-based approach to code quality improvement.")
    print("\nRecommendation: Check if these issues are still relevant given current Sonar status.")


def _process_issue(repo: str, github_token: str | None, issue_number: int) -> None:
    try:
        issue, comments_count = _load_issue_details(repo, github_token, issue_number)
        if issue is None:
            print(f"\n❌ Issue #{issue_number}: Not found or inaccessible")
            return
        _print_issue_summary(issue_number, issue, comments_count=comments_count)
    except Exception as exc:
        _report_issue_error(issue_number, exc)
        if not _is_expected_issue_error(exc):
            raise


def main() -> None:
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO", DEFAULT_REPO)
    _print_report_header()

    for issue_number in DEFAULT_ISSUES_TO_CHECK:
        _process_issue(repo, github_token, issue_number)

    _print_report_footer()


if __name__ == "__main__":
    main()
