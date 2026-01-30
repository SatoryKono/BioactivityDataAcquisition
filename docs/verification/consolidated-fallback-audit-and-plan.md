# Consolidated Fallback Strategy Audit & Implementation Plan

**Дата**: 2026-01-30
**Scope**: Publication fallback стратегия (CrossRef, OpenAlex, PubMed, SemanticScholar, UniProt)
**Источники**: 3 независимых аудита (v1 2026-01-30, v2 2026-02-01, v3 2026-01-30)
**Версия**: 1.0.0

---

## 1. Методология консолидации

Три аудита проводились независимо и сходятся по ключевым выводам, различаясь в оценке
критичности (severity) и степени детализации рекомендаций.

| Критерий | Аудит v1 | Аудит v2 | Аудит v3 |
|----------|----------|----------|----------|
| **Findings** | 5 (3 MUST, 2 SHOULD) | 5 (2 SHOULD, 3 MAY) | 7 (6 MODERATE, 1 MINOR) |
| **Фокус** | Ошибки плана, порт-контракт | Capabilities adapters | CSV-формат, multi-mode, fallback_mapping семантика |
| **План** | Минимальный, ExtendedProtocol | Детальный, BaseAlternateIdHandler | Точное текущее состояние, минимум prescription |

---

## 2. Консолидированные замечания (по убыванию критичности)

### 2.1. [CRITICAL] Отсутствие cross-ID lookup в адаптерах

**Сходимость**: 3/3 аудитов (v1: MUST, v2: SHOULD+MAY, v3: MODERATE×3)

Исходный план заявляет существование PMID/DOI cross-lookups, но код подтверждает их
отсутствие:

| Адаптер | Файл:строки | Текущий primary ID | Cross-ID lookup | Статус |
|---------|------------|-------------------|-----------------|--------|
| **OpenAlex** | `client.py:326-332` | DOI only | PMID → нет | Guard: `filter_field != "doi"` → return |
| **SemanticScholar** | `adapter.py:283-345` | DOI only | PMID → нет | `valid_dois` — только DOI обрабатываются |
| **PubMed** | `pubmed_client.py:241-246` | PMID only | DOI → нет | Warning: `filter_field != "pmid"` → assumes PMIDs |
| **CrossRef** | `client.py:149-154` | DOI only | PMID → нет API | Warning only, DOI assumed |

**Вердикт**: CRITICAL — план описывает несуществующую функциональность как текущую.
Все cross-ID lookups — это **новая разработка**, а не расширение существующей.

### 2.2. [SIGNIFICANT] Противоречие в архитектурном подходе к порту

**Сходимость**: 1/3 явно (v1: MUST), 2/3 неявно (v2 и v3 предлагают альтернативы)

v1 указывает: план заявляет «порт не менять», но затем добавляет метод в
`FilterableDataSourcePort`. Текущий порт (`data_source.py:82-168`) содержит:
- `fetch_filtered()` — primary lookup
- `fetch_multi_filtered()` — AND-логика
- `fetch_filtered_with_fallback()` — primary + title fallback

Добавление 4-phase метода требует **одного из**:
1. Нового Protocol (`ExtendedFallbackDataSourcePort`) — v1/v2 рекомендуют
2. Расширения существующего метода (breaking change) — нежелательно
3. Common-layer handler без изменения порта — v3 допускает

**Вердикт**: SIGNIFICANT — необходимо выбрать стратегию расширения до реализации.

### 2.3. [MODERATE] Семантика fallback_mapping шире, чем «title»

**Сходимость**: 1/3 явно (v3), 2/3 неявно (v1/v2 описывают только title)

`fallback_mapping: dict[str, str]` в порте (`data_source.py:150`) — обобщённый маппинг
`{primary_id: fallback_value}`. UniProt использует его для gene name, не title.
Plan описывает только `{DOI: title}` / `{PMID: title}`.

**Вердикт**: MODERATE — план должен использовать обобщённую формулировку и уточнять
«title» только для publication контекста.

### 2.4. [MODERATE] Title-only записи кодируются маркерами, не пустыми строками

**Сходимость**: 3/3 аудитов (v1: SHOULD, v2: MAY, v3: MODERATE)

Фактическое поведение (`csv_filter_reader.py:184-189`):
```python
marker = f"__title_only_{title_only_count}__"
all_ids.append(marker)
fallback_mapping[marker] = fallback_str
```

`BaseTitleFallbackHandler` (`base_title_fallback.py:304-310`) поддерживает оба формата:
маркеры `__title_only_N__` и legacy пустые строки.

**Вердикт**: MODERATE — план должен корректно описать формат маркеров.

### 2.5. [MODERATE] Пропущены существующие режимы фильтрации

**Сходимость**: 2/3 аудитов (v2: MAY, v3: MODERATE)

`InputFilterConfig` (`input_config.py:47-55`) поддерживает:
- **Single-column** — `column_name` + `fallback_column`
- **Multi-column** — `columns: tuple[FilterColumn, ...]` (AND-логика)
- **Direct IDs** — `direct_filter_ids` + `direct_fallback_mapping`

`FilteredDataSource` (`filtered_data_source.py:94-167`) реализует все три режима загрузки.

План описывает только single-column, что неполно.

**Вердикт**: MODERATE — план должен учитывать все три режима фильтрации.

### 2.6. [LOW] PubMed CSV: колонка pubmed_id, не doi

**Сходимость**: 2/3 аудитов (v1: SHOULD, v3: MINOR)

`configs/filter/entities/pubmed/publication.yaml:20-21`:
```yaml
column_name: "pubmed_id"
filter_field: "pmid"
```

**Вердикт**: LOW — документационное уточнение.

---

## 3. Верифицированное текущее состояние

### 3.1. Адаптеры публикаций — фактические возможности

| Адаптер | Primary ID | 3-Phase Fallback | Title Fallback | Title-Only | filter_field guard |
|---------|-----------|-----------------|----------------|------------|-------------------|
| **CrossRef** | DOI | ✅ | ✅ | ✅ | Warning only (`client.py:149`) |
| **OpenAlex** | DOI | ✅ | ✅ | ✅ | **Strict** return (`client.py:326-332`) |
| **PubMed** | PMID | ✅ | ✅ | ✅ | Warning only (`pubmed_client.py:241`) |
| **SemanticScholar** | DOI | ✅ | ✅ | ✅ | Warning only (`adapter.py:227`) |
| **UniProt** | Accession | ✅ (2-phase) | Generic fallback | — | Entity validation only |

### 3.2. Текущая 3-phase стратегия

```
Phase 1: Batch lookup по primary ID (DOI/PMID/accession)
         ↓ (unresolved IDs)
Phase 2: Title fallback через BaseTitleFallbackHandler.process_missing_dois()
         ↓ (title-only markers)
Phase 3: Title-only через BaseTitleFallbackHandler.process_title_only_entries()
```

### 3.3. Input filtering — три режима

| Режим | Config поля | Реализация |
|-------|-------------|------------|
| Single-column + fallback | `column_name`, `fallback_column` | `filtered_data_source.py:148-167` |
| Multi-column (AND) | `columns: tuple[FilterColumn, ...]` | `filtered_data_source.py:132-146` |
| Direct IDs | `direct_filter_ids`, `direct_fallback_mapping` | `filtered_data_source.py:94-107` |

### 3.4. CSV-форматы по провайдерам

| Провайдер | CSV колонки | filter_field | Config |
|-----------|-------------|-------------|--------|
| CrossRef | `doi,title` | `doi` | `crossref/publication.yaml:20-23` |
| OpenAlex | `doi,title` | `doi` | `openalex/publication.yaml:20-23` |
| SemanticScholar | `doi,title` | `doi` | `semanticscholar/publication.yaml:20-23` |
| PubMed | `pubmed_id,title` | `pmid` | `pubmed/publication.yaml:20-23` |

---

## 4. Консолидированный план: 4-Phase Fallback

### 4.1. Целевая архитектура

```
Phase 1: Batch lookup по primary ID (DOI/PMID/accession)
         ↓ (unresolved IDs)
Phase 2: Alternate ID lookup (DOI↔PMID cross-resolution)   ← NEW
         ↓ (still unresolved)
Phase 3: Title fallback (search by title string)
         ↓ (title-only markers)
Phase 4: Title-only lookup (entries without primary/alternate ID)
```

### 4.2. Архитектурные решения

#### Решение A: Расширение порта (рекомендуется)

**Новый Protocol**, не изменение существующего:

```python
# domain/ports/data_source.py
@runtime_checkable
class ExtendedFallbackDataSourcePort(FilterableDataSourcePort, Protocol):
    """Adapter supporting 4-phase fallback with alternate ID."""

    def fetch_filtered_with_extended_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],       # primary_id → title/fallback_value
        alternate_id_mapping: dict[str, str],    # primary_id → alternate_id
        alternate_id_field: str,                 # e.g. "pmid" for DOI→PMID
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

**Обоснование**:
- Не ломает существующий контракт `FilterableDataSourcePort`
- `FilteredDataSource` проверяет `isinstance(adapter, ExtendedFallbackDataSourcePort)`
- Адаптеры мигрируют на новый Protocol по мере реализации Phase 2

#### Решение B: Handler в common-слое

```python
# infrastructure/adapters/common/base_alternate_id_fallback.py
class BaseAlternateIdFallbackHandler(BaseTitleFallbackHandler):
    """Extends 3-phase to 4-phase with alternate ID resolution."""

    async def process_missing_by_alternate_id(
        self,
        missing_ids: list[str],
        alternate_id_mapping: dict[str, str],
        search_fn: Callable[[str], AsyncIterator[dict[str, Any]]],
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

### 4.3. Изменения по слоям

#### Domain

| Компонент | Изменение | Файл |
|-----------|----------|------|
| `ExtendedFallbackDataSourcePort` | Новый Protocol | `domain/ports/data_source.py` |
| `InputFilterConfig` | `+ alternate_id_column: str \| None = None` | `domain/filtering/input_config.py` |
| `InputFilterContext` | `+ alternate_id_mapping: dict[str, str]` | `domain/filtering/input_config.py` |

#### Application

| Компонент | Изменение | Файл |
|-----------|----------|------|
| `FilteredDataSource` | Загрузка alternate_id_column, вызов extended fallback | `application/core/filtered_data_source.py` |
| `InputFilterPort` | `+ load_filter_with_alternate()` | `domain/ports/input_filter.py` |

#### Infrastructure — Common

| Компонент | Изменение | Файл |
|-----------|----------|------|
| `BaseAlternateIdFallbackHandler` | Новый класс (extends BaseTitleFallbackHandler) | `infrastructure/adapters/common/` |
| `CsvFilterReader` | `+ load_filter_with_two_fallbacks()` | `infrastructure/adapters/input/` |

#### Infrastructure — Adapters (provider-specific)

| Адаптер | Что реализовать | API endpoint |
|---------|----------------|--------------|
| **OpenAlex** | PMID → works | `GET /works?filter=ids.pmid:{pmid}` |
| **SemanticScholar** | PMID → paper/batch | `POST /paper/batch` с `ids=["PMID:{pmid}"]` |
| **PubMed** | DOI → esearch+efetch | `esearch.fcgi?term="{doi}"[DOI]` → efetch |
| **CrossRef** | Пропуск Phase 2 | Нет PMID API — fallback через Phase 3 |
| **UniProt** | Без изменений | Accession-based, Phase 2 не применяется |

### 4.4. Конфигурация

Расширить YAML-конфиги publication pipelines:

```yaml
# Пример: crossref/publication.yaml
input_filter:
  enabled: true
  source_path: "data/input/dois.csv"
  column_name: "doi"
  filter_field: "doi"
  batch_size: 100
  fallback_column: "title"
  alternate_id_column: "pmid"       # NEW — optional

# Пример: pubmed/publication.yaml
input_filter:
  enabled: true
  source_path: "data/input/pubmed.csv"
  column_name: "pubmed_id"
  filter_field: "pmid"
  batch_size: 100
  fallback_column: "title"
  alternate_id_column: "doi"        # NEW — optional
```

CSV-форматы (расширенные):
- **DOI-провайдеры**: `doi,pmid,title` (pmid — optional column)
- **PubMed**: `pubmed_id,doi,title` (doi — optional column)
- Legacy 2-column формат остаётся совместимым (alternate_id_column=None)

### 4.5. Тестирование

| Уровень | Что тестировать |
|---------|----------------|
| **Unit** | `BaseAlternateIdFallbackHandler` — Phase 2 routing, empty mapping, partial hits |
| **Unit** | `CsvFilterReader.load_filter_with_two_fallbacks()` — 3-column CSV, legacy 2-column |
| **Unit** | `FilteredDataSource` — загрузка alternate_id_mapping, isinstance dispatch |
| **Unit** | Каждый адаптер — Phase 2 lookup (OpenAlex PMID, S2 PMID, PubMed DOI) |
| **Architecture** | `ExtendedFallbackDataSourcePort` — contract tests |
| **Integration** | VCR-кассеты для cross-ID API calls |

### 4.6. Документация

- **ADR-033**: `four-phase-publication-fallback.md` — архитектурное решение
- **Input filter docs**: обновить CSV-форматы, описание 3 режимов фильтрации
- **RULES.md**: обновить §2 (Medallion) если затронуто

---

## 5. Матрица сходимости аудитов

| # | Замечание | v1 | v2 | v3 | Консолид. |
|---|---------|------|------|------|-----------|
| 1 | OpenAlex: нет PMID lookup | MUST | SHOULD | MODERATE | **CRITICAL** |
| 2 | SemanticScholar: нет PMID batch | MUST | MAY | MODERATE | **CRITICAL** |
| 3 | PubMed: нет DOI lookup | (implicit) | SHOULD | MODERATE | **CRITICAL** |
| 4 | Противоречие в подходе к порту | MUST | — | — | **SIGNIFICANT** |
| 5 | fallback_mapping ≠ всегда title | — | — | MODERATE | **MODERATE** |
| 6 | Title-only = маркеры, не пустые строки | SHOULD | MAY | MODERATE | **MODERATE** |
| 7 | Пропущены multi-column/direct IDs | — | MAY | MODERATE | **MODERATE** |
| 8 | PubMed CSV: pubmed_id колонка | SHOULD | — | MINOR | **LOW** |

**Легенда сходимости**: число после «/» = сколько аудитов упомянули замечание.

---

## 6. Рекомендуемый порядок реализации

```
Этап 1 (Foundation):
  ├─ ADR-033
  ├─ ExtendedFallbackDataSourcePort (domain)
  ├─ InputFilterConfig + alternate_id_column (domain)
  └─ BaseAlternateIdFallbackHandler (common)

Этап 2 (CSV & Application):
  ├─ CsvFilterReader.load_filter_with_two_fallbacks()
  ├─ FilteredDataSource — alternate_id dispatch
  └─ Unit tests для foundation + CSV

Этап 3 (Adapters — параллельно):
  ├─ OpenAlex: _search_by_pmid() + integration в fallback
  ├─ SemanticScholar: PMID batch lookup
  ├─ PubMed: DOI → esearch[DOI] + efetch
  └─ VCR-кассеты для каждого

Этап 4 (Config & Docs):
  ├─ Обновить YAML-конфиги (alternate_id_column)
  ├─ Подготовить 3-column CSV примеры
  └─ Обновить документацию
```

---

## Verification Log (объединённый)

```bash
# OpenAlex — DOI-only guard
sed -n '326,332p' src/bioetl/infrastructure/adapters/openalex/client.py

# SemanticScholar — DOI-only processing
sed -n '283,345p' src/bioetl/infrastructure/adapters/semanticscholar/adapter.py

# PubMed — PMID-only processing
sed -n '241,246p' src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py

# CrossRef — DOI-only, warning
sed -n '149,154p' src/bioetl/infrastructure/adapters/crossref/client.py

# Port definition
sed -n '82,168p' src/bioetl/domain/ports/data_source.py

# Title-only markers
sed -n '184,189p' src/bioetl/infrastructure/adapters/input/csv_filter_reader.py

# BaseTitleFallbackHandler marker support
sed -n '304,310p' src/bioetl/infrastructure/adapters/common/base_title_fallback.py

# InputFilterConfig fields
sed -n '47,55p' src/bioetl/domain/filtering/input_config.py

# FilteredDataSource loading modes
sed -n '94,167p' src/bioetl/application/core/filtered_data_source.py

# PubMed config
sed -n '17,23p' configs/filter/entities/pubmed/publication.yaml
```
