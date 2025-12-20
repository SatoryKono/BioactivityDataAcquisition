"""ChEMBL adapter factory for composition layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker


def create_chembl_adapter(
    circuit_breaker: CircuitBreaker,
    run_id: Any = None,
) -> tuple[ChemblAdapter, UnifiedHTTPClient]:
    """Factory function to create ChemblAdapter with dependencies.

    This function resides in the composition layer as it wires up
    concrete infrastructure components.
    """
    rate_limiter = TokenBucket(rate=10.0, capacity=20)
    http_client = UnifiedHTTPClient(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        run_id=run_id,
    )
    adapter = ChemblAdapter(http_client=http_client)
    return adapter, http_client
