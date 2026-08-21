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
"""Forbid tracked editor-backup files under src/bioetl (ARCH-BACKUP-001 / #9317)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_SUFFIXES = (".backup", ".bak", ".orig")


def _tracked_src_bioetl_paths() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", "src/bioetl"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [path for path in completed.stdout.split("\0") if path]


def test_src_bioetl_has_no_tracked_editor_backup_files() -> None:
    """Tracked src/bioetl paths must not keep editor leftovers."""
    offenders = [
        path
        for path in _tracked_src_bioetl_paths()
        if path.endswith(_FORBIDDEN_SUFFIXES)
    ]
    assert not offenders, (
        "Tracked editor-backup files are forbidden under src/bioetl/. "
        "Delete them; do not keep *.backup/*.bak/*.orig next to product modules.\n"
        + "\n".join(f"  - {item}" for item in offenders)
    )


def test_tracked_src_bioetl_path_split_preserves_exact_names() -> None:
    """NUL-delimited git output must keep exact path bytes, including suffix."""
    paths = _tracked_src_bioetl_paths()
    assert paths, "src/bioetl must have tracked files"
    assert all("\n" not in path for path in paths)
    assert not any(path.endswith('"') for path in paths)
