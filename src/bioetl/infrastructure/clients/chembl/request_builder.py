from typing import Any, Optional
from bioetl.infrastructure.clients.base.contracts import RequestBuilderABC


class ChemblRequestBuilder(RequestBuilderABC):
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
    
    def for_endpoint(self, endpoint: str) -> "ChemblRequestBuilder":
        self._endpoint = endpoint.strip("/")
        return self

    def build(self, params: dict[str, Any]) -> str:
        """
        Строит URL с параметрами.
        Возвращает полный URL (как строку для простоты, в реальности может быть Request object).
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
             raise ValueError(f"URL length {len(url)} exceeds max_url_length {self.max_url_length}")

        return url

    def with_pagination(self, offset: int, limit: int) -> "ChemblRequestBuilder":
        self._params["offset"] = offset
        self._params["limit"] = limit
        return self
