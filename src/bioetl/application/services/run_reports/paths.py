"""Pure report-root path helpers (no process env maps).

Application code resolves an explicit ``root`` or the mutable
:data:`DEFAULT_REPORT_ROOT` default. Process environment bridging
(``BIOETL_REPORT_ROOT``) lives in the interfaces layer so this module stays
free of infrastructure/Settings imports.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from bioetl.application.services.run_reports.source_identity import (
    IDENTITY_STATE_ALIGNED,
    IDENTITY_STATE_FOREIGN,
    IDENTITY_STATE_INVALID,
    IDENTITY_STATE_MISSING,
    compare_runtime_source_identity,
    normalize_source_id,
)

# Relative default under the process CWD. In the main Docker service this is
# ``/app/reports/run-reports`` when CWD is ``/app`` and the host ``reports/``
# tree is bind-mounted at ``/app/reports``.
DEFAULT_REPORT_ROOT = Path("reports") / "run-reports"

# Identity marker on the dashboard reports bind mount (parent of run-reports).
# Stale Docker Desktop bind caches that point at an empty tree fail this check.
REPORT_ROOT_MARKER_NAME = ".bioetl-report-root"
REPORT_ROOT_MARKER_VALUE = "bioetl-report-root-v1"

# Machine-local source attestation written by the supported Docker runtime
# manager. Unlike the tracked layout marker above, this value is bound to the
# selected repository root and contracted bind mounts.
REPORT_ROOT_SOURCE_IDENTITY_NAME = ".bioetl-report-source.json"
REPORT_ROOT_SOURCE_IDENTITY_SCHEMA = "bioetl-report-source-v1"


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


def report_root_source_identity_path(*, report_root: Path | None = None) -> Path:
    """Path of the machine-local source attestation for one report root."""
    base = resolve_report_root(root=report_root)
    if base.name == "run-reports":
        return base.parent / REPORT_ROOT_SOURCE_IDENTITY_NAME
    return base / REPORT_ROOT_SOURCE_IDENTITY_NAME


def write_report_root_source_identity(
    *,
    report_root: Path,
    source_id: str,
) -> Path:
    """Atomically write a versioned machine-local report source attestation."""
    valid_source_id = normalize_source_id(source_id)
    if valid_source_id is None:
        raise ValueError("source_id must be a 64-character lowercase hex digest")
    target = report_root_source_identity_path(report_root=report_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": REPORT_ROOT_SOURCE_IDENTITY_SCHEMA,
        "runtime_source_id": valid_source_id,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f"{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        temporary_path.replace(target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return target


def _source_identity_failure(
    payload: dict[str, object],
    *,
    reason: str,
    state: str,
    message: str,
) -> dict[str, object]:
    payload.update(
        {
            "source_identity_status": "unhealthy",
            "source_identity": reason,
            "source_identity_state": state,
            "source_identity_message": message,
        }
    )
    return payload


def _read_source_identity_payload(
    marker: Path,
) -> tuple[dict[str, object] | None, tuple[str, str] | None]:
    if not marker.is_file():
        return None, (
            "missing",
            "Report-root source attestation is missing; start or recover "
            "the main stack from the intended checkout.",
        )
    try:
        raw = json.loads(marker.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, (
            "unreadable",
            f"Report-root source attestation unreadable: {exc}",
        )
    return (raw if isinstance(raw, dict) else {}), None


def _evaluate_source_identity_payload(
    payload: dict[str, object],
    *,
    raw: dict[str, object],
    expected: str,
) -> dict[str, object]:
    actual_schema = str(raw.get("schema_version") or "")[:120]
    actual_raw = str(raw.get("runtime_source_id") or "")
    actual = normalize_source_id(actual_raw)
    payload["source_identity_schema_actual"] = actual_schema or None
    payload["source_identity_actual"] = actual
    if actual_schema != REPORT_ROOT_SOURCE_IDENTITY_SCHEMA:
        return _source_identity_failure(
            payload,
            reason="schema_mismatch",
            state=IDENTITY_STATE_INVALID,
            message="Report-root source attestation schema mismatch.",
        )
    if actual is None:
        return _source_identity_failure(
            payload,
            reason="invalid",
            state=IDENTITY_STATE_INVALID,
            message="Report-root source attestation digest is invalid.",
        )
    comparison = compare_runtime_source_identity(expected=expected, actual=actual)
    if comparison.state != IDENTITY_STATE_ALIGNED:
        return _source_identity_failure(
            payload,
            reason="mismatch",
            state=IDENTITY_STATE_FOREIGN,
            message="Report-root source identity belongs to another runtime root.",
        )
    payload.update(
        {
            "source_identity_status": "healthy",
            "source_identity": "ok",
            "source_identity_state": IDENTITY_STATE_ALIGNED,
            "source_identity_message": "Report-root source identity matches runtime.",
        }
    )
    return payload


def inspect_report_root_source_identity(
    *,
    report_root: Path | None = None,
    expected_source_id: str | None,
) -> dict[str, object]:
    """Inspect source attestation and compare it with the managed runtime ID."""
    resolved = resolve_report_root(root=report_root)
    marker = report_root_source_identity_path(report_root=resolved)
    expected = normalize_source_id(expected_source_id)
    payload: dict[str, object] = {
        "source_identity_path": str(marker.as_posix()),
        "source_identity_schema_expected": REPORT_ROOT_SOURCE_IDENTITY_SCHEMA,
        "source_identity_expected": expected,
    }
    if expected is None:
        return _source_identity_failure(
            payload,
            reason="expected_missing",
            state=IDENTITY_STATE_MISSING,
            message=(
                "Managed runtime source identity is missing or invalid; "
                "start the stack through runtime_manager."
            ),
        )
    raw, failure = _read_source_identity_payload(marker)
    if failure is not None:
        return _source_identity_failure(
            payload,
            reason=failure[0],
            state=(
                IDENTITY_STATE_MISSING
                if failure[0] == "missing"
                else IDENTITY_STATE_INVALID
            ),
            message=failure[1],
        )
    return _evaluate_source_identity_payload(
        payload,
        raw=raw or {},
        expected=expected,
    )


def inspect_report_root_marker(
    *,
    report_root: Path | None = None,
) -> dict[str, object]:
    """Inspect the bind-identity marker without raising.

    Returns a JSON-friendly diagnostic payload suitable for ``/health/ready``
    and operator verify scripts.
    """
    resolved = resolve_report_root(root=report_root)
    marker = report_root_marker_path(report_root=resolved)
    payload: dict[str, object] = {
        "report_root": str(resolved.as_posix()),
        "marker_path": str(marker.as_posix()),
        "marker_token_expected": REPORT_ROOT_MARKER_VALUE,
    }
    if not marker.is_file():
        payload["status"] = "unhealthy"
        payload["marker"] = "missing"
        payload["layout_marker_state"] = "missing"
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
        payload["layout_marker_state"] = "invalid"
        payload["message"] = f"Report-root marker unreadable: {exc}"
        return payload
    if token != REPORT_ROOT_MARKER_VALUE:
        payload["status"] = "unhealthy"
        payload["marker"] = "mismatch"
        payload["layout_marker_state"] = "invalid"
        payload["marker_token_actual"] = token[:120]
        payload["message"] = (
            "Report-root marker token mismatch — bind mount is not the "
            "canonical BioETL reports tree."
        )
        return payload
    payload["status"] = "healthy"
    payload["marker"] = "ok"
    payload["layout_marker_state"] = "aligned"
    payload["message"] = "Report-root marker present"
    return payload


def report_root_marker_is_healthy(*, report_root: Path | None = None) -> bool:
    """Return True when the bind-identity marker is present and valid."""
    return (
        inspect_report_root_marker(report_root=report_root).get("status") == "healthy"
    )
