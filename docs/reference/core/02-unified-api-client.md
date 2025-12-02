# UnifiedAPIClient

**Модуль:** `src/bioetl/clients/base/unified_client.py` (концептуально)

`UnifiedAPIClient` представляет собой фасад и набор политик для надежного взаимодействия с внешними REST API.

## Принципы работы

Все запросы к внешним API должны проходить через этот слой, чтобы гарантировать:
1. Соблюдение Rate Limits.
2. Обработку временных сбоев (Retries).
3. Защиту от перегрузки (Circuit Breaker).
4. Кэширование.

## Компоненты

### 1. Rate Limiter
Использует алгоритм **Token Bucket**.
- `tokens_per_second`: Лимит запросов в секунду.
- `burst`: Размер "всплеска".

### 2. Retry Policy
Использует **Exponential Backoff** с Jitter.
- `max_retries`: Максимальное число попыток.
- `backoff_factor`: Множитель задержки.
- `status_forcelist`: Коды ошибок, требующие повтора (429, 500, 502, 503, 504).

### 3. Circuit Breaker
Предотвращает каскадные сбои, временно блокируя запросы к упавшему сервису.
- `failure_threshold`: Количество ошибок для размыкания цепи.
- `recovery_timeout`: Время ожидания перед проверкой (half-open).

## Конфигурация (YAML)

```yaml
client:
  timeout: 30.0
  max_retries: 3
  rate_limit: 10
  backoff_factor: 2.0
  circuit_breaker_threshold: 5
```

## Использование

```python
class MyClient(BaseClient):
    def fetch_data(self, id: str) -> dict:
        # Автоматически применяются retry, rate limit и circuit breaker
        return self.http.get(f"/resource/{id}")
```

