# pyright: reportArgumentType=false
"""Guard tracked src/bioetl against editor backup suffixes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
BACKUP_SUFFIXES = (".backup", ".bak", ".orig")


def test_src_bioetl_has_no_tracked_backup_suffixes() -> None:
    """Tracked product sources must not include editor leftover backups."""
    result = subprocess.run(
        ["git", "ls-files", "--", "src/bioetl"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    offenders = [
        path
        for path in result.stdout.splitlines()
        if path.lower().endswith(BACKUP_SUFFIXES)
    ]
    assert offenders == [], offenders
