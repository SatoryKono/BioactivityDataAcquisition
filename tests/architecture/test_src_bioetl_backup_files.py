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


def test_src_bioetl_has_no_tracked_editor_backup_files() -> None:
    """Tracked src/bioetl paths must not keep editor leftovers."""
    completed = subprocess.run(
        ["git", "ls-files", "--", "src/bioetl"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    offenders = [
        path
        for path in completed.stdout.splitlines()
        if path.endswith(_FORBIDDEN_SUFFIXES)
    ]
    assert not offenders, (
        "Tracked editor-backup files are forbidden under src/bioetl/. "
        "Delete them; do not keep *.backup/*.bak/*.orig next to product modules.\n"
        + "\n".join(f"  - {item}" for item in offenders)
    )
