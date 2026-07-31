# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared support for authoritative module-coverage inventory assertions."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


_GIT_STATUS_TIMEOUT_SECONDS = 15


def _run_git_command(command: list[str], *, root: Path) -> tuple[int, str]:
    """Run Git without PIPE reader threads that can hang on Windows."""
    handle = tempfile.NamedTemporaryFile(
        prefix="module_coverage_inventory_git_",
        suffix=".txt",
        delete=False,
    )
    output_path = Path(handle.name)
    handle.close()
    try:
        with output_path.open("w", encoding="utf-8", errors="replace") as output:
            result = subprocess.run(
                command,
                cwd=root,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
                stdout=output,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=_GIT_STATUS_TIMEOUT_SECONDS,
            )
        return result.returncode, output_path.read_text(
            encoding="utf-8", errors="replace"
        )
    finally:
        output_path.unlink(missing_ok=True)


def _git_path_is_dirty(path: str, *, root: Path) -> bool:
    """Check staged and unstaged changes without refreshing the Git index."""
    for cached_args in ([], ["--cached"]):
        returncode, _ = _run_git_command(
            [
                "git",
                "--no-optional-locks",
                "diff",
                "--quiet",
                *cached_args,
                "--",
                path,
            ],
            root=root,
        )
        if returncode == 1:
            return True
        if returncode != 0:
            raise OSError(f"git diff failed with exit code {returncode}")
    return False


def skip_if_artifact_is_not_authoritative(
    *,
    root: Path,
    artifact_path: Path,
) -> None:
    """Skip assertions for artifacts that are untracked, ignored, or locally dirty."""
    artifact_relpath = artifact_path.relative_to(root).as_posix()
    try:
        tracked_returncode, _ = _run_git_command(
            ["git", "ls-files", "--error-unmatch", "--", artifact_relpath],
            root=root,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed-artifact authority checks are not reliable on this checkout."
        )

    if tracked_returncode != 0:
        pytest.skip(
            "Committed-artifact assertions are only authoritative for tracked repo "
            f"artifacts. Untracked or ignored: {artifact_relpath}"
        )

    try:
        is_dirty = _git_path_is_dirty(artifact_relpath, root=root)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed-artifact dirty-state checks are not reliable on this checkout."
        )

    if is_dirty:
        pytest.skip(
            "Committed-artifact assertions are only authoritative for a clean "
            f"{artifact_relpath} artifact."
        )


def skip_if_module_coverage_inventory_is_dirty(
    *,
    root: Path,
    inventory_path: Path,
) -> None:
    """Skip committed-evidence assertions when the inventory artifact is dirty."""
    inventory_relpath = inventory_path.relative_to(root).as_posix()
    try:
        is_dirty = _git_path_is_dirty(inventory_relpath, root=root)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(
            "Committed module-coverage inventory dirty-artifact guard is not "
            "authoritative on this checkout."
        )

    if is_dirty:
        pytest.skip(
            "Committed module-coverage inventory assertions are only authoritative "
            f"for a clean {inventory_relpath} artifact."
        )
