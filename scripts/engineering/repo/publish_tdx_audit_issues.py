#!/usr/bin/env python3
"""Publish or reopen TDX-AUDIT issues from ``.github/ISSUES/TDX-AUDIT-*.md``.

Usage:
    python scripts/engineering/repo/publish_tdx_audit_issues.py
    python scripts/engineering/repo/publish_tdx_audit_issues.py --apply
    python scripts/engineering/repo/publish_tdx_audit_issues.py --apply \
        --codes TDX-AUDIT-012,TDX-AUDIT-013 --update-pack
    python scripts/engineering/repo/publish_tdx_audit_issues.py --apply --reopen 5839,5840

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

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.engineering.qa.technical_debt_audit_registry import (
    resolve_current_technical_debt_audit,
)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal envs
    load_dotenv = None  # type: ignore[assignment]

API_BASE: Final[str] = "https://api.github.com"
DEFAULT_OWNER: Final[str] = "SatoryKono"
DEFAULT_REPO: Final[str] = "BioactivityDataAcquisition"
DEFAULT_TOKEN_ENV: Final[str] = "GITHUB_TOKEN"
ISSUES_DIR: Final[Path] = REPO_ROOT / ".github" / "ISSUES"
DEFAULT_ISSUE_PACK: Final[Path] = (
    ISSUES_DIR / "TECH-DEBT-AUDIT-2026-07-03-ISSUE-PACK.md"
)
LEGACY_ISSUE_PACK: Final[Path] = ISSUES_DIR / "TECH-DEBT-AUDIT-2026-07-01-ISSUE-PACK.md"
CURRENT_AUDIT_REFERENCE: Final[str] = (
    resolve_current_technical_debt_audit(REPO_ROOT).relative_to(REPO_ROOT).as_posix()
)
REOPEN_COMMENT: Final[str] = (
    "Reopened after the refreshed `2026-07-03` technical-debt audit on current "
    "`main`.\n\n"
    "Closeout evidence from `2026-07-02` tracked governance packaging, but live "
    "artifacts still show residual debt for this owner surface (for example "
    "duplication clusters, partial-coverage tails, or retained compatibility "
    "seams). This issue remains the active owner until the acceptance criteria "
    "are met on regenerated evidence.\n\n"
    "Evidence anchors:\n"
    f"- `{CURRENT_AUDIT_REFERENCE}`\n"
    "- `reports/quality/debt-governance-gates.json`\n"
    "- `reports/quality/full-app-duplication-baseline.json`\n"
    "- `reports/quality/module-coverage-inventory.json`\n"
    "- `reports/quality/compatibility-importer-census.json`"
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
    """Created or reopened GitHub issue."""

    number: int
    title: str
    url: str
    state: str
    action: str


def _repo_root() -> Path:
    return REPO_ROOT


def _load_token(token_env: str) -> str:
    if load_dotenv is not None:
        load_dotenv(_repo_root() / ".env")
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
    if not raw:
        return ()
    return tuple(label.strip() for label in raw.split(",") if label.strip())


def _issue_code(path: Path) -> str:
    match = re.search(r"TDX-AUDIT-(\d{3})", path.name)
    if not match:
        raise ValueError(f"Cannot infer TDX-AUDIT code from {path.name}")
    return f"TDX-AUDIT-{match.group(1)}"


def _load_issue_drafts(codes: tuple[str, ...] | None = None) -> list[IssueDraft]:
    drafts: list[IssueDraft] = []
    for path in sorted(ISSUES_DIR.glob("TDX-AUDIT-*.md")):
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


def _reopen_issue(*, token: str, number: int, comment: str) -> IssueRecord:
    issue_url = f"{API_BASE}/repos/{DEFAULT_OWNER}/{DEFAULT_REPO}/issues/{number}"
    updated = _github_request(
        method="PATCH",
        url=issue_url,
        token=token,
        payload={"state": "open"},
    )
    comment_url = f"{issue_url}/comments"
    _github_request(
        method="POST", url=comment_url, token=token, payload={"body": comment}
    )
    return IssueRecord(
        number=int(updated["number"]),
        title=str(updated["title"]),
        url=str(updated["html_url"]),
        state=str(updated["state"]),
        action="reopened",
    )


def _update_issue_pack(*, issue_pack: Path, records: list[IssueRecord]) -> None:
    from scripts.engineering.common.repo_paths import ensure_repo_path

    if not records:
        return
    safe_root = REPO_ROOT.resolve(strict=False)
    confined_pack = ensure_repo_path(issue_pack, root=safe_root)
    relative_pack = confined_pack.relative_to(safe_root)
    safe_pack = safe_root.joinpath(*relative_pack.parts)
    if not safe_pack.exists():
        return
    content = safe_pack.read_text(encoding="utf-8")
    for record in records:
        code_match = re.search(r"\[(TDX-AUDIT-\d{3})\]", record.title)
        if not code_match:
            continue
        code = code_match.group(1)
        link = f"[#{record.number}]({record.url})"
        pattern = rf"(\d+\. `{code}`[^\n]*)(\s+#\d+)?$"
        replacement = rf"\1 {link}"
        content, count = re.subn(
            pattern, replacement, content, count=1, flags=re.MULTILINE
        )
        if count == 0:
            content += f"\n- {link} `{code}` {record.title}"
    safe_pack.write_text(content, encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing issues and reopen requested numbers.",
    )
    parser.add_argument(
        "--codes",
        default="",
        help="Comma-separated TDX-AUDIT codes to publish (default: all local drafts).",
    )
    parser.add_argument(
        "--reopen",
        default="",
        help="Comma-separated GitHub issue numbers to reopen (default: none).",
    )
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    parser.add_argument(
        "--skip-reopen",
        action="store_true",
        help="Only create missing issues; do not reopen closed wave.",
    )
    parser.add_argument(
        "--pack",
        default=str(DEFAULT_ISSUE_PACK.relative_to(_repo_root())),
        help="Issue pack markdown to update with GitHub links when --update-pack is set.",
    )
    parser.add_argument(
        "--update-pack",
        action="store_true",
        help="Write GitHub links back into the selected TECH-DEBT-AUDIT issue pack.",
    )
    return parser.parse_args(argv)


def _publish_or_skip_draft(
    draft: IssueDraft, *, token: str, records: list[IssueRecord]
) -> None:
    existing = _search_existing_issue(token=token, title=draft.title)
    if existing and existing.get("state") == "open":
        records.append(
            IssueRecord(
                number=int(existing["number"]),
                title=str(existing["title"]),
                url=str(existing["html_url"]),
                state=str(existing["state"]),
                action="exists-open",
            )
        )
        print(
            f"Skipping create for {draft.code}; already open as #{existing['number']}."
        )
        return
    if existing and existing.get("state") == "closed":
        print(
            f"Creating fresh issue for {draft.code}; closed duplicate exists "
            f"as #{existing['number']}."
        )
    else:
        print(f"Creating {draft.code}...")
    records.append(_create_issue(token=token, draft=draft))


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    codes = None
    if args.codes.strip():
        codes = tuple(code.strip() for code in args.codes.split(",") if code.strip())
    drafts = _load_issue_drafts(codes)
    if not drafts:
        print("No TDX-AUDIT drafts found.")
        return 1

    print(f"Prepared {len(drafts)} local TDX-AUDIT drafts.")
    for draft in drafts:
        print(f"- {draft.code}: {draft.title}")

    if not args.apply:
        print(
            "\n[DRY-RUN] Pass --apply to create missing issues and reopen closed wave."
        )
        return 0

    token = _load_token(args.token_env)
    records: list[IssueRecord] = []

    if not args.skip_reopen and args.reopen.strip():
        for raw_number in args.reopen.split(","):
            number = int(raw_number.strip())
            print(f"Reopening #{number}...")
            records.append(
                _reopen_issue(token=token, number=number, comment=REOPEN_COMMENT)
            )

    for draft in drafts:
        _publish_or_skip_draft(draft, token=token, records=records)

    if args.update_pack:
        issue_pack = _repo_root() / args.pack
        _update_issue_pack(issue_pack=issue_pack, records=records)

    print("\nSummary:")
    for record in records:
        print(f"- {record.action}: #{record.number} {record.url}")

    summary_path = (
        _repo_root() / "reports/quality/tech-debt-tdx-audit-issue-publish.json"
    )
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
