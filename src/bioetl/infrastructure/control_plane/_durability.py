"""Durability helpers shared by file-backed control-plane stores."""

from __future__ import annotations

import os

from bioetl.infrastructure.config.settings_api import get_settings

__all__ = [
    "flush_control_plane_file_descriptor",
    "should_fsync_control_plane_writes",
]


def should_fsync_control_plane_writes(*, os_name: str | None = None) -> bool:
    """Keep durable flushes unless Windows test runs explicitly relax them."""
    current_os_name = os.name if os_name is None else os_name
    if current_os_name != "nt":
        return True
    settings = get_settings()
    # Windows test runs commonly execute from cloud-synced worktrees where
    # fsync() can stall long enough to defeat reproducibility gates. Keep
    # production durability semantics unchanged and relax only test-mode writes.
    return not settings.test_mode


def flush_control_plane_file_descriptor(file_descriptor: int) -> None:
    """Flush one control-plane file descriptor when durable writes are required."""
    if not should_fsync_control_plane_writes():
        return
    os.fsync(file_descriptor)
