# BioETL: Правила Проекта
*Версия: 4.1 (Storage Fixes), 2025-05-20*

## Глоссарий
- **Bronze/Silver/Gold**: уровни качества данных (Medallion Architecture).
- **Port**: интерфейс (Protocol) для инверсии зависимостей.
- **Adapter**: реализация Port для конкретного провайдера.
- **DAG**: Directed Acyclic Graph — модель зависимостей этапов пайплайна.

## 1. Архитектура и Слои
**Философия**: "Прагматичная инженерия". Избегаем избыточной сложности (Over-engineering), архитектура должна ускорять вывод продукта на рынок (time-to-market).
**Паттерн**: Слоистая архитектура с инверсией зависимостей (Ports & Adapters).

### 1.1. Слои и Контракты
- **Infrastructure (Инфраструктура/Адаптеры)**: Реализация взаимодействия с внешним миром (HTTP, БД, файловая система).
- **Application (Приложение/Пайплайны)**: Оркестрация потоков данных. Определяет *когда* и *в каком порядке* вызываются порты.
- **Domain (Домен/Чистая логика)**: Чистые функции и контракты (Protocols). Никакого ввода-вывода (I/O).

### 1.1.1. Обеспечение Контрактов (Enforcement)
Интерфейсы определяются в `domain/ports.py` через `typing.Protocol`:
- **Development**: `mypy --strict` проверяет соответствие типов во время сборки.
- **Runtime**: Опционально использовать `@runtime_checkable` для критичных адаптеров, где нужна проверка `isinstance`.

```python
class DataSourcePort(Protocol):
    def fetch(self, query: Query) -> Iterator[RawRecord]: ...
    def health_check(self) -> bool: ...
```

## 2. Поток Данных и Стратегия Medallion
Пайплайны реализуются как направленные ациклические графы (**DAG**).

### 2.1. Архитектура Medallion
| Уровень | Формат | Валидация | Хранение (Retention) | Идемпотентность |
|---------|--------|-----------|----------------------|-----------------|
| **Bronze** (Сырые) | **JSONL + zstd** | Мин./Нет | 90 дней hot -> Archive | Append-only + `ingestion_ts`. CSV запрещен (хрупок). |
| **Silver** (Норм.) | **Delta Lake / Iceberg** | Мягкая (учет дрейфа схемы) | Постоянно | **Merge/Upsert**. Использовать Table Formats для ACID транзакций и эффективных обновлений. |
| **Gold** (Витрины) | Delta/Iceberg/Parquet | Строгая (`strict=True`) | Постоянно | Версионированные снимки (SCD Type 2) или партиционирование по дате. |

### 2.2. Политика Дрейфа Схемы (Schema Drift)
- **Bronze**: Принимает любые поля (schemaless). Цель — сохранить сырой ответ как есть.
- **Silver**: Падает только при отсутствии *критичных* ключей (например, ID). Новые или неизвестные поля логируются, но не блокируют выполнение пайплайна.

### 2.3. Data Lineage (Происхождение Данных)
Каждая запись в Silver/Gold должна содержать метаданные происхождения:
- `_source_file`: путь к файлу в Bronze (S3 path).
- `_source_record_id`: ID записи в Bronze (номер строки или нативный ID).
- `_transform_version`: хэш версии логики трансформации (git SHA или semver).
Хранение lineage осуществляется через встроенные мета-колонки или таблицу `lineage_log`.

### 2.4. Политика Backfill / Replay
- **Bronze**: Неизменяема (Immutable). Backfill = новый fetch с тем же запросом + новый `ingestion_ts`.
- **Silver/Gold**:
  - **Partial**: Перезапуск трансформации на указанном диапазоне дат.
  - **Full Rebuild**: Полное пересоздание таблицы из Bronze (флаг `--full-rebuild`).
- **Маркировка**: Использовать `_backfill_run_id` для отличия от инкрементальных запусков.

### 2.5. Стратегия Партиционирования
| Уровень | Стратегия партиционирования | Пример |
|---------|----------------------------|--------|
| **Bronze** | По `ingestion_date` (YYYY-MM-DD) | `bronze/chembl/activity/2025-05-20/` |
| **Silver** | По `source_date` или `entity_type` | `silver/chembl/activity/year=2025/month=05/` |
| **Gold** | По use-case (часто по `target_id` или `date`) | `gold/activity_by_target/target_id=CHEMBL123/` |

- **Partition Pruning**: Запросы должны включать ключ партиции для избежания полного сканирования (full scan).
- **Compaction**: Мелкие файлы в Bronze объединяются еженедельно в CI-джобе.

### 2.6. Политика NULL и Пропущенных Значений
| Состояние | Представление в Silver/Gold | Пример |
|-----------|----------------------------|--------|
| Значение отсутствует в источнике | `NULL` | API вернул `{}` без поля `ic50` |
| Источник явно указал "нет данных" | `NULL` + флаг `_{field}_explicit_null=true` | API вернул `"ic50": null` |
| Пустая строка | `""` (сохраняется как есть) | `"name": ""` |
| Невалидное значение (DQ error) | `NULL` + запись в `dq_errors` | `"ic50": "not_measured"` |

- **Запрещено**: Использовать значения-заполнители (sentinel values) типа `-1`, `"N/A"`, `9999`.
- **Pandera**: Поля, допускающие NULL, явно маркируются `nullable=True`.

### 2.7. Стратегия Загрузки (Load Strategy)
| Критерий | Incremental | Full Load |
|----------|-------------|-----------|
| Источник поддерживает `updated_since` | ✅ Предпочтительно | — |
| Объём данных > 1M записей | ✅ Обязательно | Только при rebuild |
| Источник не гарантирует immutability | — | ✅ Периодически (weekly) |
| Первичная загрузка | — | ✅ |

- **Watermark**: Для инкрементальной загрузки хранить `last_successful_watermark` (timestamp или ID).
- **Конфигурация**: `load_strategy: incremental | full` в YAML пайплайна.
- **Hybrid**: Incremental ежедневно + Full еженедельно для обеспечения консистентности.

### 2.8. Генерация ID Сущности (Entity ID)
| Сценарий | Стратегия ID |
|----------|--------------|
| Источник предоставляет стабильный ID | Использовать как есть (`chembl_id`, `pubchem_cid`) |
| ID отсутствует | **Content Hash**: `sha256(provider + sorted(content_fields))`. Использование временных меток (`ingestion_ts`) запрещено. |

- **Детекция Коллизий**: При upsert проверять `_source_record_id`; если отличается — конфликт, логировать обе записи.

## 3. Обработка Ошибок и Наблюдаемость

### 3.1. Классификация Ошибок
Вместо тотального подхода "Fail Fast" используем дифференцированный подход:

| Тип Ошибки | Поведение | Пример |
|------------|-----------|--------|
| **Критическая** (Critical) | Падение пайплайна | Ошибка авторизации, несовпадение схемы в Gold, БД недоступна. |
| **Восстановимая** (Recoverable) | Повтор N раз (Backoff) | 429 Rate Limit, 502/504 Timeout, сетевой сбой. |
| **Качество данных** (Data Quality) | Лог + Пропуск записи | Невалидный SMILES, отсутствует необязательное поле. Не роняет батч. |

### 3.1.1. Пороги Ошибок Батча (Thresholds)
- **Soft Threshold**: >10% ошибок качества данных -> Warning в логах, продолжение работы.
- **Hard Threshold**: >50% ошибок -> Fail Batch (не писать в Silver).
Конфигурируется в YAML пайплайна (`failure_thresholds`).

### 3.2. Наблюдаемость (Observability)
- **Логи**: Структурированный JSON. Обязательные поля: `ts`, `level`, `trace_id`, `pipeline`, `stage`, `record_count`, `error_type`.
- **Метрики Пайплайна**: Prometheus-совместимый эндпоинт (`/metrics`). Ключевые метрики: `pipeline_duration_seconds`, `records_processed_total`, `errors_total` (по типам).
- **Алертинг**: Триггер алерта, если уровень ошибок > 5% за 15-минутное окно.

### 3.3. Конкурентность и Блокировки
- **Pipeline Lock**: Один активный инстанс `{provider}_{entity}` в момент времени.
- **Механизм**: Advisory lock (Postgres) или Redis SETNX.
- **Timeout**: **15 минут** (с возможностью продления Heartbeat). Существенное сокращение таймаута для предотвращения зомби-блокировок.
- **Partitioned Runs**: Разрешены параллельные запуски на *непересекающихся* партициях дат.

### 3.4. Метрики Качества Данных (DQ Metrics)
Метрики записываются в таблицу `dq_metrics` для каждого прогона:
- `null_rate_{column}`: % NULL значений.
- `unique_count_{column}`: кардинальность.
- `schema_violations`: количество записей, не прошедших валидацию.
- `freshness_lag_hours`: разница между `max(updated_at)` и `now()`.

### 3.4.1. Детекция Аномалий DQ
- **Baseline (Базовая линия)**: Скользящее среднее за последние 30 дней.
- **Пороги Алертинга**:
  | Метрика | Warning | Critical |
  |---------|---------|----------|
  | Рост `null_rate` | >2x baseline | >5x baseline |
  | Падение `record_count` | <70% baseline | <50% baseline |
  | `freshness_lag_hours` | >24h | >72h |
- **Автоматизация**: CI-джоб `dq-check` сравнивает текущий запуск с базовой линией.

## 4. Стандарты Кода и Тестирование

### 4.1. Стек и Матрица Решений
| Задача | Инструмент | Альтернатива | Критерий выбора |
|--------|------------|--------------|-----------------|
| **Оркестрация** | **Prefect** | Simple Runner | <5 DAG-ов — свой Runner (скрипт). Иначе Prefect. |
| **Валидация** | **Pandera** | Great Expectations | Pandera нативна для DataFrames, легче интегрируется в CI. |
| **HTTP Клиент** | **httpx** | requests | Поддержка `async`. **Для синхронных библиотек (био-пакетов) разрешен запуск в тредах (`run_in_executor`)**. |
| **Линтер** | **Ruff** | Flake8/Black | Скорость и решение "все-в-одном". |

### 4.2. Политика Тестирования
- **Unit**: Только доменная логика. In-memory фейки. Никаких моков (mocks) внешних библиотек.
- **Integration**:
    - **VCR.py**: Запись ответов API в кассеты (`tests/fixtures/vcr/`).
    - **Санитизация**: Обязательная очистка секретов (`Authorization`, `X-API-Key`) и PII в хуке `before_record`.
    - **CI**: Падать, если кассета отсутствует (`pytest --vcr-record=none`), чтобы гарантировать отсутствие сетевых вызовов в CI.
- **Contract Tests**: Ежемесячный запуск против *реальных* API (Live) в отдельном CI workflow для обнаружения нарушения контрактов.

## 5. Операции (Лимиты, Секреты, Shutdown)

### 5.1. Ограничение скорости (Rate Limiting)
Каждый адаптер обязан реализовать `TokenBucket` или аналог, соблюдающий лимиты провайдера.
**Обратное давление (Backpressure)**: Если внутренняя очередь заполнена >80%, адаптер должен замедлить чтение (дросселировать источник).

### 5.2. Управление Секретами
- **Источник**: Переменные окружения (`os.environ`).
- **Формат**: `BIOETL_{PROVIDER}_{KEY}` (например, `BIOETL_PUBCHEM_API_KEY`).
- **Запрещено**: Хардкод секретов, файлы `.env` в git.

### 5.3. Graceful Shutdown (Штатное завершение)
При получении SIGTERM/SIGINT:
1. Прекратить извлечение (fetch) новых записей.
2. Дождаться завершения записи текущего батча.
3. Сохранить чекпоинт (last processed ID) в **S3 (Object Storage)**: `s3://bioetl/checkpoints/{pipeline}_{entity}.json`. Локальное хранение запрещено для поддержки stateless K8s подов.
4. Выйти с кодом 0.
Таймаут на завершение: 30 секунд, затем SIGKILL.

### 5.3.1. Восстановление из Чекпоинта (Checkpoint Recovery)
При запуске пайплайн:
1. Проверяет наличие чекпоинта в S3.
2. Если найден и передан флаг `--resume`:
   - Начинает с `last_processed_id + 1`.
   - Логирует: `Resuming from checkpoint: {id}`.
3. Если найден без флага:
   - Warning: "Stale checkpoint detected. Use --resume or --ignore-checkpoint."
4. После успешного завершения: удалить файл чекпоинта из S3.

### 5.4. Политика Чувствительных Данных (Sensitive Data)
- **PII Поля**: `author_email`, `author_name`, `institution` — маркировать в схеме как `pii=true`.
- **Bronze**: Хранить как есть (raw).
- **Silver**: Хэшировать PII поля: `sha256(lowercase(email))`.
- **Gold**: PII исключается или агрегируется (напр., `author_count` вместо списка имен).
- **Логирование**: Запрещено логировать PII; использовать `record_id` для трассировки.
- **Кассеты VCR**: Обязательная PII-санитизация (см. 4.2).

## 6. Документация (Автоматизация — приоритет)
- **Карта и Схемы**: Генерируются скриптами в CI (pydantic-to-json-schema, eralchemy2, mkdocs).
- **Именование**: Зеркальное (`src/bioetl/.../{provider}/` <-> `docs/providers/{provider}/`).

## 7. Управление Изменениями

### 7.1. Контракты Данных (Data Contracts)
- **Реестр Схем**: Gold-схемы публикуются в `docs/contracts/gold/{entity}.json` (JSON Schema).
- **Версионирование**: Семантическое версионирование схем: `{entity}_v{major}.{minor}`.
  - Minor: добавление nullable полей.
  - Major: удаление/переименование полей, изменение типов.
- **Уведомление о Breaking Change**:
  1. PR с изменением Gold-схемы требует лейбл `breaking-change`.
  2. CI генерирует diff схемы и постит в Slack-канал `#bioetl-contracts`.
  3. Период депрекации: 2 недели до удаления поля.
- **Consumer Tests**: Потребители могут подписаться на `contracts/` и запускать свои тесты при изменениях.

## 8. Опыт Разработчика (Developer Experience)
### 8.1. Локальная настройка
```bash
make install      # создание venv, установка зависимостей
make test         # unit + integration (на кассетах)
make lint         # ruff + mypy
make run-local    # запуск сэмплового пайплайна на фикстурах
```
### 8.2. Окружение
- **Docker Compose**: Для запуска локальных зависимостей (Postgres, Redis).
- **Volumes**: Данные Postgres/Redis персистятся в `./docker-data/` (добавлен в .gitignore).
- **Reset**: `make docker-reset` — очистка volumes для чистого старта.
- **Seed Data**: `make seed-local` — загрузка сэмпловых фикстур в локальную БД.
- **.env.example**: Шаблон переменных окружения (без секретов).

---
## Приложение А: Источники и Библиотеки

**Структура папок:** `src/bioetl/infrastructure/adapters/{provider}/`

| Источник | Библиотека | Rate Limit | Retry Strategy |
|----------|------------|------------|----------------|
| **ChEMBL** | `chembl_webresource_client` | Нет явного лимита | Exponential backoff |
| **PubChem** | `pubchempy` | 5 req/sec | 429 -> wait Retry-After |
| **UniProt** | `unipressed` | 100 req/sec (c API key) | Exponential backoff |
| **OpenAlex** | `pyalex` | 10 req/sec (polite pool) | 429 -> backoff |
| **Semantic** | `semanticscholar` | 100 req/5min | Sliding window |
| **PubMed** | `biopython` | 3 req/sec (10 c key) | 429 -> backoff |
| **Crossref** | `habanero` | 50 req/sec (polite pool) | Exponential backoff |
| **GtoP** | `pyGtoP` (deprecated) | - | - |

## Приложение B: Политика Зависимостей
- **Pinning**: Точные версии в `requirements.txt` / `pyproject.toml`.
- **Обновления**: Ежемесячные PR от Dependabot + ручное ревью.
- **Безопасность**: `pip-audit` в CI. Блокировка мержа при CVE severity >= HIGH.

## Приложение C: Error Recovery Playbook (Runbook)
| Ошибка | Симптом | Действие |
|--------|---------|----------|
| Auth failure | `401 Unauthorized` в логах | Проверить/обновить `BIOETL_{PROVIDER}_API_KEY` |
| Rate limit exhausted | `429` + пик `errors_total{type="recoverable"}` | Уменьшить `requests_per_second` в конфиге |
| Schema mismatch (Gold) | Pipeline fail + `schema_violations` > 0 | Проверить изменения API; обновить Gold-схему через ADR |
| Stale checkpoint | Warning при старте | `--resume` для продолжения или `--ignore-checkpoint` для рестарта |
| >50% DQ errors | Batch fail | Проверить источник; возможно API вернул ошибку в теле ответа |
| Lock timeout | Alert "Lock expired" | Проверить зомби-процессы; `make release-lock PIPELINE=...` |

## Приложение D: Схема Конфигурации Пайплайна
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
    format: parquet
    partition_by: [year, month]
    classification: public

dq_rules:
  soft_fail_threshold: 0.1
  hard_fail_threshold: 0.5

failure_thresholds:
  warn_pct: 10
  fail_pct: 50

rate_limit:
  requests_per_second: 5
  burst: 10
```

## История Изменений (Changelog)
- **4.1** (2025-05-20): Storage Fixes. Bronze: JSONL + zstd (no CSV). Silver: Append-Only + Compaction (no Upsert).
- **4.0** (2025-05-20): Data Contracts, Partitioning, Null Policy, Recovery Playbook.
- **3.0** (2025-05-20): Lineage, Backfill, Concurrency, Graceful Shutdown, Dev Experience.
- **2.0** (2025-05-20): Классификация ошибок, Medallion, Rate limiting, Перевод на русский.
- **1.0** (2025-04-01): Черновик.
