# ADR-032: Unified HTTP Client Pattern

**Status:** Accepted
**Date:** 2026-01-28
**Decision makers:** @BioETL-Team

## Context

All data source adapters require HTTP communication with external APIs (ChEMBL, PubChem, UniProt, CrossRef, OpenAlex, PubMed, Semantic Scholar). Each API has different requirements for:
- Rate limiting (1-100 requests/second depending on provider)
- Authentication (API keys, email headers)
- Retry strategies (different transient error patterns)
- Circuit breaking (different failure thresholds)

Without unification, each adapter would implement its own HTTP handling, leading to:
- Duplicated rate limiting and retry logic
- Inconsistent error handling
- Difficulty in applying cross-cutting concerns (tracing, metrics)
- Testing complexity

## The Decision

We have implemented **`UnifiedHTTPClient`** in `infrastructure/adapters/http/client.py` as the single HTTP abstraction for all adapters.

### Design Principles

1. **Composition over Inheritance**: Client accepts injected ports (RateLimiterPort, CircuitBreakerPort)
2. **SRP Compliance**: Each concern handled by dedicated component
3. **Observability Built-in**: Tracing and metrics integrated via ports
4. **Async-first**: Uses httpx for async HTTP

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedHTTPClient                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ RateLimiter │  │CircuitBreaker│  │  RetryConfig    │    │
│  │   Port      │  │    Port      │  │ (value object)  │    │
│  └─────────────┘  └──────────────┘  └─────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ TracingPort │  │ MetricsPort  │  │   LoggerPort    │    │
│  └─────────────┘  └──────────────┘  └─────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                     httpx.AsyncClient                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Implementation |
|---------|----------------|
| Rate Limiting | TokenBucket algorithm via RateLimiterPort |
| Circuit Breaker | 5 consecutive errors → Open 5 min (ADR-007) |
| Retry | Exponential backoff with jitter (RetryConfig) |
| Tracing | OpenTelemetry spans per request |
| Metrics | http_request_duration_seconds, http_request_errors_total |
| Correlation | X-Correlation-ID header from run_id |

## Justification

### 1. Single Point of Configuration

```python
# Before: Each adapter configured independently
class ChEMBLAdapter:
    def __init__(self):
        self._rate_limit = 10  # Hardcoded
        self._timeout = 30     # Duplicated

class PubChemAdapter:
    def __init__(self):
        self._rate_limit = 5   # Different value
        self._timeout = 30     # Duplicated
```

```python
# After: Factory creates configured client
client = HttpClientFactory.create_for_provider("chembl", settings)
# Rate limit, timeout, retry config from YAML
```

### 2. Consistent Observability

All HTTP requests automatically get:
- Tracing spans with provider/method/status attributes
- Latency histogram for SLA monitoring
- Error counters for alerting
- Correlation IDs for distributed tracing

### 3. Testability

```python
# Easy to mock for testing
mock_client = Mock(spec=UnifiedHTTPClient)
mock_client.get.return_value = {"data": [...]}
adapter = ChEMBLAdapter(http_client=mock_client)
```

## Implementation

### Client Configuration

```python
@dataclass
class UnifiedHTTPClient:
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    timeout: float = 30.0
    run_id: RunID | None = None
    user_agent: str = "BioETL/5.0.0"
    contact_email: str | None = None
    provider: str = "unknown"
    tracer: TracingPort | None = None
    metrics: MetricsPort | None = None
    logger: LoggerPort | None = None
```

### Factory Pattern

```python
class HttpClientFactory:
    @classmethod
    def create_for_provider(
        cls, provider: str, settings: Settings
    ) -> UnifiedHTTPClient:
        config = load_source_config(provider)
        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(
                rate=config.rate_limit.rate,
                capacity=config.rate_limit.capacity,
            ),
            circuit_breaker=CircuitBreaker(provider=provider),
            timeout=config.timeout,
            contact_email=settings.default_email,
        )
```

### Usage in Adapters

```python
class ChEMBLAdapter(BaseHttpAdapter):
    async def fetch(self, entity_type: str, limit: int | None = None):
        async with self._http_client:
            response = await self._http_client.get(
                f"{self.base_url}/{entity_type}",
                params={"limit": limit},
            )
            yield from response.json()["data"]
```

## Consequences

### Positive

1. **Consistency**: All adapters use same HTTP patterns
2. **Observability**: Unified metrics and tracing
3. **Maintainability**: Single place to update HTTP behavior
4. **Testability**: Easy to mock and test
5. **Configuration**: Provider settings in YAML, not code

### Negative

1. **Indirection**: Additional layer between adapter and HTTP
2. **Learning curve**: Developers must understand client API

### Mitigation

- Clear documentation and examples
- Factory hides complexity from adapter authors
- Sensible defaults reduce configuration burden

## Related ADRs

- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker Implementation
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown Strategy (client cleanup)
- [ADR-009](ADR-009-paginated-fetcher-mixin.md): Paginated Fetcher (uses HTTP client)
- [ADR-016](ADR-016-error-handling-strategy.md): Error Handling Strategy (retry classification)
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement (TracingPort, MetricsPort)
- [ADR-022](ADR-022-tracing-noop.md): NoOp Tracing for Local-Only
