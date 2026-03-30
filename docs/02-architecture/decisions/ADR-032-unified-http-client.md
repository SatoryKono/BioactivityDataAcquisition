---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ADR-032: Unified HTTP Client Pattern

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
| Metrics | http-request-duration-seconds, http-request-errors-total |
| Correlation | X-Correlation-ID header from run-id |

## Justification

### 1. Single Point of Configuration

```python
# Before: Each adapter configured independently
class ChEMBLAdapter:
    def __init__(self):
        self.-rate-limit = 10  # Hardcoded
        self.-timeout = 30     # Duplicated

class PubChemAdapter:
    def __init__(self):
        self.-rate-limit = 5   # Different value
        self.-timeout = 30     # Duplicated
```

```python
# After: Factory creates configured client
client = HttpClientFactory.create-for-provider("chembl", settings)
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
mock-client = Mock(spec=UnifiedHTTPClient)
mock-client.get.return-value = {"data": [...]}
adapter = ChEMBLAdapter(http-client=mock-client)
```

## Implementation

### Client Configuration

```python
@dataclass
class UnifiedHTTPClient:
    rate-limiter: RateLimiterPort
    circuit-breaker: CircuitBreakerPort
    retry-config: RetryConfig = field(default-factory=RetryConfig)
    timeout: float = 30.0
    run-id: RunID | None = None
    user-agent: str = "BioETL/5.0.0"
    contact-email: str | None = None
    provider: str = "unknown"
    tracer: TracingPort | None = None
    metrics: MetricsPort | None = None
    logger: LoggerPort | None = None
```

### Factory Pattern

```python
class HttpClientFactory:
    @classmethod
    def create-for-provider(
        cls, provider: str, settings: Settings
    ) -> UnifiedHTTPClient:
        config = load-source-config(provider)
        return UnifiedHTTPClient(
            rate-limiter=TokenBucket(
                rate=config.rate-limit.rate,
                capacity=config.rate-limit.capacity,
            ),
            circuit-breaker=CircuitBreaker(provider=provider),
            timeout=config.timeout,
            contact-email=settings.default-email,
        )
```

### Usage in Adapters

```python
class ChemblAdapter(BaseHttpAdapter):
    async def fetch(self, entity_type: str, limit: int | None = None):
        async with self.-http-client:
            response = await self.-http-client.get(
                f"{self.base-url}/{entity_type}",
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
