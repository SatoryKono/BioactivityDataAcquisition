#!/usr/bin/env python3
"""Smoke visual regression check for selected diagram SVG baselines.

Intended usage:
1. Run diagram render pipeline (render.sh) in CI.
2. Run this script to ensure selected baseline SVGs were not modified by render.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .diagram_paths import VISUAL_SMOKE_MANIFEST
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import VISUAL_SMOKE_MANIFEST


DEFAULT_MANIFEST = VISUAL_SMOKE_MANIFEST


def iter_git_candidates() -> list[str]:
    """Return preferred git executable candidates for the current platform."""
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(path: str | None) -> None:
        if not path:
            return
        normalized = os.path.normcase(path)
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(path)

    _add(shutil.which("git"))

    if os.name == "nt":
        _add(r"C:\Program Files\Git\cmd\git.exe")
        _add(r"C:\Program Files\Git\bin\git.exe")

    _add("git")
    return candidates


def run_git_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run git with platform-aware fallback executable resolution."""
    last_completed: subprocess.CompletedProcess[str] | None = None

    for git_executable in iter_git_candidates():
        try:
            completed = subprocess.run(
                [git_executable, *args],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            continue

        if completed.returncode == 0:
            return completed
        last_completed = completed
        break

    err = (
        last_completed.stderr.strip()
        if last_completed is not None and last_completed.stderr
        else "unknown error"
    )
    raise RuntimeError(f"git {' '.join(args)} failed: {err}")


def load_manifest(manifest_path: Path) -> list[str]:
    """Load relative paths from a manifest file."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    paths: list[str] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path = Path(line)
        if path.is_absolute():
            raise ValueError(f"Manifest paths must be relative: {line}")
        if any(part == ".." for part in path.parts):
            raise ValueError(f"Manifest paths must not escape the repository root: {line}")
        if line.startswith("-"):
            raise ValueError(f"Manifest paths must not start with '-': {line}")
        paths.append(path.as_posix())

    if not paths:
        raise ValueError(f"Manifest is empty: {manifest_path}")
    return paths


def ensure_paths_exist(repo_root: Path, rel_paths: list[str]) -> None:
    """Validate that all manifest paths exist in working tree."""
    missing = [p for p in rel_paths if not (repo_root / p).exists()]
    if missing:
        msg = "\n".join(f"  - {p}" for p in missing)
        raise FileNotFoundError(f"Missing manifest path(s):\n{msg}")


def changed_paths(rel_paths: list[str]) -> list[str]:
    """Return list of changed paths among provided manifest entries."""
    completed = run_git_command(["diff", "--name-only", "--", *rel_paths])
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-check selected SVG baselines for diagram render drift."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Path to manifest file (default: {DEFAULT_MANIFEST})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    manifest = (
        args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    )

    try:
        rel_paths = load_manifest(manifest)
        ensure_paths_exist(repo_root, rel_paths)
        changed = changed_paths(rel_paths)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if changed:
        print(
            "[ERROR] Visual smoke regression detected in baseline SVG(s):",
            file=sys.stderr,
        )
        for path in changed:
            print(f"  - {path}", file=sys.stderr)
        print(
            "[HINT] Re-run diagram render pipeline and commit updated baseline SVGs.",
            file=sys.stderr,
        )
        return 1

    print(f"[OK] Visual smoke check passed ({len(rel_paths)} baseline SVGs unchanged).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
