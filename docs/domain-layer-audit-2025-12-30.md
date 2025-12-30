# Аудит Domain-слоя BioETL

**Дата:** 2025-12-30
**Версия:** 1.0
**Автор:** Claude Code Audit

---

## 1. Краткий Обзор Архитектуры

### 1.1. Структура Domain-слоя

```
src/bioetl/domain/ (102 файла, ~15К строк)
├── aggregates/     # 4 файла: PipelineRun, Batch, QuarantineEntry, events
├── configs/        # 2 файла: базовые конфигурации (RateLimitConfig, BaseProviderConfig)
├── entities/       # 12 файлов: DTOs (Pydantic) + Domain Entities (dataclass)
├── exceptions/     # 6 файлов: иерархия исключений
├── filtering/      # фильтрация Gold-слоя
├── ports/          # 14 файлов: Protocol-интерфейсы (34 порта)
├── schemas/        # 23 файла: Pandera-схемы для валидации DataFrame
├── services/       # 6 файлов: доменные сервисы
├── value_objects/  # 6 файлов: Value Objects (ChemblId, DOI, Concentration и т.д.)
└── *.py            # 10 корневых файлов (types, config, context, transformations и др.)
```

### 1.2. Основные Агрегаты

| Агрегат | Строк | Инварианты | Состояние |
|---------|-------|------------|-----------|
| `PipelineRun` | 561 | 5 инвариантов, state machine | ✅ Хорошо структурирован |
| `Batch` | 533 | 5 инвариантов, lifecycle | ✅ Хорошо структурирован |
| `QuarantineEntry` | 513 | 5 инвариантов, resolution flow | ✅ Хорошо структурирован |

### 1.3. Паттерн DTO + Entity

Проект использует **двойной паттерн** для каждого домена:
- **DTO (Pydantic)**: `ActivityRecord`, `MoleculeRecord` — для API-границ, `extra='forbid'`
- **Domain Entity (dataclass)**: `Bioactivity`, `Molecule` — с lineage полями (`run_id`, `content_hash`)

Это **осознанное архитектурное решение**, а не дублирование.

---

## 2. Выявленные Проблемы

### 2.1. Семантическое Пересечение Имён (ВЫСОКИЙ)

| Проблема | Файлы | Описание |
|----------|-------|----------|
| **DQStatus дублирование** | `types.py:272`, `value_objects/dq_result.py:17` | Два enum с **одинаковым именем**, но **разной семантикой**: (1) статус карантина (NEW, IGNORED, REPROCESSED) vs (2) результат DQ-оценки (PASSED, WARNING, FAILED) |
| **QuarantineStatus vs DQStatus** | `aggregates/quarantine_entry.py:28`, `types.py:272` | Оба описывают статус карантина, но с разными значениями. `QuarantineStatus` богаче (добавляет UNDER_REVIEW, EXPIRED) |

**Ссылки на код:**
- `domain/types.py:272-282` — `DQStatus` для карантина
- `domain/value_objects/dq_result.py:17-30` — `DQStatus` для DQ-оценки
- `domain/aggregates/quarantine_entry.py:28-56` — `QuarantineStatus`

### 2.2. Неиспользуемые Доменные Сервисы (СРЕДНИЙ)

| Сервис | Строк | Используется в Application/Infrastructure |
|--------|-------|-------------------------------------------|
| `NormalizationService` | 385 | ❌ Нет |
| `ActivityAggregator` | 359 | ❌ Нет |
| `ValueValidator` | 296 | ❌ Нет |
| `UnitConverter` | 221 | ❌ Нет |
| `IdentityService` | 222 | ✅ Да (активно) |

**Верификация:**
```bash
grep -r "NormalizationService\|ActivityAggregator" src/bioetl/application/  # 0 matches
grep -r "NormalizationService\|ActivityAggregator" src/bioetl/infrastructure/  # 0 matches
```

Сервисы покрыты тестами (`tests/unit/domain/services/`), но не интегрированы в пайплайны.

### 2.3. Pandera-схемы Используются Только в Тестах (НИЗКИЙ)

| Директория | Файлов | Использование |
|------------|--------|---------------|
| `schemas/chembl/` | 13 | Только в `tests/unit/infrastructure/schemas/test_silver.py` |
| `schemas/crossref/` | 6 | Только в тестах |
| `schemas/pubchem/` | 1 | Только в тестах |
| `schemas/pubmed/` | 1 | Только в тестах |
| `schemas/uniprot/` | 2 | Только в тестах |

**Статус:** Это не критично — схемы используются для валидации в тестах, что является валидным паттерном.

### 2.4. Deprecated Alias `Work` (НИЗКИЙ)

**Файл:** `domain/entities/crossref.py:223-241`

```python
class Work(PublicationEntity, metaclass=_WorkMeta):
    """Deprecated alias for PublicationEntity."""
```

Используется только в экспортах, не в продакшн-коде.

---

## 3. Анализ Соответствия DDD

### 3.1. Что Реализовано Хорошо ✅

| Аспект | Оценка | Обоснование |
|--------|--------|-------------|
| **Aggregate Roots** | ✅ Отлично | `PipelineRun`, `Batch`, `QuarantineEntry` — чёткие границы, инварианты, state machines |
| **Value Objects** | ✅ Хорошо | `ChemblId`, `DOI`, `UniProtId`, `PChemblValue` — с валидацией и нормализацией |
| **Domain Events** | ✅ Хорошо | `PipelineCompleted`, `BatchSealed`, `RecordQuarantined` — все агрегаты эмитят события |
| **Ports (Protocols)** | ✅ Отлично | 34 порта, все `@runtime_checkable`, чёткое разделение ответственностей |
| **Иммутабельность** | ✅ Отлично | `frozen=True`, `slots=True` везде в entities и value objects |
| **Layered Architecture** | ✅ Отлично | Нет импортов из infrastructure в domain (проверяется `import-linter`) |

### 3.2. Нарушения DDD

| Нарушение | Серьёзность | Описание |
|-----------|-------------|----------|
| **Неконсистентность Ubiquitous Language** | Средняя | `DQStatus` означает разное в разных контекстах |
| **Unused Domain Services** | Средняя | Сервисы существуют, но не интегрированы в пайплайны |
| **Избыточность статусов карантина** | Низкая | `DQStatus` в types.py vs `QuarantineStatus` в aggregates |

### 3.3. Границы Bounded Contexts

Проект имеет **неявные bounded contexts** по провайдерам:

| Context | Entities | DTOs | Schemas |
|---------|----------|------|---------|
| **ChEMBL** | Bioactivity, Molecule, Target, Assay, Document, CellLine, TargetComponent | ActivityRecord, MoleculeRecord, TargetRecord, AssayRecord, DocumentRecord, CellLineRecord, TargetComponentRecord | activity.py, molecule.py, target.py, assay.py + 9 others |
| **PubChem** | Compound | PubChemCompoundRecord | compound.py |
| **PubMed** | Publication | ArticleRecord | article.py |
| **CrossRef** | PublicationEntity | PublicationRecord | 6 schemas |
| **UniProt** | Protein | - | protein.py, isoform.py |

---

## 4. Рекомендации по Рефакторингу

### 4.1. Высокий Приоритет

#### 4.1.1. Переименовать `DQStatus` в `value_objects/dq_result.py`

**Проблема:** Коллизия имён с `DQStatus` в `types.py`

**Решение:** Переименовать в `DQEvaluationStatus` или `DataQualityStatus`

```python
# domain/value_objects/dq_result.py
class DQEvaluationStatus(str, Enum):  # Было: DQStatus
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
```

**Затронутые файлы:**
- `domain/value_objects/dq_result.py`
- `domain/value_objects/__init__.py`
- `domain/__init__.py`

**Effort:** ~1 час

#### 4.1.2. Удалить или Переименовать `DQStatus` в `types.py`

**Проблема:** Дублирует семантику `QuarantineStatus`

**Решение:** Переименовать в `QuarantineRecordStatus` или удалить в пользу `QuarantineStatus`

**Верификация:**
```bash
# Проверка использования
grep -r "from bioetl.domain.types import.*DQStatus" src/
# Результат: только quarantine/operations.py и quarantine/unified.py
```

**Effort:** ~2 часа (требует проверки infrastructure)

### 4.2. Средний Приоритет

#### 4.2.1. Интегрировать или Удалить Неиспользуемые Сервисы

**Опция A (интеграция):**
- Добавить `NormalizationService` в трансформеры для нормализации значений
- Добавить `ActivityAggregator` для агрегации множественных измерений
- Добавить `UnitConverter` для конвертации единиц измерения

**Опция B (удаление):**
Если сервисы не планируются к использованию, удалить для снижения cognitive load.

**Рекомендация:** Опция A — сервисы хорошо спроектированы и покрыты тестами.

**Effort:** ~4-8 часов

#### 4.2.2. Консолидировать Статусы Карантина

**Текущее состояние:**
- `types.py:DQStatus` — NEW, IGNORED, REPROCESSED (3 значения)
- `aggregates/quarantine_entry.py:QuarantineStatus` — NEW, UNDER_REVIEW, IGNORED, REPROCESSED, EXPIRED (5 значений)

**Решение:** Использовать только `QuarantineStatus`, удалить `DQStatus` из `types.py`

**Effort:** ~2 часа

### 4.3. Низкий Приоритет

#### 4.3.1. Удалить Deprecated `Work` Alias

**Файл:** `domain/entities/crossref.py:223-241`

**Решение:** После периода deprecation удалить класс `Work` и связанные экспорты.

**Effort:** ~30 минут

#### 4.3.2. Документировать Назначение Pandera-схем

Добавить в `schemas/README.md` объяснение, что схемы используются для:
1. Валидации в тестах
2. Документации структуры данных
3. Потенциального runtime enforcement (не активировано)

**Effort:** ~30 минут

---

## 5. Что НЕ Является Проблемой

Согласно протоколу верификации (CLAUDE.md §0), следующие паттерны **НЕ являются нарушениями**:

| Паттерн | Почему Не Проблема |
|---------|-------------------|
| **DTO + Entity для одной сущности** | Осознанный паттерн: DTO для API-границ, Entity с lineage |
| **Pandera-схемы в отдельной директории** | Служат для валидации и документации |
| **Большие агрегаты (500+ LOC)** | Все агрегаты имеют чёткие инварианты и state machines |
| **NoOp implementations** | Null Object Pattern для опциональной observability |
| **34 порта** | Каждый порт имеет ясную ответственность |

---

## 6. Итоговое Резюме

### Общая Оценка: ✅ Хорошо Структурирован

**Domain-слой BioETL** демонстрирует **зрелую DDD-архитектуру**:

1. **Сильные стороны:**
   - Чёткие Aggregate Roots с инвариантами
   - Богатая модель Value Objects
   - Чистое разделение Ports/Adapters
   - Domain Events для side effects
   - Иммутабельность везде

2. **Требует внимания:**
   - Коллизия имён `DQStatus` (2 разных enum)
   - 4 неиспользуемых доменных сервиса
   - Дублирование статусов карантина

3. **Трудозатраты на рефакторинг:**
   - Высокий приоритет: ~3 часа
   - Средний приоритет: ~6-10 часов
   - Низкий приоритет: ~1 час

**Вывод:** Структурно консистентен, но есть 2-3 узла коллизии имён, требующих внимания для улучшения Ubiquitous Language.

---

## Приложение: Статистика Domain-слоя

### Размеры Файлов (топ-10)

| Файл | Строк |
|------|-------|
| `entities/chembl.py` | 714 |
| `aggregates/pipeline_run.py` | 561 |
| `aggregates/batch.py` | 533 |
| `aggregates/quarantine_entry.py` | 513 |
| `__init__.py` | 455 |
| `value_objects/activity_values.py` | 436 |
| `types.py` | 396 |
| `services/normalization_service.py` | 385 |
| `services/activity_aggregator.py` | 359 |
| `ports/normalization.py` | 341 |

### Количество Компонентов

| Категория | Количество |
|-----------|------------|
| Файлы Python | 102 |
| Aggregates | 3 |
| Domain Entities | 12 |
| Pydantic DTOs | 10 |
| Value Objects | 15+ |
| Ports (Protocols) | 34 |
| Domain Services | 6 |
| Pandera Schemas | 23 |
| Exceptions | 28 |
