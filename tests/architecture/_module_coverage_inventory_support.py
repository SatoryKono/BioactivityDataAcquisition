"""Shared support for authoritative module-coverage inventory assertions."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def skip_if_artifact_is_not_authoritative(
    *,
    root: Path,
    artifact_path: Path,
) -> None:
    """Skip assertions for artifacts that are untracked, ignored, or locally dirty."""
    artifact_relpath = artifact_path.relative_to(root).as_posix()
    try:
        tracked_result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", artifact_relpath],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed-artifact authority checks are not reliable on this checkout."
        )

    if tracked_result.returncode != 0:
        pytest.skip(
            "Committed-artifact assertions are only authoritative for tracked repo "
            f"artifacts. Untracked or ignored: {artifact_relpath}"
        )

    try:
        dirty_result = subprocess.run(
            ["git", "status", "--short", "--", artifact_relpath],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed-artifact dirty-state checks are not reliable on this checkout."
        )

    dirty_entries = [
        line.strip() for line in dirty_result.stdout.splitlines() if line.strip()
    ]
    if dirty_entries:
        pytest.skip(
            "Committed-artifact assertions are only authoritative for a clean "
            f"{artifact_relpath} artifact. Dirty entries: "
            + ", ".join(dirty_entries[:20])
        )


def skip_if_module_coverage_inventory_is_dirty(
    *,
    root: Path,
    inventory_path: Path,
) -> None:
    """Skip committed-evidence assertions when the inventory artifact is dirty."""
    inventory_relpath = inventory_path.relative_to(root).as_posix()
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", inventory_relpath],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed module-coverage inventory dirty-artifact guard is not "
            "authoritative on this checkout."
        )

    dirty_entries = [
        line.strip() for line in result.stdout.splitlines() if line.strip()
    ]
    if dirty_entries:
        pytest.skip(
            "Committed module-coverage inventory assertions are only authoritative "
            f"for a clean {inventory_relpath} artifact. Dirty entries: "
            + ", ".join(dirty_entries[:20])
        )
