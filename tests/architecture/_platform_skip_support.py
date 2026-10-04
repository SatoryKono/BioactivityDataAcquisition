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
"""Shared platform skip helpers for mounted-worktree architecture tests."""

from __future__ import annotations

import sys
from pathlib import Path


def mounted_worktree_skip_reason() -> str | None:
    """Return the canonical skip reason for Windows-backed slow filesystem lanes."""
    if sys.platform.startswith("win"):
        return "Skipped on Windows due to filesystem performance"

    root = Path(__file__).resolve().parents[2]
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    # WSL also supports native Linux checkouts. Only the filesystem containing
    # this checkout determines whether the expensive scan needs a skip.
    containing_mounts = []
    for row in mounts:
        fields = row.split()
        if len(fields) < 4:
            continue
        mount = Path(fields[1].replace(r"\040", " "))
        if root.is_relative_to(mount):
            containing_mounts.append((len(mount.parts), fields[2], fields[3]))
    if containing_mounts:
        _, filesystem, options = max(containing_mounts)
        if filesystem == "drvfs" or (filesystem == "9p" and "aname=drvfs" in options):
            return "Skipped on WSL due to filesystem performance"
    return None
