"""Fail-closed guard against partial-tree commits in shared history.

A reports-only snapshot built on an empty index breaks three-point diffs.
Check local sparse state independently, then inspect every candidate commit
for legacy collapse or loss of mandatory directory anchors. Relocations need
Git rename evidence. Individual omissions still require project contracts.
History and index are never rewritten by this check.

Usage:
  python scripts/engineering/repo/check_no_partial_tree.py
  python scripts/engineering/repo/check_no_partial_tree.py --base origin/main --tip HEAD
  python scripts/engineering/repo/check_no_partial_tree.py --repo /path/to/checkout
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

# A full checkout carries an order of magnitude more top-level entries.
# Commits below this size built on a full parent tree are never legitimate
# restructures; restructures rename or move entries instead of dropping them.
MAX_COLLAPSED_TOP_LEVEL = 3
MIN_FULL_PARENT_TOP_LEVEL = 10
DIRECTORY_ANCHORS = frozenset(
    {
        "src",
        "tests",
        "scripts",
        "configs",
        "docs",
        ".github",
        ".codex",
        ".junie",
        ".devin",
    }
)
_GIT_VERBS = frozenset(
    {
        "ls-tree",
        "rev-list",
        "log",
        "rev-parse",
        "config",
        "ls-files",
        "diff",
        "merge-base",
    }
)
_REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./@^{}~+-]*$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class EvidenceError(ValueError):
    """Git or event evidence cannot qualify the protected operation."""


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
        raise EvidenceError(f"invalid git revision: {token!r}")
    return text


def validate_repo(repo: str | Path) -> Path:
    """Resolve cwd to an existing git work tree; refuse flag-like paths."""
    raw = str(repo).strip()
    if not raw or raw.startswith("-"):
        raise EvidenceError(f"invalid git repository path: {repo!r}")
    path = Path(raw).resolve()
    if not path.is_dir():
        raise EvidenceError(f"git repository is not a directory: {path}")
    git_meta = path / ".git"
    if not git_meta.exists():
        raise EvidenceError(f"not a git repository: {path}")
    return path


def _run_git(repo: Path, verb: str, *args: str) -> str:
    if verb not in _GIT_VERBS:
        raise EvidenceError(f"unsupported git verb: {verb!r}")
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", verb, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=repo,
            shell=False,
            check=False,
            env=env,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise EvidenceError("Git evidence unavailable or timed out") from None
    if result.returncode != 0:
        raise EvidenceError(f"git {verb} failed; evidence unavailable")
    return result.stdout


def check_checkout_state(repo: str | Path) -> list[str]:
    """Inspect sparse checkout/index separately from committed tree content."""
    cwd = validate_repo(repo)
    sparse = _run_git(
        cwd, "config", "--type=bool", "--default=false", "--get", "core.sparseCheckout"
    )
    problems = []
    if sparse.strip() == "true":
        problems.append("sparse checkout is enabled")
    sparse_index = _run_git(
        cwd, "config", "--type=bool", "--default=false", "--get", "index.sparse"
    )
    if sparse_index.strip() == "true":
        problems.append("sparse index is enabled")
    index = _run_git(cwd, "ls-files", "--sparse", "--stage", "-z")
    if any(row.startswith("040000 ") for row in index.split("\x00")):
        problems.append("sparse directory entries exist in index")
    flags = _run_git(cwd, "ls-files", "-v", "-z")
    if any(row.startswith(("S ", "s ")) for row in flags.split("\x00")):
        problems.append("skip-worktree entries exist in index")
    return problems


def _top_directories(repo: Path, sha: str) -> frozenset[str]:
    """Read directory anchors; optional root-file removal is a separate policy."""
    rows = _run_git(repo, "ls-tree", "-z", "--end-of-options", sha)
    return frozenset(
        row.split("\t", 1)[1]
        for row in rows.split("\x00")
        if row and row.split()[1] == "tree"
    )


def _renamed_paths(repo: Path, base: str, tip: str | None) -> set[str]:
    """Account for actual file moves, rather than a newly added dummy root."""
    revisions = [base, tip] if tip is not None else ["--cached", base]
    fields = _run_git(
        repo,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--name-status",
        "--find-renames=50%",
        "-z",
        *revisions,
        "--",
    ).split("\x00")
    renamed = set()
    position = 0
    while position < len(fields) and fields[position]:
        status = fields[position]
        if status.startswith("R"):
            renamed.add(fields[position + 1])
            position += 3
        else:
            position += 2
    return renamed


def _missing_directory_content(repo: Path, base: str, tip: str) -> bool:
    """Reject loss of whole directory anchors, allowing evidenced relocations.

    A tree cannot prove whether individual deletions were intentional. Existing
    root, artifact and product contracts remain necessary for intra-directory
    omissions. Local sparse provenance is checked independently.
    """
    missing = (
        _top_directories(repo, base) - _top_directories(repo, tip)
    ) & DIRECTORY_ANCHORS
    if not missing:
        return False
    paths = _run_git(
        repo, "ls-tree", "-r", "--name-only", "-z", base, "--", *sorted(missing)
    )
    return _unrelocated_paths(repo, base, tip, set(filter(None, paths.split("\x00"))))


def _unrelocated_paths(
    repo: Path, base: str, tip: str | None, required: set[str]
) -> bool:
    """Account for ambiguous identical-blob renames without reusing destinations.

    Git may attribute a move to a simultaneously deleted optional file with
    identical contents. Each detected relocation covers at most one missing
    mandatory file, so adding one dummy cannot hide multiple omitted files.
    """
    entries = _run_git(repo, "ls-tree", "-r", "-z", base)
    blobs = {}
    for row in filter(None, entries.split("\x00")):
        metadata, path = row.split("\t", 1)
        blobs[path] = metadata.split()[2]
    by_blob: dict[str, set[str]] = {}
    for path in required:
        by_blob.setdefault(blobs[path], set()).add(path)
    for source in _renamed_paths(repo, base, tip):
        candidates = by_blob.get(blobs[source], set())
        if candidates:
            candidates.remove(
                source if source in candidates else next(iter(candidates))
            )
    return any(by_blob.values())


def check_index_tree(repo: str | Path, base: str) -> list[str]:
    """Check the proposed index without write-tree, refresh, or staging."""
    cwd = validate_repo(repo)
    base_sha = resolve_revision(cwd, base)
    before = _run_git(cwd, "ls-files", "--stage", "-z")
    roots = set()
    for record in filter(None, before.split("\x00")):
        metadata, path = record.split("\t", 1)
        if metadata.split()[2] != "0":
            raise EvidenceError("unmerged index is unqualified")
        if "/" in path:
            roots.add(path.split("/", 1)[0])
    missing = (_top_directories(cwd, base_sha) - roots) & DIRECTORY_ANCHORS
    problems = []
    if missing:
        paths = _run_git(
            cwd, "ls-tree", "-r", "--name-only", "-z", base_sha, "--", *sorted(missing)
        )
        if _unrelocated_paths(
            cwd, base_sha, None, set(filter(None, paths.split("\x00")))
        ):
            problems.append("proposed index loses directory anchors")
    if before != _run_git(cwd, "ls-files", "--stage", "-z"):
        problems.append("index changed during inspection")
    return problems


def select_event_range(event_name: str, event: dict[str, Any]) -> tuple[str, str]:
    """Select event-owned identities without mixing PR, push and manual fields."""
    try:
        if event_name in {"pull_request", "pull_request_target"}:
            pr = event["pull_request"]
            base, tip = pr["base"]["sha"], pr["head"]["sha"]
        elif event_name == "push":
            base, tip = event["before"], event["after"]
        elif event_name == "workflow_dispatch":
            inputs = event["inputs"]
            base, tip = inputs["base"], inputs["tip"]
            if not isinstance(base, str) or not isinstance(tip, str):
                raise ValueError("manual identities must be strings")
            return validate_revision_token(base), validate_revision_token(tip)
        else:
            raise ValueError("unsupported event")
        if not all(
            isinstance(sha, str) and _SHA_RE.fullmatch(sha) and set(sha) != {"0"}
            for sha in (base, tip)
        ):
            raise ValueError("missing immutable identities")
        return base, tip
    except (KeyError, TypeError, ValueError):
        raise EvidenceError(
            "event has no qualified base/tip; new branches require an explicit trusted base"
        ) from None


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
        raise EvidenceError(f"git rev-parse did not return a commit SHA for {token!r}")
    return sha


def _git(repo: str | Path, *args: str) -> str:
    """Run an allowlisted git verb in a validated repository."""
    cwd = validate_repo(repo)
    if not args:
        raise EvidenceError("git verb is required")
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


def _shallow_boundaries(repo: Path) -> frozenset[str]:
    """Only truncation intersecting the untrusted range makes it incomplete."""
    state = _run_git(repo, "rev-parse", "--is-shallow-repository").strip()
    if state == "false":
        return frozenset()
    if state != "true":
        raise EvidenceError("history completeness is unknown")
    try:
        path = Path(
            _run_git(
                repo, "rev-parse", "--path-format=absolute", "--git-path", "shallow"
            ).strip()
        )
        with path.open("rb") as stream:
            payload = stream.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("oversized shallow metadata")
        boundaries = frozenset(payload.decode("ascii").splitlines())
        if not boundaries or not all(_SHA_RE.fullmatch(sha) for sha in boundaries):
            raise ValueError("invalid shallow identities")
        return boundaries
    except (OSError, ValueError):
        raise EvidenceError("history completeness is unavailable") from None


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
    shallow = _shallow_boundaries(cwd)
    common = _run_git(cwd, "merge-base", "--all", base_sha, tip_sha).strip()
    if not _SHA_RE.fullmatch(common):
        raise EvidenceError("trusted base and tip have no verified common ancestor")
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
    if shallow.intersection(revisions):
        raise EvidenceError("candidate range crosses incomplete shallow history")
    base_top = _top_level_names(cwd, base_sha)
    offenders: list[str] = []
    for revision in revisions:
        if not _parent_shas(cwd, revision):
            continue
        if is_collapsed_tree(
            base_top, _top_level_names(cwd, revision)
        ) or _missing_directory_content(cwd, common, revision):
            offenders.append(revision)
    if shallow != _shallow_boundaries(cwd):
        raise EvidenceError("history completeness changed during inspection")
    return offenders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--tip", default="HEAD")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check-index", action="store_true")
    parser.add_argument("--event-name")
    parser.add_argument("--event-json", type=Path)
    args = parser.parse_args(argv)
    if bool(args.event_name) != bool(args.event_json):
        parser.error("--event-name and --event-json are required together")
    try:
        if args.event_json:
            args.base, args.tip = _load_event_range(args.event_name, args.event_json)
        return _run_checks(args.repo, args.base, args.tip, check_index=args.check_index)
    except EvidenceError:
        print("ERROR: incomplete or invalid Git/event evidence")
        return 2


def _load_event_range(event_name: str, path: Path) -> tuple[str, str]:
    """Read caller-supplied metadata only inside the current working directory."""
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(Path.cwd().resolve()):
            raise ValueError("event path escaped invocation directory")
        with resolved.open("rb") as stream:
            payload = stream.read(1024 * 1024 + 1)
    except (OSError, ValueError, RecursionError):
        raise EvidenceError("event evidence is unavailable or invalid") from None
    return parse_event_payload(event_name, payload)


def parse_event_payload(event_name: str, payload: bytes) -> tuple[str, str]:
    """Parse bounded bytes; GitHub's host-owned event reader shares this API."""
    try:
        event = json.loads(payload) if len(payload) <= 1024 * 1024 else None
        if not isinstance(event, dict):
            raise ValueError("invalid event")
    except (ValueError, RecursionError):
        raise EvidenceError("event evidence is unavailable or invalid") from None
    return select_event_range(event_name, event)


def _print_problems(title: str, problems: list[str]) -> bool:
    """Render only controlled reasons or immutable commit identities."""
    if not problems:
        return False
    print(title)
    for problem in problems:
        print(f"- {problem}")
    return True


def _run_checks(repo: str, base: str, tip: str, *, check_index: bool) -> int:
    """Keep local state qualification independent of history inspection."""
    cwd = validate_repo(repo)
    if _print_problems("unqualified local checkout/index:", check_checkout_state(cwd)):
        return 2
    if check_index and _print_problems(
        "unqualified proposed index:", check_index_tree(cwd, base)
    ):
        return 2
    offenders = find_collapsing_commits(base, tip, repo=cwd)
    if _print_problems(
        "partial-tree commits must not enter shared history:", offenders
    ):
        return 1
    print(f"no partial-tree commits in {base}..{tip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
