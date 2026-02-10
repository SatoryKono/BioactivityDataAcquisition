# Publication Type Normalization Analysis

**Дата:** 2026-02-10
**Версия:** 1.0.0
**Scope:** Нормализация полей publication_type в composite publication pipeline

---

## Executive Summary

Нормализация полей `publication_type` в BioETL происходит в **два этапа**:

1. **Silver Layer Transformation** — провайдер-специфичные raw типы классифицируются с помощью унифицированной 3-уровневой иерархии (214 типов, 4 провайдера)
2. **Composite Pipeline Merging** — все provider-qualified поля сохраняются (preserve_all_sources=true), coalescing НЕ происходит

**Ключевые файлы:**
- `domain/mapping/publication_type_classification.py` — 214 mappings (OpenAlex, CrossRef, PubMed, SemanticScholar)
- `application/pipelines/common/base_publication_transformer.py` — метод `_classify_publication_type()`
- `configs/composite/field_groups/publication.yaml` — field grouping для composite
- Provider transformers — вызывают классификацию для каждой записи

---

## Часть 1: Исходные Поля от Провайдеров (Bronze Layer)

### 1.1 CrossRef

**Поле:** `type` (строка)

**Примеры значений:**
- `"journal-article"`
- `"proceedings-article"`
- `"book-chapter"`
- `"posted-content"` (preprint)
- `"peer-review"`

**Mapping table:** 191 уникальных mappings (строки 59-1423 в classification.py)

---

### 1.2 OpenAlex

**Поле:** `type` (строка)

**Примеры значений:**
- `"article"`
- `"book"`
- `"dataset"`
- `"review"`
- `"editorial"`
- `"preprint"`

**Mapping table:** 191 уникальных mappings (column 4 в _CLASSIFICATION_TABLE)

---

### 1.3 PubMed

**Поля:**
- Внутри XML: `<PublicationType>` (множественные значения)
- После парсинга: список строк

**Примеры значений:**
```python
["Journal Article", "Research Support, NIH, Extramural"]
["Clinical Trial", "Randomized Controlled Trial"]
["Review", "Systematic Review"]
["Meta-Analysis"]
```

**Mapping table:** 191 уникальных mappings (column 6 в _CLASSIFICATION_TABLE)

**Особенность:** Multi-value provider — классификатор выбирает **наиболее специфичный тип** (highest specificity row number)

---

### 1.4 SemanticScholar

**Поле:** `publicationTypes` (список строк)

**Примеры значений:**
```python
["JournalArticle"]
["Conference"]
["Review"]
["CaseReport", "JournalArticle"]
["MetaAnalysis"]
```

**Mapping table:** 191 уникальных mappings (column 7 в _CLASSIFICATION_TABLE)

**Особенность:** Multi-value provider — классификатор выбирает **наиболее специфичный тип**

---

### 1.5 ChEMBL

**Поле:** `doc_type` (строка)

**Примеры значений:**
- `"PUBLICATION"`
- `"PATENT"`
- `"DATASET"`
- `"BOOK"`

**Mapping:** Использует константу `PUBLICATION_TYPES` из `domain/schemas/constants.py` (line 187-194):

```python
PUBLICATION_TYPES: frozenset[str] = frozenset([
    "PUBLICATION",
    "PATENT",
    "DATASET",
    "BOOK",
])
```

**Отличие:** ChEMBL использует ограниченный enum (4 значения), не участвует в unified classification с 214 типами.

---

## Часть 2: Унифицированная Классификация (3-Level Hierarchy)

### 2.1 Архитектура Классификации

**Файл:** `src/bioetl/domain/mapping/publication_type_classification.py`

**Структура:**

```python
@dataclass(frozen=True, slots=True)
class PublicationTypeEntry:
    unified_type: str       # Level 3: 214 типов (e.g., "Journal Article")
    subclass: str           # Level 2: ~25 groupings (e.g., "Original Experimental Data")
    class_code: str         # Level 1: 3 codes (EXP | REV | PEER)
    specificity: int        # Row number (higher = more specific)
```

**Level 1: Class Code (3 значения)**
- `EXP` — Experimental (original research)
- `REV` — Review (secondary literature)
- `PEER` — Peer Review

**Level 2: Subclass (~25 groupings)**
- Original Experimental Data
- Reviews & Syntheses
- Editorial & Commentary
- Corrections & Retractions
- Books & Monographs
- Reference & Encyclopedic
- Guidelines & Consensus
- Standards
- Journal / Proceedings Infrastructure
- Grants & Funding
- Biographical & Historical
- Educational & Instructional
- Visual / Media
- Literary / Miscellaneous
- Administrative / Catalogs / Legal
- Format / Meta-types

**Level 3: Unified Type (214 значений)**

См. примеры в таблице ниже.

---

### 2.2 Примеры Mapping

| Row | Unified Type | Subclass | Class | OpenAlex | CrossRef | PubMed | S2 |
|-----|-------------|----------|-------|----------|----------|--------|-----|
| 2 | Journal Article | Original Experimental Data | EXP | article | journal-article | Journal Article | JournalArticle |
| 3 | Conference Paper | Original Experimental Data | EXP | article* | proceedings-article | Congress | Conference |
| 4 | Preprint | Original Experimental Data | EXP | preprint | posted-content | Preprint | — |
| 5 | Dataset | Original Experimental Data | EXP | dataset | dataset | Dataset | Dataset |
| 14 | Case Report | Original Experimental Data | EXP | — | — | Case Reports | CaseReport |
| 16 | Clinical Trial | Original Experimental Data | EXP | — | — | Clinical Trial | ClinicalTrial |
| 39 | Review | Reviews & Syntheses | REV | review | — | Review | Review |
| 40 | Systematic Review | Reviews & Syntheses | REV | — | — | Systematic Review | — |
| 41 | Meta-Analysis | Reviews & Syntheses | REV | — | — | Meta-Analysis | MetaAnalysis |
| 45 | Editorial | Editorial & Commentary | REV | editorial | — | Editorial | Editorial |
| 57 | Erratum | Corrections & Retractions | REV | erratum | — | Published Erratum | — |
| 63 | Book | Books & Monographs | REV | book | book | — | Book |
| 1 | Peer Review | Peer Review | PEER | peer-review | peer-review | — | — |

**Примечание:**
- `*` (asterisk suffix) — вторичный mapping (e.g., OpenAlex "article" → Conference Paper OR Journal Article)
- `—` — нет mapping для этого провайдера

---

### 2.3 Функция Классификации

**Файл:** `src/bioetl/domain/mapping/publication_type_classification.py:1585`

```python
def classify_publication_type(
    provider: str,
    raw_type: str | None = None,
    raw_types_list: list[str] | None = None,
) -> PublicationTypeEntry | None:
    """Classify a publication type using the unified 3-level hierarchy.

    For single-value providers (OpenAlex, CrossRef): uses raw_type for
    a direct lookup.

    For multi-value providers (PubMed, Semantic Scholar): iterates
    raw_types_list, collects all matches, and returns the entry with
    the highest specificity (largest row number = most specific type).

    Args:
        provider: Provider name ("openalex", "crossref", "pubmed", "semanticscholar").
        raw_type: Single raw type string (for OpenAlex / CrossRef).
        raw_types_list: List of raw type strings (for PubMed / S2).

    Returns:
        The matching PublicationTypeEntry, or None if no match.
    """
```

**Lookup Tables (built at import time):**
- `_OPENALEX_LOOKUP: dict[str, PublicationTypeEntry]`
- `_CROSSREF_LOOKUP: dict[str, PublicationTypeEntry]`
- `_PUBMED_LOOKUP: dict[str, PublicationTypeEntry]`
- `_S2_LOOKUP: dict[str, PublicationTypeEntry]`

**Normalization:** Keys normalized to lowercase (`"JournalArticle"` → `"journalarticle"`)

**Multi-value strategy:**
```python
# PubMed example: ["Journal Article", "Clinical Trial", "Randomized Controlled Trial"]
# Returns: "Randomized Controlled Trial" (row 287, most specific)
best: PublicationTypeEntry | None = None
for raw in raw_types_list:
    entry = lookup.get(raw.strip().lower())
    if entry is not None and (best is None or entry.specificity > best.specificity):
        best = entry
return best
```

---

## Часть 3: Трансформация в Silver Layer

### 3.1 BasePublicationTransformer

**Файл:** `src/bioetl/application/pipelines/common/base_publication_transformer.py:206`

**Метод:**

```python
def _classify_publication_type(
    self,
    provider: str,
    raw_type: str | None = None,
    raw_types_list: list[str] | None = None,
) -> dict[str, str | None]:
    """Classify publication type using the unified 3-level hierarchy.

    Delegates to domain classification module.

    Returns:
        Dict with keys publication_type_unified, publication_subclass,
        publication_class (all str | None).
    """
    entry = classify_publication_type(
        provider, raw_type=raw_type, raw_types_list=raw_types_list
    )
    if entry is None:
        return {
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
        }
    return {
        "publication_type_unified": entry.unified_type,
        "publication_subclass": entry.subclass,
        "publication_class": entry.class_code,
    }
```

**Возвращает 3 поля:**
- `publication_type_unified` — Level 3 (e.g., "Journal Article")
- `publication_subclass` — Level 2 (e.g., "Original Experimental Data")
- `publication_class` — Level 1 (e.g., "EXP")

---

### 3.2 CrossRef Transformer

**Файл:** `src/bioetl/application/pipelines/crossref/transformer.py:177-178`

```python
return {
    # ... other fields ...
    "publication_type": rec.get("type"),  # Raw CrossRef type
    **self._classify_publication_type("crossref", raw_type=rec.get("type")),
    # ... other fields ...
}
```

**Пример:**

Bronze record:
```json
{
  "DOI": "10.1038/nature12345",
  "type": "journal-article",
  "title": ["Example Article"]
}
```

Silver record:
```python
{
    "doi": "10.1038/nature12345",
    "publication_type": "journal-article",  # Raw
    "publication_type_unified": "Journal Article",  # Level 3
    "publication_subclass": "Original Experimental Data",  # Level 2
    "publication_class": "EXP",  # Level 1
    # ...
}
```

---

### 3.3 OpenAlex Transformer

**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py:241-242`

```python
return {
    # ... other fields ...
    "publication_type": rec.get("type"),  # Raw OpenAlex type
    **self._classify_publication_type("openalex", raw_type=rec.get("type")),
    # ... other fields ...
}
```

**Пример:**

Bronze record:
```json
{
  "id": "https://openalex.org/W2741809807",
  "type": "article",
  "title": "Example Article"
}
```

Silver record:
```python
{
    "openalex_id": "W2741809807",
    "publication_type": "article",  # Raw
    "publication_type_unified": "Journal Article",  # Level 3
    "publication_subclass": "Original Experimental Data",  # Level 2
    "publication_class": "EXP",  # Level 1
    # ...
}
```

---

### 3.4 PubMed Transformer

**Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py:366-386`

**Метод:**

```python
def _build_pubmed_classification(
    self, pub_types: list[str]
) -> dict[str, str | None]:
    """Build publication_type and classification fields for PubMed.

    Joins raw types with | for the raw publication_type field,
    then uses the unified classifier to pick the most specific match.

    Args:
        pub_types: List of raw publication type strings from XML.

    Returns:
        Dict with publication_type and the 3 classification fields.
    """
    raw_type = "|".join(pub_types) if pub_types else None
    classification = self._classify_publication_type(
        "pubmed",
        raw_types_list=pub_types,
    )
    return {"publication_type": raw_type, **classification}
```

**Пример:**

Bronze record (parsed XML):
```python
pub_types = ["Journal Article", "Clinical Trial", "Randomized Controlled Trial"]
```

Silver record:
```python
{
    "pmid": "12345678",
    "publication_type": "Journal Article|Clinical Trial|Randomized Controlled Trial",  # Raw (joined)
    "publication_type_unified": "Randomized Controlled Trial",  # Level 3 (most specific)
    "publication_subclass": "Original Experimental Data",  # Level 2
    "publication_class": "EXP",  # Level 1
    # ...
}
```

**Алгоритм выбора:**
1. Iterate pub_types: ["Journal Article", "Clinical Trial", "Randomized Controlled Trial"]
2. Lookup each in `_PUBMED_LOOKUP`
3. Compare `specificity` (row number)
4. Return entry with highest specificity

Row numbers in classification table:
- "Journal Article" → row 2 (specificity=2)
- "Clinical Trial" → row 16 (specificity=16)
- "Randomized Controlled Trial" → row 26 (specificity=26) ← **Winner**

---

### 3.5 SemanticScholar Transformer

**Файл:** `src/bioetl/application/pipelines/semanticscholar/transformer.py:219-230`

```python
publication_types = extract_publication_types(rec)

return {
    # ... other fields ...
    "publication_type": self._resolve_publication_type(publication_types),
    **self._classify_publication_type(
        "semanticscholar",
        raw_types_list=[
            str(t).strip()
            for t in publication_types
            if t is not None and str(t).strip()
        ]
        if isinstance(publication_types, list)
        else None,
    ),
    "publication_types": self.serialize_json(publication_types),
    # ... other fields ...
}
```

**Пример:**

Bronze record:
```json
{
  "paperId": "1234567890abcdef",
  "publicationTypes": ["JournalArticle", "Review"]
}
```

Silver record:
```python
{
    "paper_id": "1234567890abcdef",
    "publication_type": "JournalArticle",  # First item (from _resolve_publication_type)
    "publication_type_unified": "Review",  # Level 3 (most specific)
    "publication_subclass": "Reviews & Syntheses",  # Level 2
    "publication_class": "REV",  # Level 1
    "publication_types": '["JournalArticle", "Review"]',  # JSON string
    # ...
}
```

**Алгоритм:**
1. `publication_type` = первый элемент списка (fallback логика)
2. `publication_type_unified` = most specific match from ["JournalArticle", "Review"]
3. `publication_types` = JSON-сериализованный исходный список

Row numbers:
- "JournalArticle" → row 2 (specificity=2)
- "Review" → row 39 (specificity=39) ← **Winner**

---

## Часть 4: Field Naming в Silver Schemas

### 4.1 Поля в Silver Layer (post-transformation)

Каждый provider schema содержит следующие поля:

| Field Name | Type | Description |
|------------|------|-------------|
| `publication_type` | `Series[str] \| None` | Raw provider-specific type (для backward compatibility) |
| `publication_type_unified` | `Series[str] \| None` | Level 3: унифицированный тип из 214 значений |
| `publication_subclass` | `Series[str] \| None` | Level 2: подкласс (~25 значений) |
| `publication_class` | `Series[str] \| None` | Level 1: class code (EXP/REV/PEER) |

**PubMed дополнительно:**
- `publication_type_list` — не используется (deprecated/placeholder)
- `publication_types` — не используется (deprecated/placeholder)

**SemanticScholar дополнительно:**
- `publication_types` — JSON string с исходным списком типов

---

### 4.2 Field Name Mapping (publication_fields.py)

**Файл:** `src/bioetl/domain/mapping/publication_fields.py:34-41`

**Цель:** Унификация field names между провайдерами для будущей интеграции.

**ChEMBL Mapping:**
```python
_CHEMBL_MAPPING: Final[dict[str, str]] = {
    "doc_type": "publication_type",  # ChEMBL doc_type → unified publication_type
    "year": "publication_year",
}
```

**Примечание:** Это mapping для field names, НЕ для значений. ChEMBL не участвует в unified classification (использует enum из 4 значений).

---

## Часть 5: Composite Publication Pipeline

### 5.1 Field Groups Configuration

**Файл:** `configs/composite/field_groups/publication.yaml:40-44, 496-514`

**Doc Type Group (line 40-44):**
```yaml
- base_name: publication_type
  columns:
    - chembl.publication.publication_type
    - pubmed.publication.publication_type
```

**Publication Types Group (line 496-514):**
```yaml
# ===== PUBLICATION_TYPES =====
- id: publication_types
  display_name: "Publication Types"
  include_in_gold: true
  fields:
    - base_name: publication_type_list
      columns:
        - pubmed.publication.publication_type_list

    - base_name: publication_types
      columns:
        - pubmed.publication.publication_types
        - semanticscholar.publication.publication_types

    - base_name: type
      columns:
        - crossref.publication.type
        - openalex.publication.type
```

**Интерпретация:**

1. `publication_type` — базовое поле (ChEMBL, PubMed)
2. `publication_type_list` — PubMed-specific (deprecated)
3. `publication_types` — PubMed + SemanticScholar (JSON списки)
4. `type` — CrossRef + OpenAlex (raw типы)

**Отсутствуют в field_groups:**
- `publication_type_unified` (Level 3)
- `publication_subclass` (Level 2)
- `publication_class` (Level 1)

Эти поля **сохраняются** с provider qualification (e.g., `crossref.publication.publication_type_unified`).

---

### 5.2 Merge Strategy (preserve_all_sources)

**Файл:** `configs/pipelines/composite/publication.yaml:132`

```yaml
merge:
  preserve_all_sources: true
  conflict_resolution: seed_priority
```

**Файл:** `src/bioetl/application/composite/merger.py:1334-1346`

```python
def _resolve_conflicts(
    self,
    df: pl.DataFrame,
    enricher_dfs: dict[str, pl.DataFrame],
    enrichers: Sequence[EnricherConfig],
    seed_pipeline: str | None = None,
) -> pl.DataFrame:
    """Apply conflict resolution based on configured strategy."""
    # Skip coalescing if preserve_all_sources is enabled
    if self._config.preserve_all_sources:
        qualified_cols = [
            c for c in df.columns if "." in c and not c.startswith("_")
        ]
        self._logger.info(
            "Skipping conflict resolution - preserve_all_sources=True",
            qualified_columns=len(qualified_cols),
        )
        return df
```

**Вывод:** С `preserve_all_sources: true`, **coalescing НЕ происходит**. Все поля сохраняются с квалификацией провайдера.

---

### 5.3 Результирующие Колонки в Composite Publication

**Пример для публикации, присутствующей во всех 5 провайдерах:**

| Column Name | Type | Example Value | Source |
|-------------|------|---------------|--------|
| `entity_id` | str | "pub-HASH123" | Unified PK |
| `doi` | str | "10.1038/nature12345" | Coalesced DOI |
| `pmid` | str | "12345678" | PubMed ID |
| **ChEMBL** |||
| `chembl.publication.publication_type` | str | "PUBLICATION" | Raw ChEMBL enum |
| **CrossRef** |||
| `crossref.publication.type` | str | "journal-article" | Raw CrossRef type |
| `crossref.publication.publication_type` | str | "journal-article" | Raw (duplicated) |
| `crossref.publication.publication_type_unified` | str | "Journal Article" | Level 3 |
| `crossref.publication.publication_subclass` | str | "Original Experimental Data" | Level 2 |
| `crossref.publication.publication_class` | str | "EXP" | Level 1 |
| **OpenAlex** |||
| `openalex.publication.type` | str | "article" | Raw OpenAlex type |
| `openalex.publication.publication_type` | str | "article" | Raw (duplicated) |
| `openalex.publication.publication_type_unified` | str | "Journal Article" | Level 3 |
| `openalex.publication.publication_subclass` | str | "Original Experimental Data" | Level 2 |
| `openalex.publication.publication_class` | str | "EXP" | Level 1 |
| **PubMed** |||
| `pubmed.publication.publication_type` | str | "Journal Article\|Clinical Trial" | Raw (pipe-joined) |
| `pubmed.publication.publication_type_unified` | str | "Clinical Trial" | Level 3 (most specific) |
| `pubmed.publication.publication_subclass` | str | "Original Experimental Data" | Level 2 |
| `pubmed.publication.publication_class` | str | "EXP" | Level 1 |
| `pubmed.publication.publication_type_list` | str? | NULL | Deprecated field |
| `pubmed.publication.publication_types` | str? | NULL | Deprecated field |
| **SemanticScholar** |||
| `semanticscholar.publication.publication_type` | str | "JournalArticle" | Raw (first item) |
| `semanticscholar.publication.publication_type_unified` | str | "Journal Article" | Level 3 |
| `semanticscholar.publication.publication_subclass` | str | "Original Experimental Data" | Level 2 |
| `semanticscholar.publication.publication_class` | str | "EXP" | Level 1 |
| `semanticscholar.publication.publication_types` | str | '["JournalArticle"]' | JSON list |

**Итого:** ~20 publication_type-related колонок (с provider qualification)

---

### 5.4 Column Ordering

**Файл:** `configs/pipelines/composite/publication.yaml:406-409`

```yaml
- name: doc_type
  fields:
    - publication_status
    - publication_type
    - publication_type_list
    - publication_types
```

**Интерпретация:**

Колонки группируются по `base_name` из field_groups, но фактически в DataFrame будут provider-qualified:
- `chembl.publication.publication_type`
- `pubmed.publication.publication_type`
- `crossref.publication.type`
- `openalex.publication.type`
- `pubmed.publication.publication_type_list`
- `pubmed.publication.publication_types`
- `semanticscholar.publication.publication_types`

**Дополнительно:**
- `*.publication.publication_type_unified`
- `*.publication.publication_subclass`
- `*.publication.publication_class`

Эти колонки НЕ перечислены в column_groups, но сохраняются в DataFrame.

---

## Часть 6: Поток Данных (End-to-End)

### 6.1 Диаграмма

```
┌──────────────────────────────────────────────────────────────────────┐
│                       BRONZE LAYER (Provider APIs)                     │
├──────────────────────────────────────────────────────────────────────┤
│ CrossRef:         type: "journal-article"                             │
│ OpenAlex:         type: "article"                                     │
│ PubMed:           PublicationType: ["Journal Article", "Clinical..."] │
│ SemanticScholar:  publicationTypes: ["JournalArticle", "Review"]     │
│ ChEMBL:           doc_type: "PUBLICATION"                             │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    TRANSFORMATION (Silver Transformer)                 │
├──────────────────────────────────────────────────────────────────────┤
│ 1. Extract raw type(s) from Bronze record                             │
│ 2. Call _classify_publication_type(provider, raw_type/raw_types_list) │
│ 3. Lookup in provider-specific table (case-insensitive)              │
│ 4. Return PublicationTypeEntry:                                      │
│    - unified_type (Level 3)                                           │
│    - subclass (Level 2)                                               │
│    - class_code (Level 1)                                             │
│ 5. Multi-value providers: select most specific (highest row number)  │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                       SILVER LAYER (Per-Provider)                      │
├──────────────────────────────────────────────────────────────────────┤
│ CrossRef Silver:                                                      │
│   - publication_type: "journal-article" (raw)                         │
│   - publication_type_unified: "Journal Article"                       │
│   - publication_subclass: "Original Experimental Data"                │
│   - publication_class: "EXP"                                          │
│                                                                       │
│ OpenAlex Silver:                                                      │
│   - publication_type: "article" (raw)                                 │
│   - publication_type_unified: "Journal Article"                       │
│   - publication_subclass: "Original Experimental Data"                │
│   - publication_class: "EXP"                                          │
│                                                                       │
│ PubMed Silver:                                                        │
│   - publication_type: "Journal Article|Clinical Trial" (joined)       │
│   - publication_type_unified: "Clinical Trial" (most specific)        │
│   - publication_subclass: "Original Experimental Data"                │
│   - publication_class: "EXP"                                          │
│                                                                       │
│ SemanticScholar Silver:                                               │
│   - publication_type: "JournalArticle" (first item)                   │
│   - publication_type_unified: "Review" (most specific)                │
│   - publication_subclass: "Reviews & Syntheses"                       │
│   - publication_class: "REV"                                          │
│   - publication_types: '["JournalArticle", "Review"]' (JSON)          │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                   COMPOSITE PIPELINE (Merge Service)                   │
├──────────────────────────────────────────────────────────────────────┤
│ 1. Load seed (e.g., ChEMBL) and enrichers (CrossRef, OpenAlex, etc.)  │
│ 2. Apply qualified column renaming:                                  │
│    - crossref.publication.publication_type                            │
│    - openalex.publication.publication_type                            │
│    - pubmed.publication.publication_type                              │
│    - semanticscholar.publication.publication_type                     │
│    - crossref.publication.publication_type_unified                    │
│    - openalex.publication.publication_type_unified                    │
│    - pubmed.publication.publication_type_unified                      │
│    - semanticscholar.publication.publication_type_unified             │
│    - (same for publication_subclass, publication_class)               │
│ 3. Join on doi/pmid                                                   │
│ 4. preserve_all_sources=true → NO coalescing                          │
│ 5. Apply field_groups ordering (semantic grouping)                   │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    COMPOSITE PUBLICATION (Gold Layer)                  │
├──────────────────────────────────────────────────────────────────────┤
│ Result DataFrame:                                                     │
│   - entity_id: "pub-HASH123"                                          │
│   - doi: "10.1038/nature12345"                                        │
│   - pmid: "12345678"                                                  │
│                                                                       │
│   # ChEMBL (seed)                                                     │
│   - chembl.publication.publication_type: "PUBLICATION"                │
│                                                                       │
│   # CrossRef (enricher)                                               │
│   - crossref.publication.type: "journal-article"                      │
│   - crossref.publication.publication_type: "journal-article"          │
│   - crossref.publication.publication_type_unified: "Journal Article"  │
│   - crossref.publication.publication_subclass: "Original..."          │
│   - crossref.publication.publication_class: "EXP"                     │
│                                                                       │
│   # OpenAlex (enricher)                                               │
│   - openalex.publication.type: "article"                              │
│   - openalex.publication.publication_type: "article"                  │
│   - openalex.publication.publication_type_unified: "Journal Article"  │
│   - openalex.publication.publication_subclass: "Original..."          │
│   - openalex.publication.publication_class: "EXP"                     │
│                                                                       │
│   # PubMed (enricher)                                                 │
│   - pubmed.publication.publication_type: "Journal Article|Clinical..."│
│   - pubmed.publication.publication_type_unified: "Clinical Trial"     │
│   - pubmed.publication.publication_subclass: "Original..."            │
│   - pubmed.publication.publication_class: "EXP"                       │
│                                                                       │
│   # SemanticScholar (enricher)                                        │
│   - semanticscholar.publication.publication_type: "JournalArticle"    │
│   - semanticscholar.publication.publication_type_unified: "Review"    │
│   - semanticscholar.publication.publication_subclass: "Reviews..."    │
│   - semanticscholar.publication.publication_class: "REV"              │
│   - semanticscholar.publication.publication_types: '["Journal..."]'   │
│                                                                       │
│   # ~20 publication_type-related columns total                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Часть 7: Ключевые Выводы

### 7.1 Нормализация Происходит в 2 Этапа

1. **Silver Layer** — провайдер-специфичные raw типы классифицируются через unified 3-level hierarchy (214 типов)
2. **Composite Layer** — все provider-qualified поля сохраняются (preserve_all_sources=true)

---

### 7.2 Unified Classification (214 Types)

- **Источник:** `domain/mapping/publication_type_classification.py`
- **Провайдеры:** OpenAlex, CrossRef, PubMed, SemanticScholar (ChEMBL НЕ участвует)
- **Структура:** 3 уровня (class_code → subclass → unified_type)
- **Алгоритм:** Multi-value провайдеры (PubMed, S2) выбирают most specific type (highest row number)

---

### 7.3 Silver Layer Output (4 поля)

Каждый трансформер создает:
1. `publication_type` — raw provider-specific type (backward compatibility)
2. `publication_type_unified` — Level 3 unified type
3. `publication_subclass` — Level 2 subclass
4. `publication_class` — Level 1 class code (EXP/REV/PEER)

---

### 7.4 Composite Layer Preservation

С `preserve_all_sources: true`:
- **НЕТ автоматического coalescing** полей
- **ВСЕ поля сохраняются** с provider qualification
- Результат: ~20 publication_type-related колонок для записи с 5 провайдерами

---

### 7.5 ChEMBL Отличие

ChEMBL:
- Использует ограниченный enum (4 значения): `PUBLICATION`, `PATENT`, `DATASET`, `BOOK`
- **НЕ участвует** в unified classification с 214 типами
- `doc_type` → `publication_type` mapping существует в `publication_fields.py`, но это field name mapping, не value classification

---

### 7.6 Field Naming Inconsistencies

**Внутри провайдеров (Bronze → Silver):**
- CrossRef: `type` (Bronze) → `type` + `publication_type` (Silver, duplicated)
- OpenAlex: `type` (Bronze) → `type` + `publication_type` (Silver, duplicated)
- PubMed: `PublicationType` (Bronze XML) → `publication_type` (Silver, joined with `|`)
- SemanticScholar: `publicationTypes` (Bronze) → `publication_type` + `publication_types` (Silver, resolved + JSON)

**В Composite:**
- `crossref.publication.type` vs `crossref.publication.publication_type` (оба содержат одинаковое значение)
- `openalex.publication.type` vs `openalex.publication.publication_type` (оба содержат одинаковое значение)

**Причина:** field_groups configuration сохраняет оба имени для backward compatibility.

---

## Часть 8: Примеры Реальных Данных

### 8.1 Пример: Journal Article

**Bronze (OpenAlex):**
```json
{
  "id": "https://openalex.org/W2741809807",
  "type": "article",
  "title": "Mechanisms of autophagy"
}
```

**Silver (OpenAlex):**
```python
{
    "openalex_id": "W2741809807",
    "publication_type": "article",
    "publication_type_unified": "Journal Article",
    "publication_subclass": "Original Experimental Data",
    "publication_class": "EXP",
}
```

**Composite:**
```
openalex.publication.type: "article"
openalex.publication.publication_type: "article"
openalex.publication.publication_type_unified: "Journal Article"
openalex.publication.publication_subclass: "Original Experimental Data"
openalex.publication.publication_class: "EXP"
```

---

### 8.2 Пример: Meta-Analysis (PubMed Multi-Value)

**Bronze (PubMed XML):**
```xml
<PublicationTypeList>
  <PublicationType UI="D016428">Journal Article</PublicationType>
  <PublicationType UI="D017418">Meta-Analysis</PublicationType>
  <PublicationType UI="D016454">Review</PublicationType>
</PublicationTypeList>
```

**Silver (PubMed):**
```python
{
    "pmid": "12345678",
    "publication_type": "Journal Article|Meta-Analysis|Review",  # Joined
    "publication_type_unified": "Meta-Analysis",  # Most specific (row 41)
    "publication_subclass": "Reviews & Syntheses",
    "publication_class": "REV",
}
```

**Алгоритм:**
- "Journal Article" → row 2 (specificity=2)
- "Meta-Analysis" → row 41 (specificity=41) ← **Winner**
- "Review" → row 39 (specificity=39)

**Composite:**
```
pubmed.publication.publication_type: "Journal Article|Meta-Analysis|Review"
pubmed.publication.publication_type_unified: "Meta-Analysis"
pubmed.publication.publication_subclass: "Reviews & Syntheses"
pubmed.publication.publication_class: "REV"
```

---

### 8.3 Пример: Conference Paper (Mixed Providers)

**Bronze:**
- CrossRef: `"type": "proceedings-article"`
- OpenAlex: `"type": "article"` (secondary mapping with asterisk)

**Silver (CrossRef):**
```python
{
    "doi": "10.1109/CVPR.2020.00123",
    "publication_type": "proceedings-article",
    "publication_type_unified": "Conference Paper",
    "publication_subclass": "Original Experimental Data",
    "publication_class": "EXP",
}
```

**Silver (OpenAlex):**
```python
{
    "openalex_id": "W3012345678",
    "publication_type": "article",
    "publication_type_unified": "Conference Paper",  # Secondary mapping
    "publication_subclass": "Original Experimental Data",
    "publication_class": "EXP",
}
```

**Примечание:** OpenAlex `"article"` может мапиться на "Journal Article" (row 2) ИЛИ "Conference Paper" (row 3, secondary with `*`). Classifier выбирает primary mapping (row 2).

---

## Часть 9: Архитектурные Инварианты

### 9.1 Domain Layer Purity

**Файл:** `domain/mapping/publication_type_classification.py`

✅ **Соответствует RULES.md:**
- Pure Python (no I/O)
- Lookup tables built at import time (no file reading)
- Value Objects (PublicationTypeEntry dataclass)
- Type-safe API (typing.Protocol not needed here, but consistent)

---

### 9.2 Template Method Pattern

**Файл:** `application/pipelines/common/base_publication_transformer.py`

✅ **Соответствует Pattern:**
- `_transform_impl()` — Template Method (base class)
- `_extract_business_data()` — Abstract (provider-specific)
- `_classify_publication_type()` — Reusable helper (base class)

---

### 9.3 Single Responsibility

**Classification module:**
- ✅ Only classifies types (no transformation)
- ✅ No I/O (stateless lookup)

**Transformer:**
- ✅ Orchestrates extraction and classification
- ✅ Delegates to extractors (REFACTOR-004)

**Composite merger:**
- ✅ Only merges DataFrames (no classification)

---

## Часть 10: Потенциальные Улучшения

### 10.1 Deduplicate `type` and `publication_type`

**Проблема:** CrossRef и OpenAlex имеют оба поля с одинаковым значением.

**Текущее состояние:**
```python
{
    "publication_type": rec.get("type"),  # Raw
    # ...
    "type": rec.get("type"),  # Duplicate via field_groups
}
```

**Решение:** Удалить дублирование, оставить только `publication_type` в Silver schemas.

**Impact:** Requires field_groups update and schema validation tests.

---

### 10.2 ChEMBL Integration в Unified Classification

**Проблема:** ChEMBL использует 4-value enum, не участвует в unified 214-type classification.

**Текущее состояние:**
- ChEMBL: `doc_type` ∈ {PUBLICATION, PATENT, DATASET, BOOK}
- No `publication_type_unified`, `publication_subclass`, `publication_class`

**Решение:** Add ChEMBL column to `_CLASSIFICATION_TABLE` for 4 types:

```python
# Row example
("Journal Article", "Original Experimental Data", "EXP",
 "article", "journal-article", "Journal Article", "JournalArticle",
 "PUBLICATION"),  # Add ChEMBL column
```

**Benefit:** Consistent classification across all 5 providers.

**Effort:** ~2 hours (update table, add tests)

---

### 10.3 Explicit Column Ordering для classification fields

**Проблема:** `publication_type_unified`, `publication_subclass`, `publication_class` не перечислены в `column_groups`.

**Текущее состояние:**
```yaml
# configs/pipelines/composite/publication.yaml:406-409
- name: doc_type
  fields:
    - publication_status
    - publication_type
    - publication_type_list
    - publication_types
    # Missing: publication_type_unified, publication_subclass, publication_class
```

**Решение:** Add to column_groups for explicit ordering:

```yaml
- name: doc_type
  fields:
    - publication_status
    - publication_type
    - publication_type_unified  # Add
    - publication_subclass      # Add
    - publication_class         # Add
    - publication_type_list
    - publication_types
```

**Benefit:** Explicit control over column ordering in composite output.

---

### 10.4 Deprecate `publication_type_list` and `publication_types` (PubMed)

**Проблема:** PubMed Silver schema имеет deprecated placeholders:
- `publication_type_list` — always NULL
- `publication_types` — always NULL (not to be confused with SemanticScholar's field)

**Текущее состояние:**
```python
# pubmed/publication.py schema
publication_type_list: Series[str] | None = pa.Field(nullable=True, ...)
publication_types: Series[str] | None = pa.Field(nullable=True, ...)
```

**Решение:** Remove from schema, update field_groups, update skipped tests analysis.

**Benefit:** Reduce schema complexity, eliminate confusion with SemanticScholar's `publication_types`.

---

## Заключение

**Нормализация publication_type полей в BioETL:**

1. ✅ **Unified 3-level classification** (214 types) применяется в Silver Layer для OpenAlex, CrossRef, PubMed, SemanticScholar
2. ✅ **Multi-value strategy** (PubMed, S2): выбор most specific type (highest row number)
3. ✅ **Preserve all sources** в Composite Layer: все provider-qualified колонки сохраняются
4. ⚠️ **ChEMBL не участвует** в unified classification (4-value enum)
5. ⚠️ **Дублирование полей** (`type` vs `publication_type` для CrossRef/OpenAlex)
6. ⚠️ **Classification fields не перечислены** в column_groups (неявный порядок)

**Метрики:**
- **214 unified types** (Level 3)
- **~25 subclasses** (Level 2)
- **3 class codes** (Level 1: EXP/REV/PEER)
- **4 провайдера** в unified classification (OpenAlex, CrossRef, PubMed, SemanticScholar)
- **5 провайдеров total** (+ ChEMBL с отдельным enum)
- **~20 publication_type columns** в composite output (для записи с 5 провайдерами)

---

**Дата создания:** 2026-02-10
**Автор:** Claude Code (AI-generated analysis)
**Статус:** ✅ Complete — ready for review
