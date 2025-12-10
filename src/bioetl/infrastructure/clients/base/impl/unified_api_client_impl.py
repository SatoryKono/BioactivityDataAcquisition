"""
Unified API client implementation that conforms to ApiClientABC.
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.clients.base.contracts import ApiClientABC
from bioetl.domain.configs import ClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.base.impl._http_transport import _HttpTransport


class UnifiedAPIClientImpl(ApiClientABC):
    """
    Unified implementation of the API client interface.

    Delegates actual HTTP handling to the internal transport layer while
    providing a consistent interface for the application layer.
    """

    def __init__(
        self,
        *,
        provider: str,
        config: ClientConfig,
        base_client: Any | None = None,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
    ) -> None:
        self._transport = _HttpTransport(
            provider=provider,
            config=config,
            base_client=base_client,
            logger=logger,
            metrics=metrics,
        )

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            **kwargs: Additional request arguments (params, json, etc.)

        Returns:
            The raw response object or data depending on configuration.
        """
        return self._transport.request(method, url, **kwargs)

    def close(self) -> None:
        """Close the underlying client session and release resources."""
        self._transport.close()
