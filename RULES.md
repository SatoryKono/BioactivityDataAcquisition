# BioETL: Project Rules
*Version: 2.0 (Enhanced), 2025-05-20*

## 1. Architecture & Layers
**Philosophy**: "Pragmatic Engineering". Избегаем Over-engineering, архитектура должна ускорять time-to-market.
**Pattern**: Layered Architecture with Dependency Inversion (Ports & Adapters).

### 1.1. Layers & Contracts
- **Infrastructure (Adapters)**: Реализация взаимодействия с внешним миром (HTTP, DB, FS).
- **Application (Pipelines)**: Оркестрация потоков данных. Определяет *когда* и *в каком порядке* вызываются порты.
- **Domain (Pure Logic)**: Чистые функции и контракты (Protocols). Никакого I/O.

**Явные Контракты (Ports)**:
Интерфейсы определяются в `domain/ports.py` через `typing.Protocol`:
```python
class DataSourcePort(Protocol):
    def fetch(self, query: Query) -> Iterator[RawRecord]: ...
    def health_check(self) -> bool: ...

class TransformPort(Protocol):
    def apply(self, df: pd.DataFrame) -> pd.DataFrame: ...
```

## 2. Data Flow & Medallion Strategy
Пайплайны реализуются как **DAGs** (Directed Acyclic Graphs).

### 2.1. Medallion Architecture
| Level | Format | Validation | Retention | Idempotency |
|-------|--------|------------|-----------|-------------|
| **Bronze** (Raw) | JSON/CSV (Blob) | Min/None | 90 days + Archive | Append-only + `ingestion_ts`. Дубликаты допустимы. |
| **Silver** (Norm) | Parquet/Table | Soft (Schema Drift aware) | Permanent | Upsert по `(provider, entity_id, version)`. Хранить `updated_at`. |
| **Gold** (Curated) | Parquet/Table | Strict (`strict=True`) | Permanent | Версионированные снапшоты (SCD Type 2) или partition by date. |

### 2.2. Schema Drift Policy
- **Bronze**: Принимает любые поля (schemaless). Цель — сохранить сырой ответ.
- **Silver**: Падает только на отсутствии *критичных* ключей (ID). Новые/неизвестные поля логируются, но не блокируют пайплайн.

## 3. Error Handling & Observability

### 3.1. Error Classification
Вместо тотального "Fail Fast" используем дифференцированный подход:

| Тип Ошибки | Поведение | Пример |
|------------|-----------|--------|
| **Critical** | Fail Pipeline | Auth failure, Schema mismatch в Gold, DB down. |
| **Recoverable** | Retry N раз (Backoff) | 429 Rate Limit, 502/504 Timeout, Network glitch. |
| **Data Quality** | Log + Skip Record | Невалидный SMILES, missing optional field. Не роняет батч. |

### 3.2. Observability
- **Логи**: Структурированный JSON (JSON Logs). Обязательные поля: `ts`, `level`, `trace_id`, `pipeline`, `stage`, `record_count`, `error_type`.
- **Метрики**: Prometheus-style endpoint (`/metrics`). Ключевые метрики: `pipeline_duration_seconds`, `records_processed_total`, `errors_total` (by type).
- **Alerting**: Trigger alert if error rate > 5% over 15 min window.

## 4. Code Standards & Testing

### 4.1. Stack & Decision Matrix
| Задача | Инструмент | Альтернатива | Критерий выбора |
|--------|------------|--------------|-----------------|
| **Оркестрация** | **Prefect** | Dagster, Runner | Prefect для >10 DAGs и сложной логики ретраев. |
| **Валидация** | **Pandera** | Great Expectations | Pandera нативна для DataFrames, легче в CI. |
| **HTTP Client** | **httpx** | requests | `async` поддержка из коробки для high-throughput. |
| **Linter** | **Ruff** | Flake8/Black | Скорость и "все-в-одном". |

### 4.2. Testing Policy
- **Unit**: Domain logic only. In-memory fakes. No mocks of external libs.
- **Integration**:
    - **VCR.py**: Запись ответов API в кассеты (`tests/fixtures/vcr/`).
    - **Policy**: Обновлять кассеты при смене версии API.
- **Contract Tests**: Ежемесячный запуск против *реальных* API (Live) в отдельном CI workflow для детекции поломок контракта.

## 5. Operations (Rate Limits & Secrets)

### 5.1. Rate Limiting
Каждый адаптер обязан реализовать `TokenBucket` или аналог, уважающий лимиты провайдера.
Конфигурация в `configs/providers/{provider}.yaml`:
```yaml
rate_limit:
  requests_per_second: 5
  burst: 10
  retry_after_429: true
  backoff_factor: 1.5
```
**Backpressure**: Если внутренняя очередь заполнена >80%, адаптер должен замедлить чтение (throttle upstream).

### 5.2. Secrets Management
- **Source**: Environment Variables (`os.environ`).
- **Format**: `BIOETL_{PROVIDER}_{KEY}` (e.g., `BIOETL_PUBCHEM_API_KEY`).
- **Forbidden**: Hardcoded secrets, `.env` файлы в git. Использовать AWS Secrets Manager / Vault для инъекции в Env.

## 6. Documentation (Automation First)

- **Map & Schemas**: Генерируются скриптами в CI:
    - Схемы: `pydantic-to-json-schema` -> `docs/schemas/`.
    - ER: `eralchemy2` из моделей.
    - API Reference: `mkdocs` + `mkdocstrings`.
- **Naming**:
    - Code: `src/bioetl/infrastructure/adapters/{provider}/`
    - Docs: `docs/providers/{provider}/{entity}.md`

## 7. Change Management
- **Breaking Changes**: Изменение Gold-схем, смена мажорной версии API провайдера. Требует миграции и ADR.
- **Non-Breaking**: Добавление полей в Bronze/Silver.

---
## Приложение А: Источники и Библиотеки

**Структура папок:** `src/bioetl/infrastructure/adapters/{provider}/`

| Источник | Библиотека | Комментарий |
|----------|------------|-------------|
| **ChEMBL** | `chembl_webresource_client` | Официальный клиент. |
| **PubChem** | `pubchempy` | Стандарт де-факто. |
| **UniProt** | `unipressed` | Эффективный клиент. |
| **Guide to Pharm**| `pyGtoP` | *Deprecated*: писать свой адаптер на `httpx` если сломан. |
| **OpenAlex** | `pyalex` | Typed wrapper. |
| **Crossref** | `habanero` | Better maintained than `crossrefapi`. |
| **Semantic** | `semanticscholar` | Official lib. |
| **PubMed** | `biopython` | Low-level. Consider `metapub` for search. |
