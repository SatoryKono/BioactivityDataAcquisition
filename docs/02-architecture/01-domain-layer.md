# Слой Domain (Домен)

**Расположение:** `src/bioetl/domain/`

## 1. Назначение

Слой `Domain` — это ядро системы, содержащее чистую бизнес-логику и правила. Он не зависит ни от каких других слоёв и не содержит кода, связанного с вводом-выводом (I/O), базами данных, веб-фреймворками или другими инфраструктурными деталями.

**Ключевые характеристики:**
- **Чистота:** Только Python-объекты и чистые функции.
- **Независимость:** Не импортирует модули из `application`, `infrastructure` или `interfaces`.
- **Стабильность:** Изменяется только при изменении бизнес-правил, а не технических деталей.

## 2. Ключевые Компоненты

### 2.1. `ports/` — Пакет Портов (Контракты)

**Расположение:** `src/bioetl/domain/ports/`

Этот пакет является краеугольным камнем архитектуры **Ports & Adapters**. Он определяет интерфейсы (через `typing.Protocol`), которые должны реализовывать адаптеры из слоя `Infrastructure`.

**Структура пакета (26 файлов):**

Пакет содержит 26 protocol-файлов, организованных по категориям:

**Основные порты:**
- `DataSourcePort`, `FilterableDataSourcePort` — абстракция для источников данных
- `StoragePort` — хранилища данных (Bronze, Silver, Gold)
- `LockPort` — распределённые блокировки
- `CheckpointPort` — сохранение/загрузка состояния пайплайнов
- `QuarantinePort` — карантин записей, не прошедших валидацию

**Observability порты:**
- `MetricsPort` — сбор метрик
- `TracingPort` — распределённый трейсинг (OpenTelemetry)
- `LoggerPort` — структурированное логирование
- `DQMonitorPort` — Data Quality мониторинг
- `PipelineObserverPort` — наблюдение за пайплайнами

**Data Quality порты:**
- `BronzeDQAnalyzerPort`, `SilverDQAnalyzerPort`, `GoldDQAnalyzerPort` — DQ анализ по слоям
- `DQReportWriterPort` — запись DQ-отчётов
- `GoldValidatorPort` — валидация Gold-записей

**Input/Output порты:**
- `InputFilterPort` — загрузка filter IDs
- `ExportPort` — экспорт данных

**Infrastructure порты:**
- `HealthCheckPort` — проверка здоровья адаптеров
- `AuditPort` — аудит операций
- `RetentionPort` — управление политиками хранения

**Правило импорта (MUST):**
```python
# ✅ Правильно — из фасада:
from bioetl.domain.ports import StoragePort, LockPort

# ❌ Неправильно — из внутренних модулей:
from bioetl.domain.ports.storage import StoragePort  # Запрещено!
```

Это правило проверяется архитектурным тестом `test_ports_imported_only_from_facade`.

### 2.2. `aggregates/` — DDD Aggregates

**Расположение:** `src/bioetl/domain/aggregates/`

Пакет содержит DDD-агрегаты с защищёнными инвариантами и доменными событиями.
См. [ADR-021: DDD Aggregates](decisions/ADR-021-ddd-aggregates-adoption.md).

**Структура:**
```
src/bioetl/domain/aggregates/
├── __init__.py
├── batch.py             # Batch Aggregate (530 LOC)
├── pipeline_run.py      # PipelineRun Aggregate (566 LOC)
├── quarantine_entry.py  # QuarantineEntry Aggregate (517 LOC)
└── events.py            # Domain Events (260 LOC)
```

**Ключевые агрегаты:**

| Aggregate | Инварианты | State Machine |
|-----------|------------|---------------|
| `Batch` | Records sealed before write; sequential indices | OPEN → SEALED → WRITING → COMMITTED/FAILED |
| `PipelineRun` | COMPLETED only if all stages SUCCESS | PENDING → RUNNING → COMPLETED/FAILED/SHUTDOWN |
| `QuarantineEntry` | Atomic retry increment | PENDING → RETRYING → RECOVERED/DEAD_LETTER |

**Пример использования:**
```python
from bioetl.domain.aggregates import Batch
from bioetl.domain.types import RunID

batch = Batch.create(run_id=RunID(uuid4()))
batch.add_record({"id": "1", "value": 100})
batch.seal()
batch.mark_writing()
batch.mark_committed("silver")

events = batch.collect_events()  # [BatchCreated, BatchSealed, BatchWritten]
```

### 2.3. `value_objects/` — Value Objects

**Расположение:** `src/bioetl/domain/value_objects/`

Неизменяемые доменные примитивы с типобезопасностью (19 файлов).

**Идентификаторы:**
- `RunID(UUID)` — идентификатор запуска пайплайна
- `BatchID(UUID)` — идентификатор batch
- `EntityID(str)` — бизнес-ключ сущности
- `ContentHash(str)` — SHA256 хэш содержимого

**Измерения:**
- `ActivityValue(value, unit, relation)` (`activity.py`, 329 LOC) — составной value object для биоактивности (IC50, EC50, Ki), включает `RelationOperator` enum и `ConfidenceScore`

**Data Quality:**
- `DQMetrics` — метрики качества данных
- `DQReport` — отчёт о качестве данных

**Pipeline Results:**
- `BronzeResult` — результат записи в Bronze
- `Publications` — value objects для публикаций
- `ActivityValues` — concentration & unit handling

### 2.4. `types.py` — Пользовательские Типы

**Источник:** `src/bioetl/domain/types.py`

Определяет простые и составные типы данных, используемые во всей системе для обеспечения консистентности и семантической ясности. Включает типизированные идентификаторы: `RunID`, `BatchID`, `EntityID`, `ContentHash`.

### 2.5. `config.py` — Конфигурационные Value Objects

**Источник:** `src/bioetl/domain/config.py`

Содержит dataclass Value Objects для конфигурации пайплайнов:
- `PipelineConfig` — полная конфигурация пайплайна
- `RuntimeConfig` — параметры выполнения
- `DQConfig` — пороги Data Quality
- `TableConfig` — настройки таблиц

### 2.6. `error_classifier.py` — Классификатор Ошибок

**Источник:** `src/bioetl/domain/error_classifier.py`

Реализует логику классификации ошибок в соответствии с правилами из `RULES.md` (раздел 3.1.1):
- **Critical**: Ошибки, останавливающие пайплайн.
- **Recoverable**: Временные сбои, требующие повторной попытки.
- **Data Quality**: Проблемы с данными, которые можно пропустить, отправив запись в карантин.

### 2.7. Дополнительные поддиректории

Domain содержит 8 дополнительных поддиректорий:

| Директория | Назначение | Содержание |
|------------|------------|------------|
| `composite/` | Composite pipeline domain | Field groups, state, strategy |
| `configs/` | Конфигурационные базовые классы | Базовые dataclass-ы для конфигураций |
| `contracts/gold/` | Gold-слой контракты данных | Pandera DataFrameModel схемы |
| `entities/` | Доменные сущности | Entity-классы для каждого провайдера |
| `exceptions/` | Доменные исключения | 5 файлов с иерархией ошибок |
| `filtering/` | Фильтрация данных | Конфигурации и логика фильтров |
| `mapping/` | Маппинг полей публикаций | Publication field & type mappings |
| `models/` | Доменные модели | Filter & metadata models |
| `registry/` | Реестр публикаций | Publication registry |
| `schemas/` | Pydantic/Pandera схемы | ~60 файлов для всех провайдеров |
| `services/` | Доменные сервисы | Нормализация, агрегация |

## 3. Принципы Работы

- **Никакого I/O:** В этом слое запрещены любые операции, связанные с сетью, файловой системой или базами данных.
- **Валидация данных:** Логика валидации бизнес-сущностей (например, проверка SMILES-строк) может находиться здесь, если она не требует внешних зависимостей.
- **Иммутабельность:** Предпочтение отдаётся иммутабельным структурам данных (например, `NamedTuple`, `dataclasses(frozen=True)`).

---

## 4. Связанные Материалы

### Навигация по Слоям

| ← Предыдущий | Текущий | Следующий → |
|--------------|---------|-------------|
| — | **Domain** | [Application Layer](02-application-layer.md) |

### Связанные Диаграммы

| Диаграмма | Файл | Описание |
|-----------|------|----------|
| Domain Layer Classes | [04-domain-layer-class-diagram.mermaid](diagrams/04-domain-layer-class-diagram.mermaid) | Классы портов, сущностей, конфигурации |
| Domain DDD | [08-domain-ddd.mermaid](diagrams/08-domain-ddd.mermaid) | DDD-структура домена |
| Domain Models | [13-domain-models-relationship.mermaid](diagrams/13-domain-models-relationship.mermaid) | Связи доменных моделей |
| DDD Aggregates | [diagrams/mermaid/09_ddd_aggregates.mmd](diagrams/mermaid/09_ddd_aggregates.mmd) | DDD агрегаты: Batch, PipelineRun, QuarantineEntry |
| Ports Architecture | [diagrams/mermaid/07_ports_architecture.mmd](diagrams/mermaid/07_ports_architecture.mmd) | Архитектура 26 портов |

### Связанные ADR

| ADR | Тема |
|-----|------|
| [ADR-004](decisions/ADR-004-pydantic-vs-dataclasses.md) | Pydantic vs Dataclasses — выбор dataclasses |
| [ADR-021](decisions/ADR-021-ddd-aggregates-adoption.md) | DDD Aggregates — внедрение агрегатов |

### Смежные Разделы Документации

- [RULES.md §1 "Архитектура и Слои"](../RULES.md) — матрица импортов, правила слоёв
- [API Reference: Domain](../04-reference/api/domain.md) — API документация слоя
- [Glossary](../glossary.md) — терминология Ubiquitous Language
