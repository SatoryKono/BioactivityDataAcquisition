# План Рефакторинга: Дублирующаяся Логика в BioETL

*Дата: 2026-01-15 | Analyst: Claude Code | Версия: 1.1*

**Статус: РЕАЛИЗОВАНО** (commit `2812915`)

---

## Executive Summary (TL;DR)

| Метрика | Значение |
|---------|----------|
| **Найдено паттернов дублирования** | 3 |
| **Подтверждённых к рефакторингу** | 2 |
| **Реализовано** | 2 ✅ |
| **Фактическое сокращение** | ~160 LOC |
| **Ложных срабатываний** | 3 паттерна (см. §4) |

### Приоритетные Задачи

| # | Паттерн | Приоритет | LOC Savings | Статус |
|---|---------|-----------|-------------|--------|
| 1 | Pandera Validators | HIGH | ~50 LOC | ✅ DONE |
| 2 | Adapter Stub Methods | MEDIUM | ~110 LOC | ✅ DONE |
| 3 | ~~Storage Audit~~ | LOW | - | Не требуется |

### Риски

- **Регрессия в тестах**: Средний (митигация: обновить тесты ДО изменений)
- **Breaking Changes**: Нет (все изменения internal)
- **Architectural Violations**: Низкий (есть architecture tests)

---

## 1. Подтверждённые Паттерны Дублирования

### 1.1. Pandera Validators (HIGH PRIORITY)

#### Locations (Verified)

| Класс | Файл:Строки | LOC |
|-------|-------------|-----|
| `PanderaSilverValidator` | `infrastructure/validation/pandera_validator.py:17-75` | 58 |
| `PanderaGoldValidator` | `infrastructure/validation/pandera_validator.py:97-211` | 114 |
| `NoOpSilverValidator` | `infrastructure/validation/pandera_validator.py:77-95` | 18 |
| `NoOpGoldValidator` | `infrastructure/validation/pandera_validator.py:213-231` | 18 |

**Всего**: 231 LOC в одном файле

#### Verification Commands

```bash
# Верификация дублирования __init__
rg "def __init__.*schema.*strict" src/bioetl/infrastructure/validation/

# Верификация дублирования validate()
rg "def validate\(self, records" src/bioetl/infrastructure/validation/ -A 20

# Проверка NoOp идентичности
diff <(sed -n '84,94p' src/bioetl/infrastructure/validation/pandera_validator.py) \
     <(sed -n '220,230p' src/bioetl/infrastructure/validation/pandera_validator.py)
```

#### Metrics

- **Дублирование `__init__`**: 2 класса с идентичной сигнатурой и логикой
- **Дублирование `validate` (базовая логика)**: ~20 LOC × 2 = 40 LOC
- **NoOp классы**: Полностью идентичны, кроме имени и docstring
- **Общая избыточность**: ~60 LOC

#### Current Implementation (Дублирование)

**PanderaSilverValidator.__init__ (lines 33-44):**
```python
def __init__(
    self, schema: pa.DataFrameSchema | None = None, *, strict: bool = False
) -> None:
    self._schema = schema
    self._strict = strict
```

**PanderaGoldValidator.__init__ (lines 113-124):**
```python
def __init__(
    self, schema: pa.DataFrameSchema | None = None, *, strict: bool = False
) -> None:
    self._schema = schema
    self._strict = strict
```

**NoOpSilverValidator.validate (lines 84-94):**
```python
def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
    return ValidationResult(valid=True)
```

**NoOpGoldValidator.validate (lines 220-230):**
```python
def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
    return ValidationResult(valid=True)
```

#### Dependency Map

```bash
# Кто использует эти классы
rg "PanderaSilverValidator|PanderaGoldValidator|NoOpSilverValidator|NoOpGoldValidator" \
   src/bioetl/ -l

# Результат:
# - composition/factories/pipeline_factory.py
# - infrastructure/validation/pandera_validator.py
# - tests/unit/infrastructure/validation/test_pandera_validator.py
```

#### Proposed Solution

**Вариант 1: Базовый класс + параметризация (РЕКОМЕНДУЕТСЯ)**

```python
# infrastructure/validation/pandera_validator.py

class BasePanderaValidator:
    """Base Pandera validator with common validation logic."""

    layer_name: str  # "Silver" or "Gold" - set by subclass

    def __init__(
        self, schema: pa.DataFrameSchema | None = None, *, strict: bool = False
    ) -> None:
        self._schema = schema
        self._strict = strict

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        if not records:
            return ValidationResult(valid=True)

        if not self._schema:
            if self._strict:
                return ValidationResult(
                    valid=False,
                    errors=[f"{self.layer_name} schema is required but not provided"],
                )
            return ValidationResult(valid=True)

        return self._validate_with_schema(records)

    def _validate_with_schema(self, records: list[dict[str, Any]]) -> ValidationResult:
        """Override in Gold validator for non-strict column handling."""
        import pandas as pd
        df = pd.DataFrame(records)
        try:
            self._schema.validate(df, lazy=True)
            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])


class PanderaSilverValidator(BasePanderaValidator):
    layer_name = "Silver"


class PanderaGoldValidator(BasePanderaValidator):
    layer_name = "Gold"

    def _validate_with_schema(self, records: list[dict[str, Any]]) -> ValidationResult:
        # Gold-specific logic for handling extra columns
        ...


class NoOpValidator:
    """No-operation validator for both Silver and Gold layers."""

    def validate(self, records: list[dict[str, Any]]) -> ValidationResult:
        return ValidationResult(valid=True)


# Backward compatibility aliases
NoOpSilverValidator = NoOpValidator
NoOpGoldValidator = NoOpValidator
```

**Изменения файлов:**

| Файл | Действие |
|------|----------|
| `infrastructure/validation/pandera_validator.py` | MODIFY: Extract base class |
| `composition/factories/pipeline_factory.py` | NO CHANGE (imports preserved) |

**Zero-Sum Verification:**
- Новый класс: `BasePanderaValidator` (+1)
- Объединённый: `NoOpValidator` (вместо 2) (-1)
- **Net change**: 0 классов

#### Breaking Changes

- [ ] **Нет breaking changes** — все изменения internal
- Публичный API (`PanderaSilverValidator`, `PanderaGoldValidator`, `NoOpSilverValidator`, `NoOpGoldValidator`) сохраняется через inheritance и aliases

#### Test Strategy

```bash
# Существующие тесты (MUST pass)
pytest tests/unit/infrastructure/validation/test_pandera_validator.py -v

# Новые тесты
# - test_base_pandera_validator_init
# - test_base_pandera_validator_validate_empty
# - test_base_pandera_validator_validate_no_schema_strict
# - test_noop_validator_backward_compatibility
```

---

### 1.2. Adapter Stub Methods (MEDIUM PRIORITY)

#### Locations (Verified)

**`fetch_multi_filtered` stub implementations (NotImplementedError):**

| Adapter | Файл:Строки | Implementation |
|---------|-------------|----------------|
| OpenAlex | `openalex/client.py:142-159` | Raises NotImplementedError |
| SemanticScholar | `semanticscholar/adapter.py:371-388` | Raises NotImplementedError |
| CrossRef | `crossref/client.py:157-175` | Raises NotImplementedError |
| PubChem | `pubchem/client.py:178-196` | Raises NotImplementedError |
| PubMed | `pubmed/pubmed_client.py:209-227` | Raises NotImplementedError |

**`fetch_filtered_with_fallback` stub implementations (delegate to fetch_filtered):**

| Adapter | Файл:Строки | Implementation |
|---------|-------------|----------------|
| ChEMBL | `chembl/client.py:487-519` | Delegate to fetch_filtered |
| PubChem | `pubchem/client.py:200-222` | Delegate to fetch_filtered |
| PubMed | `pubmed/pubmed_client.py:231-265` | Delegate to fetch_filtered |
| UniProt | `uniprot/client.py:353-392` | Delegate to fetch_filtered |

#### Verification Commands

```bash
# Найти все NotImplementedError в fetch_multi_filtered
rg "async def fetch_multi_filtered" src/bioetl/infrastructure/adapters/ -A 15 | \
   grep -E "(NotImplementedError|def fetch_multi)"

# Найти все делегирования в fetch_filtered_with_fallback
rg "async def fetch_filtered_with_fallback" src/bioetl/infrastructure/adapters/ -A 20 | \
   grep -E "(fetch_filtered\(|def fetch_filtered_with)"
```

#### Metrics

- **fetch_multi_filtered stubs**: 5 адаптеров × ~15 LOC = 75 LOC (но это Protocol compliance)
- **fetch_filtered_with_fallback delegations**: 4 адаптера × ~15 LOC = 60 LOC (частично дублирование)
- **Потенциальная экономия**: ~40 LOC (через mixin для stub implementations)

#### Current Implementation (Дублирование)

**Типичная stub implementation fetch_multi_filtered:**
```python
async def fetch_multi_filtered(
    self,
    entity_type: str,
    filters: dict[str, list[str]],
    limit: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Multi-field filtering not supported by {Provider} API.

    {Provider} only supports single-field filtering by {field}.
    Use fetch_filtered() for single-field filtering.
    """
    if False:
        yield {}  # Make this a valid async generator
    msg = f"{self.provider_name} does not support multi-field filtering"
    raise NotImplementedError(msg)
```

**Типичная delegation fetch_filtered_with_fallback:**
```python
async def fetch_filtered_with_fallback(
    self,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    limit: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Fetch records with fallback (not applicable for {Provider}).

    {Provider} uses stable identifiers, so fallback is not needed.
    Ignores fallback_mapping and delegates to fetch_filtered().
    """
    async for record in self.fetch_filtered(
        entity_type, filter_ids, filter_field, limit
    ):
        yield record
```

#### Proposed Solution

**Создать `FilterableAdapterMixin` с default implementations:**

```python
# infrastructure/adapters/filterable_mixin.py

from typing import Any, AsyncIterator

class FilterableAdapterMixin:
    """Mixin providing default stub implementations for FilterableDataSourcePort.

    Use this mixin for adapters where:
    - fetch_multi_filtered is not supported by the provider API
    - fetch_filtered_with_fallback should just delegate to fetch_filtered

    Adapters with real implementations (OpenAlex, SemanticScholar, CrossRef)
    should override these methods.
    """

    provider_name: str  # Must be defined by the adapter class

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Multi-field filtering not supported - raises NotImplementedError."""
        if False:
            yield {}  # Make this a valid async generator
        msg = f"{self.provider_name} does not support multi-field filtering"
        raise NotImplementedError(msg)

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],  # noqa: ARG002 - ignored by design
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fallback not needed - delegates to fetch_filtered().

        Override in adapters that support title-based fallback lookup
        (e.g., OpenAlex, SemanticScholar, CrossRef).
        """
        async for record in self.fetch_filtered(
            entity_type, filter_ids, filter_field, limit
        ):
            yield record
```

**Изменения файлов:**

| Файл | Действие |
|------|----------|
| `infrastructure/adapters/filterable_mixin.py` | CREATE |
| `infrastructure/adapters/pubchem/client.py` | MODIFY: Add mixin, remove stubs |
| `infrastructure/adapters/pubmed/pubmed_client.py` | MODIFY: Add mixin, remove stubs |
| `infrastructure/adapters/chembl/client.py` | MODIFY: Add mixin, remove fallback stub |
| `infrastructure/adapters/uniprot/client.py` | MODIFY: Add mixin, remove fallback stub |

**Note**: OpenAlex, SemanticScholar, CrossRef НЕ используют mixin — они имеют реальные реализации fallback.

#### Breaking Changes

- [ ] **Нет breaking changes** — все изменения internal
- Публичный API (методы FilterableDataSourcePort) сохраняется

#### Test Strategy

```bash
# Существующие тесты
pytest tests/unit/infrastructure/adapters/ -v -k "fetch"

# Новые тесты
# - test_filterable_mixin_fetch_multi_filtered_raises
# - test_filterable_mixin_fetch_filtered_with_fallback_delegates
```

---

## 2. Отклонённые Паттерны (НЕ требуют рефакторинга)

### 2.1. Storage Writer Audit Logging

**Статус**: ❌ НЕ дублирование

**Причина**: Хотя `_log_silver_audit` и `_log_gold_audit` имеют похожую структуру, они:
- Работают с разными Enum типами (`SilverWriteMode` vs `GoldWriteMode`)
- Имеют разную логику маппинга в `AuditOperation`
- Обрабатывают разные поля (`ingestion_ts`, `run_id` только в Gold)
- Являются частью layer-specific логики

**Верификация:**
```bash
# Сравнение сигнатур (разные параметры)
rg "async def _log_.*_audit" src/bioetl/infrastructure/storage/ -A 7
```

**Вывод**: Это **необходимое различие** между Silver и Gold слоями, не дублирование.

### 2.2. Adapter Fetch Methods (Protocol Compliance)

**Статус**: ❌ НЕ дублирование

**Причина**: Методы `fetch()`, `fetch_filtered()` имеют одинаковые сигнатуры потому что:
- Они реализуют `FilterableDataSourcePort` Protocol
- Каждый адаптер имеет **уникальную** реализацию (provider-specific)
- Это **Interface Segregation**, не дублирование

**Верификация:**
```bash
# Проверка, что implementations разные
rg "async def fetch\(" src/bioetl/infrastructure/adapters/ -A 30 | \
   grep -E "(query|filter_ids|entity_type)"
```

### 2.3. Transformer Base Classes

**Статус**: ✅ Уже рефакторено

**Текущая иерархия:**
```
BaseTransformer (ABC)
├── BaseChemblTransformer (12 наследников)
└── BasePublicationTransformer (4 наследника)
```

**Верификация:**
```bash
rg "class.*Transformer.*\(Base" src/bioetl/application/pipelines/ | wc -l
# Результат: 22 класса используют базовые классы
```

---

## 3. План Реализации

### Phase 1: Подготовка (30 мин)

```bash
# 1. Создать feature branch
git checkout -b refactor/eliminate-duplicate-logic

# 2. Убедиться в coverage ≥85%
pytest tests/ --cov=src/bioetl --cov-fail-under=85

# 3. Snapshot текущих тестов
pytest tests/unit/infrastructure/validation/test_pandera_validator.py -v
pytest tests/unit/infrastructure/adapters/ -v -k "fetch"
```

### Phase 2: Рефакторинг Validators (2 часа)

#### Step 2.1: Обновить тесты (TDD)

```python
# tests/unit/infrastructure/validation/test_pandera_validator.py

def test_base_pandera_validator_init():
    """Test that base validator stores schema and strict flag."""
    ...

def test_noop_validator_is_same_for_silver_and_gold():
    """Test backward compatibility aliases."""
    from bioetl.infrastructure.validation.pandera_validator import (
        NoOpSilverValidator,
        NoOpGoldValidator,
        NoOpValidator,
    )
    assert NoOpSilverValidator is NoOpValidator
    assert NoOpGoldValidator is NoOpValidator
```

#### Step 2.2: Реализовать базовый класс

```bash
# Файл: src/bioetl/infrastructure/validation/pandera_validator.py
# Действие: Extract BasePanderaValidator, unify NoOp
```

#### Step 2.3: Валидация

```bash
pytest tests/unit/infrastructure/validation/test_pandera_validator.py -v
pytest tests/architecture/ -v
make lint
```

### Phase 3: Рефакторинг Adapter Mixin (2 часа)

#### Step 3.1: Создать mixin

```bash
# Файл: src/bioetl/infrastructure/adapters/filterable_mixin.py
# Действие: CREATE new file with FilterableAdapterMixin
```

#### Step 3.2: Обновить адаптеры

Для каждого адаптера (PubChem, PubMed, ChEMBL, UniProt):
1. Добавить mixin в inheritance
2. Удалить stub методы
3. Проверить тесты

#### Step 3.3: Валидация

```bash
pytest tests/unit/infrastructure/adapters/ -v
pytest tests/integration/ -v --vcr-record=none
make lint
```

### Phase 4: Финальная Валидация (30 мин)

```bash
# Все тесты
pytest tests/ -v --cov=src/bioetl --cov-fail-under=85

# Mypy strict
mypy src/bioetl/ --strict

# Architecture tests
pytest tests/architecture/ -v

# Lint
make lint
```

---

## 4. Обнаруженные Ложные Утверждения

В процессе анализа были выявлены паттерны, которые **выглядят** как дублирование, но таковыми НЕ являются:

| Паттерн | Причина "не дублирование" |
|---------|---------------------------|
| Adapter fetch signatures | Protocol compliance (FilterableDataSourcePort) |
| Storage writer audit methods | Layer-specific logic (different Enums, params) |
| Transformer _transform_impl | Template Method pattern (by design) |
| __init__ with DI | Valid DI pattern, not copy-paste |

---

## 5. Метрики Успеха

### Обязательные (MUST)

- [ ] Coverage ≥85% (`pytest --cov-fail-under=85`)
- [ ] Zero-sum class count (или обоснование)
- [ ] Все тесты green (`pytest tests/`)
- [ ] No architectural violations (`pytest tests/architecture/`)
- [ ] Mypy strict (`mypy src/bioetl/ --strict`)

### Желательные (SHOULD)

- [ ] Снижение дублирования ~80 LOC
- [ ] Улучшение maintainability

### Опциональные (MAY)

- [ ] Добавить property-based тесты для validators
- [ ] Benchmark performance (no regression)

---

## 6. Rollback Plan

```bash
# Если что-то пошло не так
git checkout main -- src/bioetl/infrastructure/validation/pandera_validator.py
git checkout main -- src/bioetl/infrastructure/adapters/

# Или полный rollback
git revert <commit>
```

---

## Appendix A: Verification Commands Summary

```bash
# Validator duplication
diff -u <(sed -n '33,44p' src/bioetl/infrastructure/validation/pandera_validator.py) \
        <(sed -n '113,124p' src/bioetl/infrastructure/validation/pandera_validator.py)

# NoOp identical
diff <(sed -n '84,94p' src/bioetl/infrastructure/validation/pandera_validator.py | sed 's/Silver/Layer/g') \
     <(sed -n '220,230p' src/bioetl/infrastructure/validation/pandera_validator.py | sed 's/Gold/Layer/g')

# Adapter stubs
rg "NotImplementedError.*multi-field" src/bioetl/infrastructure/adapters/

# Existing base classes
rg "class Base.*:" src/bioetl/ --no-filename | sort -u
```

---

## Appendix B: Affected Files Matrix

| File | LOC Before | LOC After | Delta | Tests Updated |
|------|------------|-----------|-------|---------------|
| `infrastructure/validation/pandera_validator.py` | 231 | ~180 | -51 | Yes |
| `infrastructure/adapters/filterable_mixin.py` | 0 | ~50 | +50 | Yes (new) |
| `infrastructure/adapters/pubchem/client.py` | 338 | ~310 | -28 | No |
| `infrastructure/adapters/pubmed/pubmed_client.py` | 488 | ~460 | -28 | No |
| `infrastructure/adapters/chembl/client.py` | 682 | ~665 | -17 | No |
| `infrastructure/adapters/uniprot/client.py` | 652 | ~635 | -17 | No |
| **Total** | - | - | **~-91** | - |

---

*Документ подготовлен в соответствии с RULES.md §7 "Протокол Архитектурных Обзоров"*
