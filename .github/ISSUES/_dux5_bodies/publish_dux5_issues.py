#!/usr/bin/env python3
"""Publish DUX5 epic + children via GitHub CLI and write a publish record.

Usage (from repo root, after valid GH auth):

    python .github/ISSUES/_dux5_bodies/publish_dux5_issues.py --dry-run
    python .github/ISSUES/_dux5_bodies/publish_dux5_issues.py

Environment:
    GH  optional path to gh.exe (default: gh on PATH)
    Prefer CODEX_GITHUB_PERSONAL_ACCESS_TOKEN when configuring gh auth.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[3]
BODIES = Path(__file__).resolve().parent
PACK = (
    ROOT
    / ".github"
    / "ISSUES"
    / "DUX5-2026-07-29-DASHBOARD-TYPOGRAPHY-READING-ORDER-ISSUE-PACK.md"
)
PUBLISH = ROOT / "reports" / "quality" / "dux5-2026-07-29-issue-publish.json"
TITLES_PATH = BODIES / "TITLES.md"


class PublishedIssue(TypedDict):
    code: str
    number: int
    priority: str
    wave: str
    url: str
    title: str


META: dict[str, tuple[str, str]] = {
    "DUX5-00": ("meta", "epic"),
    "DUX5-01": ("P0", "V1"),
    "DUX5-02": ("P0", "V1"),
    "DUX5-03": ("P0", "V1"),
    "DUX5-04": ("P0", "V1"),
    "DUX5-05": ("P0", "V1"),
    "DUX5-06": ("P0", "V1"),
    "DUX5-10": ("P1", "V2"),
    "DUX5-11": ("P1", "V2"),
    "DUX5-12": ("P1", "V2"),
    "DUX5-13": ("P1", "V2"),
    "DUX5-14": ("P1", "V2"),
    "DUX5-20": ("P2", "V3"),
    "DUX5-21": ("P2", "V3"),
    "DUX5-22": ("P2", "V3"),
    "DUX5-23": ("P2", "V3"),
    "DUX5-30": ("P3", "V4"),
    "DUX5-31": ("P3", "V4"),
}

CHILD_ORDER = [c for c in META if c != "DUX5-00"]


def load_titles() -> dict[str, str]:
    titles: dict[str, str] = {}
    for line in TITLES_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- `(DUX5-\d+)`: `(.*)`\s*$", line)
        if m:
            titles[m.group(1)] = m.group(2)
    missing = set(META) - set(titles)
    if missing:
        raise SystemExit(f"missing titles for: {sorted(missing)}")
    return titles


def resolve_gh() -> str:
    explicit = os.environ.get("GH")
    if explicit:
        return explicit
    for candidate in (
        r"C:\Program Files\GitHub CLI\gh.exe",
        "/c/Program Files/GitHub CLI/gh.exe",
        "gh",
    ):
        if candidate == "gh":
            return candidate
        if Path(candidate).exists():
            return candidate
    return "gh"


def run_gh(gh: str, args: list[str], *, dry_run: bool) -> str:
    cmd = [gh, *args]
    if dry_run:
        print("DRY-RUN:", " ".join(cmd))
        return "https://github.com/example/repo/issues/0"
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"gh failed ({proc.returncode}): {proc.stderr or proc.stdout}")
    return (proc.stdout or "").strip()


def create_issue(
    gh: str,
    *,
    title: str,
    body_path: Path,
    labels: list[str],
    dry_run: bool,
) -> tuple[int, str]:
    args = [
        "issue",
        "create",
        "--title",
        title,
        "--body-file",
        str(body_path),
    ]
    for label in labels:
        args.extend(["--label", label])
    url = run_gh(gh, args, dry_run=dry_run)
    if dry_run:
        return 0, url
    m = re.search(r"/issues/(\d+)\s*$", url)
    if not m:
        raise SystemExit(f"could not parse issue number from: {url!r}")
    return int(m.group(1)), url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    titles = load_titles()
    gh = resolve_gh()
    # Prefer CODEX PAT when shell GITHUB_TOKEN is stale (401 Bad credentials).
    codex = os.environ.get("CODEX_GITHUB_PERSONAL_ACCESS_TOKEN")
    if codex:
        os.environ["GH_TOKEN"] = codex
        os.environ.pop("GITHUB_TOKEN", None)
    # Labels must already exist on the repo (match DUX4 epic #7088).
    labels_epic = ["grafana", "observability", "technical-debt"]
    labels_child = ["grafana", "observability"]

    created: list[PublishedIssue] = []

    epic_num, epic_url = create_issue(
        gh,
        title=titles["DUX5-00"],
        body_path=BODIES / "DUX5-00.md",
        labels=labels_epic,
        dry_run=args.dry_run,
    )
    created.append(
        {
            "code": "DUX5-00",
            "number": epic_num,
            "priority": "meta",
            "wave": "epic",
            "url": epic_url,
            "title": titles["DUX5-00"],
        }
    )

    for code in CHILD_ORDER:
        pri, wave = META[code]
        body_path = BODIES / f"{code}.md"
        if not args.dry_run and epic_num:
            text = body_path.read_text(encoding="utf-8")
            if f"#{epic_num}" not in text:
                body_path.write_text(
                    text.replace(
                        "DUX5 epic (`DUX5-00`)",
                        f"DUX5 epic (#{epic_num})",
                    ),
                    encoding="utf-8",
                )
        num, url = create_issue(
            gh,
            title=titles[code],
            body_path=body_path,
            labels=labels_child,
            dry_run=args.dry_run,
        )
        created.append(
            {
                "code": code,
                "number": num,
                "priority": pri,
                "wave": wave,
                "url": url,
                "title": titles[code],
            }
        )
        print(f"created {code} -> {url}")

    record = {
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "owner": "SatoryKono",
        "repo": "BioactivityDataAcquisition",
        "wave": "dux5-dashboard-typography-reading-order-2026-07-29",
        "issue_pack": str(PACK.relative_to(ROOT)).replace("\\", "/"),
        "source_audit": "BIOETL-GRAFANA-UX-SCREENSHOT-AUDIT-2026-07-29-SG01-SG07",
        "predecessors": {
            "dux4_epic": 7088,
            "dux3_epic": 7053,
            "dsa_epic": 6982,
            "ds2_epic": 6901,
        },
        "epic": epic_num,
        "created": created,
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        PUBLISH.parent.mkdir(parents=True, exist_ok=True)
        PUBLISH.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {PUBLISH}")
    else:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
