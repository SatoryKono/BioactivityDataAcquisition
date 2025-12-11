"""Ports for building API requests.

This module defines abstract contracts for constructing API requests
following hexagonal architecture principles. Infrastructure adapters
implement these ports to build provider-specific requests.

The RequestBuilderPortABC provides a fluent interface for constructing
URLs or request objects with pagination support.

Example::

    class ChemblRequestBuilder(RequestBuilderPortABC):
        def build_for_endpoint(self, endpoint: str) -> Self:
            self._endpoint = endpoint
            return self

        def build_request(self, params: dict[str, Any]) -> str:
            return f"{self.base_url}/{self._endpoint}?{urlencode(params)}"

        def build_with_pagination(self, offset: int, limit: int) -> Self:
            self._params.update(offset=offset, limit=limit)
            return self
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self


class RequestBuilderPortABC(ABC):
    """Port for building API requests with fluent interface.

    This abstract base class defines the contract for building API requests
    without infrastructure-specific details. Implementations provide
    provider-specific URL construction and pagination.

    The builder uses a fluent interface pattern where methods return self
    to allow chaining.

    Example:
        >>> builder = ChemblRequestBuilder(base_url="https://api.example.com")
        >>> url = builder.build_for_endpoint("activity").build_request({"limit": 100})
    """

    @abstractmethod
    def build_for_endpoint(self, endpoint: str) -> Self:
        """Configure builder for a specific API endpoint.

        Args:
            endpoint: The API endpoint name (e.g., 'activity', 'assay').

        Returns:
            Self for method chaining.
        """

    @abstractmethod
    def build_request(self, params: dict[str, Any]) -> Any:
        """Build the final request from parameters.

        Args:
            params: Query parameters for the request.

        Returns:
            Request object (URL string, Request instance, etc.).
        """

    @abstractmethod
    def build_with_pagination(self, offset: int, limit: int) -> Self:
        """Configure pagination parameters.

        Args:
            offset: Starting position in result set.
            limit: Maximum number of results per page.

        Returns:
            Self for method chaining.
        """

    def build(
        self, endpoint_or_params: dict[str, Any] | str | None = None, **kwargs: Any
    ) -> Any:
        """Build request - convenience method.

        Can be called either with:
        - A dict of params (uses current endpoint)
        - An endpoint string followed by params via kwargs
        - No arguments (uses current state)

        Args:
            endpoint_or_params: Either endpoint name or params dict.
            **kwargs: Additional params or 'params' dict.

        Returns:
            Built request object.
        """
        if isinstance(endpoint_or_params, str):
            self.build_for_endpoint(endpoint_or_params)
            params = kwargs.pop("params", {})
            params.update(kwargs)
            return self.build_request(params)
        params = endpoint_or_params or {}
        params.update(kwargs)
        return self.build_request(params)


__all__ = ["RequestBuilderPortABC"]
