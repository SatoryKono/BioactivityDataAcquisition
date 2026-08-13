"""Interfaces-layer bridge: process env → report root.

Application code must not read process environment maps. Ops HTTP, health
readiness, and CLI entrypoints call these helpers instead.
"""

from __future__ import annotations

import os
from pathlib import Path

from bioetl.application.services.run_reports.paths import (
    inspect_report_root_marker,
    inspect_report_root_source_identity,
    resolve_report_root,
)
from bioetl.application.services.run_reports.source_identity import (
    RUNTIME_SOURCE_ID_ENV,
    RuntimeSourceIdentityResolution,
    load_repository_source_environment,
    resolve_runtime_source_identity,
)
from bioetl.composition.runtime_builders.config_access import load_settings

# Absolute run-reports root inside the main Docker service when bind is correct.
REPORT_ROOT_ENV = "BIOETL_REPORT_ROOT"
# When truthy, missing/mismatched marker makes /health/ready unhealthy (fail-closed).
ENFORCE_REPORT_ROOT_MARKER_ENV = "BIOETL_ENFORCE_REPORT_ROOT_MARKER"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def env_report_root_value() -> str | None:
    """Return stripped ``BIOETL_REPORT_ROOT`` or None when unset/blank."""
    configured = load_settings().report_root
    return str(configured) if configured is not None else None


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
    return load_settings().enforce_report_root_marker


def runtime_source_identity_resolution() -> RuntimeSourceIdentityResolution:
    """Resolve Ops HTTP identity with the canonical cross-runtime precedence."""
    repository_environment = load_repository_source_environment(
        _repository_root(),
        names=(RUNTIME_SOURCE_ID_ENV,),
        process_environment=os.environ,
    )
    return resolve_runtime_source_identity(
        process_environment=os.environ,
        repository_environment=repository_environment,
    )


def runtime_source_id_value() -> str | None:
    """Return the canonical managed runtime source digest, if any."""
    return runtime_source_identity_resolution().value


def report_root_readiness_check(*, root: Path | None = None) -> dict[str, object]:
    """Diagnostic payload for ``/health/ready`` (always included)."""
    resolved = configured_report_root(root=root)
    check = inspect_report_root_marker(report_root=resolved)
    layout_status = check.get("status")
    source_resolution = runtime_source_identity_resolution()
    source_check = inspect_report_root_source_identity(
        report_root=resolved,
        expected_source_id=source_resolution.value,
    )
    if not source_resolution.is_consistent:
        source_check["source_identity_status"] = "unhealthy"
        source_check["source_identity_state"] = source_resolution.state
        source_check["source_identity_message"] = (
            "runtime source identity resolution is not consistent: "
            f"{source_resolution.state}"
        )
    check["layout_status"] = layout_status
    check["layout_message"] = check.get("message")
    check.update(source_check)
    if (
        layout_status == "healthy"
        and source_check.get("source_identity_status") == "healthy"
    ):
        check["status"] = "healthy"
    else:
        check["status"] = "unhealthy"
        if source_check.get("source_identity_status") != "healthy":
            check["message"] = source_check.get("source_identity_message")
    check["enforced"] = enforce_report_root_marker()
    check["env_name"] = REPORT_ROOT_ENV
    check["env_set"] = env_report_root_value() is not None
    check["source_identity_env_name"] = RUNTIME_SOURCE_ID_ENV
    check["source_identity_env_set"] = source_resolution.value is not None
    check["source_identity_resolution_status"] = source_resolution.status
    check["source_identity_resolution_state"] = source_resolution.state
    check["source_identity_resolution_source"] = source_resolution.source
    check["source_identity_resolution_conflicts"] = list(source_resolution.conflicts)
    return check
