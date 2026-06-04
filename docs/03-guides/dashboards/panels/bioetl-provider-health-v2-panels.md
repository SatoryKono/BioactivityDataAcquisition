# BioETL Provider Health v2 - Panels Documentation

**Dashboard File:** `grafana/dashboards/bioetl-provider-health-v2.json`

## Обзор

Dashboard мониторит здоровье и доступность внешних провайдеров данных (ChEMBL, PubMed, UniProt и т.д.).

## Ключевые панели

### 1. Provider Availability
- **Тип:** Stat
- **Назначение:** Доступность провайдеров
- **Источники данных:** `bioetl_provider_up`
- **Фильтры:** `provider`
- **Пороги:** Green (up), Red (down)

### 2. Request Success Rate
- **Тип:** Graph
- **Назначение:** Процент успешных запросов
- **Источники данных:** `bioetl_provider_request_success_rate`
- **Фильтры:** `provider`, `endpoint`

### 3. Request Latency
- **Тип:** Graph
- **Назначение:** Задержка запросов
- **Источники данных:** `bioetl_provider_request_duration_seconds`
- **Фильтры:** `provider`, `endpoint`
- **Описание:** p50, p95, p99 latency

### 4. Rate Limiting
- **Тип:** Stat
- **Назначение:** Статус rate limiting
- **Источники данных:** `bioetl_provider_rate_limited_total`
- **Фильтры:** `provider`

### 5. Retry Attempts
- **Тип:** Graph
- **Назначение:** Количество retry попыток
- **Источники данных:** `bioetl_provider_retry_attempts_total`
- **Фильтры:** `provider`, `retry_reason`

## Переменные Dashboard

- `provider` - Выбор провайдера (chembl, pubmed, uniprot, crossref, openalex, semantic_scholar, pubchem)
- `endpoint` - Конечная точка API

## Примечания

- Dashboard использует circuit breaker метрики
- Отражает состояние адаптеров в infrastructure layer