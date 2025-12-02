# HTTP Infrastructure

В этом разделе описаны компоненты, обеспечивающие надежность HTTP-взаимодействия.

## Rate Limiter
`TokenBucketRateLimiter` реализует алгоритм Token Bucket для ограничения количества запросов в единицу времени (QPS).

### Параметры
- `rate`: Количество токенов, добавляемых в секунду.
- `capacity`: Максимальный размер ведра (burst).

```python
limiter = TokenBucketRateLimiter(rate=10, capacity=20)
limiter.acquire()  # Блокирует, если токенов нет
```

## Retry Policy
`ExponentialBackoffRetry` реализует стратегию повторных попыток с экспоненциальной задержкой и Jitter'ом (случайным отклонением), чтобы избежать проблемы "thundering herd".

### Логика
Задержка рассчитывается как: `base_delay * (backoff_factor ** attempt) + jitter`.

## Circuit Breaker
Защищает систему от каскадных сбоев. Если количество ошибок превышает порог, "цепь размыкается" и запросы не отправляются в течение `recovery_timeout`.

## Cache
- **MemoryCache**: Быстрый кэш в памяти (LRU).
- **FileCache**: Персистентный кэш на диске. Используется для `SourceClientABC` для ускорения повторных запусков и отладки.

