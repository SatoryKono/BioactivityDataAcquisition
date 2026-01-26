# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-01-25
**Версия**: 1.0
**Аналитик**: Claude (claude-opus-4-5-20251101)

---

## Executive Summary

- **Проанализировано**: 3 DQ анализатора, 4 extractor-модуля, 4 fallback-обработчика, 5 базовых классов
- **Обнаружено категорий дублирования**: 1 (минорная)
- **Потенциальное сокращение**: ~60-70 LOC (0.1% кодовой базы)
- **Вердикт**: **Кодовая база хорошо спроектирована**, существующие абстракции эффективны

---

## 1. Верифицированные дублирования

### 1.1 DQ Analyzers — `_result_to_dict()` и `_update_counts()`

**Статус**: Минорное дублирование (P3)

| Файл | LOC | Методы |
|------|-----|--------|
| `bronze_analyzer.py` | 293 | 9 |
| `silver_analyzer.py` | 643 | 15 |
| `gold_analyzer.py` | 830 | 19 |

**Дублированные функции:**

| Функция | Bronze | Silver | Gold | Сходство |
|---------|--------|--------|------|----------|
| `_result_to_dict()` | L266-274 (9 LOC) | L590-605 (16 LOC) | L61-69 (9 LOC, module-level) | ~80% |
| `_update_counts()` | L276-289 (14 LOC) | L626-639 (14 LOC) | L72-80 (9 LOC, module-level) | ~95% |
| `_build_summary()` | inline | L182-213 (32 LOC) | L182-211 (30 LOC) | ~90% |

**Примеры кода:**

```python
# Bronze _update_counts (L276-289)
def _update_counts(
    self,
    status: DQCheckStatus,
    passed: int,
    failed: int,
    warnings: int,
) -> tuple[int, int, int]:
    if status == DQCheckStatus.PASS:
        return passed + 1, failed, warnings
    elif status == DQCheckStatus.FAIL:
        return passed, failed + 1, warnings
    else:  # WARN
        return passed, failed, warnings + 1

# Gold _update_counts (L72-80) — идентичный
def _update_counts(
    status: DQCheckStatus, passed: int, failed: int, warnings: int
) -> tuple[int, int, int]:
    if status == DQCheckStatus.PASS:
        return passed + 1, failed, warnings
    if status == DQCheckStatus.FAIL:
        return passed, failed + 1, warnings
    return passed, failed, warnings + 1
```

**Карта зависимостей:**

```
bioetl.application.services.dq/
├── __init__.py          # Re-exports BronzeDQAnalyzer, SilverDQAnalyzer, GoldDQAnalyzer
├── bronze_analyzer.py   # BronzeDQAnalyzer
├── silver_analyzer.py   # SilverDQAnalyzer
└── gold_analyzer.py     # GoldDQAnalyzer

Импортёры:
├── bioetl.composition.factories.dq_factory (L18)
└── bioetl.application.services.dq_report_service (indirect)

Пользователи:
├── DQReportService → batch_executor.py, postrun_service.py
├── CompositeRunner → runner.py
└── ServicesFactory → services_factory.py
```

**Рекомендация:**

Создать общий модуль `dq_utils.py`:

```python
# src/bioetl/application/services/dq/utils.py
"""Common utilities for DQ analyzers."""

from typing import Any
from bioetl.domain.value_objects.dq_report import DQCheckStatus

def update_counts(
    status: DQCheckStatus,
    passed: int,
    failed: int,
    warnings: int,
) -> tuple[int, int, int]:
    """Update check counts based on status."""
    if status == DQCheckStatus.PASS:
        return passed + 1, failed, warnings
    if status == DQCheckStatus.FAIL:
        return passed, failed + 1, warnings
    return passed, failed, warnings + 1

def result_to_dict(result: Any) -> dict[str, Any]:
    """Convert dataclass result to dict for serialization."""
    if hasattr(result, "__dataclass_fields__"):
        output = {}
        for field in result.__dataclass_fields__:
            if field.startswith("_"):
                continue
            value = getattr(result, field)
            if hasattr(value, "value"):  # Enum
                output[field] = value.value
            elif hasattr(value, "__dataclass_fields__"):
                output[field] = result_to_dict(value)
            else:
                output[field] = value
        return output
    return {"value": result}
```

**Impact**: ~60-70 LOC сокращение
**Complexity**: Низкая
**Приоритет**: P3 (nice-to-have)

---

## 2. Паттерны НЕ являющиеся дублированием

### 2.1 Publication Extractors

**Верификация**: `application/pipelines/{openalex,semanticscholar,crossref}/extractors.py`

| Функция | OpenAlex | SemanticScholar | CrossRef | Причина различий |
|---------|----------|-----------------|----------|------------------|
| `extract_authors()` | 28 LOC | 29 LOC | 43 LOC | Разные API-структуры |
| `extract_external_ids()` | 51 LOC | 28 LOC | — | Provider-specific |
| `extract_journal_info()` | 34 LOC | 30 LOC | 30 LOC | Разные поля/схемы |
| `extract_open_access_info()` | 20 LOC | 48 LOC | — | Разные API |

**Вердикт**: **НЕ дублирование**. Функции имеют одинаковые имена, но разные реализации из-за различий в API провайдеров.

**Уже реализованная абстракция:**
- `common/extractors.py` содержит `extract_author_names()` — универсальный экстрактор для простых форматов
- CrossRef требует отдельную логику из-за `given` + `family` комбинации

### 2.2 Fallback Handlers

**Верификация**: `infrastructure/adapters/{crossref,semanticscholar,openalex,pubmed}/fallback.py`

| Компонент | LOC | Роль |
|-----------|-----|------|
| `BaseTitleFallbackHandler` | 283 | ABC с Template Method |
| CrossRef `TitleFallbackHandler` | 146 | Реализация для CrossRef |
| SemanticScholar handler | 226 | Реализация для S2 |

**Вердикт**: **Хорошо спроектировано**. Уже используется Template Method pattern:
- Общая логика в `BaseTitleFallbackHandler`: `process_missing_dois()`, `process_title_only_entries()`
- Provider-specific: `_search_by_title()`, event properties
- Shared utilities: `title_matching.py` (81 LOC)

### 2.3 Base Classes (Adapters)

**Верификация**: `infrastructure/adapters/`

| Класс | LOC | Назначение |
|-------|-----|------------|
| `BaseHttpAdapter` | 123 | Async HTTP adapter base |
| `BaseSyncAdapter` | 138 | Sync adapter base (pubchempy) |
| `HealthCheckProviderMixin` | 399 | Health check template method |

**Вердикт**: **Оптимально**. Lean base classes с чёткой ответственностью.

### 2.4 Transformer Hierarchy

**Верификация**: `application/core/base_transformer.py`, `application/pipelines/*/`

```
BaseTransformer (674 LOC)
    ├── BaseChemblTransformer (183 LOC)
    │   └── 12 ChEMBL transformers
    ├── BasePublicationTransformer (201 LOC)
    │   └── 3 publication transformers
    └── Direct subclasses: UniProt, PubChem, PubMed, IDMapping
```

**Вердикт**: **Хорошо спроектировано**. 3-уровневая иерархия с Template Method:
- `BaseTransformer`: общий каркас `transform()` → `_transform_impl()`
- Provider bases: специфичные helper-методы
- Concrete: только `_extract_business_data()`

---

## 3. Матрица приоритизации

| # | Категория | Impact | Complexity | LOC | Приоритет | Рекомендация |
|---|-----------|--------|------------|-----|-----------|--------------|
| 1 | DQ Analyzer utils | Low | Low | ~60 | P3 | Extract to `dq/utils.py` |
| 2 | Publication extractors | — | — | — | — | **Keep as-is** |
| 3 | Fallback handlers | — | — | — | — | **Keep as-is** |
| 4 | Adapter base classes | — | — | — | — | **Keep as-is** |
| 5 | Transformer hierarchy | — | — | — | — | **Keep as-is** |

---

## 4. Валидация существующих абстракций

### 4.1 BaseTransformer (674 LOC)

**Проверка делегирования:**
```bash
grep -o "self\._[a-z_]*" base_transformer.py | sort -u
# _add_metadata, _compute_hash, _extract, _normalize, _serialize, _transform_impl, _validate
```

**Вердикт**: ✅ Активное делегирование, Template Method pattern, НЕ god object

### 4.2 BaseTitleFallbackHandler (283 LOC)

**Абстрактные методы:**
- `_search_by_title()`
- `_event_*` properties (4 required, 3 optional)

**Общая логика:**
- `process_missing_dois()` (37 LOC)
- `process_title_only_entries()` (32 LOC)
- `_truncate_title()`, `_get_fallback_title()`

**Вердикт**: ✅ Эффективное использование Template Method

### 4.3 HealthCheckProviderMixin (399 LOC)

**Template Method:**
- `health_check()` → `_probe_health()` (abstract) → `_fallback_health_status()`

**Вердикт**: ✅ Корректная абстракция

---

## 5. Рекомендации

### 5.1 Немедленные действия (P3)

**Создать `dq/utils.py`** для извлечения `update_counts()` и `result_to_dict()`:

```
src/bioetl/application/services/dq/
├── __init__.py
├── utils.py           # NEW: shared utilities
├── bronze_analyzer.py # Update imports
├── silver_analyzer.py # Update imports
└── gold_analyzer.py   # Update imports
```

### 5.2 Не требуется действий

| Компонент | Причина |
|-----------|---------|
| Publication extractors | Provider-specific по дизайну |
| Fallback handlers | Уже используют `BaseTitleFallbackHandler` |
| Adapter bases | Lean и эффективные |
| Transformer hierarchy | 3-level hierarchy оптимальна |

---

## 6. Заключение

Кодовая база BioETL демонстрирует **зрелую архитектуру** с эффективным использованием:

1. **Template Method pattern** — BaseTransformer, BaseTitleFallbackHandler
2. **Mixin composition** — HealthCheckProviderMixin, PaginatedFetcherMixin
3. **Provider-specific extractors** — корректно разделены по провайдерам
4. **Shared utilities** — title_matching.py, common/extractors.py

Единственное найденное дублирование (~60 LOC в DQ analyzers) — **минорное** и может быть исправлено созданием общего utility-модуля.

**Итоговая оценка**: Кодовая база находится в отличном состоянии с точки зрения DRY-принципа.

---

## История изменений

- **v1.0** (2026-01-25): Первоначальный анализ
