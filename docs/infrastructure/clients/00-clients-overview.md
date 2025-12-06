# 00 Clients Overview

## Архитектурный паттерн
Текущие клиенты строятся по схеме ABC → Default Factory → Impl и используют `UnifiedAPIClient` как транспорт с middleware (retry/backoff, rate limit, circuit breaker). Регистры ABC находятся в `src/bioetl/infrastructure/clients/base/abc_registry.yaml` и `abc_impls.yaml`, сами контракты клиентов — в `src/bioetl/domain/clients/...`.

## ChEMBL стек (актуальный)
- **ChemblDataClientABC** — контракт (`src/bioetl/domain/clients/chembl/contracts.py`).
- **ChemblDataClientHTTPImpl** — реализация на HTTP (`impl/http_client.py`), использует `UnifiedAPIClient` + `RateLimiterABC`.
- **ChemblRequestBuilderImpl** — сборка URL/фильтров (`request_builder.py`).
- **ChemblResponseParserImpl** — нормализация ответа (`response_parser.py`).
- **ChemblPaginatorImpl** — извлечение маркеров пагинации (`paginator.py`).
- **ChemblClientFactory** — создание клиента (`factories.py`) с привязкой middleware и лимитов.

## Политики
- Таймауты/ретраи/лимиты настраиваются через `UnifiedAPIClient` middleware; все обращения проходят через rate limiter.
- JSON парсится с валидацией; ошибки оборачиваются в `ClientResponseError`.
- Пагинация реализована через `ChemblPaginatorImpl` (next marker) с заготовкой под расширение.

## Использование в пайплайнах
- Пайплайны `ChemblEntityPipeline` получают `ExtractionServiceABC`, который внутри использует ChEMBL-клиент и нормализацию.
- Источник данных выбирается конфигом (`input_mode=api|csv|id_only`), при API-запросах применяется клиентский стек выше.
