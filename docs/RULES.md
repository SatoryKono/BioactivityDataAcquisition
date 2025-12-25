# BioETL: Правила Проекта
*Версия: 5.4 (Architecture Documentation Update), 2025-12-25* 
 
## Введение (Quick Reference) 
| Задача | Раздел | Инструмент | 
|--------|--------|------------| 
| Создать новый пайплайн | App D | YAML config | 
| Добавить поле в схему | 2.2, App E | Pydantic model | 
| Ошибка в проде (Alert) | App C | Runbook | 
| Удалить битые данные | 2.6 | `make quarantine-purge` | 
| Развернуть на Staging | 5.6.1 | CI/CD | 
| Восстановление при аварии | 5.5 | DR Runbook | 
| Откат релиза | 7.2 | Rollback Strategy | 
| Безопасность | 5.4 | Security Policy | 
| Forensic retention для таблицы | 2.1.1, App D | Config `forensic_retention` |
| Backfill с эксклюзивной блокировкой | 2.4 | Lock Mechanism |
| Deprecation поля | 7.1, App E | Schema Evolution |

### Уровни Требований (Governance)
В документе используются ключевые слова согласно RFC 2119:
- **MUST** (Обязательно): Абсолютное требование. Нарушение рассматривается как дефект или блокер релиза.
- **SHOULD** (Рекомендуется): Сильная рекомендация. Отклонение требует явного обоснования (комментарий в PR).
- **MAY** (Опционально): Разрешено, на усмотрение разработчика.
 
## Глоссарий 
- **Bronze/Silver/Gold**: уровни качества данных (Medallion Architecture). 
- **Port**: интерфейс (Protocol) для инверсии зависимостей. 
- **Adapter**: реализация Port для конкретного провайдера. 
- **DAG**: Directed Acyclic Graph — модель зависимостей этапов пайплайна. 
- **Quarantine**: Изолированное хранилище для данных, не прошедших валидацию (Dead Letter Queue). 
- **Entity ID (Business Key)**: Идентификатор объекта в реальном мире (напр., `chembl_id`). Стабилен во времени.
- **Content Hash (Version ID)**: Идентификатор конкретного состояния объекта (`sha256`). Изменяется при обновлении атрибутов. Используется для дедупликации и SCD Type 2.
- **Time Travel**: Возможность запроса данных на определенный момент времени (Delta Lake Feature). 
- **Circuit Breaker**: Паттерн защиты от каскадных сбоев, временно отключающий вызовы к сбойному сервису. 
- **RPO (Recovery Point Objective)**: Максимально допустимый период потери данных при аварии. 
- **RTO (Recovery Time Objective)**: Максимально допустимое время простоя системы. 
- **SCD Type 2**: Slowly Changing Dimension — сохранение истории изменений записи (новые строки для изменений). 
- **Heartbeat**: Периодическое обновление TTL блокировки для подтверждения liveness воркера.
- **Fencing Token**: Идентификатор владельца блокировки (`owner_id`) для предотвращения split-brain.
- **Game Day**: Плановые учения по проверке DR процедур.
 
## 1. Архитектура и Слои 
**Философия**: "Прагматичная инженерия". Избегаем избыточной сложности (Over-engineering), архитектура должна ускорять вывод продукта на рынок (time-to-market). 
**Паттерн**: Слоистая архитектура с инверсией зависимостей (Ports & Adapters). 
 
### 1.1. Слои и Контракты 
- **Infrastructure (Инфраструктура/Адаптеры)**: Реализация взаимодействия с внешним миром (HTTP, БД, файловая система). 
- **Application (Приложение/Пайплайны)**: Оркестрация потоков данных. Определяет *когда* и *в каком порядке* вызываются порты. 
- **Domain (Домен/Чистая логика)**: Чистые функции и контракты (Protocols). Никакого ввода-вывода (I/O). 
 
### 1.1.1. Обеспечение Контрактов (Enforcement) 
Интерфейсы определяются в `domain/ports.py` через `typing.Protocol`: 
- **Design-time**: `mypy --strict` проверяет соответствие типов во время сборки. Основной механизм контроля. 
- **Runtime Boundary**: Опционально использовать `@runtime_checkable` только для критичных адаптеров (boundary validation). Семантика поведения в runtime не проверяется типами. 
 
```python 
class DataSourcePort(Protocol): 
    def fetch(self, query: Query) -> Iterator[RawRecord]: ... 
    async def health_check(self) -> HealthStatus: ... 
```

### 1.1.2. Health Check Protocol
Все адаптеры **MUST** реализовывать асинхронный метод `health_check()`:

```python
from bioetl.domain.types import HealthStatus

class MyAdapter:
    async def health_check(self) -> HealthStatus:
        """Проверка доступности внешнего сервиса.

        Returns:
            HealthStatus.HEALTHY — сервис доступен и отвечает < 5 сек
            HealthStatus.DEGRADED — медленный отклик (> 5 сек)
            HealthStatus.UNHEALTHY — ошибка или timeout
        """
```

**Контракт:**
- **MUST** быть `async def` (асинхронный)
- **MUST** возвращать `HealthStatus` enum, не `bool`
- **MUST** использовать lightweight probe (не тяжёлые запросы)
- **SHOULD** кэшировать результат на 30 секунд для избежания лишних вызовов
- **MUST NOT** выбрасывать исключения — ловить и возвращать `UNHEALTHY`

**Проверка:** Архитектурный тест `tests/architecture/` валидирует сигнатуры.

## 2. Поток Данных и Стратегия Medallion
Пайплайны реализуются как направленные ациклические графы (**DAG**). 
 
### 2.1. Архитектура Medallion 
| Уровень | Формат | Валидация | Хранение (Retention) | Идемпотентность | 
|---------|--------|-----------|----------------------|-----------------| 
| **Bronze** (Сырые) | **JSONL + zstd** | Мин./Нет | 90 дней hot -> Archive (S3 Lifecycle) | Path: `bronze/{format_version}/{provider}/{entity}/{date}/`. Append-only. | 
| **Silver** (Норм.) | **Delta Lake / Iceberg** | Мягкая (учет дрейфа схемы) | Постоянно | **Merge/Upsert**. Raw Parquet в Silver **MUST NOT** использоваться. Обязателен ACID. Time Travel — для Ops, не для DR. | 
| **Gold** (Витрины) | Delta/Iceberg/Parquet | Строгая (`strict=True`) | Постоянно | Версионированные снимки (SCD Type 2) или партиционирование по дате. | 

**Bronze Lifecycle:**
- Формат файлов (JSONL) зафиксирован в версии пути (`/v1/`).
- Изменение формата требует новой ветки (`/v2/`). Миграция "in-place" запрещена.
 
### 2.1.1. Инфраструктура Delta Lake 
- **Engine**: Использовать `delta-rs` (Rust core) для Python-воркеров для производительности. 
- **Protocol**: Writer Version 2 (поддержка Column Mapping), Reader Version 1. 
- **Maintenance**: Обязательный запуск `VACUUM` с `retention_period=7 days` еженедельно для очистки старых файлов и уменьшения стоимости хранения. **VACUUM MUST** запускаться еженедельно.
- **Forensic Retention**: По умолчанию 7 дней. Для таблиц класса critical (Core Data) допустимо увеличение до 30 дней через конфиг (`forensic_retention: true`), если позволяет бюджет.
 
### 2.2. Политика Дрейфа Схемы (Schema Drift) 
- **Info**: Появление новых опциональных полей. Логируется. 
- **Warn**: Появление >3 новых полей. Требует ревью. 
- **Critical**: Исчезновение обязательного поля (ID). Блокирует пайплайн. 
- **Drift SLA**: Для событий WARN (дрейф схемы) назначается Owner. SLA на реакцию — 48 часов. Нерешенный дрейф блокирует следующий релиз.
 
### 2.3. Data Lineage (Происхождение Данных) 
Оптимизированная схема lineage: 
- **Silver Record**: Содержит `_source_batch_id` (FK). 
- **Lineage Log**: Таблица `sys.lineage_log` хранит маппинг `_source_batch_id` -> список файлов Bronze (S3 paths), версия трансформации, параметры запуска. 
Полные пути к файлам в каждой строке данных хранить запрещено (избыточность). 
 
### 2.4. Политика Backfill / Replay 
- **Metadata**: Обязательные поля `_run_id` (UUID), `_run_type` (`incremental` | `backfill` | `rebuild`). 
- **Merge Priority**: `rebuild` > `backfill` > `incremental`. При конфликте версий побеждает более "полный" тип запуска. 
- **Concurrency Constraint**: В один момент времени для одной сущности допустим только один процесс записи типа `rebuild` или `backfill`. Параллельный запуск запрещен (Lock должен это гарантировать).

#### 2.4.1. Backfill Lock Enforcement
Lock key включает тип запуска:
- `incremental`: `lock:{provider}_{entity}`
- `backfill`/`rebuild`: `lock:{provider}_{entity}:exclusive`

При наличии активного `incremental` lock попытка взять `:exclusive`:
- **Default**: Fail immediately (configurable).
- **Wait mode**: `--wait-for-lock TIMEOUT_SEC`. Timeout по умолчанию: 300 секунд.

#### 2.4.2. Medallion Clear Policy by Run Type
См. [ADR-012](02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md) и [ADR-013](02-architecture/decisions/ADR-013-async-storage-cleanup.md).

| Run Type | Clear Silver | Clear Gold | Rationale |
|----------|--------------|------------|-----------|
| `REBUILD` | ✅ MUST | ✅ MUST | Полная перестройка данных |
| `BACKFILL` | ✅ MUST | ✅ MUST | Историческая загрузка заново |
| `INCREMENTAL` | ❌ MUST NOT | ❌ MUST NOT | Merge/Upsert, сохранение данных |

**Инвариант Medallion**: Incremental runs **MUST NOT** вызывать `clear_silver()` или `clear_gold()`. Нарушение этого правила приводит к потере данных.

**Реализация:**
```python
# В PipelineRunner._clear_exports()
if self.runtime.run_type in (RunType.REBUILD, RunType.BACKFILL):
    await self.services.storage.clear_silver(self.config.silver_table)
    if self.config.gold_table:
        await self.services.storage.clear_gold(self.config.gold_table)
```

**Проверка:** Интеграционный тест `tests/integration/test_runner_lifecycle.py::test_incremental_skips_clear`.

### 2.5. Стратегия Партиционирования 
| Уровень | Стратегия партиционирования | Пример | 
|---------|----------------------------|--------| 
| **Bronze** | По `ingestion_date` (YYYY-MM-DD) | `bronze/v1/chembl/activity/2025-05-20/` | 
| **Silver** | По `source_date` или `entity_type` | `silver/chembl/activity/year=2025/month=05/` | 
| **Gold** | По use-case (часто по `target_id` или `date`) | `gold/activity_by_target/target_id=CHEMBL123/` | 
 
- **Soft Limits**: Warning при >10,000 партиций или >100 файлов в партиции. 
- **Hard Limits**: 50,000 партиций -> Pipeline Fail. Запрещены ключи партиционирования: UUID, Hash, Free-text (высокая кардинальность убивает Delta Log).
- **Z-ORDER**: Рекомендуется для полей с высокой кардинальностью в Gold слое (вместо глубокого партиционирования). 
 
### 2.6. Политика NULL и Пропущенных Значений 
| Состояние | Действие | Куда попадает | 
|-----------|----------|---------------| 
| Значение отсутствует в источнике | Замена на NULL | Таблица Silver | 
| Некритичная ошибка DQ (warning) | Замена на NULL | Таблица Silver (с флагом `_dq_warn=true`) | 
| Критичная ошибка DQ (error) | Исключение из основного потока | **Таблица Quarantine (Unified)** | 
 
#### Спецификация Unified Quarantine 
Единая таблица `common.quarantine` для всех сущностей. 
- `ingestion_ts` (Timestamp): Время инцидента. 
- `pipeline` (String): Имя пайплайна (напр., `chembl_activity`). 
- `error_code` (String): Тип ошибки (напр., `SCHEMA_VIOLATION`). 
- `payload` (JSON/Text): Сырая запись (**Truncated to 64KB**). 
- `payload_hash` (String): Для дедупликации ошибок. 
- `bronze_batch_id` (UUID): Ссылка на пакет исходных данных. 
- `dq_status` (String): `NEW` | `IGNORED` | `REPROCESSED`. 
 
- **Запрещено**: Sentinel values (-1, "N/A", 9999) **MUST NOT** использоваться.
- **Pandera**: Поля, допускающие NULL, явно маркируются `nullable=True`. 
 
#### Жизненный цикл Карантина 
- **Retention**: 30 дней. Старые записи удаляются автоматически (S3 Lifecycle). 
- **Triage**: Еженедельный пересмотр (Triage) ошибок аналитиками. Если ошибка системная — правим адаптер, если разовая — игнорируем. 
- **Source of Truth**: Карантин — это инструмент триажа, а не источник истины. Данные в карантине считаются "отсутствующими" в аналитическом слое.
- **Linkage**: Обязательна ссылка на Bronze-файл (`bronze_file_uri` или `batch_id`) для возможности перепарсить исходник, если payload был обрезан.
 
#### Операции с карантином 
Для управления "мусорными" данными использовать make-команды: 
- `make quarantine-inspect PIPELINE=...`: Выгрузка сэмпла ошибок для анализа. 
- `make quarantine-replay PIPELINE=...`: Повторная отправка исправленных записей в пайплайн. 
- `make quarantine-purge PIPELINE=...`: Принудительная очистка карантина. 
 
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
| ID отсутствует | **Content Hash**: `sha256(provider + canonical_json_dumps(record))`. | 
 
- **Алгоритм**: `sha256(provider + canonical_json_dumps(record))` 
- **Canonical JSON**: `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`. 
  - **Float Precision**: Все значения типа float принудительно округляются: `round(val, 10)` для нивелирования различий архитектур процессоров. 
 
### 2.8.1. Robust Content Hash 
Для обеспечения стабильности хэша перед генерацией ID данные должны быть нормализованы: 
- **NaN/Inf**: Заменяются на `null` (None). 
- **Floats**: Округляются до 10 знаков после запятой. 
- **Dates**: Приводятся к единому ISO-формату `YYYY-MM-DD`. 
- **Strings**: Удаление пробелов по краям (`strip()`). 
 
**Исключения**: Из расчета хэша исключаются технические мета-поля: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`. 
 
- **Детекция Коллизий**: При upsert проверять `_source_record_id`; если отличается — конфликт, логировать обе записи. 
 
## 3. Обработка Ошибок и Наблюдаемость

### 3.1. Стратегия Обработки Ошибок
Вместо тотального подхода "Fail Fast" используем дифференцированный подход.

### 3.1.1. Классификация Ошибок 
| Тип Ошибки | Поведение | Пример | 
|------------|-----------|--------| 
| **Критическая** (Critical) | Падение пайплайна | Ошибка авторизации, несовпадение схемы в Gold, БД недоступна. | 
| **Восстановимая** (Recoverable) | Повтор N раз (Backoff) | 429 Rate Limit, 502/504 Timeout, сетевой сбой. | 
| **Качество данных** (Data Quality) | Лог + Пропуск записи | Невалидный SMILES, отсутствует необязательное поле. Не роняет батч. | 

### 3.1.2. Пороги Ошибок Батча (Thresholds) 
- **Soft Threshold**: >5% ошибок качества данных -> Warning. 
- **Hard Threshold**: >20% ошибок -> Fail Batch. 
- **Metric Scope**: Отслеживать как `record_error_rate` (доля битых строк), так и `entity_error_rate` (доля битых уникальных сущностей). 
 
### 3.1.3. Параметры Retry (Backoff) 
Для типа ошибок **Recoverable** применять стратегию Exponential Backoff: 
- **Max Attempts**: 3 
- **Multiplier**: 2.0 (wait 1s, 2s, 4s...) 
- **Jitter**: Random(0.1s, 0.5s). Jitter **SHOULD** применяться для избежания thundering herd.
 
### 3.1.4. Circuit Breaker (Размыкатель цепи)
Паттерн защиты от каскадных сбоев. См. [ADR-007](02-architecture/decisions/ADR-007-circuit-breaker-implementation.md).
- **Trigger**: 5 последовательных ошибок соединения/таймаута.
- **Open Duration**: 5 минут (configurable: `circuit_breaker.recovery_timeout`).
- **Recovery**: Half-Open → 1 пробный запрос. Success → Closed, Failure → Open +5 мин.
- **Observability**: Метрики `circuit_breaker_state` (0=Closed, 1=Half-Open, 2=Open), `trips_total`. Алерт при зависании в Open > 10 мин. 
 
### 3.2. Наблюдаемость (Observability) 
- **Correlation ID**: `run_id` обязателен во всех логах, метриках и блокировках. 
- **Retention**: Логи хранятся 30 дней, метрики — 90 дней. 
- **Логи**: Структурированный JSON. 
- **Dataset ID**: В логи и метрики добавляется лейбл `dataset` (логическое имя таблицы, напр. `chembl.activity`), так как pipeline может писать в несколько таблиц.

### 3.2.1. Log Schema
| Поле | Обязательность | Пример |
|------|----------------|--------|
| ts | MUST | `2025-12-15T10:00:00Z` |
| level | MUST | `INFO`, `ERROR` |
| run_id | MUST | UUID |
| pipeline | MUST | `chembl_activity` |
| stage | MUST | `extract`, `transform`, `load` |
| dataset | SHOULD | `chembl.activity` |
| record_count | SHOULD | 1000 |
| error_type | При ошибках | `SCHEMA_VIOLATION` |

### 3.2.2. Prometheus Metrics

**Endpoint:** `http://localhost:{BIOETL_METRICS_PORT}/metrics` (default port: 8000)

**Запуск метрик:**
- Автоматически в `bootstrap_pipeline()` (Composition Root)
- Идемпотентный: повторный вызов безопасен (Double-Check Locking)
- Graceful degradation: ошибки метрик не блокируют пайплайн

**Pipeline Metrics (prefix: `bioetl_`):**

| Метрика | Тип | Labels | Описание |
|---------|-----|--------|----------|
| `pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type | Длительность выполнения этапов |
| `records_processed_total` | Counter | pipeline, stage, run_type | Количество обработанных записей |
| `errors_total` | Counter | pipeline, stage, error_code | Количество ошибок по типам |
| `batch_size_records` | Histogram | pipeline, stage | Распределение размеров батчей |
| `filter_ids_loaded_total` | Counter | pipeline | Загружено ID для фильтрации |
| `filter_ids_duplicates_total` | Counter | pipeline | Дубликаты в файле фильтрации |

**Реализация:** См. `src/bioetl/infrastructure/observability/metrics.py` и `prometheus_metrics.py`.

### 3.3. Конкурентность и Блокировки

> **Note: Local-Only Deployment** (см. [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md))
>
> Текущая реализация использует **MemoryLock** для локального развёртывания.
> Redis-блокировки (ADR-003) остаются спецификацией для будущего распределённого развёртывания.

#### Текущая реализация (Local-Only)
- **Механизм**: In-memory блокировки (`MemoryLock`)
- **Scope**: Один процесс Python
- **Pipeline Lock**: Один активный инстанс `{provider}_{entity}`
- **Lock Max Duration**: **4 часа**. Принудительное снятие по истечении.

#### Спецификация для распределённого развёртывания
См. [ADR-003](02-architecture/decisions/ADR-003-redis-for-distributed-locking.md) (отложено).
- **Механизм**: Redis `SETNX` + `EXPIRE`
- **TTL**: 60 секунд
- **Heartbeat**: Обновление TTL каждые 20 секунд
- **Fencing Token**: `owner_id` (run_id воркера)

**Invariant** (применимо ко всем вариантам развёртывания):
- Потеря блокировки = Потеря права на запись.
- Если Heartbeat не прошел, воркер **MUST** аварийно завершиться до попытки коммита данных.
- **Safety Guard**: Адаптер **MUST** валидировать наличие блокировки перед записью данных.
 
### 3.4. Метрики Качества Данных (DQ Metrics) 
Метрики экспортируются в формате Prometheus с использованием лейблов для агрегации (`pipeline`, `entity`, `column`, `check`):
- `dq_validation_score{check="null_rate", column="..."}`: % NULL значений.
- `dq_validation_score{check="unique_count", column="..."}`: кардинальность.
- `dq_validation_score{check="schema_violations", column="all"}`: кол-во невалидных записей.
- `data_freshness_seconds`: разница между `now()` и `max(updated_at)`.
 
### 3.4.1. Детекция Аномалий DQ 
- **Baseline (Базовая линия)**: Скользящее среднее за последние 30 дней. 
- **Пороги Алертинга**: 
  | Метрика | Warning | Critical | 
  |---------|---------|----------| 
  | Рост `null_rate` | >2x baseline | >5x baseline | 
  | Падение `record_count` | <70% baseline | <50% baseline | 
  | `freshness_lag_hours` | >24h | >72h | 
- **Автоматизация**: CI-джоб `dq-check` сравнивает текущий запуск с базовой линией. 
- **Cold Start**: 
  - Days 1-7: Silence (обучение). 
  - Days 8-30: Warning only. 
  - Days 30+: Full Alerting. 
 
### 3.5. Provider Health Monitoring 
| Status | Условие | Действие |
|--------|---------|----------|
| Healthy | 0 errors за 5 мин | Normal operation |
| Degraded | 1-2 consecutive errors | Timeout ×2, batch_size ÷2 |
| Unhealthy | ≥3 errors или health_check fail | Pause pipeline, Alert P2 |

**Recovery**: Unhealthy → Degraded после 1 успешного health_check.
**Metric**: `provider_health_status{provider}` (0=Unhealthy, 1=Degraded, 2=Healthy).
 
## 4. Стандарты Кода и Тестирование 
 
### 4.1. Стек и Матрица Решений 
| Задача | Инструмент | Альтернатива | Критерий выбора | 
|--------|------------|--------------|-----------------| 
| **Оркестрация** | **Prefect** | Simple Runner | <5 DAG-ов — свой Runner (скрипт). Иначе Prefect. | 
| **Валидация** | **Pandera** | Great Expectations | Pandera нативна для DataFrames, легче интегрируется в CI. | 
| **HTTP Клиент** | **httpx** | requests | Поддержка `async`. **Legacy Wrappers**: Для библиотек без async поддержки (pubchempy, biopython) обязателен запуск в отдельном пуле потоков: `await loop.run_in_executor(thread_pool, fetch_func)`. | 
| **Линтер** | **Ruff** | Flake8/Black | Скорость и решение "все-в-одном". | 
 
### 4.2. Политика Тестирования
**Цель покрытия:** >80% line coverage (проверяется в CI через `--cov-fail-under=80`).

- **Unit**: Только доменная логика. In-memory фейки. Никаких моков (mocks) внешних библиотек.
- **Integration**:
    - **VCR.py**: Запись ответов API в кассеты (`tests/fixtures/vcr/`).
    - **Санитизация**: Обязательная очистка секретов (`Authorization`, `X-API-Key`) и PII в хуке `before_record`.
    - **CI**: Падать, если кассета отсутствует (`pytest --vcr-record=none`), чтобы гарантировать отсутствие сетевых вызовов в CI.
- **E2E (End-to-End)**: Полный цикл пайплайна от fetch до Gold (`tests/e2e/`).
    - **Архитектура**: Local-Only (файловая система, MemoryLock, LocalCheckpoint).
    - **Helpers**: `create_test_context()`, `assert_bronze_files_exist()`, `assert_silver_table_has_records()`.
    - **Маркер**: `@pytest.mark.e2e` для селективного запуска.
    - **Запуск**: `pytest tests/e2e/ -v -m e2e`.
- **Contract Tests**: Ежемесячный запуск против *реальных* API (Live) в отдельном CI workflow для обнаружения нарушения контрактов.

### 4.3. Детерминизм и Воспроизводимость
См. [ADR-014](02-architecture/decisions/ADR-014-deterministic-writes.md).

#### MUST (Обязательно)
1. Storage writers **MUST NOT** использовать модуль `random`
2. Timestamps **MUST** передаваться из application слоя, не создаваться в infrastructure
3. Retry jitter **MUST** быть детерминистичным при `deterministic=True`
4. `PipelineContext.started_at` — единственный источник времени для batch

#### Архитектурные Тесты
| Тест | Цель | Файл |
|------|------|------|
| `test_no_random_in_writers` | Блокирует `random` в storage | `tests/architecture/` |
| `test_no_datetime_now_in_infrastructure` | Блокирует `datetime.now()` в infra | `tests/architecture/` |

#### Детерминистичный Jitter
```python
# RetryConfig (src/bioetl/infrastructure/adapters/http/client.py)
RetryConfig(
    deterministic=True,  # Hash-based jitter
    jitter_seed=42,      # Reproducible seed
)
```

При `deterministic=True` jitter вычисляется как:
```python
hash_input = f"{attempt}:{url}:{seed}"
jitter_factor = (hash(hash_input) % 1000) / 1000.0
```

#### Единый Источник Времени
```python
# Application layer создаёт timestamp
context = PipelineContext.create(run_id, run_type, logger)
# context.started_at используется во всех компонентах

# Infrastructure получает timestamp как параметр
await bronze_writer.write_bronze(..., ingestion_ts=context.started_at)
await quarantine.write(..., ingestion_ts=context.started_at)
```

### 4.4. Python Standards

#### 4.4.1. Future Annotations (PEP 563)
Все Python-файлы **MUST** начинаться с:

```python
from __future__ import annotations
```

**Причины:**
- Отложенная evaluation типов (производительность)
- Поддержка forward references без кавычек
- Совместимость с Python 3.10+ стилем типизации

**Проверка:** `ruff check --select FA` (Future Annotations rules).

**Расположение в файле:**
1. Shebang (если есть): `#!/usr/bin/env python`
2. Encoding declaration (если есть): `# -*- coding: utf-8 -*-`
3. Module docstring
4. `from __future__ import annotations`  ← сразу после docstring
5. Другие импорты

#### 4.4.2. Type Hints
- **MUST** использовать новый стиль типов: `list[str]` вместо `List[str]`
- **MUST** использовать `X | None` вместо `Optional[X]`
- **SHOULD** использовать `X | Y` вместо `Union[X, Y]`

## 5. Операции (Лимиты, Секреты, Shutdown) 
 
### 5.1. Ограничение скорости (Rate Limiting) 
Каждый адаптер обязан реализовать `TokenBucket` или аналог, соблюдающий лимиты провайдера. 
**Обратное давление (Backpressure)**: Если внутренняя очередь заполнена >80%, адаптер должен замедлить чтение (дросселировать источник). 
 
### 5.2. Управление Секретами 
- **Источник**: Переменные окружения (`os.environ`). 
- **Формат**: `BIOETL_{PROVIDER}_{KEY}` (например, `BIOETL_PUBCHEM_API_KEY`). 
- **Запрещено**: Хардкод секретов **MUST NOT**. Файлы `.env` в git **MUST NOT**. 
 
### 5.3. Graceful Shutdown (Штатное завершение)
См. [ADR-008](02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md).
При получении SIGTERM/SIGINT: 
1. Прекратить извлечение (fetch) новых записей. 
2. Дождаться завершения записи текущего батча. 
3. Сохранить чекпоинт в **S3** с использованием **If-Match / ETag** для обеспечения атомарности и предотвращения Lost Updates. 
4. Выйти с кодом 0. 

- **Guarantees**: Система гарантирует At-Least-Once доставку + Дедупликацию в Silver (через Content Hash). Гарантия Exactly-Once на уровне транспорта не требуется.
 
### 5.3.1. Восстановление из Чекпоинта (Checkpoint Recovery) 
При запуске пайплайн: 
1. Проверяет наличие чекпоинта в S3. 
2. Если найден и передан флаг `--resume`: 
   - Начинает с `last_processed_id + 1`. 
   - Логирует: `Resuming from checkpoint: {id}`. 
3. Если найден без флага: 
   - Warning: "Stale checkpoint detected. Use --resume or --ignore-checkpoint." 
4. После успешного завершения: удалить файл чекпоинта из S3.

### 5.3.2. Async Resource Cleanup
См. [ADR-013](02-architecture/decisions/ADR-013-async-storage-cleanup.md) и [ADR-015](02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md).

**Контракт `aclose()`:**
Все адаптеры и сервисы **MUST** реализовывать асинхронный метод `aclose()` для освобождения ресурсов:

```python
class MyAdapter:
    async def aclose(self) -> None:
        """Освобождение ресурсов.

        Идемпотентный — безопасен для повторных вызовов.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
```

**Требования:**
- **MUST** быть `async def` (асинхронный)
- **MUST** быть идемпотентным (безопасен для повторных вызовов)
- **MUST NOT** выбрасывать исключения
- **SHOULD** обнулять ссылки после закрытия (`self._client = None`)

**PipelineServices Lifecycle:**
```python
async with services:  # __aenter__ инициализирует ресурсы
    await runner.run()
# __aexit__ вызывает aclose() для всех компонентов
```

### 5.4. Политика Чувствительных Данных (Sensitive Data) 
- **Classification**: Public / Internal / Restricted. 
- **IAM**: Принцип Least Privilege. Разделение ролей `writer` (пайплайн) и `reader` (аналитик). 
- **Bronze**: Хранить как есть (Internal). 
- **Silver**: Хэшировать PII поля: `sha256(lowercase(value) + SALT)` (Restricted). **PII fields MUST be salted.**
- **Gold**: PII исключается или агрегируется (Public/Internal).

**Threat Model Scope**:
- В фокусе: Утечка PII через логи, SQL-инъекции, несанкционированный доступ к S3.
- Out of Scope: Физический доступ к серверам, компрометация AWS Root Account (управляемый сервис).
 
### 5.5. Disaster Recovery (DR) 
- **RPO**: 24 часа. 
- **RTO**: 4 часа. 
- **Game Days**: Game Days **SHOULD** проводиться ежегодно. Обязательные учения по восстановлению. Success criteria: данные идентичны, время < RTO. 
 
#### 5.5.1. Detailed DR Procedures (Runbook) 
| Сценарий | Действие | 
|----------|----------| 
| **Повреждение Bronze/Silver** | 1. Остановить пайплайны. 2. Восстановить S3 бакет из Backup (Point-in-Time Restore). 3. Перезапустить пайплайны с флагом `--full-rebuild` (если затронут Silver). | 
| **Потеря чекпоинта** | Запуск с `--ignore-checkpoint` (приведет к дубликатам в Bronze, но дедупликация в Silver исправит это). | 
| **Отказ региона AWS** | Переключение DNS на Failover Region. Развертывание Infrastructure-as-Code (Terraform) в резервном регионе. | 
 
### 5.6. Среды (Environments) 
- **Dev**: Локальная разработка (Docker Compose). Данные: фикстуры или сэмпл Bronze. 
- **Staging**: Полная копия архитектуры. Данные: Prod-like (обфусцированные). Тест деплоя. 
- **Prod**: Боевая среда. Доступ на запись только у CI/CD. 
 
### 5.6.1. Environment Isolation 
Изоляция ресурсов для предотвращения "Cross-Env Pollution". 
- **S3**: Разные бакеты (`bioetl-dev`, `bioetl-staging`, `bioetl-prod`). 
- **Redis**: Разные префиксы ключей или отдельные инстансы DB (`db0`, `db1`). 
- **Configs**: Строгое разделение переменных окружения. Доступ к Prod-секретам только у CI Runner. 
 
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
  1. PR с изменением Gold-схемы **MUST** иметь лейбл `breaking-change`. 
  2. CI генерирует diff схемы и постит в Slack-канал `#bioetl-contracts`. 
  3. Период депрекации: 2 недели до удаления поля. 
- **Consumer Tests**: Потребители могут подписаться на `contracts/` и запускать свои тесты при изменениях. 
 
### 7.2. Rollback Strategy 
- **Scope**: 
  - **Infrastructure/Code**: Auto Rollback при Error Rate > 10%. 
  - **Data DQ**: Ручной анализ и replay. Ошибки качества данных не должны триггерить автоматический откат версии приложения. 
- **Manual Rollback**: `make rollback VERSION=...`. 
 
## 8. Опыт Разработчика (Developer Experience) 
### 8.1. Локальная настройка 
```bash 
make install      # создание venv, установка зависимостей 
make test         # unit + integration (на кассетах) 
make lint         # ruff + mypy 
make run-local    # запуск сэмплового пайплайна на фикстурах 
``` 
### 8.2. Окружение

> **Note: Local-Only Deployment** (см. [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md))

**Текущая реализация (Local-Only):**
- **Storage**: Локальная файловая система (`data/bronze`, `data/silver`, `data/gold`)
- **Locking**: In-memory (`MemoryLock`)
- **Checkpoints**: Локальные файлы (`data/checkpoints`)
- **Зависимости**: Только Python 3.11+ и pip

**Для распределённого развёртывания (будущее):**
- Docker Compose: Postgres, Redis, MinIO
- Volumes: `./docker-data/`
- Reset: `make docker-reset`

- **Seed Data**: `make seed-local` — загрузка сэмпловых фикстур.
- **.env.example**: Шаблон переменных окружения (без секретов). 
 
--- 
## Приложение А: Источники и Библиотеки 
 
**Структура папок:** `src/bioetl/infrastructure/adapters/{provider}/` 
 
| Источник | Библиотека | Rate Limit | Retry Strategy | Auth Type | Health Check |
|----------|------------|------------|----------------|-----------|--------------|
| **ChEMBL** | `chembl_webresource_client` | Нет явного лимита | Exponential backoff | Public | `GET /chembl/api/data/status.json` |
| **PubChem** | `pubchempy` | 5 req/sec | 429 -> wait Retry-After | Public | Lightweight: `GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON` |
| **UniProt** | `unipressed` | 100 req/sec (c API key) | Exponential backoff | API Key | Lightweight Search Probe |
| **OpenAlex** | `pyalex` | 10 req/sec (polite pool) | 429 -> backoff | API Key (Email) | Generic Probe* |
| **Semantic** | `semanticscholar` | 100 req/5min | Sliding window | API Key | Generic Probe* |
| **PubMed** | `biopython` | 3 req/sec (10 c key) | 429 -> backoff | API Key | Generic Probe* |
| **Crossref** | `habanero` | 50 req/sec (polite pool) | Exponential backoff | Email | Generic Probe* |
| **GtoP** | `pyGtoP` (deprecated) | - | - | None | - |

\* **Generic Probe**: Lightweight GET-запрос к базовому endpoint API (e.g., root или `/status`). Если API не предоставляет dedicated health endpoint, использовать минимальный запрос данных с timeout 5 секунд.
 
**Health Check Endpoints**: 
- `GET /health` (Liveness) 
- `GET /ready` (Readiness: DB/Redis connection) 
 
## Приложение B: Политика Зависимостей 
- **Pinning**: Точные версии в `requirements.txt` / `pyproject.toml`. 
- **Обновления**: Ежемесячные PR от Dependabot + ручное ревью. 
- **Безопасность**: `pip-audit` в CI. Блокировка мержа при CVE severity >= HIGH. 
 
## Приложение C: Error Recovery Playbook (Runbook) 
 
### Уровни Серьезности (Severity Levels) 
| Level | Описание | SLA реакции | SLA восстановления | 
|-------|----------|-------------|--------------------| 
| **P0** | Система недоступна или критичные данные потеряны | 15 мин | 1 час | 
| **P1** | Падение критичного пайплайна (Core Data) | 1 час | 4 часа | 
| **P2** | Падение второстепенного пайплайна | 8 часов | 24 часа | 
| **P3** | Warning / DQ аномалии | 24 часа | Next Sprint | 
 
| Ошибка | Симптом | Действие | 
|--------|---------|----------| 
| Auth failure | `401 Unauthorized` в логах | Проверить/обновить `BIOETL_{PROVIDER}_API_KEY` | 
| Rate limit exhausted | `429` + пик `errors_total{type="recoverable"}` | Уменьшить `requests_per_second` в конфиге | 
| Schema mismatch (Gold) | Pipeline fail + `schema_violations` > 0 | Проверить изменения API; обновить Gold-схему через ADR | 
| Stale checkpoint | Warning при старте | `--resume` для продолжения или `--ignore-checkpoint` для рестарта | 
| >20% DQ errors | Batch fail | Проверить источник; возможно API вернул ошибку в теле ответа | 
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
    format: delta          # Использовать Delta Lake 
    mode: merge            # Стратегия Upsert 
    primary_key: [id]      # Ключ для merge 
    partition_by: [year, month] 
    classification: public 
    forensic_retention: false  # true = 30 days for Critical tables
    # Example for Critical table (Core Data):
    # forensic_retention: true 
 
  gold: 
    path: s3://bioetl/gold/chembl/activity_aggregated/ 
    format: delta 
    mode: overwrite        # Витрины часто перезаписываются целиком или партициями 
 
dq_rules: 
  soft_fail_threshold: 0.05  # 5% 
  hard_fail_threshold: 0.20  # 20% (Strict) 
 
circuit_breaker: 
  failure_threshold: 5 
  recovery_timeout: 300      # 5 min 
 
rate_limit: 
  requests_per_second: 5 
  burst: 10 
``` 
 
## Приложение E: Примеры Schema Evolution 
 
### Minor Change (Обратная совместимость) 
Добавление необязательного поля. Не требует пересчета истории. 
```json 
// Old Schema 
{"id": "CHEMBL1", "score": 0.9} 
 
// New Schema 
{"id": "CHEMBL1", "score": 0.9, "source": "manual"} 
``` 
 
### Major Change (Breaking) 
Переименование или изменение типа. Требует миграции данных или новой версии таблицы (v2). 
```json 
// Old Schema 
{"id": 123}  // int 
 
// New Schema 
{"id": "123"} // string 
``` 

### E.3. Field Deprecation Workflow
**Day 0**: Пометить поле deprecated в схеме
```yaml
fields:
  old_field:
    deprecated: true
    replacement: new_field
```

**Days 1-14**: Dual-write период
- Писать оба поля: `old_field` и `new_field`
- Потребители мигрируют чтение на `new_field`

**Day 15** (после 14-дневного периода): Удаление `old_field`
- Bump major version схемы
- ADR с обоснованием изменения
 
## Приложение F: Реестр Architecture Decision Records (ADR)

| ADR | Название | Статус | Дата |
|-----|----------|--------|------|
| [ADR-001](02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) | Delta Lake vs Parquet | Accepted | 2025-05 |
| [ADR-002](02-architecture/decisions/ADR-002-medallion-architecture.md) | Medallion Architecture | Accepted | 2025-05 |
| [ADR-003](02-architecture/decisions/ADR-003-redis-for-distributed-locking.md) | Redis for Distributed Locking | Superseded by ADR-010 | 2025-05 |
| [ADR-004](02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md) | Pydantic vs Dataclasses | Accepted | 2025-05 |
| [ADR-005](02-architecture/decisions/ADR-005-composition-layer-separation.md) | Composition Layer Separation | Accepted | 2025-12 |
| [ADR-006](02-architecture/decisions/ADR-006-logger-metrics-ports.md) | Logger and Metrics Ports | Accepted | 2025-12-18 |
| [ADR-007](02-architecture/decisions/ADR-007-circuit-breaker-implementation.md) | Circuit Breaker Implementation | Accepted | 2025-12-22 |
| [ADR-008](02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) | Graceful Shutdown Strategy | Accepted | 2025-12-22 |
| [ADR-009](02-architecture/decisions/ADR-009-paginated-fetcher-mixin.md) | PaginatedFetcherMixin Design | Accepted | 2025-12-22 |
| [ADR-010](02-architecture/decisions/ADR-010-local-only-deployment.md) | Local-Only Deployment | Accepted | 2025-12-23 |
| [ADR-011](02-architecture/decisions/ADR-011-remove-watermark-mechanism.md) | Remove Watermark Mechanism | Accepted | 2025-12-23 |
| [ADR-012](02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md) | Storage Clear Contract and Run ID | Accepted | 2025-12-23 |
| [ADR-013](02-architecture/decisions/ADR-013-async-storage-cleanup.md) | Async Storage Cleanup | Accepted | 2025-12-24 |
| [ADR-014](02-architecture/decisions/ADR-014-deterministic-writes.md) | Deterministic Writes and Retries | Accepted | 2025-12-24 |
| [ADR-015](02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md) | Pipeline Services Lifecycle | Accepted | 2025-12-24 |

## История Изменений (Changelog)
- **5.4** (2025-12-25): Architecture Documentation Update. Добавлены §1.1.2 (Health Check Protocol), §2.4.2 (Medallion Clear Policy), §4.4 (Python Standards), §5.3.2 (Async Cleanup). Реестр ADR расширен (011-015).
- **5.3** (2025-12-24): Determinism and Reproducibility (ADR-014). Добавлен §4.3 с правилами детерминизма. Архитектурные тесты для random и datetime.now().
- **5.2** (2025-12-23): Local-Only Deployment (ADR-010). Обновлены §3.3 и §8.2 для MemoryLock. ADR-003 superseded.
- **5.1** (2025-12-22): ADR additions (007-009), ADR index appendix.
- **5.0** (2025-12-15): Production Ready. Final Governance Polish, Circuit Breaker half-open observability, Backfill lock timeouts, Generic Health Probes, Deprecation clarification.
- **4.6** (2025-12-15): Governance & Stability. RFC 2119, Entity ID vs Content Hash, Bronze Lifecycle, Hard Limits, Threat Model. Added Log Schema, Provider Health Matrix, Circuit Breaker details, Backfill Locking, and Deprecation workflows.
- **4.5** (2025-05-20): Final Polish & Governance. Medallion Paths, DQ Levels, Observability, Fencing Tokens, Security IAM. 
- **4.4** (2025-05-20): Resilience & Operations. Circuit Breaker, DR Runbooks, Quarantine Ops, Env Isolation. 
- **4.3** (2025-05-20): Security & DR. Salted Hashes, RPO/RTO, Heartbeat Locks, Environments, Delta Infrastructure. 
- **4.2** (2025-05-20): Delta Lake Strategy, Unified Quarantine Schema, Threshold adjustments. 
- **4.1** (2025-05-20): [DEPRECATED] Storage Fixes. (Заменено версией 4.2). 
- **4.0** (2025-05-20): Data Contracts, Partitioning, Null Policy, Recovery Playbook. 
- **3.0** (2025-05-20): Lineage, Backfill, Concurrency, Graceful Shutdown, Dev Experience. 
- **2.0** (2025-05-20): Классификация ошибок, Medallion, Rate limiting, Перевод на русский. 
- **1.0** (2025-04-01): Черновик. 
2
