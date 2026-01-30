# FALLBACK СТРАТЕГИИ: КОНСОЛИДИРОВАННЫЙ ПЛАН v3

> **Дата**: 2026-01-30
> **Основа**: План v2 + 3 аудиторских отчёта (8 уникальных замечаний)
> **Метод**: Каждое утверждение верифицировано через Read/Grep кодовой базы
> **Статус**: Финальная консолидированная версия

---

## 0. СВОДКА ЗАМЕЧАНИЙ АУДИТОВ (дедупликация 3 отчётов)

Три независимых аудита выявили 8 уникальных проблем в плане v2.
Все замечания **подтверждены** верификацией кода.

| # | Замечание | Отчёты | Верификация |
|---|----------|--------|-------------|
| F1 | OpenAlex: в коде **нет** PMID lookup, план утверждает обратное | 1, 2, 3 | `client.py:326`: `if filter_field != "doi": return` |
| F2 | SemanticScholar: в коде **нет** PMID batch | 1, 2, 3 | `adapter.py:312`: только `valid_dois` обрабатывается |
| F3 | PubMed: в коде **нет** DOI lookup | 2, 3 | `pubmed_client.py:241`: `if filter_field != "pmid": warning("Assuming PMIDs")` |
| F4 | Противоречие: "не менять порт" + "добавить метод в Protocol" | 1 | Добавление метода в `FilterableDataSourcePort` = изменение интерфейса для ВСЕХ реализаций |
| F5 | CSV title-only использует маркеры `__title_only_N__`, не пустые строки | 1, 2, 3 | `csv_filter_reader.py:186`: `marker = f"__title_only_{title_only_count}__"` |
| F6 | `fallback_mapping` — generic `{id: value}`, не всегда `{id: title}` | 3 | `data_source.py:162`: "fallback value" (generic контракт порта) |
| F7 | PubMed CSV: колонка `pubmed_id`, не `pmid` | 1, 3 | `pubmed/publication.yaml:20`: `column_name: "pubmed_id"` |
| F8 | Пропущены direct IDs mode и multi-column filtering | 2, 3 | `input_config.py:54`: `direct_filter_ids`, `filtered_data_source.py:86-91` |

---

## 1. ВЕРИФИЦИРОВАННОЕ ТЕКУЩЕЕ СОСТОЯНИЕ

### 1.1. Архитектура Fallback (фактическая)

```
FilterableDataSourcePort (domain/ports/data_source.py:82-168)
    │
    ├── fetch_filtered()              → Phase 1: Primary batch lookup
    ├── fetch_filtered_with_fallback() → Phases 1-3:
    │       │
    │       │   fallback_mapping: dict[str, str]  ← GENERIC: {primary_id: fallback_value}
    │       │   (title для publication pipelines)
    │       │
    │       ├── Phase 1: Primary ID batch → adapter-specific
    │       ├── Phase 2: Title fallback   → BaseTitleFallbackHandler.process_missing_dois()
    │       └── Phase 3: Title-only       → BaseTitleFallbackHandler.process_title_only_entries()
    │                                        Поддерживает маркеры __title_only_N__ и пустые строки
    │
    └── fetch_multi_filtered()         → Multi-column AND filtering
```

### 1.2. Текущие компоненты

| Компонент | Файл | LOC | Назначение |
|-----------|------|-----|------------|
| `FilterableDataSourcePort` | `domain/ports/data_source.py:82-168` | 87 | Domain Protocol (interface) |
| `BaseTitleFallbackHandler` | `infrastructure/adapters/common/base_title_fallback.py` | 335 | Template Method, Phases 2-3 |
| `titles_match()` | `infrastructure/adapters/common/title_matching.py` | 90 | Title comparison |
| `FilteredDataSource` | `application/core/filtered_data_source.py` | 343 | Decorator: CSV/direct → fetch_filtered_with_fallback |
| `InputFilterConfig` | `domain/filtering/input_config.py` | 125 | Config (single fallback_column, direct IDs, multi-column) |
| `CsvFilterReader` | `infrastructure/adapters/input/csv_filter_reader.py` | ~280 | CSV загрузка с `__title_only_N__` маркерами |

### 1.3. Реализации по провайдерам (publication pipelines)

**ВАЖНО**: Таблица разделяет **API capability** (что поддерживает API провайдера)
и **Implementation status** (что реализовано в коде адаптера).

> **Scope**: Только publication pipelines. UniProt (accession→gene_name fallback) не входит в scope данного плана.

| Provider | Handler (LOC) | Primary ID | Реализованные Phases | API supports | Code implements |
|----------|--------------|-----------|---------------------|-------------|----------------|
| **CrossRef** | `TitleFallbackHandler` (96) | DOI | 3 (DOI→Title→Title-only) | DOI | DOI only |
| **OpenAlex** | `TitleFallbackHandler` (72) | DOI | 3 (DOI→Title→Title-only) | DOI, **PMID**, Title | **DOI only** (`client.py:326`) |
| **PubMed** | `TitleFallbackHandler` (83) | PMID | 3 (PMID→Title→Title-only) | PMID, **DOI** (esearch), Title | **PMID only** (`pubmed_client.py:241`) |
| **SemanticScholar** | `S2TitleFallbackHandler` (226) | DOI | 3 (DOI→Title→Title-only) | DOI, **PMID** (batch), Title | **DOI only** (`adapter.py:312`) |

### 1.4. Режимы фильтрации (полный список)

`FilteredDataSource` поддерживает три режима (`filtered_data_source.py:78-312`):

| Режим | Конфигурация | Загрузка | Использование |
|-------|-------------|----------|---------------|
| **Single-column + fallback** | `column_name`, `filter_field`, `fallback_column` | CSV → `load_filter_with_fallback()` | `fetch_filtered_with_fallback()` |
| **Multi-column AND** | `columns: [FilterColumn, ...]` | CSV → `load_multi_column_filter()` | `fetch_multi_filtered()` |
| **Direct IDs** | `direct_filter_ids`, `direct_fallback_mapping` | In-memory (composite mode) | `fetch_filtered_with_fallback()` |

### 1.5. CSV форматы по провайдерам (фактические)

| Provider | CSV формат | column_name | filter_field | fallback_column |
|----------|-----------|-------------|-------------|-----------------|
| CrossRef | `doi,title` | `doi` | `doi` | `title` |
| OpenAlex | `doi,title` | `doi` | `doi` | `title` |
| SemanticScholar | `doi,title` | `doi` | `doi` | `title` |
| **PubMed** | `pubmed_id,title` | **`pubmed_id`** | `pmid` | `title` |

### 1.6. Title-only обработка (фактическая)

CSV reader (`csv_filter_reader.py:183-189`):
```python
# Строки без primary ID получают маркер, а не пустую строку
marker = f"__title_only_{title_only_count}__"
all_ids.append(marker)
fallback_mapping[marker] = fallback_str
```

`BaseTitleFallbackHandler.process_title_only_entries()` (`base_title_fallback.py:278-334`):
- Поддерживает маркеры `__title_only_N__` (штатный режим)
- Поддерживает пустые строки `""` (legacy совместимость)
- `title = fallback_mapping.get(entry, fallback_mapping.get(""))`

### 1.7. Существующие тесты (148 тест-кейсов)

| Файл | Тестов | Покрытие |
|------|--------|----------|
| `test_base_title_fallback.py` | 9 | BaseTitleFallbackHandler events |
| `test_title_matching.py` | 27 | normalize_title, titles_match |
| `crossref/test_fallback.py` | 26 | CrossRef 3-phase |
| `openalex/test_fallback.py` | 13 | OpenAlex 3-phase |
| `pubmed/test_adapter_fallback.py` | 19 | PubMed 3-phase |
| `pubmed/test_fallback.py` | 33 | PubMed TitleFallbackHandler |
| `semanticscholar/test_fallback.py` | 21 | S2 handler |

---

## 2. АРХИТЕКТУРА 4-PHASE FALLBACK

### 2.1. Суть изменения

**Расширение текущей 3-phase стратегии до 4-phase** путём добавления
промежуточной фазы alternate ID lookup:

```
Phase 1: Primary ID batch lookup           (существует, без изменений)
Phase 2: Alternate ID lookup                ← НОВОЕ (PMID→record или DOI→record)
Phase 3: Title fallback                     (существует, без изменений)
Phase 4: Title-only                         (существует, без изменений)
```

### 2.2. Архитектурный подход (исправлено по F4)

**Новый Protocol** вместо изменения существующего порта:

```python
# domain/ports/data_source.py — НОВЫЙ Protocol
@runtime_checkable
class ExtendedFallbackDataSourcePort(FilterableDataSourcePort, Protocol):
    """Extension of FilterableDataSourcePort with 4-phase fallback.

    Adapters implementing this Protocol support an additional alternate ID
    lookup phase between primary batch and title fallback.

    Detection via isinstance() in FilteredDataSource:
        if isinstance(adapter, ExtendedFallbackDataSourcePort):
            async for record in adapter.fetch_filtered_with_extended_fallback(...):
                ...
        elif isinstance(adapter, FilterableDataSourcePort):
            async for record in adapter.fetch_filtered_with_fallback(...):
                ...
    """

    def fetch_filtered_with_extended_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        alternate_id_mapping: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with 4-phase fallback.

        Args:
            fallback_mapping: Generic {primary_id: fallback_value} for title search.
            alternate_id_mapping: Optional {primary_id: alternate_id}
                e.g., {doi: pmid} or {pmid: doi}.
        """
        ...
```

**Преимущества нового Protocol перед изменением существующего:**
- `FilterableDataSourcePort` остаётся **без изменений** → 0 breaking changes
- Адаптеры без alternate ID (CrossRef) не затрагиваются
- `FilteredDataSource` использует `isinstance()` для выбора стратегии
- Постепенная миграция: адаптеры переходят на новый Protocol по мере готовности

### 2.3. Иерархия handler классов

```
BaseTitleFallbackHandler (335 LOC — БЕЗ ИЗМЕНЕНИЙ)
    │
    ├── TitleFallbackHandler (crossref)  — БЕЗ ИЗМЕНЕНИЙ
    ├── TitleFallbackHandler (openalex)  — БЕЗ ИЗМЕНЕНИЙ
    ├── TitleFallbackHandler (pubmed)    — БЕЗ ИЗМЕНЕНИЙ
    └── S2TitleFallbackHandler           — БЕЗ ИЗМЕНЕНИЙ

BaseAlternateIdFallbackHandler (НОВЫЙ, extends BaseTitleFallbackHandler)
    │
    │   Добавляет Phase 2: process_missing_by_alternate_id()
    │
    ├── OpenAlexExtendedFallbackHandler  ← PMID → GET /works?filter=ids.pmid:{pmid}
    ├── PubMedExtendedFallbackHandler    ← DOI → esearch "{doi}[DOI]" → efetch
    └── S2ExtendedFallbackHandler        ← PMID → POST /paper/batch PMID:{pmid}
```

**CrossRef**: НЕ участвует в Phase 2 (нет PMID API). Остаётся на `FilterableDataSourcePort`.

### 2.4. API Capabilities vs Implementation Gap

| Provider | API supports Phase 2 | Current code | Required work |
|----------|---------------------|-------------|---------------|
| **OpenAlex** | `GET /works?filter=ids.pmid:{pmid}` | Нет (DOI only) | Новый `_search_by_pmid()` |
| **PubMed** | `esearch "{doi}[DOI]" → efetch` | Нет (PMID only) | Новый `_search_by_doi()` |
| **SemanticScholar** | `POST /paper/batch ids=["PMID:{pmid}"]` | Нет (DOI only) | Новый `_search_by_pmid()` |
| **CrossRef** | ❌ Нет PMID API | N/A | Phase 2 skip (отдельный ADR для PMID→DOI resolve) |

---

## 3. ПЛАН МОДИФИКАЦИИ

### Phase 1: Domain Layer

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 1.1 | `domain/ports/data_source.py` | MODIFY | Добавить **новый** Protocol `ExtendedFallbackDataSourcePort` (не менять существующий) |
| 1.2 | `domain/filtering/input_config.py:53` | MODIFY | Добавить `alternate_id_column: str \| None = None` |
| 1.3 | `domain/ports/filtering.py` | MODIFY | Добавить метод `load_filter_with_two_fallbacks()` в `InputFilterPort` |

### Phase 2: Infrastructure Common

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 2.1 | `infrastructure/adapters/common/base_alternate_id_fallback.py` | CREATE | `BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler)` |
| 2.2 | `infrastructure/adapters/common/__init__.py` | MODIFY | Экспорт нового класса |

### Phase 3: Infrastructure Adapters (реализация Phase 2 per-provider)

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 3.1 | `infrastructure/adapters/openalex/fallback.py` | MODIFY | Добавить `OpenAlexExtendedFallbackHandler` с `_search_by_pmid()` |
| 3.2 | `infrastructure/adapters/openalex/client.py` | MODIFY | Реализовать `ExtendedFallbackDataSourcePort`, метод `fetch_filtered_with_extended_fallback()` |
| 3.3 | `infrastructure/adapters/pubmed/fallback.py` | MODIFY | Добавить `PubMedExtendedFallbackHandler` с `_search_by_doi()` |
| 3.4 | `infrastructure/adapters/pubmed/pubmed_client.py` | MODIFY | Реализовать `ExtendedFallbackDataSourcePort` |
| 3.5 | `infrastructure/adapters/semanticscholar/fallback.py` | MODIFY | Добавить `S2ExtendedFallbackHandler` с `_search_by_pmid()` |
| 3.6 | `infrastructure/adapters/semanticscholar/adapter.py` | MODIFY | Реализовать `ExtendedFallbackDataSourcePort` |

**CrossRef**: НЕ затрагивается. Остаётся на `FilterableDataSourcePort`.

### Phase 4: Application Layer

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 4.1 | `application/core/filtered_data_source.py:52` | MODIFY | Добавить `self._alternate_id_mapping: dict[str, str] \| None = None` |
| 4.2 | `application/core/filtered_data_source.py:148-167` | MODIFY | Загрузка alternate_id_column из CSV (если задан) |
| 4.3 | `application/core/filtered_data_source.py:86-97` | MODIFY | Загрузка alternate_id из direct mode (direct_alternate_id_mapping) |
| 4.4 | `application/core/filtered_data_source.py:276-294` | MODIFY | `isinstance` проверка: `ExtendedFallbackDataSourcePort` → extended, иначе → стандартный |

### Phase 5: Infrastructure Input

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 5.1 | `infrastructure/adapters/input/csv_filter_reader.py` | MODIFY | Реализовать `load_filter_with_two_fallbacks()`: 3-колоночный CSV → (FilterLoadResult, fallback_mapping, alternate_id_mapping) |

### Phase 6: Configuration

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 6.1 | `configs/filter/entities/openalex/publication.yaml` | MODIFY | `alternate_id_column: "pmid"` |
| 6.2 | `configs/filter/entities/pubmed/publication.yaml` | MODIFY | `alternate_id_column: "doi"` |
| 6.3 | `configs/filter/entities/semanticscholar/publication.yaml` | MODIFY | `alternate_id_column: "pmid"` |

**CrossRef**: НЕ меняется (нет PMID API → нет alternate_id_column).

**Новый CSV формат** (3 колонки, backward-compatible):
```csv
# DOI-primary (CrossRef/OpenAlex/S2):
doi,pmid,title
10.1038/nature12345,28558982,CRISPR gene editing in human embryos
10.1016/j.cell.2020.01.001,,Novel coronavirus structure
,33264437,Machine learning predicts protein structures

# PMID-primary (PubMed):
pubmed_id,doi,title
28558982,10.1038/nature12345,CRISPR gene editing in human embryos
33264437,,Machine learning predicts protein structures
```

**Legacy 2-колоночный CSV** продолжает работать без изменений.

### Phase 7: Testing

| # | Файл | Действие | Тестов |
|---|------|----------|--------|
| 7.1 | `tests/unit/.../common/test_base_alternate_id_fallback.py` | CREATE | ~15 |
| 7.2 | `tests/unit/.../openalex/test_fallback.py` | MODIFY | +8 |
| 7.3 | `tests/unit/.../pubmed/test_fallback.py` | MODIFY | +8 |
| 7.4 | `tests/unit/.../semanticscholar/test_fallback.py` | MODIFY | +8 |
| 7.5 | `tests/unit/application/core/test_filtered_data_source.py` | MODIFY | +7 |
| 7.6 | `tests/unit/domain/filtering/test_input_config.py` | MODIFY | +3 |
| 7.7 | `tests/architecture/test_port_contracts.py` | MODIFY | +2 (new Protocol) |
| 7.8 | `tests/integration/adapters/test_openalex_pmid_fallback.py` | CREATE | ~5 (VCR) |

### Phase 8: Documentation

| # | Файл | Действие |
|---|------|----------|
| 8.1 | `docs/02-architecture/decisions/ADR-033-four-phase-publication-fallback.md` | CREATE |
| 8.2 | `docs/03-pipelines/` relevant pages | UPDATE |

---

## 4. ГРАФ ЗАВИСИМОСТЕЙ

```
Phase 1 (Domain: Protocol + Config) ─────────┐
                                               ├── Phase 4 (Application)
Phase 5 (CSV Reader) ─────────────────────────┤      │
                                               │      └── Phase 6 (Config YAMLs)
Phase 2 (Common Infra: BaseAlternateId) ──────┤
                                               ├── Phase 3 (Adapters: OA, PM, S2)
                                               │      │
                                               │      └── Phase 7.2-7.4 (Adapter tests)
                                               │
                                               └── Phase 7.1 (Common tests)

Phase 7.5-7.7 (App/Domain/Arch tests) ── depends on Phases 1, 4
Phase 8 (Docs) ── can start after Phase 1
```

**Критический путь**: Phase 1 → Phase 2 → Phase 3 → Phase 7
**Параллельные**: Phase 5 может начаться сразу после Phase 1. Phase 8 — после Phase 1.

---

## 5. РИСКИ И МИТИГАЦИЯ

### Архитектурные

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Breaking change порта | ~~Средняя~~ **Нулевая** | — | Новый Protocol `ExtendedFallbackDataSourcePort`, существующий не меняется |
| Hexagonal boundary violation | Низкая | Critical | `BaseAlternateIdFallbackHandler` зависит только от `LoggerPort`. Architecture tests |
| Обратная совместимость CSV | Низкая | Medium | `alternate_id_column` опционален, 2-колоночные CSV без изменений |
| Direct IDs mode не поддержит alternate | Средняя | Medium | Добавить `direct_alternate_id_mapping` в `InputFilterConfig` |

### Технические

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Rate limiting при Phase 2 | Высокая | High | Circuit breaker + backoff (уже в `BaseHttpAdapter`) |
| Увеличение latency | Высокая | Medium | Phase 2 = единичные запросы. Sequential by design |
| PMID→DOI для CrossRef | — | — | Out of scope. Отдельный ADR (PubMed elink) |

### Data Quality

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| False positives (PMID→record) | Низкая | Medium | PMID уникален, false positives маловероятны |
| Stale mapping | Низкая | Low | Seed pipeline обновляется регулярно |

---

## 6. МЕТРИКИ УСПЕХА

```python
# Prometheus (расширение существующих)
publication_fallback_phase_total{
    provider="openalex|pubmed|semanticscholar",
    phase="alternate_id|title|title_only",
    outcome="success|miss"
}
publication_fallback_phase_latency_seconds{provider, phase}

# Targets:
# - Phase 2 (alternate ID) success rate: ≥70% (когда alternate_id доступен)
# - Phase 3 (title) success rate: ≥40% (без изменений)
# - Общее покрытие: ≥85% (Phases 1 + 2 + 3 + 4)
```

---

## 7. ОГРАНИЧЕНИЯ (OUT OF SCOPE)

| Элемент | Причина |
|---------|---------|
| CrossRef PMID→DOI resolve | Нет PMID API. Требует PubMed elink → отдельный ADR |
| Параллельный fallback (Phase 2 ∥ Phase 3) | Sequential by design |
| Кеширование PMID↔DOI mapping | Отдельный ADR |
| Замена `BaseTitleFallbackHandler` | Unnecessary breaking change |
| Изменение типа `fallback_mapping` | Breaking change domain port |
| Изменение `FilterableDataSourcePort` | Breaking change — вместо этого новый Protocol |
| Auto-generation fallback_mapping из seed Silver | Отдельный design для composite executor |

---

## 8. ОЦЕНКА ОБЪЁМА

| Phase | Файлов | Новых | Модифицированных |
|-------|--------|-------|-----------------|
| 1. Domain | 3 | 0 | 3 |
| 2. Common Infra | 2 | 1 | 1 |
| 3. Adapters | 6 | 0 | 6 |
| 4. Application | 1 | 0 | 1 |
| 5. CSV Reader | 1 | 0 | 1 |
| 6. Config | 3 | 0 | 3 |
| 7. Tests | 8 | 2 | 6 |
| 8. Docs | 2 | 1 | 1 |
| **ИТОГО** | **26** | **4** | **22** |

---

## 9. НАБОР ПРОМТОВ ДЛЯ РЕАЛИЗАЦИИ

---

### Промт 1: Domain Layer — Новый Protocol и Config

```
Задача: Расширить domain layer для поддержки 4-phase fallback стратегии.
Создать НОВЫЙ Protocol (НЕ менять существующий FilterableDataSourcePort).

Контекст:
- FilterableDataSourcePort: src/bioetl/domain/ports/data_source.py:82-168
  Имеет 3 метода: fetch_filtered, fetch_multi_filtered, fetch_filtered_with_fallback
  Тип fallback_mapping: dict[str, str] — GENERIC {id: fallback_value}
- InputFilterConfig: src/bioetl/domain/filtering/input_config.py:24-125
  Имеет fallback_column: str | None = None
  Также: direct_filter_ids, direct_fallback_mapping, columns (multi-column)
- InputFilterPort: src/bioetl/domain/ports/filtering.py
  Имеет load_filter_with_fallback(source_path, primary_column, fallback_column)
  Возвращает tuple[FilterLoadResult, dict[str, str]]

Требования:

1. В data_source.py добавить НОВЫЙ Protocol (после FilterableDataSourcePort):

   @runtime_checkable
   class ExtendedFallbackDataSourcePort(FilterableDataSourcePort, Protocol):
       """Extension with 4-phase fallback: Primary → Alternate ID → Title → Title-Only."""

       def fetch_filtered_with_extended_fallback(
           self,
           entity_type: str,
           filter_ids: list[str],
           filter_field: str,
           fallback_mapping: dict[str, str],
           alternate_id_mapping: dict[str, str] | None = None,
           limit: int | None = None,
       ) -> AsyncIterator[dict[str, Any]]:
           """Fetch with 4-phase fallback.

           Args:
               fallback_mapping: Generic {primary_id: fallback_value} for title search.
               alternate_id_mapping: Optional {primary_id: alternate_id}
                   e.g., {doi: pmid} or {pmid: doi}.
           """
           ...

   ВАЖНО: НЕ менять FilterableDataSourcePort! Только добавить новый.

2. В input_config.py:53 добавить поле:
   alternate_id_column: str | None = None

3. В InputFilterPort (filtering.py) добавить метод:
   async def load_filter_with_two_fallbacks(
       self,
       source_path: str,
       primary_column: str,
       fallback_column: str,
       alternate_id_column: str,
   ) -> tuple[FilterLoadResult, dict[str, str], dict[str, str]]:
       """Load primary IDs, fallback mapping, and alternate ID mapping.

       Returns:
           (result, fallback_mapping, alternate_id_mapping)
           fallback_mapping: {primary_id: title} or {__title_only_N__: title}
           alternate_id_mapping: {primary_id: alternate_id}
       """

4. Обновить InputFilterConfig:
   Добавить direct_alternate_id_mapping: dict[str, str] | None = None
   для поддержки direct IDs mode.

Ограничения:
- НЕ менять FilterableDataSourcePort
- НЕ менять fallback_mapping тип
- Domain НЕ импортирует infrastructure
- Запустить: make lint && make test
```

---

### Промт 2: Infrastructure Common — BaseAlternateIdFallbackHandler

```
Задача: Создать BaseAlternateIdFallbackHandler — расширение BaseTitleFallbackHandler
для Phase 2 (alternate ID lookup).

Контекст:
- BaseTitleFallbackHandler: infrastructure/adapters/common/base_title_fallback.py (335 LOC)
  Abstract methods: _search_by_title(), _get_result_identifier()
  Concrete methods:
    process_missing_dois() — Phase 2 (title fallback для unresolved IDs)
    process_title_only_entries() — Phase 3 (поддерживает __title_only_N__ маркеры и "")
  Event naming: self._event_fallback_attempt = f"{provider_prefix}_title_fallback_attempt"
  Metadata: result["_lookup_method"] = "title_fallback" / "title_only"
- Используется: CrossRef, OpenAlex, PubMed, S2 (все наследуют, НЕ менять)

Требования:

1. Создать: infrastructure/adapters/common/base_alternate_id_fallback.py

2. Класс:
   class BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler):
       """Extends with Phase 2: alternate ID lookup.

       4-Phase strategy:
           Phase 1: Primary batch lookup (adapter)
           Phase 2: Alternate ID lookup (THIS CLASS — NEW)
           Phase 3: Title fallback (inherited: process_missing_dois)
           Phase 4: Title-only (inherited: process_title_only_entries)
       """

       @abstractmethod
       async def _search_by_alternate_id(self, alt_id: str) -> dict[str, Any] | None:
           """Search by alternate identifier (PMID or DOI)."""
           ...

       async def process_missing_by_alternate_id(
           self,
           ids: list[str],
           found_ids: set[str],
           alternate_id_mapping: dict[str, str],
           normalize_fn: Callable[[str], str | None],
           limit: int | None,
           fetched: int,
       ) -> AsyncIterator[dict[str, Any]]:
           """Phase 2: Try alternate ID before title fallback.

           For each unfound primary ID, checks alternate_id_mapping
           for an alternate identifier and searches by it.

           Yields records with:
               _lookup_method = "alternate_id_fallback"
               _original_id = original primary ID
               _alternate_id = the alternate ID used
           """
           for primary_id in ids:
               if limit and fetched >= limit:
                   return

               normalized = (normalize_fn(primary_id) or "").lower()
               if normalized in found_ids:
                   continue

               alt_id = alternate_id_mapping.get(primary_id)
               if not alt_id:
                   alt_id = alternate_id_mapping.get(normalized)
               if not alt_id:
                   self._logger.debug(
                       self._event_no_alternate_id,
                       primary_id=primary_id,
                   )
                   continue

               self._logger.info(
                   self._event_alternate_attempt,
                   primary_id=primary_id,
                   alternate_id=alt_id[:50],
               )

               try:
                   result = await self._search_by_alternate_id(alt_id)
               except Exception as e:
                   self._logger.debug(
                       self._event_alternate_error,
                       alternate_id=alt_id[:50],
                       error=str(e),
                   )
                   continue

               if result:
                   result["_lookup_method"] = "alternate_id_fallback"
                   result["_original_id"] = primary_id
                   result["_alternate_id"] = alt_id
                   # Track as found so title fallback skips this ID
                   found_ids.add(normalized)
                   id_field, id_value = self._get_result_identifier(result)
                   self._logger.info(
                       self._event_alternate_success,
                       primary_id=primary_id,
                       alternate_id=alt_id[:50],
                       **{id_field: id_value},
                   )
                   yield result
                   fetched += 1
               else:
                   self._logger.debug(
                       self._event_alternate_not_found,
                       primary_id=primary_id,
                       alternate_id=alt_id[:50],
                   )

3. Event naming (auto-generated in __init__):
   self._event_alternate_attempt = f"{provider_prefix}_alternate_id_fallback_attempt"
   self._event_alternate_success = f"{provider_prefix}_alternate_id_fallback_success"
   self._event_alternate_not_found = f"{provider_prefix}_alternate_id_fallback_not_found"
   self._event_alternate_error = f"{provider_prefix}_alternate_id_fallback_error"
   self._event_no_alternate_id = f"{provider_prefix}_no_alternate_id"

4. ВАЖНО: process_missing_by_alternate_id ДОБАВЛЯЕТ found_ids,
   чтобы последующий process_missing_dois (Phase 3) пропустил уже найденные.

5. Обновить infrastructure/adapters/common/__init__.py:
   Добавить экспорт BaseAlternateIdFallbackHandler.

Ограничения:
- Зависимости: ТОЛЬКО domain.ports.LoggerPort (TYPE_CHECKING)
- НЕ менять BaseTitleFallbackHandler
- НЕ менять существующие TitleFallbackHandler классы
- Следовать паттернам из base_title_fallback.py
- Запустить: make lint && make test
```

---

### Промт 3: OpenAlex Adapter — Phase 2 (PMID lookup)

```
Задача: Расширить OpenAlex адаптер для поддержки 4-phase fallback с PMID lookup.

Контекст:
- OpenAlex adapter: infrastructure/adapters/openalex/client.py (771 LOC)
  fetch_filtered_with_fallback(): lines 295-389
  Текущее ограничение: line 326 — `if filter_field != "doi": return`
  Не реализован: PMID lookup. API поддерживает: GET /works?filter=ids.pmid:{pmid}
- OpenAlex fallback: infrastructure/adapters/openalex/fallback.py (72 LOC)
  class TitleFallbackHandler(BaseTitleFallbackHandler) — НЕ МЕНЯТЬ
- Новый Protocol: ExtendedFallbackDataSourcePort (из Промта 1)
- Новый handler: BaseAlternateIdFallbackHandler (из Промта 2)

Требования:

1. В infrastructure/adapters/openalex/fallback.py ДОБАВИТЬ:
   class OpenAlexExtendedFallbackHandler(BaseAlternateIdFallbackHandler):
       """OpenAlex handler with PMID alternate ID lookup."""

       async def _search_by_alternate_id(self, pmid: str) -> dict[str, Any] | None:
           """Search OpenAlex by PMID.
           API: GET /works?filter=ids.pmid:{pmid}
           """
           # Delegate to adapter's _search_by_pmid method
           return await self._pmid_search_fn(pmid)

   Конструктор принимает pmid_search_fn как Callable.
   Сохранить существующий TitleFallbackHandler (обратная совместимость).

2. В infrastructure/adapters/openalex/client.py:
   a) Добавить метод _search_by_pmid(pmid: str) -> dict | None:
      - API: GET /works?filter=ids.pmid:{pmid}&per_page=1
      - Использовать self._http_client для запроса
      - Вернуть первый результат или None

   b) Реализовать ExtendedFallbackDataSourcePort:
      Добавить метод fetch_filtered_with_extended_fallback() с оркестрацией:
      Phase 1: batch DOI lookup (переиспользовать _batch_doi_lookup)
      Phase 2: PMID fallback (через _extended_handler.process_missing_by_alternate_id)
      Phase 3: title fallback (через _extended_handler.process_missing_dois)
      Phase 4: title-only (через _extended_handler.process_title_only_entries)

   c) Инициализировать _extended_handler в __init__:
      self._extended_handler = OpenAlexExtendedFallbackHandler(
          logger=self.logger,
          provider_prefix="openalex",
          search_by_title_fn=self._search_by_title,
          get_result_identifier_fn=self._get_result_identifier,
          pmid_search_fn=self._search_by_pmid,
      )

   ВАЖНО: НЕ менять существующий fetch_filtered_with_fallback!
   Он остаётся для обратной совместимости с FilterableDataSourcePort.

Ограничения:
- НЕ менять TitleFallbackHandler
- НЕ менять fetch_filtered_with_fallback
- Rate limiter через self._http_client (уже настроен)
- self.logger для structured logging
- Запустить: make lint && make test
```

---

### Промт 4: PubMed Adapter — Phase 2 (DOI lookup)

```
Задача: Расширить PubMed адаптер для 4-phase fallback с DOI lookup.

Контекст:
- PubMed adapter: infrastructure/adapters/pubmed/pubmed_client.py (629 LOC)
  fetch_filtered_with_fallback(): lines 298-379
  fetch_filtered(): line 241 — warns for filter_field != "pmid"
  Не реализован: DOI lookup. API поддерживает: esearch "{doi}[DOI]" → efetch
  Уже есть _search_by_title (lines 254-296): esearch + efetch pattern
  Уже есть _get_pmids() и _yield_articles_from_pmids()
- PubMed fallback: infrastructure/adapters/pubmed/fallback.py (83 LOC)
  class TitleFallbackHandler(BaseTitleFallbackHandler) — НЕ МЕНЯТЬ
- PubMed CSV: column_name="pubmed_id", filter_field="pmid"

Требования:

1. В infrastructure/adapters/pubmed/fallback.py ДОБАВИТЬ:
   class PubMedExtendedFallbackHandler(BaseAlternateIdFallbackHandler):
       async def _search_by_alternate_id(self, doi: str) -> dict[str, Any] | None:
           """Search PubMed by DOI via esearch.
           Query: "{doi}[DOI]" → efetch to get full record.
           """
           return await self._doi_search_fn(doi)

2. В pubmed_client.py:
   a) Добавить _search_by_doi(doi: str) -> dict | None:
      - clean_doi = doi.strip()[:200]
      - search_term = f'"{clean_doi}"[DOI]'
      - pmids = await self._get_pmids(search_term, 1)
      - Если pmids: efetch → вернуть первую запись
      - Иначе: None

   b) Реализовать ExtendedFallbackDataSourcePort:
      fetch_filtered_with_extended_fallback() с:
      Phase 1: PMID batch (переиспользовать fetch_filtered)
      Phase 2: DOI fallback (через _extended_handler.process_missing_by_alternate_id)
      Phase 3: title fallback (через _extended_handler.process_missing_dois)
      Phase 4: title-only (через _extended_handler.process_title_only_entries)

   c) PMID нормализация: normalize_fn=lambda x: x.lower().strip()

   ВАЖНО: НЕ менять fetch_filtered_with_fallback и fetch_filtered!

Ограничения:
- Rate limit: 3 req/sec (уже в адаптере)
- Использовать _get_pmids() и _yield_articles_from_pmids() (существуют)
- PubMed primary ID = PMID, alternate = DOI (обратное от DOI-провайдеров)
- Запустить: make lint && make test
```

---

### Промт 5: SemanticScholar Adapter — Phase 2 (PMID lookup)

```
Задача: Расширить SemanticScholar адаптер для 4-phase fallback с PMID batch lookup.

Контекст:
- S2 adapter: infrastructure/adapters/semanticscholar/adapter.py (596 LOC)
  fetch_filtered_with_fallback(): lines 283-345
  _batch_doi_phase(): uses POST /paper/batch with ids=["DOI:xxx"]
  Не реализован: PMID batch. API поддерживает: ids=["PMID:{pmid}"] в batch API
- S2 fallback: infrastructure/adapters/semanticscholar/fallback.py (226 LOC)
  class SemanticScholarTitleFallbackHandler(BaseTitleFallbackHandler) — НЕ МЕНЯТЬ
- S2 API batch endpoint: POST https://api.semanticscholar.org/graph/v1/paper/batch

Требования:

1. В infrastructure/adapters/semanticscholar/fallback.py ДОБАВИТЬ:
   class S2ExtendedFallbackHandler(BaseAlternateIdFallbackHandler):
       async def _search_by_alternate_id(self, pmid: str) -> dict[str, Any] | None:
           """Search S2 by PMID via batch API.
           ids=["PMID:{pmid}"]
           """
           return await self._pmid_search_fn(pmid)

2. В adapter.py:
   a) Добавить _search_by_pmid(pmid: str) -> dict | None:
      - Использовать POST /paper/batch с body={"ids": ["PMID:{pmid}"], "fields": "..."}
      - Переиспользовать _paper_fields и _build_batch_url()
      - Вернуть первый не-null результат или None

   b) Реализовать ExtendedFallbackDataSourcePort:
      fetch_filtered_with_extended_fallback() с:
      Phase 1: batch DOI (переиспользовать _batch_doi_phase)
      Phase 2: PMID fallback (process_missing_by_alternate_id)
      Phase 3: title fallback (process_missing_dois)
      Phase 4: title-only (process_title_only_entries)

   ВАЖНО: НЕ менять fetch_filtered_with_fallback!

Ограничения:
- Использовать self._http_client и self._api_key
- S2 batch API: max 500 IDs per request (для единичного — не проблема)
- Запустить: make lint && make test
```

---

### Промт 6: Application Layer — FilteredDataSource расширение

```
Задача: Расширить FilteredDataSource для поддержки alternate_id_mapping и
вызова fetch_filtered_with_extended_fallback.

Контекст:
- FilteredDataSource: application/core/filtered_data_source.py (343 LOC)
  self._fallback_mapping: dict[str, str] | None = None (line 52)
  _load_direct_filter_ids(): line 94 (direct_fallback_mapping)
  _load_single_column_filter(): lines 148-167 (CSV fallback)
  _fetch_single_column(): lines 263-294 (вызов fetch_filtered_with_fallback)
  _ensure_filterable_adapter(): line 236 (isinstance check)
- InputFilterConfig: domain/filtering/input_config.py
  Новые поля (из Промта 1): alternate_id_column, direct_alternate_id_mapping
- Новый Protocol (из Промта 1): ExtendedFallbackDataSourcePort
- InputFilterPort: load_filter_with_two_fallbacks() (из Промта 1)
- CSV маркеры: title-only строки → __title_only_N__ (csv_filter_reader.py:186)

Требования:

1. Добавить state (после line 52):
   self._alternate_id_mapping: dict[str, str] | None = None

2. В _load_direct_filter_ids() (line 94-107):
   Добавить загрузку direct_alternate_id_mapping:
   self._alternate_id_mapping = self._filter_config.direct_alternate_id_mapping

3. В _load_single_column_filter() (lines 148-167):
   Если self._filter_config.alternate_id_column задан:
   - Вызвать load_filter_with_two_fallbacks() вместо load_filter_with_fallback()
   - Сохранить alternate_id_mapping в self._alternate_id_mapping
   Если не задан — поведение не меняется (обратная совместимость).

4. В _fetch_single_column() (lines 263-294):
   Добавить isinstance проверку:

   if self._alternate_id_mapping and isinstance(
       self._data_source, ExtendedFallbackDataSourcePort
   ):
       async for record in self._data_source.fetch_filtered_with_extended_fallback(
           entity_type=entity_type,
           filter_ids=self._filter_ids,
           filter_field=config_filter_field,
           fallback_mapping=self._fallback_mapping,
           alternate_id_mapping=self._alternate_id_mapping,
           limit=limit,
       ):
           yield record
   elif self._fallback_mapping:
       # Existing path (unchanged)
       ...

5. Логирование: при загрузке alternate_id_mapping логировать размер mapping.

Ограничения:
- Обратная совместимость: без alternate_id_column — поведение НЕ меняется
- Direct IDs mode: поддержать direct_alternate_id_mapping
- 2-колоночные CSV продолжают работать
- Import ExtendedFallbackDataSourcePort из domain.ports
- Запустить: make lint && make test
```

---

### Промт 7: CSV Filter Reader — 3-колоночная загрузка

```
Задача: Реализовать load_filter_with_two_fallbacks() в CsvFilterReader
для загрузки 3-колоночного CSV.

Контекст:
- CsvFilterReader: infrastructure/adapters/input/csv_filter_reader.py
  load_filter_with_fallback() (lines 126-214):
    - Обрабатывает 3 случая: primary+title, primary only, title only
    - Title-only: создаёт маркер __title_only_N__ (line 186)
    - Возвращает: tuple[FilterLoadResult, dict[str, str]]
- InputFilterPort.load_filter_with_two_fallbacks() (из Промта 1)

Требования:

1. Добавить метод load_filter_with_two_fallbacks():
   async def load_filter_with_two_fallbacks(
       self,
       source_path: str,
       primary_column: str,
       fallback_column: str,
       alternate_id_column: str,
   ) -> tuple[FilterLoadResult, dict[str, str], dict[str, str]]:
       """Load primary, fallback, and alternate ID from CSV.

       Handles cases:
       1. primary + alternate + fallback → all three mappings
       2. primary + fallback (no alternate) → fallback only
       3. primary + alternate (no fallback) → alternate only
       4. fallback only → __title_only_N__ marker
       5. alternate only → ignore (no primary to map from)

       Returns:
           (result, fallback_mapping, alternate_id_mapping)
           fallback_mapping: {primary_id: title} or {__title_only_N__: title}
           alternate_id_mapping: {primary_id: alternate_id}
       """

2. Паттерн маркеров:
   - Title-only строки (нет primary, нет alternate) → __title_only_N__
   - Маркеры используются как ключи в fallback_mapping

3. CSV форматы для поддержки:
   DOI-primary: doi,pmid,title (alternate=pmid)
   PMID-primary: pubmed_id,doi,title (alternate=doi)
   Legacy: doi,title (alternate отсутствует → load_filter_with_fallback)

4. Логирование: info с counts (total, title_only, with_alternate, without_alternate)

Ограничения:
- Следовать паттерну load_filter_with_fallback (Polars DataFrame, iter_rows)
- Если alternate_id_column отсутствует в CSV → warning + пустой alternate_id_mapping
- Запустить: make lint && make test
```

---

### Промт 8: Configuration — Filter YAMLs

```
Задача: Добавить alternate_id_column в filter-конфигурации publication pipelines.

Контекст:
- configs/filter/entities/openalex/publication.yaml (fallback_column: "title")
- configs/filter/entities/pubmed/publication.yaml (fallback_column: "title",
  column_name: "pubmed_id", filter_field: "pmid")
- configs/filter/entities/semanticscholar/publication.yaml (fallback_column: "title")
- CrossRef НЕ меняется (нет PMID API → Phase 2 невозможен)

Требования:

1. OpenAlex publication.yaml:
   alternate_id_column: "pmid"   # Phase 2: GET /works?filter=ids.pmid:{pmid}

2. PubMed publication.yaml:
   alternate_id_column: "doi"    # Phase 2: esearch "{doi}[DOI]"

3. SemanticScholar publication.yaml:
   alternate_id_column: "pmid"   # Phase 2: POST /paper/batch PMID:{pmid}

4. НЕ менять CrossRef (нет Phase 2).

5. Обновить комментарии в каждом файле для пояснения 4-phase стратегии.

Ограничения:
- Только ДОБАВИТЬ поле — НЕ менять существующие
- Обратная совместимость: если alternate_id_column не указан → 3-phase
```

---

### Промт 9: Testing — Полный набор тестов

```
Задача: Написать тесты для 4-phase fallback стратегии.

Контекст:
- Существующие тесты (148 кейсов) — НЕ МЕНЯТЬ
- Новые компоненты:
  - ExtendedFallbackDataSourcePort (domain Protocol)
  - BaseAlternateIdFallbackHandler (common infra)
  - OpenAlexExtendedFallbackHandler, PubMedExtendedFallbackHandler, S2ExtendedFallbackHandler
  - FilteredDataSource (расширенная логика)
  - CsvFilterReader.load_filter_with_two_fallbacks()
- Title-only маркеры: __title_only_N__ (csv_filter_reader.py:186)

Требования:

1. СОЗДАТЬ tests/unit/infrastructure/adapters/common/test_base_alternate_id_fallback.py (~15):
   - test_process_missing_found_by_alternate_id: alt ID найден → yield + metadata
   - test_process_missing_alternate_id_not_found: alt ID не найден → skip to Phase 3
   - test_process_missing_alternate_id_exception: Exception → log + skip
   - test_process_missing_respects_limit: limit enforcement
   - test_process_missing_skips_found_ids: already found → skip
   - test_process_missing_no_alternate_in_mapping: нет alt ID → skip
   - test_process_missing_empty_mapping: пустой mapping → 0 results
   - test_event_names_auto_generated: verify event naming convention
   - test_metadata_injection: _lookup_method, _original_id, _alternate_id
   - test_found_ids_updated: found_ids пополняется для Phase 3 skip
   - test_normalize_fn_applied: normalize_fn корректно вызывается
   Каждый тест: in-memory fakes, verify structured events.

2. МОДИФИЦИРОВАТЬ adapter тесты (добавить, не менять существующие):
   OpenAlex (+8): _search_by_pmid(), 4-phase orchestration, PMID API call
   PubMed (+8): _search_by_doi(), 4-phase orchestration, DOI esearch
   SemanticScholar (+8): _search_by_pmid(), 4-phase orchestration, PMID batch

3. МОДИФИЦИРОВАТЬ tests/unit/application/core/test_filtered_data_source.py (+7):
   - test_extended_fallback_with_alternate_id: isinstance → extended path
   - test_standard_fallback_without_alternate: fallback_mapping only → existing path
   - test_alternate_id_loading_from_csv: 3-column CSV → alternate_id_mapping
   - test_alternate_id_loading_direct_mode: direct_alternate_id_mapping
   - test_backward_compat_two_column_csv: 2-column CSV → no alternate
   - test_adapter_without_extended_protocol: instanceof → standard fallback
   - test_alternate_id_none_when_not_configured: no alternate_id_column → None

4. МОДИФИЦИРОВАТЬ tests/unit/domain/filtering/test_input_config.py (+3):
   - test_alternate_id_column_optional: default None
   - test_alternate_id_column_set: value preserved
   - test_direct_alternate_id_mapping: config with direct mapping

5. МОДИФИЦИРОВАТЬ tests/architecture/test_port_contracts.py (+2):
   - test_extended_fallback_protocol_inherits_filterable
   - test_extended_fallback_protocol_runtime_checkable

6. СОЗДАТЬ tests/integration/adapters/test_openalex_pmid_fallback.py (~5, VCR):
   - test_pmid_lookup_existing_paper: PMID → record
   - test_pmid_lookup_nonexistent: PMID → None
   - test_four_phase_orchestration: DOI miss → PMID hit
   VCR кассеты: tests/fixtures/vcr/openalex_pmid_*.yaml

Ограничения:
- НЕ менять существующие тесты
- pytest + pytest-asyncio
- In-memory fakes (unit), VCR.py (integration)
- Запустить: make test
```

---

### Промт 10: ADR-033 и Documentation

```
Задача: Создать ADR-033 для 4-phase publication fallback стратегии.

Контекст:
- 31 ADR в docs/02-architecture/decisions/ (последний: ADR-031)
- Формат: ADR-NNN-kebab-case-title.md
- Язык: Русский, RFC 2119 keywords (как в RULES.md)
- Связанные ADR: ADR-026 (Composite Pipeline), ADR-028 (Filter Rules)

Требования:

1. Создать docs/02-architecture/decisions/ADR-033-four-phase-publication-fallback.md:

   Title: Four-Phase Publication Fallback Strategy
   Status: Proposed
   Date: 2026-01-30

   Context:
   - Текущая 3-phase стратегия (Primary → Title → Title-Only) не использует
     доступные cross-identifiers (PMID↔DOI)
   - OpenAlex, PubMed, S2 API поддерживают PMID и DOI, но адаптеры
     реализуют только primary ID lookup
   - CrossRef не имеет PMID API

   Decision:
   - Новый Protocol: ExtendedFallbackDataSourcePort
   - Новый handler: BaseAlternateIdFallbackHandler
   - 4 phases: Primary → Alternate ID → Title → Title-only
   - Per-provider: OA (PMID), PM (DOI), S2 (PMID). CrossRef: skip Phase 2

   Consequences:
   - (+) ≥15-25% recall improvement для publication pipelines
   - (+) 0 breaking changes (новый Protocol, existing untouched)
   - (-) +1 API запрос per unresolved ID (Phase 2)
   - (-) Увеличение latency для unresolved IDs

   Alternatives Considered:
   1. Изменение FilterableDataSourcePort → отвергнуто (breaking change, все адаптеры)
   2. Изменение fallback_mapping типа → отвергнуто (breaks domain port + 4 adapters)
   3. UnifiedPublicationFallbackHandler → отвергнуто (unnecessary replacement)
   4. Parallel Phase 2 + Phase 3 → отвергнуто (complexity, sequential by design)

   References: ADR-026, ADR-028

2. Обновить docs по CSV форматам (если есть):
   Добавить описание 3-колоночного CSV и alternate_id_column.

Ограничения:
- Формат существующих ADR
- Русский язык
```

---

*Консолидировано из 3 аудиторских отчётов. Все 8 замечаний учтены.*
*Верифицировано: 2026-01-30. Ссылки на файл:строку проверены.*
