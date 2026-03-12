#!/usr/bin/env python3
"""Smoke visual regression check for selected diagram SVG baselines.

Intended usage:
1. Run diagram render pipeline (render.sh) in CI.
2. Run this script to ensure selected baseline SVGs were not modified by render.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_MANIFEST = Path("docs/02-architecture/mmd-diagrams/visual-smoke-manifest.txt")


def load_manifest(manifest_path: Path) -> list[str]:
    """Load relative paths from a manifest file."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    paths: list[str] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)

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
    cmd = ["git", "diff", "--name-only", "--", *rel_paths]
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        err = completed.stderr.strip()
        raise RuntimeError(f"git diff failed: {err or 'unknown error'}")
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
