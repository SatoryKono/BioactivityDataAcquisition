# FALLBACK СТРАТЕГИИ: ВЕРИФИЦИРОВАННЫЙ ПЛАН МОДИФИКАЦИИ v2

> **Дата верификации**: 2026-01-30
> **Метод верификации**: Полный анализ кодовой базы (Read + Grep + Glob)
> **Статус**: Верифицирован и скорректирован

---

## 0. КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ ОТНОСИТЕЛЬНО ПЛАНА v1

> **ВАЖНО**: Первоначальный план содержал ряд фактических ошибок.
> Ниже приведены исправления с ссылками на код.

| # | Ошибка в плане v1 | Реальность (верифицировано) |
|---|---|---|
| 1 | "PubMed: PMID → Title (2-phase)" | **УЖЕ 3-phase**: Primary PMID → Title Fallback → Title-Only (`pubmed_client.py:298-379`, `pubmed/fallback.py`) |
| 2 | "CrossRef: DOI → Title (2-phase)" | **УЖЕ 3-phase**: Batch DOI → Title Fallback → Title-Only (`crossref/client.py:232-265`, `crossref/fallback.py`) |
| 3 | "SemanticScholar: DOI → Title (2-phase)" | **УЖЕ 3-phase**: POST /paper/batch → Title Fallback → Title-Only (`semanticscholar/adapter.py:316-345`, `semanticscholar/fallback.py`) |
| 4 | "UniProt: accession → gene_name (2-phase)" | UniProt использует **generic fallback** (accession → альтернативный идентификатор), НЕ title-based (`uniprot/client.py:393-410`) |
| 5 | "Нужно расширить до three-phase: DOI → PMID → Title" | Фактически предлагается **4-phase**: Primary ID → Alternate ID (PMID/DOI) → Title Fallback → Title-Only. Текущая 3-phase стратегия уже реализована |
| 6 | Plan references `publication_input_filter.py` | Файл **НЕ существует**. Реальный файл: `application/core/filtered_data_source.py` (343 строки) |
| 7 | "Модификация Adapter Signature: `dict[str, tuple]`" | Текущий тип `fallback_mapping: dict[str, str]` определён в domain port (`data_source.py:150`). Изменение сломает ВСЕ 4 адаптера + application layer |
| 8 | Plan предлагает `UnifiedPublicationFallbackHandler` | `BaseTitleFallbackHandler` (335 строк) УЖЕ существует в `common/base_title_fallback.py` и используется 4-мя адаптерами. Замена = breaking change |

---

## 1. ВЕРИФИЦИРОВАННОЕ ТЕКУЩЕЕ СОСТОЯНИЕ

### 1.1. Архитектура Fallback (фактическая)

```
FilterableDataSourcePort (domain/ports/data_source.py:82-168)
    │
    ├── fetch_filtered()              → Phase 1: Primary batch lookup
    ├── fetch_filtered_with_fallback() → Phases 1-3 orchestration
    │       │
    │       │   fallback_mapping: dict[str, str]  ← {primary_id: title}
    │       │
    │       ├── Phase 1: Primary ID batch → adapter-specific
    │       ├── Phase 2: Title fallback   → BaseTitleFallbackHandler.process_missing_dois()
    │       └── Phase 3: Title-only       → BaseTitleFallbackHandler.process_title_only_entries()
    │
    └── fetch_multi_filtered()         → Multi-column AND filtering
```

### 1.2. Компоненты текущей инфраструктуры

| Компонент | Файл | LOC | Назначение |
|-----------|------|-----|------------|
| `FilterableDataSourcePort` | `domain/ports/data_source.py:82-168` | 87 | Domain Protocol (interface) |
| `BaseTitleFallbackHandler` | `infrastructure/adapters/common/base_title_fallback.py` | 335 | Base class (Template Method) |
| `titles_match()` | `infrastructure/adapters/common/title_matching.py` | 90 | Title comparison utility |
| `FilteredDataSource` | `application/core/filtered_data_source.py` | 343 | Decorator: CSV → fetch_filtered_with_fallback |
| `InputFilterConfig` | `domain/filtering/input_config.py` | 125 | Config: fallback_column (single string) |

### 1.3. Реализации по провайдерам (верифицировано)

| Provider | Handler | Primary ID | Phases | Fallback Type | Search Capability |
|----------|---------|-----------|--------|--------------|-------------------|
| **CrossRef** | `TitleFallbackHandler` (96 LOC) | DOI (batch 50) | 3 | `{doi: title}` | DOI (native), Title (search API) |
| **OpenAlex** | `TitleFallbackHandler` (72 LOC) | DOI (batch 50) | 3 | `{doi: title}` | DOI (filter), Title (title.search), **PMID** (`ids.pmid` filter) |
| **PubMed** | `TitleFallbackHandler` (83 LOC) | PMID (batch 200) | 3 | `{pmid: title}` | PMID (efetch), Title (esearch[Title]), **DOI** (esearch) |
| **SemanticScholar** | `SemanticScholarTitleFallbackHandler` (226 LOC) | DOI (POST batch) | 3 | `{doi: title}` | DOI (batch), Title (search), **PMID** (`PMID:` prefix in batch) |
| **UniProt** | Generic (inline) | accession | 2 | `{accession: gene}` | accession, gene_name |

### 1.4. Текущий формат CSV фильтров

```yaml
# configs/filter/entities/crossref/publication.yaml:17-23
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  fallback_column: "title"    # ← ОДИН столбец fallback
```

**Текущий CSV формат** (2 колонки):
```csv
doi,title
10.1038/nature12345,CRISPR gene editing in human embryos
10.1016/j.cell.2020.01.001,Novel coronavirus structure
```

### 1.5. Существующие тесты (148 тест-кейсов)

| Тестовый файл | Тестов | Покрытие |
|--------------|--------|----------|
| `tests/unit/.../common/test_base_title_fallback.py` | 9 | BaseTitleFallbackHandler events, result processing |
| `tests/unit/.../common/test_title_matching.py` | 27 | normalize_title, titles_match (exact/substring/fuzzy) |
| `tests/unit/.../crossref/test_fallback.py` | 26 | CrossRef TitleFallbackHandler, 3-phase processing |
| `tests/unit/.../openalex/test_fallback.py` | 13 | OpenAlex TitleFallbackHandler |
| `tests/unit/.../pubmed/test_adapter_fallback.py` | 19 | PubMed 3-phase fetch_filtered_with_fallback |
| `tests/unit/.../pubmed/test_fallback.py` | 33 | PubMed TitleFallbackHandler, events, title matching |
| `tests/unit/.../semanticscholar/test_fallback.py` | 21 | S2 handler, API headers, search, metrics |

---

## 2. ПРЕДЛАГАЕМАЯ АРХИТЕКТУРА (СКОРРЕКТИРОВАННАЯ)

### 2.1. Суть изменения

**Расширение текущей 3-phase стратегии до 4-phase:**

```
Phase 1: Primary ID batch lookup     (существует)
Phase 2: Alternate ID lookup          ← НОВОЕ (PMID→DOI или DOI→PMID)
Phase 3: Title fallback               (существует, сдвигается с Phase 2)
Phase 4: Title-only                   (существует, сдвигается с Phase 3)
```

### 2.2. Стратегия минимальных изменений

Вместо замены `BaseTitleFallbackHandler` на `UnifiedPublicationFallbackHandler`, предлагается **расширение** существующей иерархии:

```
BaseTitleFallbackHandler (335 LOC, существует — БЕЗ ИЗМЕНЕНИЙ)
    │
    ├── TitleFallbackHandler (crossref)  — БЕЗ ИЗМЕНЕНИЙ
    ├── TitleFallbackHandler (openalex)  — БЕЗ ИЗМЕНЕНИЙ
    ├── TitleFallbackHandler (pubmed)    — БЕЗ ИЗМЕНЕНИЙ
    └── SemanticScholarTitleFallbackHandler — БЕЗ ИЗМЕНЕНИЙ

BaseAlternateIdFallbackHandler (НОВЫЙ, extends BaseTitleFallbackHandler)
    │
    │   Добавляет Phase 2: process_missing_ids_by_alternate()
    │   Вызывается ДО process_missing_dois (title fallback)
    │
    ├── CrossRefAlternateIdHandler     ← PMID → DOI search (через PubMed API)
    ├── OpenAlexAlternateIdHandler     ← PMID → OpenAlex /works?filter=ids.pmid:X
    ├── PubMedAlternateIdHandler       ← DOI → PMID search (esearch)
    └── SemanticScholarAlternateIdHandler ← PMID → POST /paper/batch PMID:X
```

### 2.3. Изменения в Domain Port

**Вариант A (минимальный, рекомендуется)**: НЕ менять `FilterableDataSourcePort`.

Расширить `InputFilterConfig` для поддержки нескольких fallback-колонок:

```python
# domain/filtering/input_config.py — РАСШИРЕНИЕ
@dataclass(frozen=True, slots=True)
class InputFilterConfig:
    ...
    fallback_column: str | None = None           # Существует (title)
    alternate_id_column: str | None = None        # НОВОЕ (pmid или doi)
```

Расширить `FilteredDataSource` для загрузки дополнительной колонки:

```python
# application/core/filtered_data_source.py — РАСШИРЕНИЕ
class FilteredDataSource:
    ...
    self._fallback_mapping: dict[str, str] | None = None        # Существует
    self._alternate_id_mapping: dict[str, str] | None = None     # НОВОЕ
```

Расширить `FilterableDataSourcePort` с новым методом:

```python
# domain/ports/data_source.py — НОВЫЙ МЕТОД
class FilterableDataSourcePort(DataSourcePort, Protocol):
    ...
    def fetch_filtered_with_extended_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],           # {id: title}
        alternate_id_mapping: dict[str, str] | None, # {id: pmid/doi}
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with 4-phase fallback: Primary → Alternate ID → Title → Title-Only."""
        ...
```

**Вариант B (альтернативный)**: Расширить fallback_mapping тип.

```python
# Тип fallback_mapping меняется:
# Было:  dict[str, str]                           # {doi: title}
# Стало: dict[str, str] | dict[str, FallbackInfo]  # Union для обратной совместимости

@dataclass(frozen=True, slots=True)
class FallbackInfo:
    """Extended fallback data for multi-phase resolution."""
    title: str | None = None
    alternate_id: str | None = None
    alternate_id_type: str | None = None  # "pmid" | "doi"
```

> **Рекомендация**: Вариант A — обратная совместимость, минимум изменений domain port.

### 2.4. API Capabilities по провайдерам (верифицировано)

| Provider | PMID → Record | DOI → Record | API Method |
|----------|--------------|-------------|------------|
| **CrossRef** | ❌ Нет нативного PMID API | ✅ GET /works/{doi} | Нужен промежуточный PMID→DOI resolve |
| **OpenAlex** | ✅ `filter=ids.pmid:{pmid}` | ✅ `filter=doi:{doi}` | Нативная поддержка обоих |
| **PubMed** | ✅ efetch (нативный) | ✅ esearch `{doi}[DOI]` | Нативная поддержка обоих |
| **SemanticScholar** | ✅ `PMID:{pmid}` в batch API | ✅ `DOI:{doi}` в batch API | Нативная поддержка обоих |

**Вывод**: CrossRef — единственный провайдер БЕЗ нативного PMID API. Для CrossRef Phase 2 (PMID fallback) невозможен без внешнего PMID→DOI resolve.

---

## 3. ПЛАН МОДИФИКАЦИИ (ПОШАГОВЫЙ)

### Phase 1: Domain Layer (расширение интерфейсов)

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 1.1 | `domain/filtering/input_config.py:53` | MODIFY | Добавить `alternate_id_column: str \| None = None` |
| 1.2 | `domain/ports/data_source.py` | MODIFY | Добавить метод `fetch_filtered_with_extended_fallback()` |
| 1.3 | `domain/context.py:40` | MODIFY | Добавить `alternate_id_column` в `InputFilterContext` |

### Phase 2: Infrastructure Common (новый base handler)

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 2.1 | `infrastructure/adapters/common/base_alternate_id_fallback.py` | CREATE | `BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler)` |
| 2.2 | `infrastructure/adapters/common/__init__.py` | MODIFY | Экспорт нового класса |

**Ключевой класс** `BaseAlternateIdFallbackHandler`:

```python
class BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler):
    """Extends BaseTitleFallbackHandler with alternate ID lookup (Phase 2).

    4-Phase strategy:
        Phase 1: Primary batch lookup (adapter-specific)
        Phase 2: Alternate ID lookup (NEW - this class)
        Phase 3: Title fallback (inherited from BaseTitleFallbackHandler)
        Phase 4: Title-only (inherited from BaseTitleFallbackHandler)
    """

    @abstractmethod
    async def _search_by_alternate_id(self, alt_id: str) -> dict[str, Any] | None:
        """Search by alternate identifier (PMID or DOI)."""
        ...

    async def process_missing_by_alternate_id(
        self,
        ids: list[str],
        found_ids: set[str],
        alternate_id_mapping: dict[str, str],  # {primary_id: alternate_id}
        normalize_fn: Callable[[str], str | None],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Phase 2: Try alternate ID before falling back to title."""
        ...
```

### Phase 3: Infrastructure Adapters (4-phase интеграция)

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 3.1 | `infrastructure/adapters/openalex/fallback.py` | MODIFY | Наследовать `BaseAlternateIdFallbackHandler`, добавить `_search_by_pmid()` |
| 3.2 | `infrastructure/adapters/openalex/client.py` | MODIFY | Вызов Phase 2 перед Phase 3 в `fetch_filtered_with_extended_fallback()` |
| 3.3 | `infrastructure/adapters/pubmed/fallback.py` | MODIFY | Наследовать `BaseAlternateIdFallbackHandler`, добавить `_search_by_doi()` |
| 3.4 | `infrastructure/adapters/pubmed/pubmed_client.py` | MODIFY | Вызов Phase 2 |
| 3.5 | `infrastructure/adapters/semanticscholar/fallback.py` | MODIFY | Наследовать `BaseAlternateIdFallbackHandler`, добавить `_search_by_pmid()` |
| 3.6 | `infrastructure/adapters/semanticscholar/adapter.py` | MODIFY | Вызов Phase 2 |
| 3.7 | `infrastructure/adapters/crossref/client.py` | MODIFY | Реализовать `fetch_filtered_with_extended_fallback()` с пропуском Phase 2 |
| 3.8 | `infrastructure/adapters/filterable_mixin.py` | MODIFY | Добавить stub для нового метода |

**Примечание по CrossRef**: CrossRef НЕ имеет PMID API, поэтому Phase 2 пропускается. CrossRef может участвовать в Phase 2 только если внедрить PMID→DOI resolve через внешний сервис (PubMed elink), что выходит за scope данного плана.

### Phase 4: Application Layer (расширение)

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 4.1 | `application/core/filtered_data_source.py:52` | MODIFY | Добавить `self._alternate_id_mapping: dict[str, str] \| None = None` |
| 4.2 | `application/core/filtered_data_source.py:148-167` | MODIFY | Загрузка alternate_id_column из CSV |
| 4.3 | `application/core/filtered_data_source.py:276-284` | MODIFY | Вызов `fetch_filtered_with_extended_fallback()` при наличии alternate_id_mapping |

### Phase 5: Configuration

| # | Файл | Действие | Описание |
|---|------|----------|----------|
| 5.1 | `configs/filter/entities/crossref/publication.yaml` | MODIFY | Добавить `alternate_id_column: "pmid"` (CrossRef пропустит Phase 2) |
| 5.2 | `configs/filter/entities/openalex/publication.yaml` | MODIFY | Добавить `alternate_id_column: "pmid"` |
| 5.3 | `configs/filter/entities/pubmed/publication.yaml` | MODIFY | Добавить `alternate_id_column: "doi"` |
| 5.4 | `configs/filter/entities/semanticscholar/publication.yaml` | MODIFY | Добавить `alternate_id_column: "pmid"` |

**Новый CSV формат** (3 колонки):
```csv
doi,pmid,title
10.1038/nature12345,28558982,CRISPR gene editing in human embryos
10.1016/j.cell.2020.01.001,,Novel coronavirus structure reveals drug targets
,33264437,Machine learning predicts protein structures
```

### Phase 6: Testing

| # | Файл | Действие | Тестов |
|---|------|----------|--------|
| 6.1 | `tests/unit/.../common/test_base_alternate_id_fallback.py` | CREATE | ~15 |
| 6.2 | `tests/unit/.../openalex/test_fallback.py` | MODIFY | +8 |
| 6.3 | `tests/unit/.../pubmed/test_fallback.py` | MODIFY | +8 |
| 6.4 | `tests/unit/.../semanticscholar/test_fallback.py` | MODIFY | +8 |
| 6.5 | `tests/unit/.../crossref/test_fallback.py` | MODIFY | +3 (skip Phase 2) |
| 6.6 | `tests/unit/application/core/test_filtered_data_source.py` | MODIFY | +5 |
| 6.7 | `tests/integration/adapters/test_openalex_pmid_fallback.py` | CREATE | ~5 (VCR) |

### Phase 7: Documentation

| # | Файл | Действие |
|---|------|----------|
| 7.1 | `docs/02-architecture/decisions/ADR-033-four-phase-fallback.md` | CREATE |
| 7.2 | `docs/03-pipelines/` relevant docs | UPDATE |

---

## 4. РИСКИ И МИТИГАЦИЯ

### Архитектурные

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Нарушение Hexagonal boundary | Низкая | Critical | `BaseAlternateIdFallbackHandler` в infrastructure, зависит только от `LoggerPort`. Architecture tests (`tests/architecture/`) |
| Breaking change domain port | Средняя | High | Новый метод `fetch_filtered_with_extended_fallback()` вместо изменения существующего. `DelegatingFallbackMixin` получает stub |
| Обратная совместимость CSV | Низкая | Medium | Колонка `alternate_id_column` — опциональная. Существующие 2-колоночные CSV работают без изменений |

### Технические

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| Rate limiting при Phase 2 | Высокая | High | Circuit breaker + exponential backoff (уже реализован в `BaseHttpAdapter`) |
| Увеличение latency (4 phases) | Высокая | Medium | Phase 2 — единичные запросы, не batch. Sequential execution по design |
| CrossRef без PMID API | — | — | Phase 2 пропускается. Future: PMID→DOI resolve через PubMed elink (отдельный ADR) |

### Data Quality

| Риск | Вероятность | Воздействие | Митигация |
|------|-------------|-------------|-----------|
| False positives при PMID→record | Низкая | Medium | PMID — уникальный идентификатор, false positives маловероятны |
| Stale PMID↔DOI mapping | Низкая | Low | Seed pipeline (ChEMBL) обновляется регулярно |

---

## 5. МЕТРИКИ УСПЕХА

```python
# Prometheus counters (расширение существующих)
publication_fallback_phase_total{provider, phase="alternate_id|title|title_only", outcome="success|miss"}
publication_fallback_phase_latency_seconds{provider, phase}

# Targets:
# - Phase 2 (alternate ID) success rate: ≥70% (когда alternate_id доступен)
# - Phase 3 (title) success rate: ≥40% (остаётся)
# - Общее покрытие: ≥85% (Phase 1 + 2 + 3)
```

---

## 6. ОГРАНИЧЕНИЯ (OUT OF SCOPE)

| Элемент | Причина |
|---------|---------|
| CrossRef PMID→DOI resolve (через PubMed elink) | Требует cross-adapter dependency. Отдельный ADR |
| Параллельный fallback (Phase 2 \|\| Phase 3) | Sequential execution для упрощения. Future optimization |
| Кеширование PMID↔DOI mapping | Отдельный ADR |
| Автоматическая генерация fallback_mapping из seed Silver | Требует design composite pipeline executor |
| Замена `BaseTitleFallbackHandler` на `UnifiedPublicationFallbackHandler` | Unnecessary breaking change. Расширение через наследование |
| Изменение типа `fallback_mapping: dict[str, str]` | Breaking change domain port + 4 адаптера. Вместо этого — новый параметр |

---

## 7. ПОРЯДОК РЕАЛИЗАЦИИ И ЗАВИСИМОСТИ

```
Phase 1 (Domain) ──────────┐
                            ├── Phase 4 (Application) ── Phase 5 (Config) ── Phase 7 (Docs)
Phase 2 (Common Infra) ────┤
                            ├── Phase 3 (Adapters) ───── Phase 6 (Tests)
                            │
                            └── Phase 6.1 (Common Tests)
```

**Критический путь**: Phase 1 → Phase 2 → Phase 3 → Phase 6
**Параллельные**: Phase 4 + Phase 5 могут начаться сразу после Phase 1

---

## 8. НАБОР ПРОМТОВ ДЛЯ РЕАЛИЗАЦИИ

### Промт 1: Domain Layer Extension

```
Задача: Расширить domain layer для поддержки 4-phase fallback стратегии.

Контекст:
- FilterableDataSourcePort определён в src/bioetl/domain/ports/data_source.py:82-168
- InputFilterConfig определён в src/bioetl/domain/filtering/input_config.py:24-125
- InputFilterContext определён в src/bioetl/domain/context.py

Требования:
1. В InputFilterConfig (input_config.py:53) добавить поле:
   alternate_id_column: str | None = None
   Это опциональное поле для второй fallback-колонки (например "pmid" для DOI-primary pipelines)

2. В FilterableDataSourcePort (data_source.py) добавить НОВЫЙ метод
   (НЕ менять существующий fetch_filtered_with_fallback!):

   def fetch_filtered_with_extended_fallback(
       self,
       entity_type: str,
       filter_ids: list[str],
       filter_field: str,
       fallback_mapping: dict[str, str],
       alternate_id_mapping: dict[str, str] | None = None,
       limit: int | None = None,
   ) -> AsyncIterator[dict[str, Any]]:
       """Fetch with 4-phase fallback: Primary → Alternate ID → Title → Title-Only.

       Extension of fetch_filtered_with_fallback that adds an intermediate
       alternate ID lookup phase between primary batch and title fallback.

       Args:
           alternate_id_mapping: Optional mapping {primary_id: alternate_id}
               e.g., {doi: pmid} or {pmid: doi} for cross-identifier resolution.
       """
       ...

3. В InputFilterContext (context.py) добавить:
   alternate_id_column: str | None = None
   И обновить factory methods (from_config, from_ids) соответственно.

4. В DelegatingFallbackMixin (infrastructure/adapters/filterable_mixin.py) добавить
   stub-реализацию нового метода, которая делегирует в fetch_filtered_with_fallback
   (игнорируя alternate_id_mapping).

Ограничения:
- НЕ менять существующий fetch_filtered_with_fallback — обратная совместимость
- НЕ менять существующий fallback_mapping тип (dict[str, str])
- Следовать Hexagonal Architecture: domain НЕ импортирует infrastructure
- Запустить make lint && make test после изменений
```

### Промт 2: Infrastructure Common (Base Alternate ID Handler)

```
Задача: Создать BaseAlternateIdFallbackHandler — расширение BaseTitleFallbackHandler
для Phase 2 (alternate ID lookup).

Контекст:
- BaseTitleFallbackHandler: infrastructure/adapters/common/base_title_fallback.py (335 LOC)
  - process_missing_dois(): Phase 2 (title fallback) → станет Phase 3
  - process_title_only_entries(): Phase 3 (title-only) → станет Phase 4
- Existing event naming: {provider}_title_fallback_attempt, etc.

Требования:
1. Создать файл: infrastructure/adapters/common/base_alternate_id_fallback.py

2. Класс BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler):
   - Добавляет Phase 2: alternate ID lookup
   - НЕ переопределяет методы BaseTitleFallbackHandler
   - Новый абстрактный метод: _search_by_alternate_id(alt_id: str) -> dict | None
   - Новый метод: process_missing_by_alternate_id(
       ids: list[str],
       found_ids: set[str],
       alternate_id_mapping: dict[str, str],
       normalize_fn: Callable,
       limit: int | None,
       fetched: int,
     ) -> AsyncIterator[dict[str, Any]]

3. Event naming convention (auto-generated from provider_prefix):
   - {provider}_alternate_id_fallback_attempt
   - {provider}_alternate_id_fallback_success
   - {provider}_alternate_id_fallback_not_found
   - {provider}_no_alternate_id

4. Metadata injection:
   - _lookup_method = "alternate_id_fallback"
   - _original_id = original primary ID

5. Обновить infrastructure/adapters/common/__init__.py:
   Добавить экспорт BaseAlternateIdFallbackHandler

Ограничения:
- Зависимости: ТОЛЬКО domain.ports.LoggerPort (TYPE_CHECKING)
- НЕ менять BaseTitleFallbackHandler
- НЕ менять существующие TitleFallbackHandler классы
- Следовать паттернам из base_title_fallback.py (event properties, truncation, etc.)
- Запустить make lint && make test
```

### Промт 3: OpenAlex Adapter (4-phase integration)

```
Задача: Расширить OpenAlex адаптер для поддержки Phase 2 (PMID fallback).

Контекст:
- OpenAlex adapter: infrastructure/adapters/openalex/client.py (771 LOC)
- OpenAlex fallback: infrastructure/adapters/openalex/fallback.py (72 LOC)
  - TitleFallbackHandler(BaseTitleFallbackHandler)
- OpenAlex API поддерживает PMID фильтрацию: GET /works?filter=ids.pmid:{pmid}
- Текущая 3-phase: batch DOI → title fallback → title-only

Требования:
1. В infrastructure/adapters/openalex/fallback.py:
   - Создать новый класс ExtendedFallbackHandler(BaseAlternateIdFallbackHandler)
   - Реализовать _search_by_alternate_id(pmid) → GET /works?filter=ids.pmid:{pmid}
   - Сохранить существующий TitleFallbackHandler для обратной совместимости

2. В infrastructure/adapters/openalex/client.py:
   - Добавить метод fetch_filtered_with_extended_fallback()
   - Orchestration: Phase 1 (batch DOI) → Phase 2 (PMID lookup) → Phase 3 (title) → Phase 4 (title-only)
   - Добавить метод _search_by_pmid(pmid: str) → dict | None
     API: GET /works?filter=ids.pmid:{pmid}

3. Обновить __init__.py если нужно.

Ограничения:
- НЕ менять существующий fetch_filtered_with_fallback (обратная совместимость)
- НЕ менять TitleFallbackHandler (только добавить новый класс)
- Использовать rate limiter через self._http_client
- Использовать self._logger для structured logging
- Запустить make lint && make test
```

### Промт 4: SemanticScholar Adapter (4-phase integration)

```
Задача: Расширить SemanticScholar адаптер для поддержки Phase 2 (PMID fallback).

Контекст:
- S2 adapter: infrastructure/adapters/semanticscholar/adapter.py (596 LOC)
- S2 fallback: infrastructure/adapters/semanticscholar/fallback.py (226 LOC)
  - SemanticScholarTitleFallbackHandler(BaseTitleFallbackHandler)
- S2 batch API поддерживает PMID: POST /paper/batch с ids=["PMID:12345678"]
- Текущая 3-phase: POST /paper/batch (DOI:) → title search → title-only

Требования:
1. В infrastructure/adapters/semanticscholar/fallback.py:
   - Создать ExtendedFallbackHandler(BaseAlternateIdFallbackHandler)
   - Реализовать _search_by_alternate_id(pmid) → POST /paper/batch с PMID:{pmid}
   - Сохранить SemanticScholarTitleFallbackHandler для обратной совместимости

2. В infrastructure/adapters/semanticscholar/adapter.py:
   - Добавить fetch_filtered_with_extended_fallback()
   - Phase 2: для unfound DOIs — попробовать PMID через batch API
   - Добавить _search_by_pmid(pmid: str) → dict | None
     API: POST /paper/batch body={"ids": ["PMID:{pmid}"], "fields": "..."}

Ограничения:
- НЕ менять существующие методы
- Использовать self._http_client и существующие headers
- API key через self._api_key (если задан)
- Запустить make lint && make test
```

### Промт 5: PubMed Adapter (4-phase integration)

```
Задача: Расширить PubMed адаптер для поддержки Phase 2 (DOI fallback).

Контекст:
- PubMed adapter: infrastructure/adapters/pubmed/pubmed_client.py (629 LOC)
- PubMed fallback: infrastructure/adapters/pubmed/fallback.py (83 LOC)
  - TitleFallbackHandler(BaseTitleFallbackHandler)
- PubMed Primary ID = PMID. Alternate ID = DOI
- PubMed esearch поддерживает DOI: query="10.1038/nature12345[DOI]"

Требования:
1. В infrastructure/adapters/pubmed/fallback.py:
   - Создать ExtendedFallbackHandler(BaseAlternateIdFallbackHandler)
   - Реализовать _search_by_alternate_id(doi) → esearch с "{doi}[DOI]" → efetch
   - Сохранить TitleFallbackHandler для обратной совместимости

2. В infrastructure/adapters/pubmed/pubmed_client.py:
   - Добавить fetch_filtered_with_extended_fallback()
   - Phase 2: для unfound PMIDs — попробовать DOI через esearch
   - Добавить _search_by_doi(doi: str) → dict | None
     API: esearch query="{doi}[DOI]" → efetch (get full record)

Ограничения:
- НЕ менять существующие методы
- Rate limit: 3 req/sec (уже в адаптере)
- Использовать существующий _build_efetch_url, _parse_xml_articles
- Запустить make lint && make test
```

### Промт 6: CrossRef Adapter (stub Phase 2)

```
Задача: Добавить fetch_filtered_with_extended_fallback в CrossRef адаптер.

Контекст:
- CrossRef adapter: infrastructure/adapters/crossref/client.py (458 LOC)
- CrossRef НЕ имеет нативного PMID API
- Phase 2 для CrossRef = skip (log + continue to Phase 3)

Требования:
1. В infrastructure/adapters/crossref/client.py:
   - Добавить fetch_filtered_with_extended_fallback()
   - Phase 2: пропускается (log info "crossref_no_pmid_api_support")
   - Делегирует Phases 1, 3, 4 в существующую логику fetch_filtered_with_fallback

2. НЕ создавать ExtendedFallbackHandler для CrossRef — нет PMID API.

Ограничения:
- Максимально делегировать в существующий код
- НЕ менять fetch_filtered_with_fallback
- Запустить make lint && make test
```

### Промт 7: Application Layer (FilteredDataSource extension)

```
Задача: Расширить FilteredDataSource для загрузки alternate_id_column и вызова
fetch_filtered_with_extended_fallback.

Контекст:
- FilteredDataSource: application/core/filtered_data_source.py (343 LOC)
- Текущая логика загрузки fallback: lines 148-167 (_load_single_column_filter)
- Текущий вызов fallback: lines 276-284 (_fetch_single_column)
- InputFilterPort.load_filter_with_fallback() в domain/ports/filtering.py:142

Требования:
1. В filtered_data_source.py:
   - Добавить self._alternate_id_mapping: dict[str, str] | None = None (строка ~52)
   - В _load_single_column_filter: если config.alternate_id_column задан,
     загрузить дополнительный mapping через InputFilterPort
   - В _fetch_single_column: если self._alternate_id_mapping не None,
     вызвать fetch_filtered_with_extended_fallback() вместо fetch_filtered_with_fallback()

2. В domain/ports/filtering.py (InputFilterPort):
   - Добавить метод load_filter_with_two_fallbacks() или расширить
     load_filter_with_fallback для поддержки двух fallback колонок

3. В infrastructure/adapters/input/csv_filter_reader.py:
   - Реализовать загрузку трёх колонок из CSV

Ограничения:
- Обратная совместимость: 2-колоночные CSV продолжают работать
- Если alternate_id_column не указан — поведение не меняется
- Запустить make lint && make test
```

### Промт 8: Configuration Update

```
Задача: Обновить filter-конфигурации для поддержки alternate_id_column.

Контекст:
- configs/filter/entities/crossref/publication.yaml (fallback_column: "title")
- configs/filter/entities/openalex/publication.yaml (fallback_column: "title")
- configs/filter/entities/pubmed/publication.yaml (fallback_column: "title")
- configs/filter/entities/semanticscholar/publication.yaml

Требования:
1. Добавить alternate_id_column в каждый filter config:

   CrossRef:    alternate_id_column: "pmid"    # Phase 2 skipped (no PMID API)
   OpenAlex:    alternate_id_column: "pmid"    # Phase 2: filter=ids.pmid:{pmid}
   PubMed:      alternate_id_column: "doi"     # Phase 2: {doi}[DOI] search
   S2:          alternate_id_column: "pmid"    # Phase 2: PMID:{pmid} batch

2. Обновить composite/publication.yaml output_keys (line 46-50):
   Добавить pmid в join_keys для enrichers если отсутствует

Ограничения:
- НЕ менять существующие поля
- Только ДОБАВИТЬ alternate_id_column
```

### Промт 9: Testing

```
Задача: Написать тесты для 4-phase fallback стратегии.

Контекст (существующие тесты — 148 кейсов):
- tests/unit/infrastructure/adapters/common/test_base_title_fallback.py (9 тестов)
- tests/unit/infrastructure/adapters/common/test_title_matching.py (27 тестов)
- tests/unit/infrastructure/adapters/crossref/test_fallback.py (26 тестов)
- tests/unit/infrastructure/adapters/openalex/test_fallback.py (13 тестов)
- tests/unit/infrastructure/adapters/pubmed/test_adapter_fallback.py (19 тестов)
- tests/unit/infrastructure/adapters/pubmed/test_fallback.py (33 тестов)
- tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py (21 тестов)

Требования:
1. СОЗДАТЬ tests/unit/infrastructure/adapters/common/test_base_alternate_id_fallback.py:
   - test_process_missing_by_alternate_id_success: Alt ID found → yield result
   - test_process_missing_by_alternate_id_not_found: Alt ID not found → skip
   - test_process_missing_by_alternate_id_error: Exception → log + skip
   - test_process_missing_by_alternate_id_limit: Respects limit
   - test_process_missing_by_alternate_id_already_found: Skip found IDs
   - test_process_missing_by_alternate_id_no_mapping: No alt ID in mapping → skip
   - test_event_names: Auto-generated event names с provider_prefix
   - test_metadata_injection: _lookup_method = "alternate_id_fallback"
   - test_empty_alternate_id_mapping: Empty mapping → no Phase 2 results
   ~15 тест-кейсов

2. МОДИФИЦИРОВАТЬ тесты адаптеров:
   - OpenAlex: +8 тестов (PMID search, 4-phase orchestration)
   - PubMed: +8 тестов (DOI search, 4-phase orchestration)
   - SemanticScholar: +8 тестов (PMID batch, 4-phase orchestration)
   - CrossRef: +3 тестов (Phase 2 skip, delegation)

3. МОДИФИЦИРОВАТЬ tests/unit/application/core/test_filtered_data_source.py:
   - +5 тестов (alternate_id_mapping loading, extended fallback call)

4. Каждый тест ДОЛЖЕН:
   - Использовать in-memory fakes (не HTTP)
   - Проверять event logging (structured events)
   - Проверять metadata injection (_lookup_method, _original_id)
   - Проверять limit enforcement

Ограничения:
- НЕ менять существующие тесты (обратная совместимость)
- Использовать pytest + pytest-asyncio
- Следовать паттернам из существующих fallback тестов
- Запустить make test для проверки
```

### Промт 10: ADR и Documentation

```
Задача: Создать ADR-033 для 4-phase fallback стратегии.

Контекст:
- 31 существующих ADR в docs/02-architecture/decisions/
- Формат: ADR-NNN-kebab-case-title.md
- Последний: ADR-031

Требования:
1. Создать docs/02-architecture/decisions/ADR-033-four-phase-publication-fallback.md

2. Структура ADR:
   - Title: Four-Phase Publication Fallback Strategy
   - Status: Proposed
   - Context: Текущая 3-phase стратегия (Primary → Title → Title-Only) не использует
     доступные cross-identifier (PMID↔DOI) для повышения recall
   - Decision: Расширить до 4-phase: Primary → Alternate ID → Title → Title-Only
   - Consequences:
     - Положительные: +15-25% recall для publication pipelines
     - Отрицательные: +1 API запрос per unresolved ID, увеличение latency
   - Alternatives Considered:
     - Замена BaseTitleFallbackHandler (отвергнуто: breaking change)
     - Изменение fallback_mapping типа (отвергнуто: breaks domain port)
   - References: ADR-026 (Composite Pipeline), ADR-028 (Filter Rules)

Ограничения:
- Следовать формату существующих ADR
- Русский язык для описаний (как в RULES.md)
```

---

## 9. ОЦЕНКА ОБЪЁМА

| Phase | Файлов | Новых | Модифицированных | Оценка |
|-------|--------|-------|-----------------|--------|
| 1. Domain | 3 | 0 | 3 | Малый |
| 2. Common Infra | 2 | 1 | 1 | Малый |
| 3. Adapters | 8 | 0 | 8 | Средний |
| 4. Application | 3 | 0 | 3 | Средний |
| 5. Config | 5 | 0 | 5 | Малый |
| 6. Tests | 7 | 2 | 5 | Средний |
| 7. Docs | 1 | 1 | 0 | Малый |
| **ИТОГО** | **29** | **4** | **25** | — |

---

*Верифицировано: 2026-01-30. Все утверждения подкреплены ссылками на файл:строку.*
