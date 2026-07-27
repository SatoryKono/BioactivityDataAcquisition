#!/usr/bin/env python3
"""Publish offline Grafana simplification status comments to GitHub issues.

Reads comment bodies from::

    reports/observability/grafana-issue-updates/{issue}-*.md

Requires a working GitHub auth (``gh auth login`` or valid ``GITHUB_TOKEN``).

Usage::

    python scripts/ops/observability/grafana/publish_simplification_issue_status.py
    python scripts/ops/observability/grafana/publish_simplification_issue_status.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_OWNER = "SatoryKono"
REPO_NAME = "BioactivityDataAcquisition"
ISSUE_FILES = {
    6570: "6570-epic.md",
    6571: "6571-phase0.md",
    6572: "6572-phase1a.md",
    6573: "6573-phase1b.md",
    6574: "6574-phase2.md",
    6575: "6575-phase3.md",
    6576: "6576-phase4.md",
    6577: "6577-playbook.md",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _bodies_dir(root: Path) -> Path:
    return root / "reports" / "observability" / "grafana-issue-updates"


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _post_with_api(issue: int, body: str) -> None:
    token = _token()
    if not token:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN not set")
    url = (
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue}/comments"
    )
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "bioetl-grafana-status-publisher",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"HTTP {resp.status} for issue #{issue}")


def _post_with_gh(issue: int, body: str, root: Path) -> None:
    gh = "gh"
    # Prefer installed Windows CLI if present.
    candidate = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    if candidate.exists():
        gh = str(candidate)
    env = os.environ.copy()
    # Avoid poisoned invalid GITHUB_TOKEN shadowing gh keyring when unset works.
    # Keep token if caller explicitly set a valid one.
    proc = subprocess.run(
        [
            gh,
            "issue",
            "comment",
            str(issue),
            "--repo",
            f"{REPO_OWNER}/{REPO_NAME}",
            "--body-file",
            "-",
        ],
        input=body,
        text=True,
        capture_output=True,
        cwd=root,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh failed for #{issue}: {proc.stderr.strip() or proc.stdout.strip()}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print bodies and issue numbers without posting",
    )
    parser.add_argument(
        "--via",
        choices=("auto", "api", "gh"),
        default="auto",
        help="Post transport (default: try API then gh)",
    )
    args = parser.parse_args()
    root = _repo_root()
    bodies = _bodies_dir(root)
    if not bodies.is_dir():
        print(f"missing bodies dir: {bodies}", file=sys.stderr)
        return 2

    for issue, name in ISSUE_FILES.items():
        path = bodies / name
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 2
        body = path.read_text(encoding="utf-8").strip() + "\n"
        print(f"#{issue} <- {path.relative_to(root)} ({len(body)} chars)")
        if args.dry_run:
            continue
        errors: list[str] = []
        if args.via in ("auto", "api"):
            try:
                _post_with_api(issue, body)
                print(f"  posted via API")
                continue
            except Exception as exc:
                errors.append(f"api: {exc}")
                if args.via == "api":
                    print(f"  FAILED {exc}", file=sys.stderr)
                    return 1
        if args.via in ("auto", "gh"):
            try:
                _post_with_gh(issue, body, root)
                print(f"  posted via gh")
                continue
            except Exception as exc:
                errors.append(f"gh: {exc}")
                print(f"  FAILED {'; '.join(errors)}", file=sys.stderr)
                return 1
    if args.dry_run:
        print("dry-run complete; no comments posted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
