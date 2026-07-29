#!/usr/bin/env python3
"""Publish DUX4 epic + children via GitHub CLI and write a publish record.

Usage (from repo root, after valid GH token (prefer CODEX_GITHUB_PERSONAL_ACCESS_TOKEN)`gh auth login`):

    python .github/ISSUES/_dux3_bodies/publish_dux3_issues.py
    python .github/ISSUES/_dux3_bodies/publish_dux3_issues.py --dry-run

Environment:
    GH  optional path to gh.exe (default: gh on PATH)
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

ROOT = Path(__file__).resolve().parents[3]
BODIES = Path(__file__).resolve().parent
PACK = ROOT / ".github" / "ISSUES" / "DUX4-2026-07-29-DASHBOARD-VISUAL-ENFORCEMENT-ISSUE-PACK.md"
PUBLISH = ROOT / "reports" / "quality" / "dux4-2026-07-29-issue-publish.json"
TITLES_PATH = BODIES / "TITLES.md"

# code -> (priority, wave)
META: dict[str, tuple[str, str]] = {
    "DUX4-00": ("meta", "epic"),
    "DUX4-01": ("P0", "V0"),
    "DUX4-02": ("P0", "V0"),
    "DUX4-03": ("P0", "V0"),
    "DUX4-10": ("P0", "V1"),
    "DUX4-11": ("P0", "V1"),
    "DUX4-12": ("P0", "V1"),
    "DUX4-13": ("P0", "V1"),
    "DUX4-14": ("P0", "V1"),
    "DUX4-15": ("P0", "V1"),
    "DUX4-16": ("P1", "V1"),
    "DUX4-17": ("P0", "V1"),
    "DUX4-20": ("P1", "V2"),
    "DUX4-21": ("P1", "V2"),
    "DUX4-22": ("P1", "V2"),
    "DUX4-23": ("P1", "V2"),
    "DUX4-24": ("P1", "V2"),
    "DUX4-25": ("P1", "V2"),
    "DUX4-30": ("P1", "V3"),
    "DUX4-31": ("P1", "V3"),
    "DUX4-32": ("P1", "V3"),
    "DUX4-33": ("P1", "V3"),
    "DUX4-34": ("P1", "V3"),
    "DUX4-40": ("P2", "V4"),
    "DUX4-41": ("P2", "V4"),
    "DUX4-42": ("P2", "V4"),
    "DUX4-43": ("P2", "V4"),
    "DUX4-44": ("P3", "track"),
}

CHILD_ORDER = [c for c in META if c != "DUX4-00"]


def load_titles() -> dict[str, str]:
    titles: dict[str, str] = {}
    for line in TITLES_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- `(DUX4-\d+)`: `(.*)`\s*$", line)
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
    env = os.environ.copy()
    # Prefer CODEX oauth token over possibly-stale GITHUB_TOKEN PATs.
    for key in (
        "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN",
        "GH_TOKEN",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "GITHUB_TOKEN",
    ):
        candidate = env.get(key)
        if candidate:
            env["GH_TOKEN"] = candidate
            env["GITHUB_TOKEN"] = candidate
            break
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"gh failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return (proc.stdout or "").strip()


def issue_number_from_url(url: str) -> int:
    m = re.search(r"/issues/(\d+)\s*$", url)
    if not m:
        raise SystemExit(f"cannot parse issue number from: {url!r}")
    return int(m.group(1))


def patch_parent(body: str, epic: int) -> str:
    return body.replace("_TBD_ (DUX4-00)", f"#{epic} (DUX4-00)")


def update_pack(created: list[dict[str, object]]) -> None:
    text = PACK.read_text(encoding="utf-8")
    for row in created:
        code = str(row["code"])
        number = int(row["number"])
        url = str(row["url"])
        # Replace matrix cell: | DUX4-XX | _TBD_ |  -> | DUX4-XX | [#N](url) |
        pattern = rf"(\| {re.escape(code)} \| )_TBD_( \|)"
        repl = rf"\g<1>[#{number}]({url})\g<2>"
        text, n = re.subn(pattern, repl, text, count=1)
        if n != 1:
            print(f"warning: pack matrix row not updated for {code}", file=sys.stderr)
    # publish record pointer
    if "dux4-2026-07-29-issue-publish.json" not in text:
        text = text.rstrip() + (
            "\n\n## Publish artifact\n\n"
            "- `reports/quality/dux4-2026-07-29-issue-publish.json`\n"
        )
    PACK.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--labels",
        default="observability,grafana,technical-debt",
        help="Comma-separated labels (must already exist or gh will fail)",
    )
    args = parser.parse_args()
    gh = resolve_gh()
    titles = load_titles()

    if not args.dry_run:
        # Fail fast on API auth. Prefer env token (GITHUB_TOKEN/GH_TOKEN);
        # do not require `gh auth status` (stored host token may be stale).
        login = run_gh(gh, ["api", "user", "-q", ".login"], dry_run=False)
        print(f"authenticated as: {login}")

    labels = [part.strip() for part in args.labels.split(",") if part.strip()]
    label_args: list[str] = []
    for lab in labels:
        label_args.extend(["--label", lab])

    created: list[dict[str, object]] = []

    epic_url = run_gh(
        gh,
        [
            "issue",
            "create",
            "--title",
            titles["DUX4-00"],
            "--body-file",
            str(BODIES / "DUX4-00.md"),
            *label_args,
        ],
        dry_run=args.dry_run,
    )
    epic = 0 if args.dry_run else issue_number_from_url(epic_url)
    created.append(
        {
            "code": "DUX4-00",
            "number": epic,
            "priority": "meta",
            "wave": "epic",
            "url": epic_url,
            "title": titles["DUX4-00"],
        }
    )
    print(f"created epic #{epic}: {epic_url}")

    for code in CHILD_ORDER:
        body_path = BODIES / f"{code}.md"
        body = body_path.read_text(encoding="utf-8")
        if not args.dry_run:
            body = patch_parent(body, epic)
        tmp = BODIES / f".{code}.publish.md"
        tmp.write_text(body, encoding="utf-8", newline="\n")
        try:
            url = run_gh(
                gh,
                [
                    "issue",
                    "create",
                    "--title",
                    titles[code],
                    "--body-file",
                    str(tmp),
                    *label_args,
                ],
                dry_run=args.dry_run,
            )
        finally:
            if tmp.exists():
                tmp.unlink()
        number = 0 if args.dry_run else issue_number_from_url(url)
        pri, wave = META[code]
        created.append(
            {
                "code": code,
                "number": number,
                "priority": pri,
                "wave": wave,
                "url": url,
                "title": titles[code],
            }
        )
        print(f"created {code} #{number}: {url}")

    if not args.dry_run:
        # Link children in epic body comment
        child_lines = "\n".join(
            f"- #{int(row['number'])} — `{row['code']}` {row['title']}"
            for row in created
            if row["code"] != "DUX4-00"
        )
        comment = (
            "## Children (published)\n\n"
            f"{child_lines}\n\n"
            "Pack: `.github/ISSUES/DUX4-2026-07-29-DASHBOARD-VISUAL-ENFORCEMENT-ISSUE-PACK.md`\n"
        )
        run_gh(
            gh,
            ["issue", "comment", str(epic), "--body", comment],
            dry_run=False,
        )

        record = {
            "published_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "owner": "SatoryKono",
            "repo": "BioactivityDataAcquisition",
            "wave": "dux4-dashboard-visual-enforcement-2026-07-29",
            "issue_pack": ".github/ISSUES/DUX4-2026-07-29-DASHBOARD-VISUAL-ENFORCEMENT-ISSUE-PACK.md",
            "source_audit": "BIOETL-GRAFANA-UX-AUDIT-20260729-085334",
            "predecessors": {
                "dux3_epic": 7053,
                "dsa_epic": 6982,
                "ds2_epic": 6901,
                "adr_053_issue": 6911,
            },
            "epic": epic,
            "created": created,
        }
        PUBLISH.parent.mkdir(parents=True, exist_ok=True)
        PUBLISH.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        update_pack(created)
        print(f"publish record: {PUBLISH}")
        print(f"pack updated: {PACK}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
