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

**Структура пакета:**
```
src/bioetl/domain/ports/
├── __init__.py          # Фасад — единая точка импорта всех портов
├── data_source.py       # DataSourcePort, FilterableDataSourcePort
├── storage.py           # StoragePort
├── locking.py           # LockPort
├── checkpoint.py        # CheckpointPort
├── quarantine.py        # QuarantinePort
├── observability.py     # MetricsPort, TracingPort, LoggerPort, DQMonitorPort
├── validation.py        # GoldValidatorPort
└── filtering.py         # InputFilterPort
```

**Основные порты (12 шт):**
- `DataSourcePort`: Абстракция для источников данных (API, файлы).
- `FilterableDataSourcePort`: Расширение с server-side фильтрацией.
- `StoragePort`: Абстракция для хранилищ данных (Bronze, Silver, Gold).
- `LockPort`: Контракт для распределённых блокировок.
- `CheckpointPort`: Интерфейс для сохранения и загрузки состояния пайплайнов.
- `QuarantinePort`: Контракт для "карантина" — хранилища записей, не прошедших валидацию.
- `MetricsPort`: Интерфейс для сбора метрик.
- `TracingPort`: Распределённый трейсинг (OpenTelemetry).
- `LoggerPort`: Структурированное логирование.
- `DQMonitorPort`: Data Quality мониторинг.
- `GoldValidatorPort`: Валидация Gold-записей.
- `InputFilterPort`: Загрузка filter IDs.

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
├── pipeline_run.py      # PipelineRun Aggregate (350 LOC)
├── quarantine_entry.py  # QuarantineEntry Aggregate (180 LOC)
└── events.py            # Domain Events (200 LOC)
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

Неизменяемые доменные примитивы с типобезопасностью.

**Идентификаторы:**
- `RunID(UUID)` — идентификатор запуска пайплайна
- `BatchID(UUID)` — идентификатор batch
- `EntityID(str)` — бизнес-ключ сущности
- `ContentHash(str)` — SHA256 хэш содержимого

**Измерения:**
- `Measurement(value, unit, relation)` — биоактивность (IC50, EC50, Ki)

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

## 3. Принципы Работы

- **Никакого I/O:** В этом слое запрещены любые операции, связанные с сетью, файловой системой или базами данных.
- **Валидация данных:** Логика валидации бизнес-сущностей (например, проверка SMILES-строк) может находиться здесь, если она не требует внешних зависимостей.
- **Иммутабельность:** Предпочтение отдаётся иммутабельным структурам данных (например, `NamedTuple`, `dataclasses(frozen=True)`).
