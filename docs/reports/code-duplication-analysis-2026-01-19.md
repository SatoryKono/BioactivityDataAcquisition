# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-01-19
**Ветка**: claude/refactor-code-duplication-0pXgo
**Версия**: 1.0

---

## Executive Summary

- **Проанализировано**: 18 трансформеров, 8 адаптеров, 15 базовых классов, 9 mixins
- **Обнаружено категорий дублирования**: 2 (P2 - Medium)
- **Потенциальное сокращение**: ~90 LOC (<0.15% кодовой базы)
- **Вердикт**: Кодовая база **хорошо спроектирована**, дублирование минимальное

---

## 1. Верифицированные дублирования

### 1.1 `_parse_pages` и `_normalize_pmc_id` (P2 - Medium)

**Локации**:
- `pubmed/transformer.py:239-286` (48 LOC)
- `semanticscholar/transformer.py:106-150` (45 LOC)

**Идентичная логика**:
```python
def _parse_pages(self, pages: str | None) -> tuple[str | None, str | None]:
    """Parse pages string into first_page and last_page."""
    if not pages or not pages.strip():
        return None, None
    pages = pages.strip()
    if "-" in pages:
        parts = pages.split("-", 1)
        first = parts[0].strip() or None
        last = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        return first, last
    return pages, None

def _normalize_pmc_id(self, pmc_id: str | None) -> str | None:
    """Ensure PMC ID has 'PMC' prefix."""
    if not pmc_id:
        return None
    pmc_id = pmc_id.strip()
    if not pmc_id.upper().startswith("PMC"):
        return f"PMC{pmc_id}"
    return pmc_id.upper()
```

**Рекомендация**: Вынести в `DataNormalizationService` как `parse_pages()` и `normalize_pmc_id()`.

**Impact**: Medium - используется в 2 publication трансформерах
**Complexity**: Low - простая функциональность без зависимостей
**LOC Reduction**: ~45 LOC

---

## 2. Паттерны НЕ являющиеся дублированием

### 2.1 Template Method Hooks (Валидный паттерн)

| Метод | Места | Причина |
|-------|-------|---------|
| `_extract_business_data` | 18 | Provider-specific логика |
| `_get_primary_id_field` | 5 | Entity-specific primary key |
| `_get_health_endpoint` | 10 | Provider-specific endpoint |
| `_get_entity_class` | 5 | Entity class factory |
| `_event_*` (fallback) | 5 каждый | Provider-specific event names |

### 2.2 Разная семантика (НЕ дублирование)

| Компонент | Локация 1 | Локация 2 | Различие |
|-----------|-----------|-----------|----------|
| `_compute_publication_date` | PubMed | CrossRef | Разный приоритет дат, разная нормализация |
| `extract_authors` | CrossRef | S2/OpenAlex | CrossRef: given+family, другие: single field |

### 2.3 Делегирование в крупных компонентах (Верифицировано)

| Компонент | LOC | Делегирование | Вывод |
|-----------|-----|---------------|-------|
| `base_transformer.py` | 673 | 8 сервисов | НЕ god object |
| `runner.py` | 189 | 13 сервисов | НЕ god object |
| `batch_executor.py` | 754 | 38 атрибутов | НЕ god object |

---

## 3. Карта зависимостей для рефакторинга

### 3.1 `DataNormalizationService` (целевой компонент)

**Текущее состояние** (`domain/services/data_normalization_service.py`):
- 190 LOC
- Методы: `normalize_doi`, `normalize_pmid`, `normalize_year`, `normalize_authors`, etc.
- **Отсутствует**: `parse_pages`, `normalize_pmc_id`

**Импортёры DataNormalizationService**:
```bash
grep -r "DataNormalizationService\|data_normalizer" src/bioetl/ | grep -v __pycache__
```
- `application/core/base_transformer.py` - используется через `_data_normalizer`
- `application/pipelines/chembl/publication_transformer.py` - через base
- `application/pipelines/pubmed/transformer.py` - через base
- `application/pipelines/*/transformer.py` (все publication) - через base

### 3.2 Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `domain/services/data_normalization_service.py` | Добавить `parse_pages`, `normalize_pmc_id` |
| `application/pipelines/pubmed/transformer.py` | Удалить локальные методы, делегировать |
| `application/pipelines/semanticscholar/transformer.py` | Удалить локальные методы, делегировать |

---

## 4. Матрица приоритизации

| # | Категория | Impact | Complexity | LOC | Приоритет |
|---|-----------|--------|------------|-----|-----------|
| 1 | `_parse_pages` + `_normalize_pmc_id` | Medium | Low | ~45 | **P2** |
| 2 | `extract_authors` → `extract_author_names` | Low | Low | ~30 | P4 (Optional) |

---

## 5. План миграции

### Этап 1: Расширение DataNormalizationService

1. Добавить `parse_pages(pages: str | None) -> tuple[str | None, str | None]`
2. Добавить `normalize_pmc_id(pmc_id: str | None) -> str | None`
3. Добавить unit-тесты

### Этап 2: Рефакторинг трансформеров

1. PubMed: заменить `self._parse_pages` → `self._data_normalizer.parse_pages`
2. PubMed: заменить `self._normalize_pmc_id` → `self._data_normalizer.normalize_pmc_id`
3. SemanticScholar: аналогично
4. Удалить локальные методы

### Этап 3: Валидация

```bash
make lint && make test
```

---

## 6. Чеклист валидации

- [ ] `pytest tests/ -v --tb=short`
- [ ] `mypy src/bioetl/ --strict`
- [ ] Coverage остаётся ≥85%
- [ ] Нет регрессий в integration тестах

---

## 7. Заключение

Кодовая база BioETL демонстрирует **зрелую архитектуру** с минимальным дублированием:

1. **Существующие абстракции** (15 базовых классов, 9 mixins) эффективно переиспользуются
2. **Template Method паттерн** корректно применяется для provider-specific логики
3. **Делегирование** в крупных компонентах подтверждено верификацией
4. **Обнаруженное дублирование** (~90 LOC) составляет <0.15% кодовой базы

**Рекомендация**: Выполнить рефакторинг P2 категории для улучшения консистентности.

---

*Верификация выполнена 2026-01-19 согласно Протоколу Двойной Верификации (CLAUDE.md §0)*
