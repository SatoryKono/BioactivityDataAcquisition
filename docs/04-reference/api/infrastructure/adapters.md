# Infrastructure Adapters

Implementations of domain ports for external systems.

## HTTP Adapters

### UnifiedHTTPClient

Unified HTTP client with rate limiting, circuit breaker, and observability.

::: bioetl.infrastructure.adapters.http.client.UnifiedHTTPClient
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - get
            - post
            - health_check
            - aclose

### TokenBucket

Token bucket rate limiter implementation.

::: bioetl.infrastructure.adapters.http.rate_limiter.TokenBucket
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - acquire
            - try_acquire
            - available_tokens

### CircuitBreaker

Circuit breaker pattern implementation.

::: bioetl.infrastructure.adapters.http.circuit_breaker.CircuitBreaker
    options:
        show_root_heading: true
        show_source: false
        members:
            - __init__
            - call
            - state

### PaginatedFetcherMixin

Mixin for handling paginated API responses.

::: bioetl.infrastructure.adapters.http.pagination.PaginatedFetcherMixin
    options:
        show_root_heading: true
        show_source: false
        members:
            - fetch_all_pages

## Storage Adapters

### DeltaWriter

Storage adapter for Delta Lake (Silver/Gold layers).

::: bioetl.infrastructure.storage.delta_writer.DeltaWriter
    options:
        show_root_heading: true
        show_source: false
        members:
            - write_silver
            - write_gold
            - read_table
            - table_exists

### BronzeWriter

Storage adapter for local filesystem (Bronze layer).

::: bioetl.infrastructure.storage.bronze_writer.BronzeWriter
    options:
        show_root_heading: true
        show_source: false
        members:
            - write_bronze
            - list_files

## Lock Adapters

### MemoryLockAdapter

In-memory lock implementation (Local-Only).

::: bioetl.infrastructure.adapters.lock.memory_lock.MemoryLockAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - acquire
            - release
            - heartbeat

## Checkpoint Adapters

### LocalCheckpointAdapter

Local filesystem checkpoint implementation.

::: bioetl.infrastructure.adapters.checkpoint.local_checkpoint.LocalCheckpointAdapter
    options:
        show_root_heading: true
        show_source: false
        members:
            - save
            - load
            - delete

## Observability Adapters

### StructLogAdapter

Structured logging adapter.

::: bioetl.infrastructure.adapters.observability.structlog_adapter.StructLogAdapter
    options:
        show_root_heading: true
        show_source: false

### PrometheusMetricsAdapter

Prometheus metrics adapter.

::: bioetl.infrastructure.adapters.observability.prometheus_adapter.PrometheusMetricsAdapter
    options:
        show_root_heading: true
        show_source: false

### OpenTelemetryTracingAdapter

OpenTelemetry tracing adapter.

::: bioetl.infrastructure.adapters.observability.opentelemetry_adapter.OpenTelemetryTracingAdapter
    options:
        show_root_heading: true
        show_source: false

## Usage Example

```python
from bioetl.infrastructure.adapters.http.client.UnifiedHTTPClient import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter.TokenBucket import TokenBucket

# Create rate limiter
limiter = TokenBucket(rate=5.0, capacity=10)

# Create client
client = UnifiedHTTPClient(
    rate_limiter=limiter,
    provider="chembl",
)

# Make request
response = await client.get("https://www.ebi.ac.uk/chembl/api/data/activity")
```

## See Also

- [Domain Ports](../domain/ports.md) - Interfaces implemented by adapters
- [Configuration](../domain/config.md) - Adapter configuration
