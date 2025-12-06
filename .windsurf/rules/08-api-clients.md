> Scope:
> - USE WHEN accessing external HTTP APIs; require UnifiedAPIClient, retry/backoff, rate limit, circuit breaker, timeouts
> - Use when editing files matching: `src/**/*client*.py`, `src/**/api_*.py`, `src/**/api*.py`
# CONTRACT
- All HTTP calls via `UnifiedAPIClient`.
- Retries: exponential backoff with jitter; give up on non-retryable 4xx.
- Throttling: token bucket with jitter; respect Retry-After.
- Circuit breaker to prevent cascades.
- TTL cache for expensive reads.
- Strict timeouts; include proper User-Agent and required headers.
- Handle pagination consistently.

# ERROR HANDLING
- Log status_code, retry_after, url; re-raise as domain errors where appropriate.

# REFERENCE
See [docs/styleguide/07-api-clients.md](../../docs/styleguide/07-api-clients.md) for detailed documentation.
