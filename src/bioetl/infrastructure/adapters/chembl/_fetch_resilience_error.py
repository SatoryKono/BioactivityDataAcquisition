"""Error wrapping helper for ChEMBL fetch resilience."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn, Protocol

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort
    from bioetl.domain.types import HealthStatus
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class ChemblErrorHost(Protocol):
    """Host contract needed to wrap fetch errors."""

    provider_name: str
    _http_client: UnifiedHTTPClient
    _error_handler: ErrorHandlerPort

    def _get_health_status(self) -> HealthStatus: ...


def handle_fetch_error(
    host: ChemblErrorHost,
    error: Exception,
    context: str,
) -> NoReturn:
    """Handle errors with unified classification."""
    failure_count = host._http_client.circuit_breaker.get_failure_count()
    health_status = host._get_health_status()
    error_context = {
        "circuit_breaker_state": host._http_client.circuit_breaker.get_state().value,
        "circuit_breaker_failures": failure_count,
        "health_status": health_status.value,
    }
    wrapped = host._error_handler.handle_error(
        error=error,
        provider=host.provider_name,
        operation=context,
        context=error_context,
    )
    raise wrapped from error
