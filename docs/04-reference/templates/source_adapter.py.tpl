"""
Template for a new Source Adapter.
Location: src/bioetl/infrastructure/adapters/<provider>/client.py
"""
from typing import Any, AsyncGenerator

from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

class {{ProviderName}}Adapter:
    """Adapter for {{ProviderName}} API."""

    def __init__(self, http_client: UnifiedHTTPClient, api_key: str | None = None):
        self.http_client = http_client
        self.base_url = "{{BaseUrl}}"
        self.api_key = api_key

    async def fetch_data(self, params: dict[str, Any]) -> AsyncGenerator[dict, None]:
        """
        Fetch data from the source.
        Implement pagination and error handling here if not handled by UnifiedHTTPClient.
        """
        # Example implementation
        endpoint = f"{self.base_url}/endpoint"
        response = await self.http_client.get(endpoint, params=params)

        # Yield records
        for item in response.get("results", []):
            yield item
