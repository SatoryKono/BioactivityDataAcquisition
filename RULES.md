# BioETL: Правила Проекта
*Версия: 5.0 (Enterprise Operational), 2025-05-20*

## Глоссарий
- **Bronze/Silver/Gold**: уровни качества данных (Medallion Architecture).
- **Capability**: логически законченный набор портов и пайплайнов (например, "chemical activity ingestion"). Единица владения.
- **Port**: публичный интерфейс (Protocol) для инверсии зависимостей.
- **Adapter**: реализация Port для конкретного провайдера.
- **DAG**: Directed Acyclic Graph — модель зависимостей этапов пайплайна.

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

### 2.1. Готовность Данных (Data Readiness) и SLA
| Статус | Уровень | Критерий Готовности | SLA (Пример) |
|--------|---------|---------------------|--------------|
| **raw_available** | **Bronze** | Fetch завершён, файл сохранен | Latency: <1h, Completeness: >99% |
| **validated** | **Silver** | Пройдена схема + DQ пороги | Validity: 100% compliant rows |
| **published** | **Gold** | Контракт соблюден + Freshness OK | Freshness: <24h, Stability: 0 breaking changes |

*Запрещено прямое потребление Silver внешними системами без явного контракта.*

### 2.2. Политика Дрейфа Схемы (Schema Drift)
| Тип Дрейфа | Описание | Действие Системы |
|------------|----------|------------------|
| **Additive** | Новое поле | **Continue** (Silver добавляет колонку, warning в лог). |
| **Mutative** | Изменение типа/семантики | **Fail** (Silver), создание Issue в Jira/GitHub. |
| **Destructive** | Удаление поля | **Fail** (если поле required), **Warn** (если optional). |

### 2.3. Data Lineage (Происхождение)
Обязательный набор метаданных lineage:
- **Record Lineage**: `_source_file`, `_source_record_id`.
- **Pipeline Lineage**: `_pipeline_run_id`, `_parent_run_ids` (список ID предыдущих этапов).
- **Versioning**: `_transform_version`, `_schema_version`.

### 2.4. Политика Backfill / Replay
#### Классы Риска Backfill
| Класс | Риск | Процедура Запуска |
|-------|------|-------------------|
| **A** | Низкий | **Auto**. Запускается оператором без согласования. |
| **B** | Средний | **Manual Approval**. Требует ревью плана (Impact Analysis). |
| **C** | Высокий | **Freeze**. Требует Change Window и остановки потребителей. |

- **Diff Metrics**: Любой backfill обязан публиковать метрики изменений: `delta_record_count`, `delta_null_rate`.

### 2.5. Стратегия Партиционирования
| Уровень | Стратегия партиционирования | Пример |
|---------|----------------------------|--------|
| **Bronze** | По `ingestion_date` (YYYY-MM-DD) | `bronze/chembl/activity/2025-05-20/` |
| **Silver** | По `source_date` или `entity_type` | `silver/chembl/activity/year=2025/month=05/` |
| **Gold** | По use-case (часто по `target_id` или `date`) | `gold/activity_by_target/target_id=CHEMBL123/` |

### 2.6. Генерация ID и Стабильность
- **Immutable IDs**: Entity ID никогда не переиспользуется для другой сущности.
- **Versioning**: Изменение логики генерации ID считается Breaking Change и требует инкремента `_id_strategy_version`.

## 3. Обработка Ошибок, DQ и SLO

### 3.1. Классификация и Бюджет Ошибок
Вводится понятие **Error Budget** на пайплайн.
- **Degraded Mode**: При превышении бюджета recoverable-ошибок система переходит в режим деградации (снижение частоты запросов, частичная загрузка) вместо полного падения.

### 3.2. Пороги DQ
| Тип | Порог (Threshold) | Действие |
|-----|-------------------|----------|
| **Soft** | >10% DQ ошибок | Warning, алерт инженерам. |
| **Hard** | >50% DQ ошибок | Fail Batch, блокировка записи в Silver. |

## 4. Наблюдаемость (Observability) как Gate
**CI/CD Gate**: Merge Request блокируется, если:
1. В коде нет отправки метрик.
2. Отсутствует `trace_id` в логах.
3. Не определен `dataset_id`.

**Метрики**: Обязателен breakdown задержек по стадиям (Latency Breakdown): `extract_duration`, `transform_duration`, `load_duration`.

## 5. Безопасность и Классификация Данных

### 5.1. Уровни Доступа (Data Classification)
| Уровень | Описание | Требования к Хранению |
|---------|----------|-----------------------|
| **Public** | Открытые данные | Стандартный доступ. |
| **Internal** | Внутренние технические поля | Доступ только сотрудникам. |
| **Sensitive** | PII, IP, коммерческая тайна | Хэширование, шифрование at-rest. |
| **Restricted** | Ключи, пароли | Отдельные бакеты, строгий IAM, Audit Log. |

### 5.2. Управление Секретами
- **Запрещено**: `.env` в репозитории, хардкод.
- **Обязательно**: Использование Vault/Secrets Manager.

## 6. CI/CD Политики и Гейты (Gates)
CI/CD — это набор обязательных правил, а не рекомендаций. Без прохождения гейтов деплой невозможен.

**Обязательные CI Gates**:
1. **Schema Diff Check**: Проверка изменений контрактов (additive/mutative).
2. **Contract Tests**: Успешное прохождение тестов потребителей.
3. **DQ Baseline Check**: Сравнение DQ метрик с исторической базой.
4. **Security Scan**: `pip-audit`, проверка контейнеров и кода (SAST).

## 7. Конфигурация и Жизненный Цикл
- **Конфиг = Контракт**: YAML-конфиг версионируется и валидируется схемой.
- **Immutability**: Конфиг неизменяем после деплоя. Любое изменение = новый `pipeline_revision`.

## 8. Документация и Управление Изменениями
- **Artifact**: Документация версионируется вместе с кодом.
- **Traceability**: Каждая версия пайплайна в доках указывает: `schema_version`, `transform_version`, `deprecation_plan`.

### 8.1. Контракты Данных (Data Contracts)
- **Реестр**: Gold-схемы в `docs/contracts/`.
- **Notification**: Автоматическое уведомление в Slack при Breaking Change.

## 9. Опыт Разработчика (DevEx)
### 9.1. Локальная настройка
```bash
make install      # venv, dependencies
make test         # unit + integration + contract
make lint         # ruff + mypy + security check
make run-local    # sample pipeline
```
### 9.2. Docker
- `make docker-reset`: Очистка volumes.
- `make seed-local`: Загрузка фикстур.

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

## Приложение B: Конфигурация (Пример)
```yaml
pipeline:
  name: chembl_activity
  version: "1.2.0"
  capability: "chemical_activity_ingestion"

source:
  type: api
  load_strategy: incremental

sink:
  silver:
    path: s3://bioetl/silver/chembl/
    partition_by: [year, month]
    classification: public

dq_rules:
  soft_fail_threshold: 0.1
  hard_fail_threshold: 0.5
```

## История Изменений (Changelog)
- **5.0** (2025-05-20): Enterprise Operational. Добавлены CI Gates, Data Readiness, Backfill Classes, Negative Rules, Security Classification.
- **4.0** (2025-05-20): Data Contracts, Partitioning, Null Policy, Recovery Playbook.
- **3.0** (2025-05-20): Lineage, Backfill, Concurrency.
- **2.0** (2025-05-20): Перевод и базовые политики.
