# UnifiedHTTPClient Reference

**Module:** `bioetl.infrastructure.adapters.http.client`
**Version:** 5.14.0
**Last updated:** 2026-02-10

---

## Overview

`UnifiedHTTPClient` provides a standardized HTTP client for all data source adapters. It encapsulates:
- **Rate limiting** (provider-specific)
- **Circuit breaker** (cascading failure prevention)
- **Retry logic** (exponential backoff)
- **Observability** (metrics, tracing, logging)

All API adapters **MUST** use `UnifiedHTTPClient` instead of direct `httpx` calls.

**Related ADR:** [ADR-032: Unified HTTP Client Pattern](../../../02-architecture/decisions/ADR-032-unified-http-client.md)

---

## Architecture

```mermaid
flowchart TB
    subgraph UnifiedHTTPClient
        RateLimiter[RateLimiterPort]
        CircuitBreaker[CircuitBreakerPort]
        RetryConfig[RetryConfig]
    end

    subgraph Observability
        Tracing[TracingPort]
        Metrics[MetricsPort]
        Logger[LoggerPort]
    end

    subgraph HTTPX
        AsyncClient[httpx.AsyncClient]
    end

    UnifiedHTTPClient --> Observability
    UnifiedHTTPClient --> HTTPX

    Adapter[ChEMBLAdapter] -->|uses| UnifiedHTTPClient
```

### Design Principles

1. **Composition over Inheritance:** Ports injected, not inherited
2. **SRP Compliance:** Each concern (rate limit, circuit breaker, retry) is a separate component
3. **Observability Built-in:** Tracing and metrics integrated via ports
4. **Async-first:** Uses `httpx.AsyncClient` for async HTTP

---

## Basic Usage

### Simple GET Request

```python
from bioetl.infrastructure.adapters.http import UnifiedHTTPClient
from bioetl.domain.models.retry_config import RetryConfig

# Create client
client = UnifiedHTTPClient(
    base_url="https://www.ebi.ac.uk/chembl/api/data",
    rate_limiter=rate_limiter,
    circuit_breaker=circuit_breaker,
    retry_config=RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=60.0,
    ),
    logger=logger,
    metrics=metrics,
    tracing=tracing,
)

# Make request
response = await client.get("/activity", params={"limit": 100})
data = response.json()
```

### POST Request

```python
response = await client.post(
    "/search",
    json={"query": "aspirin"},
    headers={"Content-Type": "application/json"},
)
```

---

## Rate Limiting

### Provider-Specific Limits

Each provider has different rate limit policies:

| Provider | Limit | Implementation |
|----------|-------|----------------|
| **ChEMBL** | None | `NoOpRateLimiter` |
| **PubChem** | 5 req/sec | `TokenBucketLimiter(rate=5.0)` |
| **UniProt** | 100 req/sec | `TokenBucketLimiter(rate=100.0)` |
| **PubMed** | 3 req/sec (no key) | `TokenBucketLimiter(rate=3.0)` |
| **CrossRef** | Polite pool (50 req/sec) | `TokenBucketLimiter(rate=50.0)` |
| **OpenAlex** | ~10 req/sec | `TokenBucketLimiter(rate=10.0)` |
| **Semantic Scholar** | 100 req/5min | `SlidingWindowLimiter(100, window=300)` |

### Token Bucket Example

```python
from bioetl.infrastructure.adapters.rate_limiting import TokenBucketLimiter

# PubChem: 5 requests per second
rate_limiter = TokenBucketLimiter(
    rate=5.0,  # tokens per second
    burst=10,  # max burst size
    logger=logger,
    metrics=metrics,
)

client = UnifiedHTTPClient(
    base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
    rate_limiter=rate_limiter,
    # ... other config
)

# Requests are automatically throttled
for cid in compound_ids:
    response = await client.get(f"/compound/cid/{cid}/JSON")
    # Rate limiter ensures ≤ 5 req/sec
```

### Sliding Window Example

```python
from bioetl.infrastructure.adapters.rate_limiting import SlidingWindowLimiter

# Semantic Scholar: 100 requests per 5 minutes
rate_limiter = SlidingWindowLimiter(
    max_requests=100,
    window_seconds=300,  # 5 minutes
    logger=logger,
    metrics=metrics,
)

client = UnifiedHTTPClient(
    base_url="https://api.semanticscholar.org/graph/v1",
    rate_limiter=rate_limiter,
    # ... other config
)
```

### Rate Limit Headers

The client automatically respects standard rate limit headers:

```python
# X-RateLimit-Remaining: 950
# X-RateLimit-Reset: 1640000000
# Retry-After: 60

# Client will automatically:
# 1. Parse headers from response
# 2. Adjust internal rate limiter state
# 3. Wait until reset time if limit exceeded
```

---

## Circuit Breaker

**Purpose:** Prevent cascading failures when external API is unhealthy.

### Configuration

```python
from bioetl.infrastructure.adapters.circuit_breaker import SimpleCircuitBreaker

circuit_breaker = SimpleCircuitBreaker(
    failure_threshold=5,      # Open after 5 consecutive failures
    success_threshold=2,      # Close after 2 consecutive successes in half-open
    timeout_seconds=60,       # Try again after 60 seconds
    logger=logger,
    metrics=metrics,
)

client = UnifiedHTTPClient(
    base_url="https://api.example.com",
    circuit_breaker=circuit_breaker,
    # ... other config
)
```

### States

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: 5 failures
    Open --> HalfOpen: 60s timeout
    HalfOpen --> Closed: 2 successes
    HalfOpen --> Open: 1 failure
    Closed --> Closed: success
```

| State | Behavior |
|-------|----------|
| **Closed** | Normal operation, all requests pass through |
| **Open** | Circuit breaker tripped, all requests fail fast |
| **Half-Open** | Testing if service recovered, limited requests allowed |

### Exception Types

```python
from bioetl.domain.exceptions import CircuitBreakerOpenError

try:
    response = await client.get("/endpoint")
except CircuitBreakerOpenError:
    # Circuit breaker is open, service is unhealthy
    logger.error("API circuit breaker tripped, skipping request")
    # Fail gracefully or use fallback
```

---

## Retry Logic

### Exponential Backoff

```python
from bioetl.domain.models.retry_config import RetryConfig

retry_config = RetryConfig(
    max_attempts=5,       # Maximum 5 attempts total
    base_delay=1.0,       # Start with 1 second delay
    max_delay=60.0,       # Cap delay at 60 seconds
    backoff_factor=2.0,   # Double delay each retry
)

client = UnifiedHTTPClient(
    base_url="https://api.example.com",
    retry_config=retry_config,
    # ... other config
)

# Retry delays: 1s, 2s, 4s, 8s, 16s
# Total max delay: ~31 seconds
```

### Retry Strategy

**Retryable errors:**
- HTTP 429 (Rate Limit)
- HTTP 500, 502, 503, 504 (Server errors)
- Network errors (`httpx.NetworkError`)
- Timeout errors (`httpx.TimeoutException`)

**Non-retryable errors:**
- HTTP 400, 401, 403, 404 (Client errors)
- HTTP 422 (Unprocessable Entity)
- JSON decode errors

```python
try:
    response = await client.get("/endpoint")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        # Non-retryable, entity not found
        logger.warning(f"Entity not found: {e.request.url}")
    elif e.response.status_code >= 500:
        # Retryable, already attempted with exponential backoff
        logger.error("API server error after retries", exc_info=e)
```

---

## Observability Integration

### Metrics

The client automatically emits metrics:

```python
# Counter: HTTP requests by method and status
http_requests_total{method="GET", status="200", provider="chembl"}

# Histogram: Request duration
http_request_duration_seconds{method="GET", provider="chembl"}

# Counter: Rate limiter wait events
rate_limiter_wait_total{provider="pubchem"}

# Counter: Circuit breaker state changes
circuit_breaker_state_change_total{provider="uniprot", state="open"}
```

### Tracing

```python
from bioetl.infrastructure.observability import OpenTelemetryTracer

# With distributed tracing enabled
tracing = OpenTelemetryTracer()

client = UnifiedHTTPClient(
    base_url="https://api.example.com",
    tracing=tracing,
    # ... other config
)

# Each HTTP request creates a span
with tracing.start_span("fetch_compounds") as span:
    span.set_attribute("provider", "pubchem")
    response = await client.get("/compound/cid/2244/JSON")
    span.set_attribute("http.status_code", response.status_code)
```

**Note:** For Local-Only deployment, use `NoOpTracing` (default, ADR-022).

### Logging

All HTTP operations are logged with structured context:

```json
{
  "event": "http_request",
  "method": "GET",
  "url": "https://www.ebi.ac.uk/chembl/api/data/activity?limit=100",
  "status_code": 200,
  "duration_ms": 523.45,
  "provider": "chembl",
  "run_id": "run-20260210-143022-abc123"
}
```

---

## Error Handling

### Exception Hierarchy

```
HTTPError
├── CircuitBreakerOpenError (domain)
├── RateLimitExceededError (domain)
├── httpx.HTTPStatusError
│   ├── 4xx ClientError
│   └── 5xx ServerError
├── httpx.NetworkError
└── httpx.TimeoutException
```

### Recommended Pattern

```python
from bioetl.domain.exceptions import (
    CircuitBreakerOpenError,
    RateLimitExceededError,
)
import httpx

async def fetch_with_error_handling(client: UnifiedHTTPClient, url: str):
    try:
        response = await client.get(url)
        return response.json()

    except CircuitBreakerOpenError:
        # Service is unhealthy, fail fast
        logger.error("Circuit breaker open, service unavailable")
        raise

    except RateLimitExceededError as e:
        # Rate limit exceeded despite throttling
        wait_seconds = e.retry_after or 60
        logger.warning(f"Rate limit exceeded, retry after {wait_seconds}s")
        await asyncio.sleep(wait_seconds)
        return await fetch_with_error_handling(client, url)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.info(f"Entity not found: {url}")
            return None
        elif e.response.status_code >= 500:
            logger.error(f"Server error: {e.response.status_code}")
            raise

    except httpx.NetworkError as e:
        logger.error(f"Network error: {e}")
        raise

    except httpx.TimeoutException:
        logger.error(f"Request timeout: {url}")
        raise
```

---

## Testing

### Unit Tests with Mocking

```python
import pytest
import httpx
import respx

@respx.mock
async def test_unified_http_client_retry():
    """Test retry logic with mocked responses."""
    # First two attempts fail, third succeeds
    route = respx.get("https://api.example.com/data")
    route.mock(side_effect=[
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(200, json={"result": "success"}),
    ])

    client = UnifiedHTTPClient(
        base_url="https://api.example.com",
        retry_config=RetryConfig(max_attempts=3),
        rate_limiter=NoOpRateLimiter(),
        circuit_breaker=NoOpCircuitBreaker(),
        logger=logger,
        metrics=NoOpMetrics(),
        tracing=NoOpTracing(),
    )

    response = await client.get("/data")
    assert response.status_code == 200
    assert route.call_count == 3
```

### Integration Tests with VCR

```python
import pytest
import vcr

@pytest.mark.vcr(cassette_library_dir="tests/fixtures/vcr/chembl")
async def test_chembl_activity_fetch_real():
    """Test with recorded HTTP interactions."""
    client = UnifiedHTTPClient(
        base_url="https://www.ebi.ac.uk/chembl/api/data",
        # ... config
    )

    response = await client.get("/activity", params={"limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
```

---

## Configuration via YAML

Source configs support HTTP client settings:

```yaml
# configs/sources/pubchem.yaml
name: pubchem
version: "1.0"
http_config:
  timeout_sec: 30.0
  max_retries: 3
  retry_base_delay: 1.0
  retry_max_delay: 60.0
  rate_limit:
    type: token_bucket
    rate: 5.0  # 5 requests per second
    burst: 10
  circuit_breaker:
    failure_threshold: 5
    success_threshold: 2
    timeout_seconds: 60
```

**Note:** See [ADR-032 Configuration](../../../02-architecture/decisions/ADR-032-unified-http-client.md#configuration) for full schema.

---

## Migration from Direct httpx

**Before (legacy):**
```python
import httpx

async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

**After (unified):**
```python
from bioetl.infrastructure.adapters.http import UnifiedHTTPClient

class MyAdapter:
    def __init__(self, http_client: UnifiedHTTPClient):
        self._http = http_client

    async def fetch_data(self):
        response = await self._http.get("/data")
        return response.json()
```

**Benefits:**
- ✅ Automatic rate limiting
- ✅ Circuit breaker protection
- ✅ Standardized retry logic
- ✅ Built-in observability
- ✅ Testability with NoOp implementations

---

## See Also

- [ADR-032: Unified HTTP Client Pattern](../../../02-architecture/decisions/ADR-032-unified-http-client.md)
- [ADR-007: Circuit Breaker Implementation](../../../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md)
- [Common Adapter Utilities](adapters-common.md)
- [Infrastructure Layer Overview](../infrastructure.md)
