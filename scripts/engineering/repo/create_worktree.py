"""Create BioETL worktrees through the workstation's governed Windows entrypoint.

Bootstrap with --install-helper from the primary checkout; --validate-only
checks the destination without Git calls or filesystem mutation. Creation never
copies a machine-local .env. --env-example-approved records prior, explicit
per-task approval for the tracked root template; it does not grant consent.
"""

from __future__ import annotations

import argparse
import os
import re
import runpy
import subprocess
import sys
from pathlib import Path, PurePosixPath

APPROVED_ROOT = Path("D:/github")
WORKTREE_ROOT = APPROVED_ROOT / "BioactivityDataAcquisition-worktrees"
HELPER_NAME = "bioetl-create-worktree.py"
DEFAULT_START_POINT = "origin/main"
_TASK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *[f"COM{i}" for i in range(1, 10)],
    *[f"LPT{i}" for i in range(1, 10)],
}


def _require_windows() -> None:
    if os.name != "nt":
        raise ValueError(
            "Use Windows Python: this workstation policy requires D:/github; no POSIX fallback is allowed"
        )


def _inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path resolves outside approved root {root}: {resolved}")
    return resolved


def _roots() -> tuple[Path, Path]:
    _require_windows()
    approved = APPROVED_ROOT.absolute()
    if not approved.is_dir() or approved.resolve() != approved:
        raise ValueError(
            "D:/github must exist and must not redirect through junctions/symlinks"
        )
    worktrees = _inside(WORKTREE_ROOT, approved)
    # A renamed/redirected worktree parent is not an alternative permission root.
    if worktrees != WORKTREE_ROOT.absolute():
        raise ValueError("The approved worktree parent must not redirect")
    return approved, worktrees


def validate_destination(value: str) -> Path:
    """Validate all existing ancestors; create nothing and run no Git command."""
    approved, worktrees = _roots()
    raw = Path(value)
    candidate = raw if raw.is_absolute() else WORKTREE_ROOT / value
    name = candidate.name
    if (
        not _TASK.fullmatch(name)
        or name.endswith(".")
        or name.split(".")[0].upper() in _RESERVED
    ):
        raise ValueError(
            "Use a task slug, not traversal, separators, trailing dots or Windows device names"
        )
    if candidate.parent.absolute() != WORKTREE_ROOT.absolute():
        raise ValueError(
            "New worktrees must be one task child of D:/github/BioactivityDataAcquisition-worktrees"
        )
    resolved = _inside(candidate, approved)
    if resolved.parent != worktrees:
        raise ValueError("Destination redirects outside the approved worktree parent")
    if os.path.lexists(candidate):
        raise ValueError(
            f"Destination already exists; reuse or inspect it: {candidate}"
        )
    return resolved


def _source_repo() -> Path:
    approved, _ = _roots()
    repo = _inside(Path(__file__).resolve().parents[3], approved)
    if not (repo / ".git").exists():
        raise ValueError(
            "The tracked implementation must run from a complete BioETL checkout"
        )
    return repo


def _git(repo: Path, *args: str) -> str:
    # This CLI accepts simple ref names/SHA values, never arbitrary Git options
    # or revision expressions. Fixed options below are implementation-owned.
    checked_args = []
    for argument in args:
        if not re.fullmatch(r"[A-Za-z0-9_./:\\{}^-]+", argument):
            raise ValueError("Git argument contains unsupported characters")
        checked_args.append(argument)
    result = subprocess.run(
        [
            "git",
            "-c",
            "gc.auto=0",
            "-c",
            f"safe.directory={repo}",
            "-C",
            str(repo),
            *checked_args,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def _revision(repo: Path, ref: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", ref):
        raise ValueError("Invalid Git revision")
    sha = _git(
        repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", sha):
        raise ValueError("Git did not return an immutable commit SHA")
    return sha


def _check_env(repo: Path, sha: str, approved: bool) -> None:
    paths = _git(repo, "ls-tree", "-rz", "--name-only", sha, "--").split("\0")
    env_paths = []
    for path in paths:
        normalized = path.replace("\\", "/").casefold()
        name = PurePosixPath(normalized).name
        if name == ".env" or name.startswith(".env."):
            env_paths.append(normalized)
    if any(p != ".env.example" for p in env_paths) or len(env_paths) > 1:
        raise ValueError(
            "Checkout contains other .env files; this helper can approve only the tracked root .env.example"
        )
    if env_paths and not approved:
        raise ValueError(
            "Checkout creates .env.example: obtain explicit per-task user approval before --env-example-approved"
        )


def install_helper() -> Path:
    """Install an exclusive managed entrypoint; never overwrite a local helper."""
    repo = _source_repo()
    metadata = repo / ".git"
    if not metadata.is_dir():
        raise ValueError("Install from the primary checkout, not a linked worktree")
    approved, _ = _roots()
    if _inside(metadata, approved) != metadata.absolute():
        raise ValueError("Primary Git metadata must not redirect")
    hooks = _inside(metadata / "hooks", metadata.resolve())
    implementation = repo / "scripts/engineering/repo/create_worktree.py"
    if not implementation.is_file():
        raise ValueError("Primary checkout is missing the tracked implementation")
    target = hooks / HELPER_NAME
    content = (
        '"""Managed BioETL worktree entrypoint; source: scripts/engineering/repo/create_worktree.py."""\n'
        "from pathlib import Path\nimport runpy\n"
        'raise SystemExit(runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/engineering/repo/create_worktree.py"))["main"]())\n'
    )
    if os.path.lexists(target):
        if target.is_symlink() or target.read_text(encoding="utf-8") != content:
            raise ValueError(
                "Existing local helper is unmanaged/different; preserve it and review migration explicitly"
            )
        return target
    hooks.mkdir(exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return target


def _created_target(destination: Path) -> None:
    _, parent = _roots()
    if (
        not destination.is_dir()
        or _inside(destination, parent) != destination.absolute()
    ):
        raise ValueError(
            f"Created target changed or redirected; preserve and inspect {destination}"
        )


def _populate_existing(destination: Path, sha: str) -> None:
    _created_target(destination)
    if any(child.name != ".git" for child in destination.iterdir()):
        raise ValueError(f"New target gained files; preserve and inspect {destination}")
    _git(destination, "read-tree", "--reset", "-u", sha)
    if _revision(destination, "HEAD") != sha:
        raise ValueError(
            f"Branch moved during creation; preserve and inspect {destination}; no ref was reset"
        )


def create_worktree(args: argparse.Namespace) -> Path:
    destination = validate_destination(args.destination)
    # Execute the tracked stdlib guard without importing project packages or
    # writing bytecode. Keep its ancestor identities in process until creation.
    path_guard = runpy.run_path(str(Path(__file__).with_name("operation_guards.py")))
    permit = path_guard["prepare_worktree"](
        str(destination), allowed_root=APPROVED_ROOT
    )
    repo = _source_repo()
    approved, _ = _roots()
    _inside(
        Path(
            _git(
                repo, "rev-parse", "--path-format=absolute", "--git-common-dir"
            ).strip()
        ),
        approved,
    )
    if args.existing_branch and args.start_point != DEFAULT_START_POINT:
        raise ValueError("--existing-branch cannot be combined with --start-point")
    ref = (
        f"refs/heads/{args.existing_branch}"
        if args.existing_branch
        else args.start_point
    )
    sha = _revision(repo, ref)
    branch = args.existing_branch or args.branch or f"codex/{destination.name}"
    if not args.detach:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch):
            raise ValueError("Use a simple branch name, never Git options")
        _git(repo, "check-ref-format", "--branch", branch)
    if not args.no_checkout:
        _check_env(repo, sha, args.env_example_approved)
    # Resolve again immediately before creation, after all potentially slow reads.
    validate_destination(args.destination)
    command = ["worktree", "add"]
    if args.no_checkout or args.existing_branch:
        command.append("--no-checkout")
    if args.detach:
        command.append("--detach")
    elif not args.existing_branch:
        command.extend(["-b", branch])
    command.extend(["--", str(destination), args.existing_branch or sha])
    decision = path_guard["revalidate_worktree"](permit, allowed_root=APPROVED_ROOT)
    if decision.status != "PASS":
        raise ValueError("Shared worktree guard refused creation: " + decision.code)
    _git(repo, *command)
    _created_target(destination)
    if args.existing_branch and not args.no_checkout:
        # Native add reserves the branch without checkout. Populate only the
        # consent-checked immutable tree, even if another process moves its ref.
        _populate_existing(destination, sha)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--install-helper", action="store_true")
    mode.add_argument("--validate-only", action="store_true")
    branch = parser.add_mutually_exclusive_group()
    branch.add_argument("--branch")
    branch.add_argument("--existing-branch")
    branch.add_argument("--detach", action="store_true")
    parser.add_argument("--start-point", default=DEFAULT_START_POINT)
    parser.add_argument("--no-checkout", action="store_true")
    parser.add_argument("--env-example-approved", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.install_helper:
            if (
                args.destination
                or args.branch
                or args.existing_branch
                or args.detach
                or args.no_checkout
                or args.env_example_approved
                or args.start_point != DEFAULT_START_POINT
            ):
                raise ValueError(
                    "--install-helper cannot be combined with creation options"
                )
            result = install_helper()
        elif not args.destination:
            raise ValueError("A task destination is required")
        elif args.validate_only:
            result = validate_destination(args.destination)
        else:
            result = create_worktree(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(result)
    return 0
