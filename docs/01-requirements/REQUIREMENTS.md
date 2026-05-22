______________________________________________________________________

Version: 1.8.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-22'

______________________________________________________________________

# BioETL: Требования к Проекту

*Синхронизировано с RULES.md v6.1.3 (2026-04-29); ADR registry verified through ADR-047 (2026-05-08).*

______________________________________________________________________

## Формат Требований

Каждое требование имеет:

- **ID**: Уникальный идентификатор `REQ-{раздел}-{номер}`
- **Уровень**: MUST / SHOULD / MAY (по RFC 2119)
- **Описание**: Что требуется
- **Проверка**: Как можно протестировать

______________________________________________________________________

## 1. Архитектура и Слои

### REQ-ARCH-001

- **Уровень**: MUST
- **Описание**: Интерфейсы (Ports) определяются в пакете `domain/ports/` через `typing.Protocol`. Импорт **MUST** быть из фасада (`from bioetl.domain.ports import ...`). Это правило относится и к runtime-oriented cross-layer contracts (`LoggerPort`, `RunnerFactoryPort`, `RunnablePort`, `RateLimiterPort`, `CircuitBreakerPort`): они остаются санкционированной частью `bioetl.domain.ports`, потому что выражают чистые абстракции, а не concrete infrastructure behavior.
- **Проверка**: Статический анализ — проверить наличие пакета и использование Protocol. Архитектурный тест `test-ports-imported-only-from-facade`.

### REQ-ARCH-002

- **Уровень**: MUST
- **Описание**: `mypy --strict` проверяет соответствие типов во время сборки без ошибок
- **Проверка**: Запуск `mypy --strict` возвращает код 0

### REQ-ARCH-003

- **Уровень**: MUST
- **Описание**: Доменный слой (Domain) не содержит операций ввода-вывода (I/O)
- **Проверка**: Статический анализ импортов в `domain/` — отсутствие httpx, requests, sqlite3, psycopg2, boto3 и т.д.

### REQ-ARCH-004

- **Уровень**: SHOULD
- **Описание**: Критичные адаптеры используют `@runtime-checkable` декоратор
- **Проверка**: Проверить наличие декоратора на Protocol классах для критичных адаптеров

### REQ-ARCH-005

- **Уровень**: MUST
- **Описание**: Все адаптеры реализуют асинхронный метод `health_check()` возвращающий `HealthStatus` enum
- **Проверка**: Проверить наличие `async def health_check(self) -> HealthStatus` в каждом адаптере

### REQ-ARCH-006

- **Уровень**: MUST
- **Описание**: `health_check()` использует lightweight probe (не тяжёлые запросы)
- **Проверка**: Проверить что health check не загружает большие данные

### REQ-ARCH-007

- **Уровень**: MUST NOT
- **Описание**: `health_check()` не должен выбрасывать исключения — ловить и возвращать `UNHEALTHY`
- **Проверка**: Тест — исключение в health check возвращает UNHEALTHY

______________________________________________________________________

## 2. Поток Данных и Medallion Architecture

### 2.1 Bronze Layer

#### REQ-DATA-001

- **Уровень**: MUST
- **Описание**: Bronze данные хранятся в формате JSONL + zstd компрессия
- **Проверка**: Проверить расширения файлов в Bronze директории (.jsonl.zst)

#### REQ-DATA-002

- **Уровень**: MUST
- **Описание**: Bronze путь соответствует формату `bronze/{provider}/{entity}/{date}/`
- **Проверка**: Regex валидация путей Bronze файлов

#### REQ-DATA-003

- **Уровень**: MUST
- **Описание**: Bronze данные — append-only (только добавление)
- **Проверка**: Отсутствие операций UPDATE/DELETE на Bronze данных

#### REQ-DATA-004

- **Уровень**: MUST
- **Описание**: Изменение формата Bronze требует явной миграционной стратегии; in-place миграция запрещена
- **Проверка**: Для breaking-изменений определён отдельный путь/версия хранения и план миграции

#### REQ-DATA-005

- **Уровень**: MUST
- **Описание**: Bronze retention — 90 дней hot, затем архив (local archive policy)
- **Проверка**: Проверить local archive policy policy на Bronze бакете

### 2.2 Silver Layer

#### REQ-DATA-006

- **Уровень**: MUST
- **Описание**: Silver данные хранятся в формате **Delta Lake** (ACID обязателен)
- **Проверка**: Проверить наличие `_delta_log/` директории у Silver таблиц

#### REQ-DATA-007

- **Уровень**: MUST NOT
- **Описание**: Raw Parquet без ACID в Silver запрещен
- **Проверка**: Отсутствие `.parquet` Silver-таблиц без `_delta_log/`

#### REQ-DATA-008

- **Уровень**: MUST
- **Описание**: Silver использует строго типизированные режимы записи `MERGE`, `APPEND` или `DELETE` в зависимости от семантики сущности
- **Проверка**: Конфиг пайплайна и код записи используют только поддерживаемые режимы `SilverWriteMode`

### 2.3 Gold Layer

#### REQ-DATA-009

- **Уровень**: MUST
- **Описание**: Gold данные проходят строгую валидацию (`strict=True`)
- **Проверка**: Конфиг пайплайна содержит strict=True для Gold

#### REQ-DATA-010

- **Уровень**: MUST
- **Описание**: Gold использует версионированные снимки (SCD Type 2) или партиционирование по дате
- **Проверка**: Наличие полей версионирования или date партиций в Gold

### 2.4 Delta Lake Infrastructure

#### REQ-DELTA-001

- **Уровень**: MUST
- **Описание**: Использовать `delta-rs` (Rust core) для Python-воркеров
- **Проверка**: Import проверка — `import deltalake` (delta-rs)

#### REQ-DELTA-002

- **Уровень**: MUST
- **Описание**: VACUUM запускается еженедельно с `retention-period=7 days`
- **Проверка**: Проверить наличие scheduled job для VACUUM

#### REQ-DELTA-003

- **Уровень**: MUST
- **Описание**: Forensic retention по умолчанию 7 дней, до 30 дней для critical таблиц через конфиг
- **Проверка**: Проверить значение forensic-retention в конфигах пайплайнов

### 2.5 Schema Drift

#### REQ-SCHEMA-001

- **Уровень**: MUST
- **Описание**: Исчезновение обязательного поля или смена типа классифицируется как Critical drift и блокирует пайплайн
- **Проверка**: Unit-тест — удаление обязательного поля или смена типа вызывает исключение и остановку

#### REQ-SCHEMA-002

- **Уровень**: MUST
- **Описание**: Появление новых опциональных полей логируется (Info drift)
- **Проверка**: Проверить логирование при добавлении нового поля

#### REQ-SCHEMA-003

- **Уровень**: MUST
- **Описание**: Для событий Critical drift назначается owner и устанавливается SLA реакции 48 часов
- **Проверка**: Проверить наличие механизма назначения owner и отслеживания SLA для Critical drift

#### REQ-SCHEMA-004

- **Уровень**: MUST
- **Описание**: Нерешенный Critical drift блокирует следующий релиз
- **Проверка**: Проверить наличие механизма отслеживания Critical drift и блокировки релиза

### 2.6 Data Lineage

#### REQ-LINEAGE-001

- **Уровень**: MUST
- **Описание**: Publication metadata / lineage artifacts содержат canonical Bronze lineage anchor (`_source_batch_id` или formal Bronze artifact ref)
- **Проверка**: Проверить наличие lineage anchor в sidecar metadata / lineage publication contract

#### REQ-LINEAGE-002

- **Уровень**: MUST
- **Описание**: Lineage metadata (`*_metadata.yaml` sidecar + metadata models) хранит маппинг batch-id -> Bronze файлы
- **Проверка**: Проверить наличие и схему metadata sidecar/моделей lineage

#### REQ-LINEAGE-003

- **Уровень**: MUST NOT
- **Описание**: Полные пути к файлам в каждой строке данных запрещены (избыточность)
- **Проверка**: Отсутствие внешних путей хранения; используются локальные пути

### 2.7 Backfill / Replay

#### REQ-BACKFILL-001

- **Уровень**: MUST
- **Описание**: Каждый run публикует `run_id` (UUID) и `run_type` (`incremental` | `backfill` | `rebuild`) в control-plane / lineage artifacts
- **Проверка**: Проверить наличие runtime provenance anchors в run manifest, run ledger, sidecar metadata или audit contract

#### REQ-BACKFILL-002

- **Уровень**: MUST
- **Описание**: Семантика `backfill` / `rebuild` должна обеспечиваться на execution-level через exclusive lock и cleanup-before-run. Persisted Silver/Gold row updates MUST оставаться детерминированными и content-hash-based, без зависимости от `_run_type` в физических Delta rows.
- **Проверка**: Unit-тесты подтверждают, что `_run_type` не участвует в physical Delta merge predicate, а governance/lock tests подтверждают exclusive execution для `backfill`/`rebuild`

#### REQ-BACKFILL-003

- **Уровень**: MUST NOT
- **Описание**: Параллельный запуск rebuild/backfill для одной сущности запрещен
- **Проверка**: Тест concurrent запуска — второй процесс получает ошибку блокировки

#### REQ-BACKFILL-004

- **Уровень**: MUST
- **Описание**: Lock key для exclusive операций: `lock:{provider}-{entity}:exclusive`
- **Проверка**: Проверить формат lock key в MemoryLock при backfill/rebuild

#### REQ-BACKFILL-005

- **Уровень**: MUST
- **Описание**: Default timeout для `--wait-for-lock`: 300 секунд
- **Проверка**: Проверить значение по умолчанию в конфигурации

### 2.7.1 Medallion Clear Policy

#### REQ-CLEAR-001

- **Уровень**: MUST
- **Описание**: REBUILD и BACKFILL run types вызывают `clear-silver()` перед execute
- **Проверка**: Integration тест `test-rebuild-lifecycle-order` — clear вызывается

#### REQ-CLEAR-002

- **Уровень**: MUST
- **Описание**: REBUILD и BACKFILL run types вызывают `clear-gold()` перед execute (если gold-table настроен)
- **Проверка**: Integration тест — gold очищается при rebuild

#### REQ-CLEAR-003

- **Уровень**: MUST NOT
- **Описание**: INCREMENTAL run type НЕ вызывает `clear-silver()` или `clear-gold()`
- **Проверка**: Integration тест `test-incremental-skips-clear` — clear НЕ вызывается

#### REQ-CLEAR-004

- **Уровень**: MUST
- **Описание**: Очистка storage выполняется асинхронно через `async def` lifecycle API
- **Проверка**: Проверить, что путь очистки объявлен как `async def` и вызывается через `await`

### 2.8 Партиционирование

#### REQ-PARTITION-001

- **Уровень**: MUST
- **Описание**: Bronze партиционируется по `ingestion-date` (YYYY-MM-DD)
- **Проверка**: Проверить структуру директорий Bronze

#### REQ-PARTITION-002

- **Уровень**: MUST
- **Описание**: Warning при >10,000 партиций или >100 файлов в партиции
- **Проверка**: Мониторинг метрик партиционирования, алерты

#### REQ-PARTITION-003

- **Уровень**: MUST
- **Описание**: Pipeline Fail при >50,000 партиций
- **Проверка**: Тест — превышение лимита вызывает ошибку пайплайна

#### REQ-PARTITION-004

- **Уровень**: MUST NOT
- **Описание**: Запрещены ключи партиционирования: UUID, Hash, Free-text
- **Проверка**: Статический анализ конфигов — partition-by не содержит запрещенных типов

### 2.9 NULL и Пропущенные Значения

#### REQ-NULL-001

- **Уровень**: MUST
- **Описание**: Отсутствующие в источнике значения заменяются на NULL
- **Проверка**: Unit-тест — отсутствующее поле преобразуется в NULL

#### REQ-NULL-002

- **Уровень**: MUST NOT
- **Описание**: Sentinel values (-1, "N/A", 9999) запрещены
- **Проверка**: Статический анализ кода на использование sentinel values

#### REQ-NULL-003

- **Уровень**: MUST
- **Описание**: Поля, допускающие NULL, явно маркируются `nullable=True` в Pandera
- **Проверка**: Проверить Pandera схемы на явную маркировку nullable полей

#### REQ-NULL-004

- **Уровень**: MUST
- **Описание**: Критичные DQ ошибки направляются в Unified Quarantine таблицу
- **Проверка**: Integration тест — невалидная запись попадает в quarantine

### 2.10 Quarantine

#### REQ-QUARANTINE-001

- **Уровень**: MUST
- **Описание**: Единая таблица `common.quarantine` для всех сущностей
- **Проверка**: Проверить существование таблицы и её схему

#### REQ-QUARANTINE-002

- **Уровень**: MUST
- **Описание**: Quarantine payload обрезается до 64KB
- **Проверка**: Тест — большой payload обрезается

#### REQ-QUARANTINE-003

- **Уровень**: MUST
- **Описание**: Quarantine retention — 30 дней
- **Проверка**: Проверить local archive policy или retention policy

#### REQ-QUARANTINE-004

- **Уровень**: MUST
- **Описание**: Quarantine записи содержат ссылку на Bronze файл (bronze-file-uri или batch-id)
- **Проверка**: Проверить наличие обязательного поля в схеме quarantine

### 2.11 Load Strategy

#### REQ-LOAD-001

- **Уровень**: MUST
- **Описание**: Для `loading_strategy: full_scan_only` checkpoint resume MUST быть отключён
- **Проверка**: Unit/architecture тесты `CheckpointRuntimeService` блокируют resume для `full_scan_only`

#### REQ-LOAD-002

- **Уровень**: MUST
- **Описание**: Publication-related pipeline configs MUST явно задавать `loading_strategy: full_scan_only`
- **Проверка**: Архитектурный тест `tests/architecture/test_force_full_scan_publication.py`

### 2.12 Entity ID Generation

#### REQ-ID-001

- **Уровень**: MUST
- **Описание**: Алгоритм `content_hash`: lowercase SHA-256 hex от `provider + canonical_json(normalized_record)` через canonical serialization helper.
- **Проверка**: Unit-тест генерации ID — результат соответствует алгоритму

#### REQ-ID-002

- **Уровень**: MUST
- **Описание**: Canonical JSON строится только через domain serialization helper с stable key ordering, compact separators и ASCII-safe deterministic output.
- **Проверка**: Unit-тест — JSON формат соответствует спецификации

#### REQ-ID-003

- **Уровень**: MUST
- **Описание**: Float значения округляются до 10 знаков: `round(val, 10)`
- **Проверка**: Unit-тест — float округление в ID генерации

#### REQ-ID-004

- **Уровень**: MUST
- **Описание**: NaN/Inf заменяются на `null` перед генерацией хэша
- **Проверка**: Unit-тест — NaN/Inf нормализация

#### REQ-ID-005

- **Уровень**: MUST
- **Описание**: Даты приводятся к ISO-формату `YYYY-MM-DD`
- **Проверка**: Unit-тест — нормализация дат

#### REQ-ID-006

- **Уровень**: MUST
- **Описание**: Строки обрезаются по краям (`strip()`)
- **Проверка**: Unit-тест — пробелы удаляются

#### REQ-ID-007

- **Уровень**: MUST
- **Описание**: Occurrence-scoped meta-поля (`_ingestion_ts`, `_run_id`, `_run_type`, `_source_batch_id`, `_dq_*`) исключаются из семантического хэша
- **Проверка**: Unit-тест — мета-поля не влияют на хэш

#### REQ-ID-008

- **Уровень**: MUST
- **Описание**: При коллизии хэшей (разные `source_record_id`) — логировать обе записи
- **Проверка**: Тест детекции коллизий

______________________________________________________________________

## 3. Обработка Ошибок и Наблюдаемость

### 3.1 Классификация Ошибок

#### REQ-ERR-001

- **Уровень**: MUST
- **Описание**: Критические ошибки (Auth, Schema Gold, DB unavailable) вызывают падение пайплайна
- **Проверка**: Тест — 401 ошибка останавливает пайплайн

#### REQ-ERR-002

- **Уровень**: MUST
- **Описание**: Восстановимые ошибки (429, 502/504) повторяются N раз с backoff
- **Проверка**: Тест — 429 вызывает retry с exponential backoff

#### REQ-ERR-003

- **Уровень**: MUST
- **Описание**: Ошибки качества данных логируются и запись пропускается (не роняет батч)
- **Проверка**: Тест — невалидный SMILES не останавливает обработку

### 3.2 Пороги Ошибок

#### REQ-THRESHOLD-001

- **Уровень**: MUST
- **Описание**: >5% DQ ошибок — Warning (Soft Threshold)
- **Проверка**: Тест — 6% ошибок генерирует warning

#### REQ-THRESHOLD-002

- **Уровень**: MUST
- **Описание**: >20% DQ ошибок — Fail Batch (Hard Threshold)
- **Проверка**: Тест — 21% ошибок останавливает батч

### 3.3 Retry (Backoff)

#### REQ-RETRY-001

- **Уровень**: MUST
- **Описание**: Max Attempts: 3
- **Проверка**: Тест — после 3 неудач операция прекращается

#### REQ-RETRY-002

- **Уровень**: MUST
- **Описание**: Multiplier: 2.0 (wait 1s, 2s, 4s...)
- **Проверка**: Тест — интервалы между retry соответствуют multiplier

#### REQ-RETRY-003

- **Уровень**: SHOULD
- **Описание**: Jitter: Random(0.1s, 0.5s) для избежания thundering herd
- **Проверка**: Проверить наличие jitter в retry логике

### 3.4 Circuit Breaker

#### REQ-CB-001

- **Уровень**: MUST
- **Описание**: Trigger: 5 последовательных ошибок соединения/таймаута
- **Проверка**: Тест — после 5 ошибок circuit открывается

#### REQ-CB-002

- **Уровень**: MUST
- **Описание**: Open Duration: 5 минут (по умолчанию)
- **Проверка**: Тест — circuit остается открытым 5 минут

#### REQ-CB-003

- **Уровень**: MUST
- **Описание**: Recovery: Half-Open → 1 пробный запрос
- **Проверка**: Тест — после recovery-timeout делается пробный запрос

#### REQ-CB-004

- **Уровень**: MUST
- **Описание**: Метрика `circuit-breaker-state` (0=Closed, 1=Half-Open, 2=Open)
- **Проверка**: Проверить экспорт метрики в правильном формате

#### REQ-CB-005

- **Уровень**: MUST
- **Описание**: Алерт при зависании в Open > 10 минут
- **Проверка**: Проверить наличие алерта в мониторинге

### 3.5 Observability

#### REQ-OBS-001

- **Уровень**: MUST
- **Описание**: `run-id` обязателен во всех логах, метриках и блокировках
- **Проверка**: Статический анализ — все log вызовы содержат run-id

#### REQ-OBS-002

- **Уровень**: MUST
- **Описание**: Логи хранятся 30 дней
- **Проверка**: Проверить retention policy логов

#### REQ-OBS-003

- **Уровень**: MUST
- **Описание**: Метрики хранятся 90 дней
- **Проверка**: Проверить retention policy метрик

#### REQ-OBS-004

- **Уровень**: MUST
- **Описание**: Логи в формате структурированного JSON
- **Проверка**: Проверить формат логов — валидный JSON

#### REQ-OBS-005

- **Уровень**: MUST
- **Описание**: Log Schema содержит обязательные поля: ts, level, run-id, pipeline, stage
- **Проверка**: Валидация схемы логов

#### REQ-OBS-006

- **Уровень**: SHOULD
- **Описание**: Log Schema содержит рекомендуемые поля: dataset, record-count
- **Проверка**: Проверить наличие дополнительных полей в логах

### 3.6 Concurrency и Блокировки

#### REQ-LOCK-001

- **Уровень**: MUST
- **Описание**: Механизм блокировки: `MemoryLock` (Local-Only). Распределенные блокировки запрещены ADR-010.
- **Проверка**: Проверить реализацию LockPort в коде блокировок

#### REQ-LOCK-002

- **Уровень**: MUST
- **Описание**: Lock TTL: `heartbeat-interval * 3` = 90 секунд по умолчанию
- **Проверка**: Проверить значение TTL при создании блокировки

#### REQ-LOCK-003

- **Уровень**: MUST
- **Описание**: Heartbeat: обновление TTL каждые 30 секунд (настраивается в RuntimeConfig)
- **Проверка**: Тест — heartbeat обновляет TTL

#### REQ-LOCK-004

- **Уровень**: MUST NOT
- **Описание**: Смешивание распределенных и локальных блокировок запрещено (Local-Only).
- **Проверка**: Статический анализ — один бэкенд для блокировок

#### REQ-LOCK-005

- **Уровень**: MUST
- **Описание**: Fencing Token: в тело блокировки записывается `owner-id` (run-id)
- **Проверка**: Проверить наличие owner-id в данных блокировки

#### REQ-LOCK-006

- **Уровень**: MUST
- **Описание**: Lock Max Duration: 4 часа, принудительное снятие
- **Проверка**: Тест — блокировка снимается после 4 часов

#### REQ-LOCK-007

- **Уровень**: MUST
- **Описание**: Потеря блокировки = потеря права на запись, аварийное завершение
- **Проверка**: Тест — при потере heartbeat воркер завершается до коммита

#### REQ-LOCK-008

- **Уровень**: MUST
- **Описание**: Safety Guard: валидация блокировки перед записью в local storage/Delta
- **Проверка**: Тест — проверка owner-id перед commit

### 3.7 DQ Metrics

#### REQ-DQ-001

- **Уровень**: MUST
- **Описание**: Метрики экспортируются в формате Prometheus
- **Проверка**: Проверить endpoint /metrics возвращает Prometheus формат

#### REQ-DQ-002

- **Уровень**: MUST
- **Описание**: Метрика `dq-validation-score` с лейблами check, column
- **Проверка**: Проверить наличие метрики с правильными лейблами

#### REQ-DQ-003

- **Уровень**: MUST
- **Описание**: Метрика `data-freshness-seconds`
- **Проверка**: Проверить наличие метрики freshness

### 3.8 DQ Anomaly Detection

#### REQ-ANOMALY-001

- **Уровень**: MUST
- **Описание**: Baseline — скользящее среднее за 30 дней
- **Проверка**: Проверить расчет baseline

#### REQ-ANOMALY-002

- **Уровень**: MUST
- **Описание**: Warning при росте null-rate >2x baseline
- **Проверка**: Тест — 2.5x baseline генерирует warning

#### REQ-ANOMALY-003

- **Уровень**: MUST
- **Описание**: Critical при росте null-rate >5x baseline
- **Проверка**: Тест — 6x baseline генерирует critical

#### REQ-ANOMALY-004

- **Уровень**: MUST
- **Описание**: Warning при падении record-count \<70% baseline
- **Проверка**: Тест — 60% baseline генерирует warning

#### REQ-ANOMALY-005

- **Уровень**: MUST
- **Описание**: Critical при падении record-count \<50% baseline
- **Проверка**: Тест — 40% baseline генерирует critical

#### REQ-ANOMALY-006

- **Уровень**: MUST
- **Описание**: Cold Start: Days 1-7 silence, Days 8-30 warning only, Days 30+ full alerting
- **Проверка**: Тест — корректное поведение на разных этапах cold start

### 3.9 Provider Health

#### REQ-HEALTH-001

- **Уровень**: MUST
- **Описание**: Status Degraded при 1-2 consecutive errors (Timeout ×2, batch-size ÷2)
- **Проверка**: Тест — параметры корректируются при degraded

#### REQ-HEALTH-002

- **Уровень**: MUST
- **Описание**: Status Unhealthy при ≥3 errors — Pause pipeline, Alert P2
- **Проверка**: Тест — пайплайн ставится на паузу

#### REQ-HEALTH-003

- **Уровень**: MUST
- **Описание**: Метрика `provider-health-status` (0=Unhealthy, 1=Degraded, 2=Healthy)
- **Проверка**: Проверить экспорт метрики

______________________________________________________________________

## 4. Стандарты Кода и Тестирование

### 4.1 Стек

#### REQ-STACK-001

- **Уровень**: MUST
- **Описание**: HTTP клиент — httpx с поддержкой async
- **Проверка**: Проверить использование httpx в адаптерах

#### REQ-STACK-002

- **Уровень**: MUST
- **Описание**: Legacy библиотеки без async — через `run-in-executor`
- **Проверка**: Проверить обёртки для pubchempy, biopython

#### REQ-STACK-003

- **Уровень**: MUST
- **Описание**: Валидация — Pandera для DataFrames
- **Проверка**: Проверить использование Pandera схем

#### REQ-STACK-004

- **Уровень**: MUST
- **Описание**: Линтер — Ruff
- **Проверка**: Проверить наличие ruff в dev dependencies и CI

### 4.1.1 Python Standards

#### REQ-PYTHON-001

- **Уровень**: MUST
- **Описание**: Все Python-файлы начинаются с `from __future__ import annotations`
- **Проверка**: `ruff check --select FA` проходит без ошибок

#### REQ-PYTHON-002

- **Уровень**: MUST
- **Описание**: Использовать новый стиль типов: `list[str]` вместо `List[str]`
- **Проверка**: Отсутствие импортов `from typing import List, Dict, Set, Tuple`

#### REQ-PYTHON-003

- **Уровень**: MUST
- **Описание**: Использовать `X | None` вместо `Optional[X]`
- **Проверка**: Отсутствие импортов `from typing import Optional`

### 4.2 Тестирование

#### REQ-TEST-001

- **Уровень**: MUST
- **Описание**: Unit тесты — только доменная логика, in-memory фейки
- **Проверка**: Проверить отсутствие моков внешних библиотек в unit тестах

#### REQ-TEST-002

- **Уровень**: MUST NOT
- **Описание**: Моки (mocks) внешних библиотек в unit тестах запрещены
- **Проверка**: Статический анализ тестов на использование mock

#### REQ-TEST-003

- **Уровень**: MUST
- **Описание**: Integration тесты — VCR.py для записи ответов API
- **Проверка**: Проверить наличие cassettes в `tests/fixtures/vcr/`

#### REQ-TEST-004

- **Уровень**: MUST
- **Описание**: VCR санитизация: удаление Authorization, X-API-Key, PII
- **Проверка**: Проверить хук `before-record` в конфиге VCR

#### REQ-TEST-005

- **Уровень**: MUST
- **Описание**: CI падает при отсутствии cassette (`pytest --vcr-record=none`)
- **Проверка**: Проверить pytest команду в CI

#### REQ-TEST-006

- **Уровень**: MUST
- **Описание**: Contract Tests — ежемесячный запуск против реальных API
- **Проверка**: Проверить наличие scheduled workflow для contract tests

______________________________________________________________________

## 5. Операции

### 5.1 Rate Limiting

#### REQ-RATE-001

- **Уровень**: MUST
- **Описание**: Каждый адаптер реализует `TokenBucket` или аналог
- **Проверка**: Проверить наличие rate limiter в каждом адаптере

#### REQ-RATE-002

- **Уровень**: MUST
- **Описание**: Backpressure: при заполнении очереди >80% — дросселирование
- **Проверка**: Тест — при заполненной очереди скорость чтения снижается

### 5.2 Секреты

#### REQ-SECRET-001

- **Уровень**: MUST
- **Описание**: Секреты из переменных окружения (`os.environ`)
- **Проверка**: Проверить источник секретов в коде

#### REQ-SECRET-002

- **Уровень**: MUST
- **Описание**: Формат: `BIOETL_{PROVIDER}_{KEY}`
- **Проверка**: Проверить имена переменных окружения

#### REQ-SECRET-003

- **Уровень**: MUST NOT
- **Описание**: Хардкод секретов запрещен
- **Проверка**: Статический анализ на хардкод секретов (API keys, passwords)

#### REQ-SECRET-004

- **Уровень**: MUST NOT
- **Описание**: Файлы .env в git запрещены
- **Проверка**: Проверить .gitignore содержит .env

### 5.3 Graceful Shutdown

#### REQ-SHUTDOWN-001

- **Уровень**: MUST
- **Описание**: При SIGTERM/SIGINT — прекратить fetch новых записей
- **Проверка**: Тест — SIGTERM останавливает извлечение

#### REQ-SHUTDOWN-002

- **Уровень**: MUST
- **Описание**: Дождаться завершения записи текущего батча
- **Проверка**: Тест — текущий батч дописывается до конца

#### REQ-SHUTDOWN-003

- **Уровень**: MUST
- **Описание**: Сохранить чекпоинт в локальном хранилище (`data/output/checkpoints`) с атомарной записью (tmp + rename)
- **Проверка**: Тест — чекпоинт сохраняется атомарно

#### REQ-SHUTDOWN-004

- **Уровень**: MUST
- **Описание**: Выход с кодом 0 при graceful shutdown
- **Проверка**: Тест — exit code = 0

### 5.4 Checkpoint Recovery

#### REQ-CHECKPOINT-001

- **Уровень**: MUST
- **Описание**: При запуске — проверка наличия чекпоинта в локальном хранилище
- **Проверка**: Тест — при старте проверяется локальное хранилище

#### REQ-CHECKPOINT-002

- **Уровень**: MUST
- **Описание**: С флагом `--resume` — продолжение с `last-processed-id + 1`
- **Проверка**: Тест — resume начинает с правильной позиции

#### REQ-CHECKPOINT-003

- **Уровень**: MUST
- **Описание**: Без флага при найденном чекпоинте — Warning
- **Проверка**: Тест — генерируется warning о stale checkpoint

#### REQ-CHECKPOINT-004

- **Уровень**: MUST
- **Описание**: После успешного завершения — удалить чекпоинт
- **Проверка**: Тест — чекпоинт удаляется при успехе

### 5.4.1 Async Resource Cleanup

#### REQ-CLEANUP-001

- **Уровень**: MUST
- **Описание**: Все адаптеры и сервисы реализуют асинхронный метод `aclose()` для освобождения ресурсов
- **Проверка**: Проверить наличие `async def aclose(self) -> None` в адаптерах

#### REQ-CLEANUP-002

- **Уровень**: MUST
- **Описание**: `aclose()` должен быть идемпотентным (безопасен для повторных вызовов)
- **Проверка**: Тест — повторный вызов `aclose()` не вызывает ошибку

#### REQ-CLEANUP-003

- **Уровень**: MUST NOT
- **Описание**: `aclose()` не должен выбрасывать исключения
- **Проверка**: Тест — исключения внутри aclose перехватываются

#### REQ-CLEANUP-004

- **Уровень**: MUST
- **Описание**: `PipelineService` реализует async context manager (`__aenter__`/`__aexit__`)
- **Проверка**: Проверить использование `async with services:` в runner

### 5.5 Security

#### REQ-SEC-001

- **Уровень**: MUST
- **Описание**: Для текущего Local-Only runtime доступ к секретам и локальным данным организуется по принципу least privilege: live credentials приходят через environment/secret injection, а write-доступ к data/output путям ограничен оператором или процессом, запускающим пайплайн
- **Проверка**: Проверить, что секреты берутся не из репозитория, а из environment/secret injection; review локальных permission/profile настроек

#### REQ-SEC-002

- **Уровень**: MUST
- **Описание**: Silver: PII хэшируется с солью `sha256(lowercase(value) + SALT)`
- **Проверка**: Проверить хэширование PII в Silver трансформациях

#### REQ-SEC-003

- **Уровень**: MUST
- **Описание**: PII поля обязательно с солью (salted)
- **Проверка**: Тест — хэширование без соли вызывает ошибку

#### REQ-SEC-004

- **Уровень**: MUST
- **Описание**: Gold: PII исключается или агрегируется
- **Проверка**: Проверить отсутствие PII полей в Gold схемах

### 5.6 DR (Disaster Recovery)

#### REQ-DR-001

- **Уровень**: MUST
- **Описание**: RPO: 24 часа
- **Проверка**: Проверить backup schedule обеспечивает RPO

#### REQ-DR-002

- **Уровень**: MUST
- **Описание**: RTO: 4 часа
- **Проверка**: Провести DR drill и замерить время восстановления

#### REQ-DR-003

- **Уровень**: SHOULD
- **Описание**: Restore drills SHOULD проводиться периодически для активных локальных backup-процедур
- **Проверка**: Проверить наличие зафиксированного restore drill или rehearsal по runbook

### 5.7 Environments

#### REQ-ENV-001

- **Уровень**: MUST
- **Описание**: Локальное хранение: отдельные директории/override paths для dev, staging-like и prod-like local profiles
- **Проверка**: Проверить конфигурации локальных путей и profile overrides

#### REQ-ENV-002

- **Уровень**: MUST
- **Описание**: MemoryLock: изоляция по рабочей директории/окружению
- **Проверка**: Проверить изоляцию локальных данных между окружениями

#### REQ-ENV-003

- **Уровень**: MUST
- **Описание**: Secrets для prod-like local profile загружаются через environment/secret injection и не хранятся в репозитории или опубликованных docs
- **Проверка**: Проверить `.env.example`, source-of-secrets в коде и отсутствие live credentials в tracked files

______________________________________________________________________

## 6. Документация

#### REQ-DOC-001

- **Уровень**: MUST
- **Описание**: Активная документация в `docs/00-05` является нормативным published surface и вместе с generated docs проверяется автоматическими docs guardrails; материалы в `docs/99-archive/` сохраняются только как historical/non-normative context
- **Проверка**: Прогнать `uv run python -m scripts.docs check-links --links --specs --configs` и убедиться, что generated-doc проверки (например dependency-map / schema export checks) проходят в CI, а active entry points не ссылаются на `docs/99-archive/` как на источник текущих требований

#### REQ-DOC-002

- **Уровень**: MUST
- **Описание**: Именование: `src/bioetl/.../{provider}/` \<-> `docs/04-reference/providers/{provider}/`
- **Проверка**: Проверить соответствие структур папок

______________________________________________________________________

## 7. Управление Изменениями

### 7.1 Data Contracts

#### REQ-CONTRACT-001

- **Уровень**: MUST
- **Описание**: Gold-схемы публикуются в `docs/04-reference/contracts/gold/{provider}_{entity}_v{major}.{minor}.json`
- **Проверка**: Проверить наличие JSON Schema файлов

#### REQ-CONTRACT-002

- **Уровень**: MUST
- **Описание**: Версионирование: `{provider}_{entity}_v{major}.{minor}`
- **Проверка**: Проверить формат версий в схемах

#### REQ-CONTRACT-003

- **Уровень**: MUST
- **Описание**: PR с изменением Gold-схемы содержит явный consumer-impact note / migration note и обновлённые generated contract artifacts
- **Проверка**: Проверить diff PR: обновлены JSON exports/contract parity и есть impact note в PR/changelog/ADR-контексте

#### REQ-CONTRACT-004

- **Уровень**: MUST
- **Описание**: Период депрекации: 2 недели до удаления поля
- **Проверка**: Проверить наличие deprecated маркеров в схемах

### 7.2 Rollback

#### REQ-ROLLBACK-001

- **Уровень**: MUST
- **Описание**: Automatic application rollback не является частью текущего Local-Only runtime; rollback выполняется по documented manual platform/deployment procedure
- **Проверка**: Проверить наличие manual rollback procedure и placeholder/guard, запрещающий несуществующий runtime rollback command

#### REQ-ROLLBACK-002

- **Уровень**: MUST NOT
- **Описание**: DQ ошибки не триггерят автоматический откат версии
- **Проверка**: Тест — DQ ошибки не вызывают rollback

______________________________________________________________________

## 8. Developer Experience

#### REQ-DX-001

- **Уровень**: MUST
- **Описание**: `make install` — создание venv, установка зависимостей
- **Проверка**: Команда выполняется без ошибок

#### REQ-DX-002

- **Уровень**: MUST
- **Описание**: `make test` — локальный стабильный suite с coverage (без E2E)
- **Проверка**: Команда выполняется и запускает рекомендуемый локальный pre-commit прогон

#### REQ-DX-003

- **Уровень**: MUST
- **Описание**: `make lint` — ruff + mypy
- **Проверка**: Команда выполняется и запускает линтеры

#### REQ-DX-004

- **Уровень**: MUST
- **Описание**: Docker Compose для локальных зависимостей
- **Проверка**: docker-compose.yml допускается как legacy, но не требуется для Local-Only.

#### REQ-DX-005

- **Уровень**: MUST
- **Описание**: .env.example — шаблон переменных окружения
- **Проверка**: Файл существует и содержит все необходимые переменные

______________________________________________________________________

## Приложение: Dependencies

#### REQ-DEP-001

- **Уровень**: MUST
- **Описание**: Используется mixed strategy для зависимостей: диапазоны версий в `pyproject.toml` + фиксированный `uv.lock` для воспроизводимости окружения
- **Проверка**: Проверить, что `uv.lock` закоммичен и обновляется при изменении зависимостей; точечные `==` используются только для обоснованных исключений

#### REQ-DEP-002

- **Уровень**: MUST
- **Описание**: `pip-audit` в CI, блокировка мержа при CVE >= HIGH
- **Проверка**: Проверить наличие pip-audit в CI workflow

______________________________________________________________________

## Приложение: Provider Health Checks

#### REQ-PROVIDER-001

- **Уровень**: MUST
- **Описание**: ChEMBL health check: `GET /chembl/api/data/status.json`
- **Проверка**: Проверить реализацию health check для ChEMBL

#### REQ-PROVIDER-002

- **Уровень**: MUST
- **Описание**: PubChem health check: lightweight compound query
- **Проверка**: Проверить реализацию health check для PubChem

#### REQ-PROVIDER-003

- **Уровень**: MUST
- **Описание**: Generic Probe для API без dedicated health endpoint (timeout 5s)
- **Проверка**: Проверить fallback health check с timeout

______________________________________________________________________

## Сводка Требований

| Категория            | MUST    | SHOULD | MUST NOT | Всего   |
| -------------------- | ------- | ------ | -------- | ------- |
| Архитектура          | 5       | 1      | 1        | 7       |
| Данные/Medallion     | 45      | 0      | 6        | 51      |
| Ошибки/Observability | 36      | 2      | 1        | 39      |
| Код/Тесты            | 12      | 0      | 1        | 13      |
| Операции             | 24      | 1      | 3        | 28      |
| Документация         | 2       | 0      | 0        | 2       |
| Изменения            | 5       | 0      | 1        | 6       |
| DX                   | 5       | 0      | 0        | 5       |
| Dependencies         | 2       | 0      | 0        | 2       |
| Providers            | 3       | 0      | 0        | 3       |
| **Итого**            | **139** | **4**  | **13**   | **156** |

______________________________________________________________________

## История Изменений

- **1.8** (2026-03-13): Уточнён REQ-DOC-001: docs guardrails и generated-doc checks синхронизированы с текущей publication/navigation governance.
- **1.7** (2026-03-02): Pre-v6.1 dependency policy update. Обновлена REQ-DEP-001: mixed strategy (`pyproject.toml` ranges + `uv.lock`) вместо требования глобального `==` pinning.
- **1.6** (2026-02-27): Pre-v6.1 terminology cleanup. Исправлена терминология требований (`health_check`, `from __future__ import annotations`, формат env vars `BIOETL_{PROVIDER}_{KEY}`).
- **1.5** (2026-02-04): Local-Only sync. Удалены ссылки на S3/Redis. Синхронизировано с RULES.md v5.20.
- **1.4** (2026-01-21): Пересчитана сводка требований (156 вместо 139). Исправлены категории и уровни. Синхронизировано с RULES.md v5.20.
- **1.3** (2026-01-05): Синхронизировано с RULES.md v5.20.
- **1.2** (2025-12-27): Добавлены требования REQ-ARCH-005..007 (Health Check), REQ-CLEAR-001..004 (Medallion Clear Policy), REQ-PYTHON-001..003 (Future Annotations), REQ-CLEANUP-001..004 (Async Resource Cleanup). Синхронизировано с RULES.md v5.6.
- **1.1** (2025-12-25): Добавлены требования REQ-ARCH-005..007 (Health Check), REQ-CLEAR-001..004 (Medallion Clear Policy), REQ-PYTHON-001..003 (Future Annotations), REQ-CLEANUP-001..004 (Async Resource Cleanup). Синхронизировано с RULES.md v5.4.
- **1.0** (2025-12-15): Первоначальная версия. Извлечено из RULES.md v5.0.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
