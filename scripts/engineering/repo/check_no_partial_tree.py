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
import re
import subprocess
from pathlib import Path

# A full checkout carries an order of magnitude more top-level entries.
# Commits below this size built on a full parent tree are never legitimate
# restructures; restructures rename or move entries instead of dropping them.
MAX_COLLAPSED_TOP_LEVEL = 3
MIN_FULL_PARENT_TOP_LEVEL = 10
_GIT_VERBS = frozenset({"ls-tree", "rev-list", "log", "rev-parse"})
_REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./@^{}~+-]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


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


def validate_revision_token(token: str) -> str:
    """Reject git flag-injection in revision tokens from CLI/agents."""
    text = str(token).strip()
    if not text or text.startswith("-") or not _REVISION_RE.fullmatch(text):
        raise SystemExit(f"invalid git revision: {token!r}")
    return text


def validate_repo(repo: str | Path) -> Path:
    """Resolve cwd to an existing git work tree; refuse flag-like paths."""
    raw = str(repo).strip()
    if not raw or raw.startswith("-"):
        raise SystemExit(f"invalid git repository path: {repo!r}")
    path = Path(raw).resolve()
    if not path.is_dir():
        raise SystemExit(f"git repository is not a directory: {path}")
    git_meta = path / ".git"
    if not git_meta.exists():
        raise SystemExit(f"not a git repository: {path}")
    return path


def _run_git(repo: Path, verb: str, *args: str) -> str:
    if verb not in _GIT_VERBS:
        raise SystemExit(f"unsupported git verb: {verb!r}")
    result = subprocess.run(
        ["git", verb, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=repo,
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"git {verb} failed: {detail}")
    return result.stdout


def resolve_revision(repo: str | Path, token: str) -> str:
    """Return a verified commit SHA for *token* inside *repo*."""
    cwd = validate_repo(repo)
    safe = validate_revision_token(token)
    stdout = _run_git(
        cwd,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{safe}^{{commit}}",
    )
    sha = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    if not _SHA_RE.fullmatch(sha):
        raise SystemExit(f"git rev-parse did not return a commit SHA for {token!r}")
    return sha


def _git(repo: str | Path, *args: str) -> str:
    """Run an allowlisted git verb in a validated repository."""
    cwd = validate_repo(repo)
    if not args:
        raise SystemExit("git verb is required")
    verb = args[0]
    extra = args[1:]
    return _run_git(cwd, verb, *extra)


def _top_level_names(repo: str | Path, revision: str) -> frozenset[str]:
    cwd = validate_repo(repo)
    sha = resolve_revision(cwd, revision)
    stdout = _run_git(cwd, "ls-tree", "--name-only", "--end-of-options", sha)
    return frozenset(line for line in stdout.splitlines() if line)


def _parent_shas(repo: str | Path, revision: str) -> list[str]:
    cwd = validate_repo(repo)
    sha = resolve_revision(cwd, revision)
    stdout = _run_git(cwd, "log", "--format=%P", "-1", "--end-of-options", sha)
    return stdout.split()


def find_collapsing_commits(
    base: str, tip: str, *, repo: str | Path = "."
) -> list[str]:
    """Return collapsing commits in base..tip, oldest first.

    Root commits (no parents) are skipped: they cannot collapse anything.
    Every other commit is compared against the base tree so inherited
    collapses inside the range are still reported.
    """
    cwd = validate_repo(repo)
    base_sha = resolve_revision(cwd, base)
    tip_sha = resolve_revision(cwd, tip)
    revisions = [
        line
        for line in _run_git(
            cwd,
            "rev-list",
            "--reverse",
            "--end-of-options",
            f"{base_sha}..{tip_sha}",
        ).splitlines()
        if line
    ]
    base_top = _top_level_names(cwd, base_sha)
    offenders: list[str] = []
    for revision in revisions:
        if not _parent_shas(cwd, revision):
            continue
        if is_collapsed_tree(base_top, _top_level_names(cwd, revision)):
            offenders.append(revision)
    return offenders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--tip", default="HEAD")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    cwd = validate_repo(args.repo)
    offenders = find_collapsing_commits(args.base, args.tip, repo=cwd)
    if offenders:
        print("partial-tree commits must not enter shared history:")
        for revision in offenders:
            subject = _run_git(
                cwd, "log", "--format=%s", "-1", "--end-of-options", revision
            ).strip()
            print(f"- {revision} {subject}")
        return 1
    print(f"no partial-tree commits in {args.base}..{args.tip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
