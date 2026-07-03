#!/usr/bin/env python3
"""Publish TEST-AUDIT issues from ``.github/ISSUES/TEST-AUDIT-*.md``.

Usage:
    python scripts/engineering/repo/publish_test_audit_issues.py
    python scripts/engineering/repo/publish_test_audit_issues.py --apply
    python scripts/engineering/repo/publish_test_audit_issues.py --apply --codes TEST-AUDIT-013,TEST-AUDIT-014 --update-pack

Requires a GitHub token in ``GITHUB_TOKEN`` or ``GITHUB_PERSONAL_ACCESS_TOKEN``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal envs
    load_dotenv = None  # type: ignore[assignment]

API_BASE: Final[str] = "https://api.github.com"
DEFAULT_OWNER: Final[str] = "SatoryKono"
DEFAULT_REPO: Final[str] = "BioactivityDataAcquisition"
DEFAULT_TOKEN_ENV: Final[str] = "GITHUB_TOKEN"
ISSUES_DIR: Final[Path] = Path(__file__).resolve().parents[3] / ".github" / "ISSUES"
DEFAULT_ISSUE_PACK: Final[Path] = ISSUES_DIR / "TEST-AUDIT-2026-07-03-ISSUE-PACK.md"
ISSUE_PACK_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^TEST-AUDIT-\d{3}-.+\.md$",
)


@dataclass(frozen=True)
class IssueDraft:
    """Parsed local issue template."""

    code: str
    path: Path
    title: str
    body: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class IssueRecord:
    """Created or existing GitHub issue."""

    number: int
    title: str
    url: str
    state: str
    action: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_token(token_env: str) -> str:
    env_path = _repo_root() / ".env"
    if load_dotenv is not None:
        load_dotenv(env_path)
    else:
        _load_dotenv_file(env_path)
    for env_name in (token_env, "GITHUB_PERSONAL_ACCESS_TOKEN", "GH_TOKEN"):
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    raise ValueError(
        "Missing GitHub token. Set GITHUB_TOKEN or GITHUB_PERSONAL_ACCESS_TOKEN."
    )


def _github_request(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
            return {} if not raw else json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < 4:
                time.sleep(1.5 * attempt)
                continue
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {method} {url} failed: {exc.code} {detail}") from exc
    raise RuntimeError(f"GitHub API {method} {url} exhausted retries")


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, flags=re.DOTALL)
    if not match:
        raise ValueError("Issue markdown is missing YAML frontmatter")
    frontmatter_raw, body = match.groups()
    frontmatter: dict[str, str] = {}
    for line in frontmatter_raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter, body.lstrip("\n")


def _parse_labels(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(label.strip() for label in raw.split(",") if label.strip())


def _issue_code(path: Path) -> str:
    match = re.search(r"TEST-AUDIT-(\d{3})", path.name)
    if not match:
        raise ValueError(f"Cannot infer TEST-AUDIT code from {path.name}")
    return f"TEST-AUDIT-{match.group(1)}"


def _load_issue_drafts(codes: tuple[str, ...] | None = None) -> list[IssueDraft]:
    drafts: list[IssueDraft] = []
    for path in sorted(ISSUES_DIR.glob("TEST-AUDIT-*.md")):
        if path.name.endswith("-ISSUE-PACK.md"):
            continue
        if not ISSUE_PACK_PATTERN.match(path.name):
            continue
        code = _issue_code(path)
        if codes is not None and code not in codes:
            continue
        frontmatter, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        title = frontmatter.get("title", "").strip()
        if not title:
            raise ValueError(f"Missing title in {path}")
        drafts.append(
            IssueDraft(
                code=code,
                path=path,
                title=title,
                body=body,
                labels=_parse_labels(frontmatter.get("labels", "")),
            )
        )
    return drafts


def _search_existing_issue(*, token: str, title: str) -> dict[str, Any] | None:
    query = urllib.parse.quote(
        f'repo:{DEFAULT_OWNER}/{DEFAULT_REPO} "{title}" in:title',
        safe="",
    )
    url = f"{API_BASE}/search/issues?q={query}"
    payload = _github_request(method="GET", url=url, token=token)
    for item in payload.get("items", []):
        if item.get("title") == title:
            return item
    return None


def _create_issue(*, token: str, draft: IssueDraft) -> IssueRecord:
    url = f"{API_BASE}/repos/{DEFAULT_OWNER}/{DEFAULT_REPO}/issues"
    payload: dict[str, Any] = {"title": draft.title, "body": draft.body}
    if draft.labels:
        payload["labels"] = list(draft.labels)
    created = _github_request(method="POST", url=url, token=token, payload=payload)
    return IssueRecord(
        number=int(created["number"]),
        title=str(created["title"]),
        url=str(created["html_url"]),
        state=str(created["state"]),
        action="created",
    )


def _update_issue_pack(*, issue_pack: Path, records: list[IssueRecord]) -> None:
    if not records or not issue_pack.exists():
        return
    content = issue_pack.read_text(encoding="utf-8")
    for record in records:
        code_match = re.search(r"\[(TEST-AUDIT-\d{3})\]", record.title)
        if not code_match:
            continue
        code = code_match.group(1)
        link = f"[#{record.number}]({record.url})"
        pattern = rf"^(\d+\. `{code}`[^\n]*)(\s+#\d+)?$"
        replacement = rf"\1 {link}"
        content, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
        if count == 0:
            content += f"\n- {link} `{code}` {record.title}"
    issue_pack.write_text(content, encoding="utf-8")


def _update_issue_frontmatter(*, draft: IssueDraft, number: int) -> None:
    content = draft.path.read_text(encoding="utf-8")
    if re.search(r"^github_issue:\s*\d+\s*$", content, flags=re.MULTILINE):
        updated = re.sub(
            r"^github_issue:\s*\d+\s*$",
            f"github_issue: {number}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        updated = content.replace(
            "assignees: []\n---",
            f"assignees: []\ngithub_issue: {number}\n---",
            1,
        )
    draft.path.write_text(updated, encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing issues on GitHub.",
    )
    parser.add_argument(
        "--codes",
        default="",
        help="Comma-separated TEST-AUDIT codes to publish (default: 013-019 drafts).",
    )
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    parser.add_argument(
        "--pack",
        default=str(DEFAULT_ISSUE_PACK.relative_to(_repo_root())),
        help="Issue pack markdown to update with GitHub links when --update-pack is set.",
    )
    parser.add_argument(
        "--update-pack",
        action="store_true",
        help="Write GitHub links back into the selected TEST-AUDIT issue pack.",
    )
    parser.add_argument(
        "--min-code",
        type=int,
        default=13,
        help="Minimum TEST-AUDIT numeric code to publish (default: 13).",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    codes = None
    if args.codes.strip():
        codes = tuple(code.strip() for code in args.codes.split(",") if code.strip())
    drafts = _load_issue_drafts(codes)
    drafts = [draft for draft in drafts if int(draft.code.split("-")[-1]) >= args.min_code]
    if not drafts:
        print("No TEST-AUDIT drafts found.")
        return 1

    print(f"Prepared {len(drafts)} local TEST-AUDIT drafts.")
    for draft in drafts:
        print(f"- {draft.code}: {draft.title}")

    if not args.apply:
        print("\n[DRY-RUN] Pass --apply to create missing issues on GitHub.")
        return 0

    token = _load_token(args.token_env)
    records: list[IssueRecord] = []

    for draft in drafts:
        existing = _search_existing_issue(token=token, title=draft.title)
        if existing:
            records.append(
                IssueRecord(
                    number=int(existing["number"]),
                    title=str(existing["title"]),
                    url=str(existing["html_url"]),
                    state=str(existing["state"]),
                    action="exists",
                )
            )
            print(f"Skipping create for {draft.code}; already exists as #{existing['number']}.")
            _update_issue_frontmatter(draft=draft, number=int(existing["number"]))
            continue
        print(f"Creating {draft.code}...")
        created = _create_issue(token=token, draft=draft)
        records.append(created)
        _update_issue_frontmatter(draft=draft, number=created.number)

    if args.update_pack:
        issue_pack = _repo_root() / args.pack
        _update_issue_pack(issue_pack=issue_pack, records=records)

    print("\nSummary:")
    for record in records:
        print(f"- {record.action}: #{record.number} {record.url}")

    summary_path = _repo_root() / "reports/quality/test-audit-issue-publish.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "records": [record.__dict__ for record in records],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
