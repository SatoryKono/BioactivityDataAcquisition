# Audit: entity_type во всех трансформерах

**Дата аудита:** 2026-01-06
**Приоритет:** P2 (Major)
**Статус:** Завершён

---

## 1. Резюме

Систематический аудит выявил **3 паттерна** передачи `entity_type` во всех трансформерах проекта:

| Паттерн | Описание | Количество | Итоговый entity_type |
|---------|----------|------------|----------------------|
| **A** | ChEMBL через BaseChemblTransformer (нет передачи entity_type) | 12 | `"unknown"` |
| **B** | Явно передают entity_type в super() | 6 | Корректный |
| **C** | Нет entity_type, нет entity_class (PubMed) | 1 | `"unknown"` |

**Ключевой вывод:** 13 из 19 трансформеров имеют `entity_type = "unknown"`, что теряет ценную информацию для метрик и трейсинга.

---

## 2. Архитектурный Контекст

### 2.1. BaseTransformer

**Файл:** `src/bioetl/application/core/base_transformer.py:92-127`

```python
def __init__(
    self,
    provider: str,
    entity_type: str | None = None,  # ← Опциональный параметр
    tracer: TracingPort | None = None,
    ...
) -> None:
    self.provider = provider
    self.entity_type = entity_type or "unknown"  # ← Default "unknown"
```

**Использование entity_type:**
- Метрики: `transform_duration_seconds{entity_type="..."}`, `transform_errors_total{entity_type="..."}`
- Трейсинг: атрибут `bioetl.entity_type` в span
- `compute_entity_id()`: для формирования entity_id

### 2.2. BaseChemblTransformer

**Файл:** `src/bioetl/application/pipelines/chembl/base_chembl_transformer.py:56-83`

```python
def __init__(
    self,
    provider: str = "chembl",
    tracer: TracingPort | None = None,
    ...
) -> None:
    super().__init__(
        provider,
        tracer=tracer,  # ← entity_type НЕ передаётся!
        ...
    )
```

**Проблема:** `entity_type` не передаётся в `super().__init__()`, поэтому все наследники получают `entity_type = "unknown"`.

---

## 3. Матрица Паттернов

### 3.1. Паттерн A: ChEMBL (через BaseChemblTransformer)

| Трансформер | entity_type param | Передаёт в super() | entity_class ClassVar | Итоговый entity_type |
|-------------|-------------------|--------------------|-----------------------|----------------------|
| ActivityTransformer | ❌ | ❌ | ✅ Bioactivity | `"unknown"` |
| AssayTransformer | ❌ | ❌ | ✅ Assay | `"unknown"` |
| MoleculeTransformer | ❌ | ❌ | ✅ Molecule | `"unknown"` |
| TargetTransformer | ❌ | ❌ | ✅ Target | `"unknown"` |
| DocumentTransformer | ❌ | ❌ | ✅ Document | `"unknown"` |
| TargetComponentTransformer | ❌ | ❌ | ✅ TargetComponent | `"unknown"` |
| CellLineTransformer | ❌ | ❌ | ✅ CellLine | `"unknown"` |
| CompoundRecordTransformer | ❌ | ❌ | ✅ CompoundRecord | `"unknown"` |
| ProteinClassTransformer | ❌ | ❌ | ✅ ProteinClassification | `"unknown"` |
| AssayParametersTransformer | ❌ | ❌ | ✅ AssayParameters | `"unknown"` |
| DocumentSimilarityTransformer | ❌ | ❌ | ✅ DocumentSimilarity | `"unknown"` |
| DocumentTermTransformer | ❌ | ❌ | ✅ DocumentTerm | `"unknown"` |

### 3.2. Паттерн B: Явная передача entity_type

| Трансформер | entity_type param | Передаёт в super() | entity_class ClassVar | Итоговый entity_type |
|-------------|-------------------|--------------------|-----------------------|----------------------|
| SemanticScholarPublicationTransformer | ✅ `"publication"` | ✅ | ❌ | `"publication"` |
| CrossRefTransformer | ❌ | ✅ (hardcoded) | ❌ | `"publication"` |
| OpenAlexPublicationTransformer | ❌ | ✅ (hardcoded) | ❌ | `"publication"` |
| PubChemCompoundTransformer | ✅ `"compound"` | ✅ | ❌ | `"compound"` |
| UniProtProteinTransformer | ✅ `"protein"` | ✅ | ❌ | `"protein"` |
| IDMappingTransformer | ✅ `"idmapping"` | ✅ | ❌ | `"idmapping"` |

### 3.3. Паттерн C: Нет entity_type, нет entity_class

| Трансформер | entity_type param | Передаёт в super() | entity_class ClassVar | Итоговый entity_type |
|-------------|-------------------|--------------------|-----------------------|----------------------|
| PubMedPublicationTransformer | ❌ | ❌ | ❌ | `"unknown"` |

---

## 4. Принятое Решение

### 4.1. Автоматическое определение entity_type из entity_class

**Подход:** Изменить `BaseChemblTransformer.__init__()` для автоматического вывода `entity_type` из `entity_class`:

```python
def __init__(
    self,
    provider: str = "chembl",
    tracer: TracingPort | None = None,
    ...
) -> None:
    # Автоматически определить entity_type из entity_class
    entity_type = self.entity_class.__name__.lower()

    super().__init__(
        provider,
        entity_type=entity_type,  # ← Автоматически
        tracer=tracer,
        ...
    )
```

**Результат для ChEMBL трансформеров:**

| Трансформер | entity_class | Новый entity_type |
|-------------|--------------|-------------------|
| ActivityTransformer | Bioactivity | `"bioactivity"` |
| AssayTransformer | Assay | `"assay"` |
| MoleculeTransformer | Molecule | `"molecule"` |
| TargetTransformer | Target | `"target"` |
| DocumentTransformer | Document | `"document"` |
| TargetComponentTransformer | TargetComponent | `"targetcomponent"` |
| CellLineTransformer | CellLine | `"cellline"` |
| CompoundRecordTransformer | CompoundRecord | `"compoundrecord"` |
| ProteinClassTransformer | ProteinClassification | `"proteinclassification"` |
| AssayParametersTransformer | AssayParameters | `"assayparameters"` |
| DocumentSimilarityTransformer | DocumentSimilarity | `"documentsimilarity"` |
| DocumentTermTransformer | DocumentTerm | `"documentterm"` |

### 4.2. Исправление PubMedPublicationTransformer

**Подход:** Добавить явную передачу `entity_type="publication"` в `super().__init__()`.

---

## 5. Плюсы и Минусы

### 5.1. Плюсы автоматического определения

1. **Backward compatible** — не требует изменений в существующих ChEMBL трансформерах
2. **Консистентный результат** — entity_type всегда соответствует entity_class
3. **Меньше дублирования** — не нужно указывать entity_type в каждом трансформере
4. **Улучшение observability** — метрики и трейсы будут содержать полезную информацию

### 5.2. Минусы

1. **Имена в lowercase** — `"bioactivity"` вместо `"activity"` (отличается от названия пайплайна)
2. **Длинные имена** — `"proteinclassification"`, `"documentsimilarity"`

### 5.3. Альтернатива: Mapping словарь

Можно добавить явный mapping для более читаемых имён:

```python
_ENTITY_TYPE_MAP: dict[str, str] = {
    "Bioactivity": "activity",
    "ProteinClassification": "protein_class",
    # ...
}
```

**Решение:** Начать с простого `.lower()`, рефакторить при необходимости.

---

## 6. Реализованные Изменения

### 6.1. BaseChemblTransformer

**Файл:** `src/bioetl/application/pipelines/chembl/base_chembl_transformer.py`

**Изменение:** Добавлена автоматическая деривация `entity_type` из `entity_class.__name__.lower()`.

### 6.2. PubMedPublicationTransformer

**Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py`

**Изменение:** Добавлена явная передача `entity_type="publication"` в `super().__init__()`.

---

## 7. Верификация

```bash
# Запуск тестов для трансформеров
make test-unit

# Проверка метрик entity_type
grep -r "entity_type" src/bioetl/application/pipelines/
```

---

## 8. Критерии Приёмки

- [x] Все трансформеры проанализированы
- [x] Матрица паттернов заполнена
- [x] Решение принято и задокументировано
- [x] Изменения реализованы
- [x] Все тесты проходят (400 unit tests + 400 architecture tests)

---

*Аудит выполнен: 2026-01-06*
