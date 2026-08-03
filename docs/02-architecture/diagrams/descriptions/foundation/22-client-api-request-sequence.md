______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: HTTP Client API Request Sequence

- Исходная диаграмма: `foundation/22-client-api-request-sequence.mmd`

## Описание

Диаграмма теперь отражает реальный retry flow `UnifiedHTTPClient`, а не старый путь через `PipelineExecutor`. Входной вызов идёт от `ProviderAdapter` в `UnifiedHTTPClient.get()/post()`, дальше внутри `HTTPClientRetryMixin` запускаются request span, rate limiter, circuit breaker, `httpx.AsyncClient.request(...)`, retry/backoff логика и финальная observability-сводка. Отдельно отмечен путь `get_once()`, который использует те же limiter/breaker seams, но без retry loop.

Этот срез нужен как компактная модель resilience-поведения адаптеров: где именно применяется `TokenBucketRateLimiter`, как `CircuitBreakerGuard` оборачивает вызов, какие ответы считаются retryable и в какой момент формируется `RetryExhaustedError`. Ключевые участники: `ProviderAdapter`, `UnifiedHTTPClient`, `TokenBucketRateLimiter`, `CircuitBreakerGuard`, `httpx.AsyncClient`, `External Provider API`, `Tracing + Metrics`.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-03-24`
