"""Composition dependency loaders and health-server construction helpers."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.config_access import load_settings
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)

if TYPE_CHECKING:
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.composition.health_service_access import (
        HealthServerDependenciesProtocol,
        QuarantineRuntimeServiceProtocol,
    )
    from bioetl.interfaces.http.health_server import HealthServer

_RUNTIME_SOURCE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _runtime_source_id_from_environment() -> str | None:
    """Return a managed opaque source identity without exposing host paths."""
    configured = load_settings().runtime_source_id
    value = configured.strip().lower() if configured is not None else ""
    return value if _RUNTIME_SOURCE_ID_PATTERN.fullmatch(value) else None


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependenciesProtocol:
    """Load health-listener dependencies from the canonical composition seam."""
    from bioetl.composition.health_service_access import (
        get_health_server_dependencies as _impl,
    )

    if data_root is None:
        return _impl()
    return _impl(data_root=data_root)


def get_health_server_quarantine_service(
    *,
    data_root: Path | None = None,
) -> QuarantineService:
    """Load read-only quarantine service for health listener endpoints."""
    from bioetl.composition.health_service_access import get_quarantine_service as _impl

    if data_root is None:
        return _impl()
    return _impl(data_root=data_root)


def get_quarantine_runtime_service(
    pipeline: str,
) -> QuarantineRuntimeServiceProtocol:
    """Load one pipeline-scoped quarantine runtime service from composition."""
    from bioetl.composition.health_service_access import (
        get_quarantine_runtime_service as _impl,
    )

    return _impl(pipeline)


def build_health_server_pycache_prefix() -> Path:
    """Return the deterministic pycache root for the health server process."""
    return Path(tempfile.gettempdir()) / "bioetl-pycache"


def _get_optional_health_server_quarantine_service(
    *,
    data_root: Path | None = None,
) -> QuarantineService | None:
    """Return quarantine service when available without failing health probes."""
    try:
        if data_root is None:
            return get_health_server_quarantine_service()
        return get_health_server_quarantine_service(data_root=data_root)
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        return None


def build_health_server(
    *,
    host: str,
    port: int,
    deps: HealthServerDependenciesProtocol,
    quarantine_service: QuarantineService | None,
) -> HealthServer:
    """Construct the HTTP health server from composition dependencies."""
    from bioetl.interfaces.http.health_server import (
        HealthServer,
        HealthServerControlPlaneDeps,
    )

    metrics_exposition = getattr(deps, "metrics_exposition", None)
    server = HealthServer(
        host=host,
        port=port,
        control_plane=HealthServerControlPlaneDeps(
            health_monitor=deps.health_monitor,
            quarantine_service=quarantine_service,
            checkpoint_port=deps.checkpoint_port,
            run_manifest_port=deps.run_manifest_port,
            run_ledger_port=deps.run_ledger_port,
            workflow_manifest_port=deps.workflow_manifest_port,
            control_plane_evidence_service=getattr(
                deps,
                "control_plane_evidence_service",
                None,
            ),
            control_plane_integrity_refresher=getattr(
                deps,
                "control_plane_integrity_refresher",
                None,
            ),
            metrics_exposition=metrics_exposition,
            runtime_source_id=_runtime_source_id_from_environment(),
        ),
    )
    data_root = getattr(deps, "data_root", None)
    server.set_data_root(str(data_root) if data_root is not None else None)
    return server


async def close_health_server_resources(
    *,
    deps: HealthServerDependenciesProtocol,
    quarantine_service: QuarantineService | None,
) -> None:
    """Close resources shared by health-server execution modes."""
    try:
        await deps.checkpoint_port.aclose()
    finally:
        # Always attempt quarantine close even if checkpoint close fails (ARCH-CR-03 / #6865).
        if quarantine_service is not None:
            await quarantine_service.aclose()


__all__ = [
    "_get_optional_health_server_quarantine_service",
    "build_health_server",
    "build_health_server_pycache_prefix",
    "close_health_server_resources",
    "get_health_server_dependencies",
    "get_health_server_quarantine_service",
    "get_quarantine_runtime_service",
]
