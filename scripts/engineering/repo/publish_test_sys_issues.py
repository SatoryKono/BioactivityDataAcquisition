#!/usr/bin/env python3
"""Publish TEST-SYS issues from ``.github/ISSUES/TEST-SYS-*.md``.

Usage:
    python scripts/engineering/repo/publish_test_sys_issues.py
    python scripts/engineering/repo/publish_test_sys_issues.py --apply
    python scripts/engineering/repo/publish_test_sys_issues.py --apply --update-pack

Requires a working GitHub token. Prefer ``CODEX_GITHUB_PERSONAL_ACCESS_TOKEN``
or ``GITHUB_PERSONAL_ACCESS_TOKEN`` / ``GITHUB_TOKEN``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

REPO_ROOT = Path(__file__).resolve().parents[3]
API_BASE: Final[str] = "https://api.github.com"
DEFAULT_OWNER: Final[str] = "SatoryKono"
DEFAULT_REPO: Final[str] = "BioactivityDataAcquisition"
ISSUES_DIR: Final[Path] = REPO_ROOT / ".github" / "ISSUES"
ISSUE_PACK: Final[Path] = ISSUES_DIR / "TEST-SYS-2026-07-29-ISSUE-PACK.md"
PUBLISH_JSON: Final[Path] = (
    REPO_ROOT / "reports" / "quality" / "test-system-audit-2026-07-29-issue-publish.json"
)
AUDIT_REPORT: Final[str] = (
    "reports/grok/review_test_system_architecture_audit_20260729_FULL.md"
)

CODE_ORDER: Final[tuple[str, ...]] = tuple(
    f"TEST-SYS-{i:02d}" for i in range(0, 11)
)


@dataclass(frozen=True)
class IssueDraft:
    code: str
    path: Path
    title: str
    body: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class IssueRecord:
    code: str
    number: int
    title: str
    url: str
    state: str
    action: str


def _load_token() -> str:
    for env_name in (
        "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
    ):
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    raise ValueError(
        "Missing GitHub token. Set CODEX_GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_TOKEN."
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
        "User-Agent": "bioetl-test-sys-publish",
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
            raise RuntimeError(
                f"GitHub API {method} {url} failed: {exc.code} {detail}"
            ) from exc
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
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(parts)


def _code_from_path(path: Path) -> str | None:
    match = re.match(r"^(TEST-SYS-\d{2})-", path.name)
    return match.group(1) if match else None


def _load_drafts() -> list[IssueDraft]:
    by_code: dict[str, IssueDraft] = {}
    for path in sorted(ISSUES_DIR.glob("TEST-SYS-*.md")):
        if path.name.startswith("TEST-SYS-2026"):
            continue
        code = _code_from_path(path)
        if code is None:
            continue
        content = path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(content)
        title = frontmatter.get("title")
        if not title:
            raise ValueError(f"{path}: missing title in frontmatter")
        labels = _parse_labels(frontmatter.get("labels", ""))
        # Append pack + audit footer if not already present
        footer = (
            "\n\n---\n\n"
            f"**Issue pack:** `.github/ISSUES/{ISSUE_PACK.name}`  \n"
            f"**Audit report:** `{AUDIT_REPORT}`\n"
        )
        if "Issue pack:" not in body:
            body = body.rstrip() + footer
        by_code[code] = IssueDraft(
            code=code,
            path=path,
            title=title,
            body=body,
            labels=labels,
        )
    drafts: list[IssueDraft] = []
    missing: list[str] = []
    for code in CODE_ORDER:
        draft = by_code.get(code)
        if draft is None:
            missing.append(code)
        else:
            drafts.append(draft)
    if missing:
        raise FileNotFoundError(f"Missing issue templates for: {', '.join(missing)}")
    return drafts


def _search_existing(*, token: str, code: str) -> IssueRecord | None:
    import urllib.parse

    query = (
        f"repo:{DEFAULT_OWNER}/{DEFAULT_REPO} "
        f'"{code}" in:title type:issue'
    )
    url = (
        f"{API_BASE}/search/issues?"
        f"q={urllib.parse.quote(query)}&per_page=5"
    )
    payload = _github_request(method="GET", url=url, token=token)
    items = payload.get("items") or []
    for item in items:
        title = str(item.get("title") or "")
        if code in title:
            return IssueRecord(
                code=code,
                number=int(item["number"]),
                title=title,
                url=str(item.get("html_url") or ""),
                state=str(item.get("state") or "open"),
                action="exists",
            )
    return None


def _create_issue(*, token: str, draft: IssueDraft) -> IssueRecord:
    url = f"{API_BASE}/repos/{DEFAULT_OWNER}/{DEFAULT_REPO}/issues"
    payload = {
        "title": draft.title,
        "body": draft.body,
        "labels": list(draft.labels),
    }
    created = _github_request(method="POST", url=url, token=token, payload=payload)
    return IssueRecord(
        code=draft.code,
        number=int(created["number"]),
        title=str(created.get("title") or draft.title),
        url=str(created.get("html_url") or ""),
        state=str(created.get("state") or "open"),
        action="created",
    )


def _write_publish_json(records: list[IssueRecord]) -> None:
    PUBLISH_JSON.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "audit_report": AUDIT_REPORT,
        "issue_pack": ISSUE_PACK.relative_to(REPO_ROOT).as_posix(),
        "stamp": "2026-07-29",
        "owner": DEFAULT_OWNER,
        "repo": DEFAULT_REPO,
        "issues": [
            {
                "code": r.code,
                "number": r.number,
                "url": r.url,
                "title": r.title,
                "state": r.state,
                "action": r.action,
            }
            for r in records
        ],
    }
    PUBLISH_JSON.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _rewrite_pack_table_row(line: str, by_code: dict[str, IssueRecord]) -> str:
    """Rewrite one issue-pack markdown table body row when the code is known."""
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) < 4 or cells[0] not in by_code:
        return line
    rec = by_code[cells[0]]
    return f"| {rec.code} | {cells[1]} | #{rec.number} | {rec.url} |"


def _is_pack_table_separator(line: str) -> bool:
    return line.startswith("|------") or line.startswith("| ---")


def _update_pack_table_lines(
    text: str, by_code: dict[str, IssueRecord]
) -> list[str]:
    lines: list[str] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Code | Pri | Issue | URL |"):
            in_table = True
            lines.append(line)
            continue
        if not in_table:
            lines.append(line)
            continue
        if not line.startswith("|"):
            in_table = False
            lines.append(line)
            continue
        if _is_pack_table_separator(line):
            lines.append(line)
            continue
        lines.append(_rewrite_pack_table_row(line, by_code))
    return lines


def _update_pack(records: list[IssueRecord]) -> None:
    text = ISSUE_PACK.read_text(encoding="utf-8")
    by_code = {r.code: r for r in records}
    lines = _update_pack_table_lines(text, by_code)
    ISSUE_PACK.write_text("\n".join(lines) + "\n", encoding="utf-8")


_GITHUB_ISSUE_LINE_RE = re.compile(r"^github_issue:\s*\d+\s*$", flags=re.MULTILINE)
_ASSIGNEES_LINE_RE = re.compile(r"^(assignees:\s*\S.*)$", flags=re.MULTILINE)


def _stamp_one_issue_frontmatter(path: Path, rec: IssueRecord) -> None:
    content = path.read_text(encoding="utf-8")
    if _GITHUB_ISSUE_LINE_RE.search(content):
        content = _GITHUB_ISSUE_LINE_RE.sub(f"github_issue: {rec.number}", content, count=1)
    else:
        content = _ASSIGNEES_LINE_RE.sub(
            rf"\1\ngithub_issue: {rec.number}",
            content,
            count=1,
        )
    path.write_text(content, encoding="utf-8")


def _stamp_frontmatter_github_issue(records: list[IssueRecord]) -> int:
    """Stamp github_issue frontmatter fields; return how many files changed."""
    by_code = {r.code: r for r in records}
    stamped = 0
    for path in sorted(ISSUES_DIR.glob("TEST-SYS-*.md")):
        if path.name.startswith("TEST-SYS-2026"):
            continue
        code = _code_from_path(path)
        if code is None or code not in by_code:
            continue
        _stamp_one_issue_frontmatter(path, by_code[code])
        stamped += 1
    return stamped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing issues on GitHub (default is dry-run).",
    )
    parser.add_argument(
        "--update-pack",
        action="store_true",
        help="Rewrite issue pack table + publish JSON + stamp github_issue fields.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.6,
        help="Sleep seconds between create calls (rate limit).",
    )
    args = parser.parse_args(argv)

    drafts = _load_drafts()
    print(f"Loaded {len(drafts)} drafts from {ISSUES_DIR}")

    if not args.apply:
        for draft in drafts:
            print(f"[dry-run] {draft.code}: {draft.title}")
            print(f"          labels={','.join(draft.labels)}")
            print(f"          path={draft.path.relative_to(REPO_ROOT)}")
        print("Re-run with --apply to create issues.")
        return 0

    token = _load_token()
    records: list[IssueRecord] = []
    for draft in drafts:
        existing = _search_existing(token=token, code=draft.code)
        if existing is not None:
            print(f"[skip] {draft.code} already #{existing.number} ({existing.state})")
            records.append(existing)
            continue
        rec = _create_issue(token=token, draft=draft)
        print(f"[created] {draft.code} #{rec.number} {rec.url}")
        records.append(rec)
        time.sleep(max(0.0, args.sleep))

    if args.update_pack:
        _write_publish_json(records)
        _update_pack(records)
        stamped = _stamp_frontmatter_github_issue(records)
        print(f"Updated {ISSUE_PACK.relative_to(REPO_ROOT)}")
        print(f"Wrote {PUBLISH_JSON.relative_to(REPO_ROOT)}")
        print(f"Stamped github_issue frontmatter on {stamped} issue file(s)")

    print("Done.")
    for rec in records:
        print(f"  {rec.code}: #{rec.number} {rec.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
