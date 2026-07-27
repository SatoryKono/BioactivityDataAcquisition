"""HTTP Health Server for BioETL.

Provides standard liveness and readiness probes.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from bioetl.application.services.quarantine_service import QuarantineService
from bioetl.domain.ports import (
    CheckpointPort,
    ClockPort,
    HealthMonitorPort,
    LoggerPort,
    RunLedgerPort,
    RunManifestPort,
    WorkflowManifestPort,
)
from bioetl.interfaces.http._forensic_request_budget import (
    FORENSIC_ENDPOINT_CONCURRENCY,
)
from bioetl.interfaces.http.health_server_http_mixin import HealthServerHTTPMixin
from bioetl.interfaces.http.health_server_routing_mixin import (
    HealthServerRoutingMixin,
)
from bioetl.interfaces.http.health_server_state_mixin import HealthServerStateMixin
from bioetl.interfaces.http.processed_records_table import (
    DEFAULT_PROMETHEUS_BASE_URL,
)
from bioetl.interfaces.http.types import HealthResponse


@dataclass(frozen=True, slots=True)
class HealthServerControlPlaneDeps:
    """Collaborator bag for optional health-server control-plane ports."""

    health_monitor: HealthMonitorPort | None = None
    quarantine_service: QuarantineService | None = None
    checkpoint_port: CheckpointPort | None = None
    run_manifest_port: RunManifestPort | None = None
    run_ledger_port: RunLedgerPort | None = None
    workflow_manifest_port: WorkflowManifestPort | None = None


class HealthServer(
    HealthServerHTTPMixin,
    HealthServerRoutingMixin,
    HealthServerStateMixin,
):
    """Async HTTP server for health check endpoints."""

    _server_close_timeout_seconds: float = 1.0

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8081,
        control_plane: HealthServerControlPlaneDeps | None = None,
        prometheus_base_url: str | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize health server.

        Args:
            host: IP address to bind the server to. Defaults to localhost.
            port: TCP port to listen on. Defaults to 8081.
            health_monitor: Optional monitor providing provider health states for
                /health/ready and /health/providers endpoints. Endpoints report
                healthy with no provider data when None.
            quarantine_service: Optional read-only service for
                /ops/quarantine/* explorer endpoints.
            checkpoint_port: Optional read-only checkpoint storage used by
                /ops/control-plane/checkpoint-freshness.
            run_manifest_port: Optional read-only control-plane manifest catalog
                used by /ops/control-plane/* selector endpoints.
            run_ledger_port: Optional read-only control-plane run ledger used
                to resolve latest terminal run completion for selector endpoints.
            workflow_manifest_port: Optional read-only workflow manifest catalog used
                to relate workflow selectors to child pipeline run manifests.
            prometheus_base_url: Optional Prometheus HTTP API base URL for local
                dashboard helper endpoints such as
                /ops/observability/processed-records.
                Defaults to http://localhost:9090.
            logger: Optional LoggerPort for structured server event logging.
                Server events are silently dropped when None.
        """
        deps = control_plane or HealthServerControlPlaneDeps()
        self.host = host
        self.port = port
        self._health_monitor = deps.health_monitor
        self._quarantine_service = deps.quarantine_service
        self._checkpoint_port = deps.checkpoint_port
        self._run_manifest_port = deps.run_manifest_port
        self._run_ledger_port = deps.run_ledger_port
        self._workflow_manifest_port = deps.workflow_manifest_port
        self._data_root: str | None = None
        self._prometheus_base_url = (
            prometheus_base_url or DEFAULT_PROMETHEUS_BASE_URL
        ).rstrip("/")
        self._logger = logger
        self._clock: ClockPort | None = None
        self._server: asyncio.Server | None = None
        self._forensic_endpoint_limiter = asyncio.Semaphore(
            FORENSIC_ENDPOINT_CONCURRENCY
        )
        self._start_time: float | None = None
        self._request_error_allowlist = (
            UnicodeDecodeError,
            ValueError,
            RuntimeError,
            OSError,
            ConnectionError,
            asyncio.IncompleteReadError,
        )
        self._writer_close_allowlist = (
            OSError,
            RuntimeError,
            ConnectionError,
            BrokenPipeError,
        )

    def set_data_root(self, data_root: str | None) -> None:
        """Set the explicit data root served by read-only explorer ports."""
        self._data_root = data_root

    def set_clock(self, clock: ClockPort | None) -> None:
        """Set the optional response clock after server construction."""
        self._clock = clock

    async def start(self) -> None:
        """Start the health server."""
        self._start_time = time.monotonic()
        try:
            self._server = await asyncio.start_server(
                self._handle_connection,
                self.host,
                self.port,
                reuse_address=False,
            )
        except OSError as exc:
            if self._logger:
                self._logger.warning(
                    "health_server_bind_failed",
                    host=self.host,
                    port=self.port,
                    error=str(exc),
                    reason_code="HEALTH_SERVER_BIND_FAILED",
                )
            raise
        if self._logger:
            self._logger.info("health_server_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        """Stop the health server gracefully."""
        if not self._server:
            return
        self._server.close()
        try:
            await asyncio.wait_for(
                self._server.wait_closed(),
                timeout=self._server_close_timeout_seconds,
            )
        except TimeoutError as exc:
            if self._logger:
                self._logger.warning(
                    "health_server_shutdown_timeout",
                    host=self.host,
                    port=self.port,
                    error=str(exc),
                    reason_code="HEALTH_SERVER_SHUTDOWN_TIMEOUT",
                )
        self._server = None
        if self._logger:
            self._logger.info("health_server_stopped")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._server is not None and self._server.is_serving()

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time


async def run_health_server(
    host: str = "0.0.0.0",
    port: int = 8081,
    health_monitor: HealthMonitorPort | None = None,
    quarantine_service: QuarantineService | None = None,
    checkpoint_port: CheckpointPort | None = None,
    run_manifest_port: RunManifestPort | None = None,
    run_ledger_port: RunLedgerPort | None = None,
    workflow_manifest_port: WorkflowManifestPort | None = None,
    prometheus_base_url: str | None = None,
    logger: LoggerPort | None = None,
    clock: ClockPort | None = None,
) -> None:
    """Run the health server until interrupted.

    Starts the HealthServer and keeps it alive until the coroutine is cancelled
    (e.g., via asyncio.CancelledError from a task group or signal handler).

    Args:
        host: IP address to bind to. Defaults to all interfaces (0.0.0.0).
        port: TCP port to listen on. Defaults to 8081.
        health_monitor: Optional monitor providing provider health states.
            Health endpoints report no provider data when None.
        quarantine_service: Optional read-only quarantine explorer service.
        checkpoint_port: Optional read-only checkpoint storage.
        run_manifest_port: Optional read-only control-plane manifest catalog.
        run_ledger_port: Optional read-only control-plane run ledger.
        workflow_manifest_port: Optional read-only workflow manifest catalog.
        prometheus_base_url: Optional Prometheus HTTP API base URL.
        logger: Optional LoggerPort for structured server event logging.
        clock: Optional ClockPort for response timestamps.
    """
    server = HealthServer(
        host=host,
        port=port,
        control_plane=HealthServerControlPlaneDeps(
            health_monitor=health_monitor,
            quarantine_service=quarantine_service,
            checkpoint_port=checkpoint_port,
            run_manifest_port=run_manifest_port,
            run_ledger_port=run_ledger_port,
            workflow_manifest_port=workflow_manifest_port,
        ),
        prometheus_base_url=prometheus_base_url,
        logger=logger,
    )
    server.set_clock(clock)
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()


__all__ = [
    "HealthResponse",
    "HealthServer",
    "run_health_server",
]
