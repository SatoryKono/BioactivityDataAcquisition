# BioETL: Правила Проекта
*Версия: 5.1 (Audit Improvements), 2025-05-20*

## Глоссарий
- **Bronze/Silver/Gold**: уровни качества данных (Medallion Architecture).
- **Capability**: логически законченный набор портов и пайплайнов (например, "chemical activity ingestion"). Единица владения.
- **Port**: публичный интерфейс (Protocol) для инверсии зависимостей.
- **Adapter**: реализация Port для конкретного провайдера.
- **DAG**: Directed Acyclic Graph — модель зависимостей этапов пайплайна.
- **DLQ (Dead Letter Queue)**: Хранилище для изолированных записей, не прошедших валидацию, для последующего анализа.
- **Idempotency Key**: Уникальный ключ операции, гарантирующий, что повторное выполнение не создаст дублей.
- **Partition Pruning**: Оптимизация чтения, при которой движок сканирует только файлы, относящиеся к фильтру.

## 1. Архитектура и Слои
**Философия**: "Прагматичная инженерия". Архитектура диктует строгие ограничения (Negative Rules), чтобы гарантировать предсказуемость.
**Паттерн**: Слоистая архитектура с инверсией зависимостей (Ports & Adapters).

### 1.1. Ограничения Слоев (Negative Rules)
| Слой | Ответственность | **ЗАПРЕЩЕНО** |
|------|-----------------|---------------|
| **Domain** | Чистая логика, типы | I/O, `time.now()`, `random`, доступ к ENV, FS, Сети. |
| **Application** | Оркестрация, поток | Бизнес-валидация данных (это роль Domain), прямые вызовы БД (минуя Port). |
| **Infrastructure** | Реализация адаптеров | Агрегация данных, семантическая логика, бизнес-правила. |

### 1.2. Стабильность Портов
- **Port = Публичный Контракт**. Изменение сигнатуры = Major Version bump.
- **Совместимость**: Адаптеры обязаны поддерживать текущую (N) и предыдущую (N-1) версии порта при миграции.

## 2. Поток Данных и Стратегия Medallion

### 2.1. Хранение и Форматы
| Уровень | Формат | Стратегия Записи | Комментарий |
|---------|--------|------------------|-------------|
| **Bronze** (Raw) | **JSONL + zstd** | Append-Only | CSV запрещен (хрупок). Использовать Idempotency Key (ETag/Hash) для дедупликации файлов. |
| **Silver** (Norm) | **Delta Lake** / Parquet | **Merge (Upsert)** или Append+Compaction | Delta Lake предпочтительнее для атомарных upsert. Если чистый Parquet — Append only + логическая дедупликация (`rank()`). |
| **Gold** (Curated) | **Delta Lake** / Parquet | Overwrite / Upsert | Строгая схема. |

### 2.2. Готовность Данных (Data Readiness) и SLA
| Статус | Уровень | Критерий Готовности | SLA (Пример) |
|--------|---------|---------------------|--------------|
| **raw_available** | **Bronze** | Fetch завершён, файл сохранен | Latency: <1h, Completeness: >99% |
| **validated** | **Silver** | Пройдена схема + DQ пороги | Validity: 100% compliant rows |
| **published** | **Gold** | Контракт соблюден + Freshness OK | Freshness: <24h, Stability: 0 breaking changes |

### 2.3. Политика Дрейфа Схемы (Schema Drift)
| Тип Дрейфа | Описание | Действие Системы |
|------------|----------|------------------|
| **Additive** | Новое поле | **Continue** (Silver добавляет колонку, warning в лог). |
| **Mutative** | Изменение типа/семантики | **Fail** (Silver), создание Issue в Jira/GitHub. |
| **Destructive** | Удаление поля | **Fail** (если поле required), **Warn** (если optional). |

### 2.4. Data Lineage (Происхождение)
Обязательный набор метаданных lineage:
- **Record Lineage**: `_source_file`, `_source_record_id`.
- **Pipeline Lineage**: `_pipeline_run_id`, `_parent_run_ids` (список ID предыдущих этапов).
- **Versioning**: `_transform_version`, `_schema_version`.

### 2.5. Политика Backfill / Replay
#### Классы Риска Backfill
| Класс | Риск | Процедура Запуска |
|-------|------|-------------------|
| **A** | Низкий | **Auto**. Запускается оператором без согласования. |
| **B** | Средний | **Manual Approval**. Требует ревью плана (Impact Analysis). |
| **C** | Высокий | **Freeze**. Требует Change Window и остановки потребителей. |

- **Diff Metrics**: Любой backfill обязан публиковать метрики изменений: `delta_record_count`, `delta_null_rate`.

### 2.6. Политика NULL и Пропущенных Значений
| Состояние | Представление |
|-----------|---------------|
| Значение отсутствует | `NULL` |
| Пустая строка | `""` |
| Числовой NaN | `NaN` (разрешен для float, native Pandas/Polars) |
| Строковый "NaN" | **Запрещен** (преобразовывать в NULL) |
| Sentinel (-1, 9999) | **Запрещены** |

### 2.7. Генерация ID и Стабильность
- **Стратегия**: Использовать **UUIDv5** (DNS namespace), если источник не дает стабильного ID.
- **Immutable IDs**: Entity ID никогда не переиспользуется.
- **Versioning**: Изменение логики генерации ID считается Breaking Change и требует инкремента `_id_strategy_version`.

## 3. Обработка Ошибок, DQ и SLO

### 3.1. Стратегия DLQ (Dead Letter Queue)
Вместо удаления ("Log + Drop") используется карантин.
- **Маршрутизация**: Записи, не прошедшие валидацию, отправляются в `s3://bioetl/quarantine/{pipeline}/`.
- **Формат**: Оригинальный payload (JSON) + Метаданные ошибки (`error_code`, `timestamp`, `pipeline_version`).
- **Reprocessing**: Инструментарий (скрипт/job) для вычитывания DLQ, исправления и повторной подачи в пайплайн.

### 3.2. Пороги DQ
| Тип | Порог (Threshold) | Действие |
|-----|-------------------|----------|
| **Soft** | >10% DQ ошибок | Warning, алерт + запись ошибочных в DLQ. |
| **Hard** | >50% DQ ошибок | Fail Batch, весь батч не пишется в Silver (транзакционно). |

### 3.3. Бюджет Ошибок
Вводится понятие **Error Budget** на пайплайн.
- **Degraded Mode**: При превышении бюджета recoverable-ошибок система переходит в режим деградации (снижение частоты запросов, частичная загрузка).

## 4. Наблюдаемость (Observability) как Gate
**CI/CD Gate**: Merge Request блокируется, если:
1. В коде нет отправки метрик.
2. Отсутствует `trace_id` в логах.
3. Не определен `dataset_id`.

**Метрики**: Обязателен breakdown задержек по стадиям (Latency Breakdown).

## 5. Безопасность и Классификация Данных

### 5.1. Уровни Доступа (Data Classification)
| Уровень | Описание | Требования к Хранению |
|---------|----------|-----------------------|
| **Public** | Открытые данные | Стандартный доступ. |
| **Internal** | Внутренние технические поля | Доступ только сотрудникам. |
| **Sensitive** | PII, IP, коммерческая тайна | Хэширование с солью: `sha256(val + SALT)`. |
| **Restricted** | Ключи, пароли | Отдельные бакеты, строгий IAM, Audit Log. |

### 5.2. Управление Секретами
- **Запрещено**: `.env` в репозитории, хардкод.
- **Обязательно**: Использование Vault/Secrets Manager.
- **Crypto-shredding**: (Roadmap v5.0+) Удаление ключа шифрования для реализации "Права на забвение".

## 6. Конфигурация, Состояние и Жизненный Цикл

### 6.1. Управление Состоянием (Checkpoints)
- **Commit-Log Pattern**: Чекпоинт сохраняется после *успешной* записи каждого батча (или группы).
- **Атомарность**: Запись чекпоинта строго после подтверждения записи данных (S3 200 OK).
- **Восстановление**: При старте читать последний commit-offset.

### 6.2. Блокировки (Locks)
- **Heartbeat**: Воркер обязан обновлять TTL блокировки (например, каждые 5 мин).
- **Expiration**: Блокировка считается "зомби" и снимается, если Heartbeat просрочен (TTL expired), а не по фиксированному таймауту 2ч.

### 6.3. Конфиг = Контракт
YAML-конфиг версионируется и валидируется схемой. Конфиг неизменяем после деплоя.

## 7. CI/CD Политики и Гейты (Gates)
CI/CD — это набор обязательных правил.

**Обязательные CI Gates**:
1. **Schema Diff Check**: Проверка изменений контрактов.
2. **Contract Tests**: Успешное прохождение тестов.
3. **DQ Baseline Check**: Сравнение DQ метрик.
4. **Security Scan**: `pip-audit`, проверка контейнеров.

**Тестирование VCR**:
- Локально разрешено: `--vcr-mode=new_episodes`.
- CI: Строго `--vcr-mode=none` (или `once` с fail on missing).

## 8. Опыт Разработчика (DevEx)
### 8.1. Стек Технологий (Stack 2025)
- **Processing**: **Polars** (предпочтительно) вместо Pandas для Lazy evaluation и перформанса.
- **Validation**: **Pydantic v2** для моделей и конфигов.
- **Format**: JSONL (Bronze), Delta/Parquet (Silver+).

### 8.2. Локальная настройка
```bash
make install      # venv, dependencies
make test         # unit + integration + contract
make lint         # ruff + mypy + security check
make run-local    # sample pipeline
```

---
## Приложение А: Источники и Библиотеки

**Структура папок:** `src/bioetl/infrastructure/adapters/{provider}/`

| Источник | Библиотека | Rate Limit | Retry Strategy |
|----------|------------|------------|----------------|
| **ChEMBL** | `chembl_webresource_client` | Нет явного лимита | Exponential backoff |
| **PubChem** | `pubchempy` | 5 req/sec | 429 -> wait Retry-After |
| **UniProt** | `unipressed` | 100 req/sec | Exponential backoff |
| **OpenAlex** | `pyalex` | 10 req/sec | 429 -> backoff |
| **Semantic** | `semanticscholar` | 100 req/5min | Sliding window |
| **PubMed** | `biopython` | 3 req/sec | 429 -> backoff |
| **Crossref** | `habanero` | 50 req/sec | Exponential backoff |

## История Изменений (Changelog)
- **5.1** (2025-05-20): Audit Improvements. Delta Lake, DLQ, Commit-Log checkpoints, Heartbeat locks, PII Salting, Polars, UUIDv5.
- **5.0** (2025-05-20): Enterprise Operational. Gates, Readiness, Backfill Classes, Negative Rules.
- **4.0** (2025-05-20): Contracts, Partitioning, Null Policy.
- **3.0** (2025-05-20): Lineage, Backfill, Concurrency.
- **2.0** (2025-05-20): Перевод и базовые политики.
