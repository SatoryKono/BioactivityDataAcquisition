"""Interfaces-layer bridge: process env → report root.

Application code must not read process environment maps. Ops HTTP, health
readiness, and CLI entrypoints call these helpers instead.
"""

from __future__ import annotations

import os
from pathlib import Path

from bioetl.application.services.run_reports.paths import (
    inspect_report_root_marker,
    resolve_report_root,
)

# Absolute run-reports root inside the main Docker service when bind is correct.
REPORT_ROOT_ENV = "BIOETL_REPORT_ROOT"
# When truthy, missing/mismatched marker makes /health/ready unhealthy (fail-closed).
ENFORCE_REPORT_ROOT_MARKER_ENV = "BIOETL_ENFORCE_REPORT_ROOT_MARKER"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def env_report_root_value() -> str | None:
    """Return stripped ``BIOETL_REPORT_ROOT`` or None when unset/blank."""
    raw = os.environ.get(REPORT_ROOT_ENV, "").strip()
    return raw or None


def configured_report_root(*, root: Path | None = None) -> Path:
    """Resolve the effective run-reports root for interfaces surfaces.

    Precedence: explicit ``root`` → ``BIOETL_REPORT_ROOT`` → application default.
    """
    if root is not None:
        return resolve_report_root(root=root)
    env_value = env_report_root_value()
    if env_value is not None:
        return Path(env_value).expanduser()
    return resolve_report_root()


def enforce_report_root_marker() -> bool:
    """Whether readiness must fail closed on a missing report-root marker."""
    raw = os.environ.get(ENFORCE_REPORT_ROOT_MARKER_ENV, "").strip().lower()
    return raw in _TRUTHY


def report_root_readiness_check(*, root: Path | None = None) -> dict[str, object]:
    """Diagnostic payload for ``/health/ready`` (always included)."""
    resolved = configured_report_root(root=root)
    check = inspect_report_root_marker(report_root=resolved)
    check["enforced"] = enforce_report_root_marker()
    check["env_name"] = REPORT_ROOT_ENV
    check["env_set"] = env_report_root_value() is not None
    return check
