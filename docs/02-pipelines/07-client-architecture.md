# 07 Client Architecture

Архитектура клиентского слоя BioETL для внешних API (актуально: ChEMBL).

## Стек и структура
```
src/bioetl/infrastructure/clients/
├── base/               # ABC/Default/Impl для транспорта и лимитеров
│   ├── contracts.py    # RateLimiterABC, RetryPolicyABC, CircuitBreakerABC
│   ├── factories.py    # default_* фабрики + registry hookup
│   ├── impl/           # unified_client, retry_policy, rate_limiter, cache
│   ├── abc_registry.yaml
│   └── abc_impls.yaml
├── chembl/             # Поставщик ChEMBL
│   ├── contracts.py    # ChemblDataClientABC
│   ├── factories.py    # ChemblClientFactory (создаёт HTTP Impl)
│   ├── impl/http_client.py
│   ├── request_builder.py
│   ├── response_parser.py
│   └── paginator.py
└── middleware.py       # HttpClientMiddleware (timeout/retry/log)
```

## Паттерн
- **ABC** описывает контракт (например, `ChemblDataClientABC`).
- **Default factory** регистрируется в `abc_impls.yaml` и создаёт Impl с дефолтными middleware.
- **Impl** использует `UnifiedAPIClient` + `RateLimiterABC` + `RetryPolicyABC`.

## Политики и ограничения
- Все HTTP-запросы идут через `UnifiedAPIClient` с таймаутами, ретраями с backoff и rate limiting.
- Пагинация — `ChemblPaginatorImpl`; поддержка next-marker заложена, переходы расширяются по мере необходимости.
- Ошибки ответа оборачиваются в `ClientResponseError`; JSON валидируется.

## Связь с пайплайнами
- `ChemblExtractorImpl` в пайплайнах получает `ExtractionServiceABC`, который использует ChEMBL-клиент для API-режима (`input_mode=api`).
- Для `csv`/`id_only` режимов пайплайн переключается на `CsvRecordSourceImpl`/`IdListRecordSourceImpl` без сетевых вызовов.

## Минимальный пример создания клиента
```python
from bioetl.infrastructure.clients.chembl.factories import ChemblClientFactory
from bioetl.infrastructure.clients.base.factories import (
    default_rate_limiter,
    default_retry_policy,
)

factory = ChemblClientFactory(
    rate_limiter=default_rate_limiter(),
    retry_policy=default_retry_policy(),
)
client = factory.create_default()
status = client.metadata()
client.close()
```
