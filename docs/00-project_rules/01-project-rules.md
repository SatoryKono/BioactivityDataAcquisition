# Project Rules
*Синхронизировано с RULES.md v5.0 (2025-12-15)*

## Уровни Требований (Governance)
Документ использует ключевые слова согласно RFC 2119:
- **MUST** (Обязательно): Абсолютное требование. Нарушение = дефект или блокер релиза.
- **SHOULD** (Рекомендуется): Сильная рекомендация. Отклонение требует явного обоснования (комментарий в PR).
- **MAY** (Опционально): На усмотрение разработчика.

## 1. Общие принципы

1.1. Архитектура проекта **MUST** соответствовать паттерну Ports & Adapters (Hexagonal) + DDD.

1.2. Весь новый код **MUST** вписываться в существующие слои: `domain`, `application`, `infrastructure`, `interfaces`.

1.3. Любой новый функционал **MUST** сопровождаться обновлённой документацией и тестами.

1.4. Все изменения, ломающие контракты (схемы, API, конфиги), **MUST** быть задокументированы в `CHANGELOG.md` / ADR.

### 1.5. Обеспечение Контрактов (Enforcement)
Интерфейсы определяются в `domain/ports.py` через `typing.Protocol`:
- **Design-time**: `mypy --strict` проверяет соответствие типов. Основной механизм контроля.
- **Runtime Boundary**: `@runtime_checkable` **MAY** использоваться только для критичных адаптеров.

```python
class DataSourcePort(Protocol):
    def fetch(self, query: Query) -> Iterator[RawRecord]: ...
    def health_check(self) -> bool: ...
```

## 2. Соглашения об именовании

### 2.1. Базовые правила

2.1.1. Модули и переменные: `snake_case`.

2.1.2. Классы: `PascalCase`.

2.1.3. Константы: `UPPER_SNAKE_CASE`.

2.1.4. Приватные атрибуты/функции: префикс `_`.

2.1.5. camelCase, дефисы и пробелы в идентификаторах **MUST NOT** использоваться.

### 2.2. Суффиксы для классов

| Роль класса | Обязательный суффикс | Пример |
|---|---|---|
| Фабрика | `*Factory` | `ChemblClientFactory` |
| Клиент данных/API | `*Client` | `ChemblDataClient` |
| Фасад | `*Facade` | `PipelineRunnerFacade` |
| Реестр | `*Registry` | `SchemaRegistry` |
| Адаптер/транспорт | `*Adapter` / `*Transport` | `HTTPTransportAdapter` |
| Интерфейс/ABC | `*Protocol` / `*ABC` | `DataClientProtocol` |
| Конфиг/модель | `*Config` / `*Model` / `*Params` | `PipelineConfig` |
| Исключение | `*Error` | `SchemaValidationError` |
| Конкретная реализация | `*Impl` | `ChemblDataClientHTTPImpl` |

Нарушение суффиксов **MUST NOT** допускаться.

### 2.3. Префиксы для функций

| Тип функции | Префикс | Пример |
|---|---|---|
| Чтение локальных данных | `get_` | `get_local_config()` |
| Сетевые запросы / I/O | `fetch_` | `fetch_chembl_page()` |
| Генераторы | `iter_` | `iter_batches()` |
| Создание объектов | `create_` / `build_` / `make_` / `default_` | `build_pipeline()` |
| Регистрация | `register_` | `register_schema()` |
| Валидация | `validate_` | `validate_dataframe()` |
| Парсинг / сериализация | `parse_` / `serialize_` | `parse_response()` |
| Обработчики событий | `on_` | `on_pipeline_error()` |
| Булевы проверки | `is_` / `has_` / `can_` | `is_valid()`, `has_nulls()` |

Функции **SHOULD** использовать соответствующие префиксы по смыслу.

### 2.4. Пайплайны и сущности

2.4.1. Идентификатор пайплайна: `<entity>_<source>` в нижнем регистре, например: `activity_chembl`.

2.4.2. Папки пайплайнов: `src/bioetl/application/pipelines/<provider>/<entity>/`.

2.4.3. Файлы этапов **MUST** иметь названия по стадиям: `extract.py`, `transform.py`, `validate.py`, `export.py`.

2.4.4. Добавление или изменение пайплайнов **MUST** проходить ревью с использованием чек-листа `docs/templates/pipeline-review-checklist.md`.

### 2.5. Тесты

2.5.1. Файлы тестов **MUST** называться `test_*.py`.

2.5.2. Структура в `tests/` **MUST** зеркально повторять `src/`.

2.5.3. Golden-тесты **SHOULD** именоваться с суффиксом `_golden.py`.

### 2.6. Документация

2.6.1. Файлы документации: kebab-case (`01-pipelines-overview.md`).

2.6.2. Топовые файлы разделов: `README.md`, индекс в папке: `INDEX.md`.

2.6.3. ADR: `docs/architecture/decisions/NNNN-title-in-kebab-case.md`.

2.6.4. Названия файлов документации **MUST** быть на английском.

2.6.5. Первый заголовок H1 **SHOULD** соответствовать названию файла по смыслу.

## 3. Поток Данных и Medallion Architecture

### 3.1. Уровни данных

| Уровень | Формат | Валидация | Хранение (Retention) | Идемпотентность |
|---------|--------|-----------|----------------------|-----------------|
| **Bronze** (Сырые) | **JSONL + zstd** | Мин./Нет | 90 дней hot → Archive (S3 Lifecycle) | Path: `bronze/{format_version}/{provider}/{entity}/{date}/`. Append-only. |
| **Silver** (Норм.) | **Delta Lake** | Мягкая (дрейф схемы) | Постоянно | **Merge/Upsert**. Raw Parquet **MUST NOT**. |
| **Gold** (Витрины) | Delta/Parquet | Строгая (`strict=True`) | Постоянно | SCD Type 2 или партиции по дате. |

**Bronze Lifecycle**:
- Формат файлов (JSONL) зафиксирован в версии пути (`/v1/`).
- Изменение формата требует новой ветки (`/v2/`). Миграция "in-place" **MUST NOT**.

### 3.2. Инфраструктура Delta Lake

- **Engine**: `delta-rs` (Rust core) для Python-воркеров.
- **Protocol**: Writer Version 2, Reader Version 1.
- **VACUUM MUST** запускаться еженедельно с `retention_period=7 days`.
- **Forensic Retention**: По умолчанию 7 дней. Для Critical tables **MAY** увеличиваться до 30 дней через `forensic_retention: true`.

### 3.3. Политика Дрейфа Схемы (Schema Drift)

| Уровень | Условие | Действие |
|---------|---------|----------|
| **Info** | Появление новых опциональных полей | Логируется |
| **Warn** | Появление >3 новых полей | Требует ревью. **SLA: 48 часов.** |
| **Critical** | Исчезновение обязательного поля (ID) | Блокирует пайплайн |

Нерешенный дрейф (Warn) блокирует следующий релиз.

### 3.4. Data Lineage (Происхождение Данных)

- **Silver Record**: Содержит `_source_batch_id` (FK).
- **Lineage Log**: Таблица `sys.lineage_log` хранит маппинг:
  - `_source_batch_id` → список файлов Bronze (S3 paths)
  - Версия трансформации
  - Параметры запуска

Полные пути к файлам в каждой строке данных хранить **MUST NOT** (избыточность).

### 3.5. Политика Backfill / Replay

| Поле | Описание |
|------|----------|
| `_run_id` | UUID запуска (обязательно) |
| `_run_type` | `incremental` \| `backfill` \| `rebuild` |

**Merge Priority**: `rebuild` > `backfill` > `incremental`.

**Concurrency Constraint**: В один момент времени для одной сущности допустим только один процесс `rebuild` или `backfill`.

#### 3.5.1. Backfill Lock Enforcement

Lock key включает тип запуска:
- `incremental`: `lock:{provider}_{entity}`
- `backfill`/`rebuild`: `lock:{provider}_{entity}:exclusive`

При наличии активного `incremental` lock попытка взять `:exclusive`:
- **Default**: Fail immediately.
- **Wait mode**: `--wait-for-lock TIMEOUT_SEC` (default: 300 сек).

### 3.6. Стратегия Партиционирования

| Уровень | Стратегия | Пример |
|---------|-----------|--------|
| **Bronze** | По `ingestion_date` | `bronze/v1/chembl/activity/2025-05-20/` |
| **Silver** | По `source_date` или `entity_type` | `silver/chembl/activity/year=2025/month=05/` |
| **Gold** | По use-case | `gold/activity_by_target/target_id=CHEMBL123/` |

**Limits**:
- **Soft**: Warning при >10,000 партиций или >100 файлов в партиции.
- **Hard**: 50,000 партиций → Pipeline Fail.
- UUID, Hash, Free-text как ключи партиционирования **MUST NOT**.

### 3.7. Политика NULL и Пропущенных Значений

| Состояние | Действие | Куда попадает |
|-----------|----------|---------------|
| Отсутствует в источнике | Замена на NULL | Silver |
| Некритичная DQ ошибка | Замена на NULL | Silver (`_dq_warn=true`) |
| Критичная DQ ошибка | Исключение | **Quarantine** |

**Sentinel values (-1, "N/A", 9999) MUST NOT использоваться.**

#### 3.7.1. Unified Quarantine (`common.quarantine`)

| Поле | Тип | Описание |
|------|-----|----------|
| `ingestion_ts` | Timestamp | Время инцидента |
| `pipeline` | String | `chembl_activity` |
| `error_code` | String | `SCHEMA_VIOLATION` |
| `payload` | JSON | **Truncated to 64KB** |
| `payload_hash` | String | Дедупликация |
| `bronze_batch_id` | UUID | FK на Bronze |
| `dq_status` | Enum | `NEW` \| `IGNORED` \| `REPROCESSED` |

**Lifecycle**:
- Retention: 30 дней (S3 Lifecycle).
- Triage: еженедельно.
- Карантин ≠ источник истины. Данные считаются "отсутствующими" в аналитике.

**Операции**:
- `make quarantine-inspect PIPELINE=...`
- `make quarantine-replay PIPELINE=...`
- `make quarantine-purge PIPELINE=...`

### 3.8. Генерация Entity ID (Content Hash)

| Сценарий | Стратегия |
|----------|-----------|
| Источник даёт стабильный ID | Использовать как есть (`chembl_id`, `pubchem_cid`) |
| ID отсутствует | `sha256(provider + canonical_json_dumps(record))` |

**Canonical JSON**: `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`.

**Robust Content Hash** (нормализация перед хэшированием):
- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → `YYYY-MM-DD`
- Strings → `strip()`

**Исключения из хэша**: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`.

**Детекция коллизий**: При upsert проверять `_source_record_id`; если отличается — конфликт, логировать обе записи.

## 4. Обработка Ошибок и Наблюдаемость

### 4.1. Классификация Ошибок

| Тип | Поведение | Пример |
|-----|-----------|--------|
| **Critical** | Падение пайплайна | Auth failure, Gold schema mismatch, БД недоступна |
| **Recoverable** | Retry N раз (Backoff) | 429, 502/504, сетевой сбой |
| **Data Quality** | Лог + Пропуск записи | Невалидный SMILES, отсутствует опциональное поле |

### 4.2. Пороги Ошибок (Thresholds)

- **Soft**: >5% DQ ошибок → Warning.
- **Hard**: >20% → Fail Batch.
- **Scope**: `record_error_rate` + `entity_error_rate`.

### 4.3. Параметры Retry (Backoff)

| Параметр | Значение |
|----------|----------|
| Max Attempts | 3 |
| Multiplier | 2.0 (1s, 2s, 4s...) |
| Jitter | Random(0.1s, 0.5s) — **SHOULD** применяться |

### 4.4. Circuit Breaker

| Параметр | Значение |
|----------|----------|
| Trigger | 5 consecutive errors (connection/timeout) |
| Open Duration | 5 минут (`circuit_breaker.recovery_timeout`) |
| Recovery | Half-Open → 1 пробный запрос. Success → Closed, Failure → Open +5 мин |
| Metrics | `circuit_breaker_state` (0=Closed, 1=Half-Open, 2=Open), `trips_total` |
| Alert | При зависании в Open >10 мин |

### 4.5. Наблюдаемость (Observability)

- **Correlation ID**: `run_id` **MUST** быть во всех логах, метриках, блокировках.
- **Retention**: Логи — 30 дней, метрики — 90 дней.
- **Логи**: Структурированный JSON.

#### 4.5.1. Log Schema

| Поле | Обязательность | Пример |
|------|----------------|--------|
| `ts` | MUST | `2025-12-15T10:00:00Z` |
| `level` | MUST | `INFO`, `ERROR` |
| `run_id` | MUST | UUID |
| `pipeline` | MUST | `chembl_activity` |
| `stage` | MUST | `extract`, `transform`, `load` |
| `dataset` | SHOULD | `chembl.activity` |
| `record_count` | SHOULD | 1000 |
| `error_type` | При ошибках | `SCHEMA_VIOLATION` |

### 4.6. Конкурентность и Блокировки

| Параметр | Значение |
|----------|----------|
| Механизм | Redis `SETNX` + `EXPIRE` |
| TTL | 60 секунд |
| Heartbeat | Каждые 20 секунд |
| Fencing Token | `owner_id` (run_id воркера) |
| Max Duration | 4 часа |
| Lock Key | `lock:{provider}_{entity}` |

**Invariant**:
- Потеря блокировки = Потеря права на запись.
- Heartbeat не прошёл → воркер **MUST** аварийно завершиться до коммита.
- **Safety Guard**: Адаптер **MUST** валидировать `owner_id` перед записью в S3/Delta Lake.

Смешивание бэкендов (Redis + DB) **MUST NOT**.

### 4.7. Метрики Качества Данных (DQ Metrics)

Prometheus формат с лейблами (`pipeline`, `entity`, `column`, `check`):
- `dq_validation_score{check="null_rate", column="..."}`: % NULL.
- `dq_validation_score{check="unique_count", column="..."}`: кардинальность.
- `dq_validation_score{check="schema_violations"}`: невалидные записи.
- `data_freshness_seconds`: `now() - max(updated_at)`.

#### 4.7.1. Детекция Аномалий

**Baseline**: MA(30 дней).

| Метрика | Warning | Critical |
|---------|---------|----------|
| Рост `null_rate` | >2x baseline | >5x baseline |
| Падение `record_count` | <70% baseline | <50% baseline |
| `freshness_lag_hours` | >24h | >72h |

**Cold Start**:
- Days 1-7: Silence (обучение).
- Days 8-30: Warning only.
- Days 30+: Full Alerting.

### 4.8. Provider Health Monitoring

| Status | Условие | Действие |
|--------|---------|----------|
| Healthy | 0 errors за 5 мин | Normal operation |
| Degraded | 1-2 consecutive errors | Timeout ×2, batch_size ÷2 |
| Unhealthy | ≥3 errors или health_check fail | Pause pipeline, Alert P2 |

**Recovery**: Unhealthy → Degraded после 1 успешного health_check.

**Metric**: `provider_health_status{provider}` (0=Unhealthy, 1=Degraded, 2=Healthy).

## 5. Операции

### 5.1. Rate Limiting

Каждый адаптер **MUST** реализовать `TokenBucket` или аналог.

**Backpressure**: Очередь >80% → дросселировать источник.

### 5.2. Управление Секретами

- Источник: `os.environ`.
- Формат: `BIOETL_{PROVIDER}_{KEY}` (например, `BIOETL_PUBCHEM_API_KEY`).
- Хардкод секретов **MUST NOT**.
- Файлы `.env` в git **MUST NOT**.

### 5.3. Graceful Shutdown (SIGTERM/SIGINT)

1. Прекратить fetch новых записей.
2. Дождаться завершения текущего батча.
3. Сохранить чекпоинт в S3 (If-Match/ETag для атомарности).
4. Выйти с кодом 0.

**Guarantees**: At-Least-Once + Дедупликация в Silver (через Content Hash).

#### 5.3.1. Checkpoint Recovery

При запуске:
1. Проверить чекпоинт в S3.
2. С `--resume`: начать с `last_processed_id + 1`.
3. Без флага при наличии чекпоинта: Warning "Use --resume or --ignore-checkpoint."
4. После успешного завершения: удалить файл чекпоинта.

### 5.4. Политика Чувствительных Данных

| Классификация | Описание |
|---------------|----------|
| Public | Открытые данные |
| Internal | Внутреннее использование |
| Restricted | PII, требуют хэширования |

**IAM**: Least Privilege. Разделение ролей `writer` (пайплайн) и `reader` (аналитик).

| Уровень | Действие |
|---------|----------|
| Bronze | Хранить как есть (Internal) |
| Silver | Хэшировать PII: `sha256(lowercase(value) + SALT)` — **PII fields MUST be salted** |
| Gold | PII исключается или агрегируется |

#### 5.4.1. Salt Rotation (Dual-Salt Period)

1. **New Salt Generation**: `SALT_NEXT` в Secrets Manager.
2. **Transition (7 дней)**: Писать с `SALT_NEXT`, читать оба.
3. **Finalization**: `SALT_CURRENT = SALT_NEXT`, удаление старой.
4. **Resalting**: Lazy Migration с backoff. Alert если >1% не мигрировано после 14 дней.

**Threat Model Scope**:
- В фокусе: Утечка PII через логи, SQL-инъекции, несанкционированный доступ к S3.
- Out of Scope: Физический доступ, компрометация AWS Root.

### 5.5. Disaster Recovery (DR)

| Параметр | Значение |
|----------|----------|
| RPO | 24 часа |
| RTO | 4 часа |
| Game Days | **SHOULD** ежегодно |

#### 5.5.1. DR Procedures (Runbook)

| Сценарий | Действие |
|----------|----------|
| Повреждение Bronze/Silver | Stop → S3 Point-in-Time Restore → `--full-rebuild` |
| Потеря чекпоинта | `--ignore-checkpoint` (дедупликация в Silver исправит) |
| Отказ региона AWS | DNS Failover → Terraform в резервном регионе |

### 5.6. Среды (Environments)

| Среда | Данные | Доступ к Prod-секретам |
|-------|--------|------------------------|
| Dev | Фикстуры, сэмпл Bronze | Нет |
| Staging | Prod-like (обфусцированные) | Нет |
| Prod | Боевая | Только CI/CD |

#### 5.6.1. Environment Isolation

| Ресурс | Dev | Staging | Prod |
|--------|-----|---------|------|
| S3 | `bioetl-dev` | `bioetl-staging` | `bioetl-prod` |
| Redis | db0 | db1 | db2 |

Доступ к Prod-секретам только у CI Runner.

## 6. Управление Изменениями

### 6.1. Контракты Данных (Data Contracts)

- **Реестр**: Gold-схемы в `docs/contracts/gold/{entity}.json` (JSON Schema).
- **Версионирование**: `{entity}_v{major}.{minor}`.
  - Minor: добавление nullable полей.
  - Major: удаление/переименование, изменение типов.

**Breaking Change Workflow**:
1. PR **MUST** иметь лейбл `breaking-change`.
2. CI генерирует diff и постит в Slack `#bioetl-contracts`.
3. Период депрекации: 14 дней до удаления поля.

### 6.2. Field Deprecation Workflow

| День | Действие |
|------|----------|
| 0 | Пометить `deprecated: true`, указать `replacement` |
| 1-14 | Dual-write: писать оба поля (`old_field` и `new_field`) |
| 15 | Удаление `old_field`, bump major version, ADR |

```yaml
fields:
  old_field:
    deprecated: true
    replacement: new_field
```

### 6.3. Rollback Strategy

| Scope | Действие |
|-------|----------|
| Infrastructure/Code | Auto Rollback при Error Rate >10% |
| Data DQ | Ручной анализ и replay. Не триггерит автооткат |

Manual: `make rollback VERSION=...`

## 7. Структура проекта / слоёв

7.1. Код **MUST** находиться в `src/bioetl/`.

7.2. Слои:
- `domain/` — модели, схемы, абстрактные интерфейсы (Protocols).
- `application/` — пайплайны, use-case логика.
- `infrastructure/` — адаптеры API, логирование, техсервисы.
- `interfaces/` — CLI и прочие интерфейсы.

7.3. Документация в `docs/` **MUST** отражать структуру `src/`.

7.4. Новый модуль **MUST** быть размещён в соответствующем слое.

## 8. Работа с объектами и данными

### 8.1. Модели и схемы

8.1.1. Для каждой выходной таблицы **MUST** существовать Pandera-схема.

8.1.2. Схема **MUST** задавать: набор колонок, типы, порядок, nullability.

8.1.3. Перед записью **MUST** валидация через Pandera.

8.1.4. Изменение схемы **MUST** рассматриваться как потенциально ломающая смена версии.

### 8.2. Pydantic-модели

8.2.1. JSON-ответы API **SHOULD** описываться через Pydantic-модели.

8.2.2. Вложенные структуры **SHOULD** приводиться к плоскому виду для таблиц.

### 8.3. ABC / протоколы

8.3.1. Общие контракты **MUST** быть оформлены как ABC/Protocol в domain.

8.3.2. Реализации (`*Impl`) **MUST** жить в infrastructure.

8.3.3. Предпочтительная схема: ABC → Default/Facade → Impl.

8.3.4. Новый класс при дублировании **MUST** сопровождаться удалением старого (zero-sum class count).

## 9. Использование библиотек

| Задача | Инструмент | Альтернатива | Критерий |
|--------|------------|--------------|----------|
| Оркестрация | Prefect | Simple Runner | <5 DAG-ов — свой Runner |
| Валидация | Pandera | Great Expectations | Pandera нативна для DataFrames |
| HTTP | httpx | requests | Поддержка async |
| Линтер | Ruff | Flake8/Black | Скорость |

9.1. Работа с табличными данными: `pandas`.

9.2. Валидация: `pandera`.

9.3. Конфигурации: `Pydantic`.

9.4. Сетевые запросы: `UnifiedAPIClient`. Прямой `requests` **MUST NOT**.

9.5. CLI: `Typer`.

9.6. Логи: `Rich` / `UnifiedLogger`.

9.7. YAML: `PyYAML`.

**Legacy Wrappers**: Для библиотек без async (pubchempy, biopython) **MUST** использовать `loop.run_in_executor(thread_pool, fetch_func)`.

## 10. Стиль кода и качество

### 10.1. Стиль

10.1.1. PEP8.

10.1.2. Black / Ruff, max line length ~100.

10.1.3. Импорты: isort-подобный порядок. `from x import *` **MUST NOT**.

### 10.2. Типизация

10.2.1. Все публичные функции **MUST** иметь аннотации типов.

10.2.2. `mypy --strict`. `Any` только с явным обоснованием.

### 10.3. Докстринги

10.3.1. Публичные классы/функции **MUST** иметь docstring.

10.3.2. Язык — преимущественно английский.

### 10.4. Логирование

10.4.1. `print()` для логов **MUST NOT**.

10.4.2. Использовать `UnifiedLogger` (структурный JSON).

10.4.3. Секреты в логах **MUST NOT**.

### 10.5. Детерминизм

10.5.1. При одинаковых входах результаты **MUST** быть байт-в-байт идентичны.

10.5.2. Порядок строк/колонок **MUST** быть фиксирован.

10.5.3. Запись файлов: tmp + rename (атомарная).

10.5.4. Контрольные суммы **SHOULD** вычисляться для артефактов.

### 10.6. Архитектурный стиль

10.6.1. Композиция над наследованием.

10.6.2. Глобальное изменяемое состояние **MUST NOT**.

10.6.3. Константы **MUST** быть вынесены (no magic strings).

## 11. Работа с API и внешними источниками

### 11.1. HTTP / API

11.1.1. Сетевой доступ **MUST** через `UnifiedAPIClient`.

11.1.2. Клиент **MUST** поддерживать: retry с backoff, timeouts, rate limiting, circuit breaker.

11.1.3. Сетевой код в domain **MUST NOT**.

### 11.2. Тестирование сети

11.2.1. Unit-тесты **MUST NOT** ходить в сеть.

11.2.2. VCR.py для интеграционных тестов. Санитизация секретов в `before_record`.

11.2.3. CI: `pytest --vcr-record=none`.

11.2.4. Contract Tests: ежемесячно против реальных API.

### 11.3. Health Check Endpoints

| Провайдер | Endpoint |
|-----------|----------|
| ChEMBL | `GET /chembl/api/data/status.json` |
| PubChem | `GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON` |
| UniProt | `GET /rest/beta/health` |
| Others | Generic Probe (lightweight GET, timeout 5s) |

### 11.4. Секреты

11.4.1. API-ключи в коде/репозитории **MUST NOT**.

11.4.2. Источник: переменные окружения / секрет-хранилища.

11.4.3. При отсутствии секрета **MUST** fail-fast.

## 12. Конфигурация и запуск

### 12.1. Конфигурации

12.1.1. Все настройки в YAML под `configs/`.

12.1.2. YAML **MUST** мапиться на Pydantic и валидироваться.

12.1.3. Секреты в открытом виде **MUST NOT**. Только ссылки `${VAR_NAME}`.

12.1.4. Каноническая модель провайдера: `BaseProviderConfig` в `bioetl.domain.configs.pipeline`.

12.1.5. Каноническая модель нормализации: `NormalizationConfig` в `bioetl.domain.configs.normalization`.

12.1.6. Дублирующие DTO с пересекающимися полями **MUST NOT**.

### 12.2. Приоритеты конфигурации

1. Аргументы CLI.
2. Переменные окружения.
3. YAML пайплайна.
4. Профиль по умолчанию.

### 12.3. CLI

12.3.1. CLI на Typer.

12.3.2. Команды явные: `run <pipeline_id>`, `--config`, `--output`.

12.3.3. Команды **SHOULD** быть идемпотентными.

12.3.4. `run_id` и корректный код выхода (0 / не-0) **MUST**.

### 12.4. Fail-fast

12.4.1. При ошибке конфигурации / недоступности сервиса **MUST** завершаться сразу.

## 13. Тестирование и контроль качества

### 13.1. Покрытие

13.1.1. Критичный код: coverage ≥85%.

13.1.2. Новый функционал **MUST** сопровождаться тестами.

### 13.2. Типы тестов

| Тип | Описание |
|-----|----------|
| Unit | Мелкие функции, без сети/файлов |
| Integration | VCR.py кассеты |
| Golden | Сравнение с эталонами |
| Property-based | Hypothesis для сложных трансформаций |

### 13.3. CI

13.3.1. **MUST** в CI: тесты, coverage, линтеры, mypy.

13.3.2. Падение **MUST** блокировать merge.

## 14. Рефакторинг модулей

### 14.1. Подготовка

14.1.1. Перед рефакторингом **MUST** составить карту зависимостей.

14.1.2. Обязательные шаги:

```bash
# Импорты
grep -r "from bioetl.domain.X import" src/
grep -r "import bioetl.domain.X" src/

# Использования
grep -r "X\." src/ --include="*.py"

# Тесты
grep -r "X" tests/ --include="*.py"

# Re-exports
grep -r "X" src/bioetl/domain/__init__.py
```

### 14.2. Формат карты зависимостей

- Список файлов-импортёров (с конкретными классами/функциями).
- Список файлов-пользователей.
- Список тестов.
- Рекомендации по порядку миграции.

### 14.3. Правила

14.3.1. Рефакторинг без карты **MUST NOT**.

14.3.2. Тесты **MUST** обновляться до изменения реализации.

14.3.3. Обратная совместимость **MUST** поддерживаться в переходный период.

14.3.4. Breaking changes **MUST** документироваться в `CHANGELOG.md`.

### 14.4. Покрытие перед рефакторингом

14.4.1. Coverage **MUST** >80%.

14.4.2. Все тесты **MUST** быть green.

14.4.3. Тесты **SHOULD** проверять поведение, не реализацию.

### 14.5. Валидация после рефакторинга

**Чеклист**:
- [ ] `pytest tests/ -v --tb=short`
- [ ] `mypy src/bioetl/ --strict`
- [ ] `python -c "from bioetl.domain import *; print('OK')"`
- [ ] Документация обновлена
- [ ] `__init__.py` exports актуальны
- [ ] Deprecation warnings добавлены
- [ ] `CHANGELOG.md` обновлён
- [ ] PR description содержит breaking changes

Рефакторинг считается завершённым только после прохождения всего чеклиста.

---

## Приложение: Схема Конфигурации Пайплайна

```yaml
# configs/pipelines/chembl_activity.yaml
pipeline:
  name: chembl_activity
  provider: chembl
  entity: activity

source:
  type: api  # api | csv | parquet
  load_strategy: incremental  # incremental | full
  watermark_field: updated_at

transform:
  version: "1.2.0"
  steps:
    - normalize_units
    - validate_smiles
    - deduplicate

sink:
  silver:
    path: s3://bioetl/silver/chembl/activity/
    format: delta
    mode: merge
    primary_key: [id]
    partition_by: [year, month]
    classification: public
    forensic_retention: false  # true = 30 days for Critical

  gold:
    path: s3://bioetl/gold/chembl/activity_aggregated/
    format: delta
    mode: overwrite

dq_rules:
  soft_fail_threshold: 0.05
  hard_fail_threshold: 0.20

circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 300

rate_limit:
  requests_per_second: 5
  burst: 10
```
