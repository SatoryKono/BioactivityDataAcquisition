"""Pure report-root path helpers (no process env maps).

Application code resolves an explicit ``root`` or the mutable
:data:`DEFAULT_REPORT_ROOT` default. Process environment bridging
(``BIOETL_REPORT_ROOT``) lives in the interfaces layer so this module stays
free of infrastructure/Settings imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Relative default under the process CWD. In the main Docker service this is
# ``/app/reports/run-reports`` when CWD is ``/app`` and the host ``reports/``
# tree is bind-mounted at ``/app/reports``.
DEFAULT_REPORT_ROOT = Path("reports") / "run-reports"

# Identity marker on the dashboard reports bind mount (parent of run-reports).
# Stale Docker Desktop bind caches that point at an empty tree fail this check.
REPORT_ROOT_MARKER_NAME = ".bioetl-report-root"
REPORT_ROOT_MARKER_TOKEN = "bioetl-report-root-v1"


def resolve_report_root(*, root: Path | None = None) -> Path:
    """Return the effective run-reports root.

    Explicit ``root`` wins. Otherwise use :data:`DEFAULT_REPORT_ROOT`, which
    tests may rebind for isolation (see ``tests/conftest.py``).
    """
    if root is not None:
        return Path(root)
    return DEFAULT_REPORT_ROOT


def report_root_marker_path(*, report_root: Path | None = None) -> Path:
    """Path of the bind-identity marker for one run-reports root.

    Layout contract:

    - default root ``reports/run-reports`` → marker ``reports/.bioetl-report-root``
    - container root ``/app/reports/run-reports`` → ``/app/reports/.bioetl-report-root``
    - isolated test roots not named ``run-reports`` → ``<root>/.bioetl-report-root``
    """
    base = resolve_report_root(root=report_root)
    if base.name == "run-reports":
        return base.parent / REPORT_ROOT_MARKER_NAME
    return base / REPORT_ROOT_MARKER_NAME


def inspect_report_root_marker(
    *,
    report_root: Path | None = None,
) -> dict[str, Any]:  # Any: health diagnostic payload is JSON-heterogeneous
    """Inspect the bind-identity marker without raising.

    Returns a JSON-friendly diagnostic payload suitable for ``/health/ready``
    and operator verify scripts.
    """
    resolved = resolve_report_root(root=report_root)
    marker = report_root_marker_path(report_root=resolved)
    payload: dict[str, Any] = {  # Any: health diagnostic payload is JSON-heterogeneous
        "report_root": str(resolved.as_posix()),
        "marker_path": str(marker.as_posix()),
        "marker_token_expected": REPORT_ROOT_MARKER_TOKEN,
    }
    if not marker.is_file():
        payload["status"] = "unhealthy"
        payload["marker"] = "missing"
        payload["message"] = (
            "Report-root marker missing — host writes and Docker bind may "
            "point at different trees. Recreate the bioetl container from the "
            "canonical checkout and run scripts/ops/runtime/docker/verify_report_bind.py."
        )
        return payload
    try:
        token = marker.read_text(encoding="utf-8").strip()
    except OSError as exc:
        payload["status"] = "unhealthy"
        payload["marker"] = "unreadable"
        payload["message"] = f"Report-root marker unreadable: {exc}"
        return payload
    if token != REPORT_ROOT_MARKER_TOKEN:
        payload["status"] = "unhealthy"
        payload["marker"] = "mismatch"
        payload["marker_token_actual"] = token[:120]
        payload["message"] = (
            "Report-root marker token mismatch — bind mount is not the "
            "canonical BioETL reports tree."
        )
        return payload
    payload["status"] = "healthy"
    payload["marker"] = "ok"
    payload["message"] = "Report-root marker present"
    return payload


def report_root_marker_is_healthy(*, report_root: Path | None = None) -> bool:
    """Return True when the bind-identity marker is present and valid."""
    return inspect_report_root_marker(report_root=report_root).get("status") == "healthy"
