"""Request builder for constructing ChEMBL API URLs."""

from typing import Any, Optional

from bioetl.domain.clients.base.contracts import RequestBuilderABC


class ChemblRequestBuilderImpl(RequestBuilderABC):
    """
    Builder для запросов к ChEMBL API.
    """

    def __init__(self, base_url: str, max_url_length: Optional[int] = None) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.max_url_length = max_url_length
        self._endpoint: str = ""
        self._params: dict[str, Any] = {}

    def for_endpoint(self, endpoint: str) -> "ChemblRequestBuilderImpl":
        """Fluent alias for build_for_endpoint used in tests."""

        return self.build_for_endpoint(endpoint)

    def build_for_endpoint(self, endpoint: str) -> "ChemblRequestBuilderImpl":
        """Select API endpoint (e.g., activity, assay, target)."""
        self._endpoint = endpoint.strip("/")
        return self

    def build(
        self, endpoint_or_params: Optional[dict[str, Any] | str] = None, **params_kwargs: Any
    ) -> str:
        """Build request URL from endpoint name or params."""
        merged_params: dict[str, Any] = {}
        if isinstance(endpoint_or_params, str):
            self.build_for_endpoint(endpoint_or_params)
            params_value = params_kwargs.pop("params", None)
            if params_value:
                if not isinstance(params_value, dict):
                    raise TypeError("params must be a dict when provided")
                merged_params.update(params_value)
            merged_params.update(params_kwargs)
            return self.build_request(merged_params)
        params = endpoint_or_params if endpoint_or_params is not None else {}
        if params:
            if not isinstance(params, dict):
                raise TypeError("params must be a dict when provided")
            merged_params.update(params)
        merged_params.update(params_kwargs)
        return self.build_request(merged_params)

    def build_request(self, params: dict[str, Any]) -> str:
        """
        Строит URL с параметрами.
        Возвращает полный URL (строка; в реальности может быть Request object).
        """
        # Merge base params with call-specific params (without mutating state)
        current_params = self._params.copy()
        current_params.update(params)

        # Construct query string
        query_parts = []
        for k, v in current_params.items():
            if v is not None:
                query_parts.append(f"{k}={v}")

        query_string = "&".join(query_parts)
        url = f"{self.base_url}/{self._endpoint}.json"
        if query_string:
            url += f"?{query_string}"

        if self.max_url_length and len(url) > self.max_url_length:
            raise ValueError(
                f"URL length {len(url)} exceeds max_url_length {self.max_url_length}"
            )

        return url

    def build_with_pagination(
        self, offset: int, limit: int
    ) -> "ChemblRequestBuilderImpl":
        """Attach pagination parameters for subsequent requests."""
        self._params["offset"] = offset
        self._params["limit"] = limit
        return self

    def with_pagination(self, offset: int, limit: int) -> "ChemblRequestBuilderImpl":
        """Alias for build_with_pagination."""
        return self.build_with_pagination(offset, limit)
