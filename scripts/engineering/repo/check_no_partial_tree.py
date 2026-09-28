"""Fail-closed guard against partial-tree commits in shared history.

A commit whose top-level tree is a strict shrunken subset of the healthy
base tree (for example a reports-only snapshot built on an empty index)
breaks three-point diffs for every PR based on it. History is never
rewritten by this check; it only refuses to add new collapsing commits.

Usage:
  python scripts/engineering/repo/check_no_partial_tree.py
  python scripts/engineering/repo/check_no_partial_tree.py --base origin/main --tip HEAD
  python scripts/engineering/repo/check_no_partial_tree.py --repo /path/to/checkout
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

# A full checkout carries an order of magnitude more top-level entries.
# Commits below this size built on a full parent tree are never legitimate
# restructures; restructures rename or move entries instead of dropping them.
MAX_COLLAPSED_TOP_LEVEL = 3
MIN_FULL_PARENT_TOP_LEVEL = 10


def is_collapsed_tree(base_top: frozenset[str], child_top: frozenset[str]) -> bool:
    """Return whether a commit tree collapsed relative to the healthy base tree.

    The comparison is against the base revision instead of the immediate
    parent so that a collapse inherited through a chain of partial snapshots
    is still reported: every new commit must carry the full top-level tree.
    Restructures pass because they rename or add entries instead of leaving
    a strict shrunken subset behind.
    """
    if len(base_top) < MIN_FULL_PARENT_TOP_LEVEL:
        return False
    if not child_top:
        return True
    return child_top < base_top and len(child_top) <= MAX_COLLAPSED_TOP_LEVEL


def _git(repo: str | Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=repo,
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _top_level_names(repo: str | Path, revision: str) -> frozenset[str]:
    return frozenset(
        line
        for line in _git(repo, "ls-tree", "--name-only", revision).splitlines()
        if line
    )


def _parent_shas(repo: str | Path, revision: str) -> list[str]:
    return _git(repo, "log", "--format=%P", "-1", revision).split()


def find_collapsing_commits(
    base: str, tip: str, *, repo: str | Path = "."
) -> list[str]:
    """Return collapsing commits in base..tip, oldest first.

    Root commits (no parents) are skipped: they cannot collapse anything.
    Every other commit is compared against the base tree so inherited
    collapses inside the range are still reported.
    """
    revisions = [
        line
        for line in _git(repo, "rev-list", "--reverse", f"{base}..{tip}").splitlines()
        if line
    ]
    base_top = _top_level_names(repo, base)
    offenders: list[str] = []
    for revision in revisions:
        if not _parent_shas(repo, revision):
            continue
        if is_collapsed_tree(base_top, _top_level_names(repo, revision)):
            offenders.append(revision)
    return offenders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--tip", default="HEAD")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    offenders = find_collapsing_commits(args.base, args.tip, repo=args.repo)
    if offenders:
        print("partial-tree commits must not enter shared history:")
        for revision in offenders:
            subject = _git(args.repo, "log", "--format=%s", "-1", revision).strip()
            print(f"- {revision} {subject}")
        return 1
    print(f"no partial-tree commits in {args.base}..{args.tip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
