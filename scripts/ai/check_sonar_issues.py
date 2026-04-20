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


def main() -> None:
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO", DEFAULT_REPO)

    print("🔍 Analyzing Sonar Remediation Issues Relevance")
    print("=" * 60)

    for issue_number in DEFAULT_ISSUES_TO_CHECK:
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo}/issues/{issue_number}",
                headers=_github_headers(github_token),
                timeout=30,
            )

            if response.status_code != 200:
                print(f"\n❌ Issue #{issue_number}: Not found or inaccessible")
                continue

            issue = response.json()
            comments_response = requests.get(
                f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
                headers=_github_headers(github_token, include_accept=False),
                timeout=30,
            )
            comments_count = (
                len(comments_response.json()) if comments_response.status_code == 200 else 0
            )
            _print_issue_summary(issue_number, issue, comments_count=comments_count)

        except requests.exceptions.RequestException as exc:
            print(f"\n❌ Network error checking issue #{issue_number}: {exc}")
        except json.JSONDecodeError as exc:
            print(f"\n❌ JSON decode error for issue #{issue_number}: {exc}")
        except (KeyError, ValueError, IndexError) as exc:
            if isinstance(exc, KeyError):
                print(f"\n❌ Missing expected field in issue #{issue_number}: {exc}")
            else:
                print(f"\n❌ Expected error checking issue #{issue_number}: {exc}")
        except Exception as exc:
            print(f"\n❌ Unexpected error checking issue #{issue_number}: {exc}")
            raise

    print("\n" + "=" * 60)
    print("📊 SUMMARY ANALYSIS")
    print("=" * 60)
    print("These issues appear to be part of a structured Sonar remediation program.")
    print("The numbering suggests a wave-based approach to code quality improvement.")
    print("\nRecommendation: Check if these issues are still relevant given current Sonar status.")


if __name__ == "__main__":
    main()
