import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.exceptions import RetryExhaustedError

@pytest.mark.asyncio
async def test_unified_client_retries_on_protocol_error():
    # Setup
    rate_limiter = AsyncMock()
    circuit_breaker = AsyncMock()
    # Mock circuit breaker to just call the function
    circuit_breaker.call.side_effect = lambda f, *args, **kwargs: f(*args, **kwargs)
    
    retry_config = RetryConfig(max_attempts=3, base_delay=0.01)
    
    client = UnifiedHTTPClient(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        retry_config=retry_config,
        provider="test"
    )
    
    # Mock httpx AsyncClient
    mock_httpx = AsyncMock()
    # Simulate RemoteProtocolError on first two attempts, success on third
    mock_httpx.request.side_effect = [
        httpx.RemoteProtocolError("Server disconnected"),
        httpx.RemoteProtocolError("Server disconnected"),
        httpx.Response(200, content=b'{"status": "ok"}')
    ]
    
    client._client = mock_httpx
    
    # Execute
    response = await client.get("https://api.test.com")
    
    # Verify
    assert response.status_code == 200
    assert mock_httpx.request.call_count == 3
    assert circuit_breaker.call.call_count == 3

@pytest.mark.asyncio
async def test_unified_client_exhausts_retries_on_protocol_error():
    # Setup
    rate_limiter = AsyncMock()
    circuit_breaker = AsyncMock()
    circuit_breaker.call.side_effect = lambda f, *args, **kwargs: f(*args, **kwargs)
    
    retry_config = RetryConfig(max_attempts=2, base_delay=0.01)
    
    client = UnifiedHTTPClient(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        retry_config=retry_config,
        provider="test"
    )
    
    mock_httpx = AsyncMock()
    mock_httpx.request.side_effect = httpx.RemoteProtocolError("Server disconnected")
    
    client._client = mock_httpx
    
    # Execute & Verify
    with pytest.raises(RetryExhaustedError):
        await client.get("https://api.test.com")
    
    assert mock_httpx.request.call_count == 2
