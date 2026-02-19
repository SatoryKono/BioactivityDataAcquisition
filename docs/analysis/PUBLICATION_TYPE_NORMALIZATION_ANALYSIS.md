# Publication Type Normalization Analysis

**Дата:** 2026-02-10
**Версия:** 1.0.0
**Scope:** Нормализация полей publication-type в composite publication pipeline

---

## Executive Summary

Нормализация полей `publication-type` в BioETL происходит в **два этапа**:

1. **Silver Layer Transformation** — провайдер-специфичные raw типы классифицируются с помощью унифицированной 3-уровневой иерархии (214 типов, 4 провайдера)
2. **Composite Pipeline Merging** — все provider-qualified поля сохраняются (preserve-all-sources=true), coalescing НЕ происходит

**Ключевые файлы:**
- `domain/mapping/publication-type-classification.py` — 214 mappings (OpenAlex, CrossRef, PubMed, SemanticScholar)
- `application/pipelines/common/base-publication-transformer.py` — метод `-classify-publication-type()`
- `configs/composite/field-groups/publication.yaml` — field grouping для composite
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

**Mapping table:** 191 уникальных mappings (column 4 в -CLASSIFICATION-TABLE)

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

**Mapping table:** 191 уникальных mappings (column 6 в -CLASSIFICATION-TABLE)

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

**Mapping table:** 191 уникальных mappings (column 7 в -CLASSIFICATION-TABLE)

**Особенность:** Multi-value provider — классификатор выбирает **наиболее специфичный тип**

---

### 1.5 ChEMBL

**Поле:** `doc-type` (строка)

**Примеры значений:**
- `"PUBLICATION"`
- `"PATENT"`
- `"DATASET"`
- `"BOOK"`

**Mapping:** Использует константу `PUBLICATION-TYPES` из `domain/schemas/constants.py` (line 187-194):

```python
PUBLICATION-TYPES: frozenset[str] = frozenset([
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

**Файл:** `src/bioetl/domain/mapping/publication-type-classification.py`

**Структура:**

```python
@dataclass(frozen=True, slots=True)
class PublicationTypeEntry:
    unified-type: str       # Level 3: 214 типов (e.g., "Journal Article")
    subclass: str           # Level 2: ~25 groupings (e.g., "Original Experimental Data")
    class-code: str         # Level 1: 3 codes (EXP | REV | PEER)
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

**Файл:** `src/bioetl/domain/mapping/publication-type-classification.py:1585`

```python
def classify-publication-type(
    provider: str,
    raw-type: str | None = None,
    raw-types-list: list[str] | None = None,
) -> PublicationTypeEntry | None:
    """Classify a publication type using the unified 3-level hierarchy.

    For single-value providers (OpenAlex, CrossRef): uses raw-type for
    a direct lookup.

    For multi-value providers (PubMed, Semantic Scholar): iterates
    raw-types-list, collects all matches, and returns the entry with
    the highest specificity (largest row number = most specific type).

    Args:
        provider: Provider name ("openalex", "crossref", "pubmed", "semanticscholar").
        raw-type: Single raw type string (for OpenAlex / CrossRef).
        raw-types-list: List of raw type strings (for PubMed / S2).

    Returns:
        The matching PublicationTypeEntry, or None if no match.
    """
```

**Lookup Tables (built at import time):**
- `-OPENALEX-LOOKUP: dict[str, PublicationTypeEntry]`
- `-CROSSREF-LOOKUP: dict[str, PublicationTypeEntry]`
- `-PUBMED-LOOKUP: dict[str, PublicationTypeEntry]`
- `-S2-LOOKUP: dict[str, PublicationTypeEntry]`

**Normalization:** Keys normalized to lowercase (`"JournalArticle"` → `"journalarticle"`)

**Multi-value strategy:**
```python
# PubMed example: ["Journal Article", "Clinical Trial", "Randomized Controlled Trial"]
# Returns: "Randomized Controlled Trial" (row 287, most specific)
best: PublicationTypeEntry | None = None
for raw in raw-types-list:
    entry = lookup.get(raw.strip().lower())
    if entry is not None and (best is None or entry.specificity > best.specificity):
        best = entry
return best
```

---

## Часть 3: Трансформация в Silver Layer

### 3.1 BasePublicationTransformer

**Файл:** `src/bioetl/application/pipelines/common/base-publication-transformer.py:206`

**Метод:**

```python
def -classify-publication-type(
    self,
    provider: str,
    raw-type: str | None = None,
    raw-types-list: list[str] | None = None,
) -> dict[str, str | None]:
    """Classify publication type using the unified 3-level hierarchy.

    Delegates to domain classification module.

    Returns:
        Dict with keys publication-type-unified, publication-subclass,
        publication-class (all str | None).
    """
    entry = classify-publication-type(
        provider, raw-type=raw-type, raw-types-list=raw-types-list
    )
    if entry is None:
        return {
            "publication-type-unified": None,
            "publication-subclass": None,
            "publication-class": None,
        }
    return {
        "publication-type-unified": entry.unified-type,
        "publication-subclass": entry.subclass,
        "publication-class": entry.class-code,
    }
```

**Возвращает 3 поля:**
- `publication-type-unified` — Level 3 (e.g., "Journal Article")
- `publication-subclass` — Level 2 (e.g., "Original Experimental Data")
- `publication-class` — Level 1 (e.g., "EXP")

---

### 3.2 CrossRef Transformer

**Файл:** `src/bioetl/application/pipelines/crossref/transformer.py:177-178`

```python
return {
    # ... other fields ...
    "publication-type": rec.get("type"),  # Raw CrossRef type
    **self.-classify-publication-type("crossref", raw-type=rec.get("type")),
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
    "publication-type": "journal-article",  # Raw
    "publication-type-unified": "Journal Article",  # Level 3
    "publication-subclass": "Original Experimental Data",  # Level 2
    "publication-class": "EXP",  # Level 1
    # ...
}
```

---

### 3.3 OpenAlex Transformer

**Файл:** `src/bioetl/application/pipelines/openalex/transformer.py:241-242`

```python
return {
    # ... other fields ...
    "publication-type": rec.get("type"),  # Raw OpenAlex type
    **self.-classify-publication-type("openalex", raw-type=rec.get("type")),
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
    "openalex-id": "W2741809807",
    "publication-type": "article",  # Raw
    "publication-type-unified": "Journal Article",  # Level 3
    "publication-subclass": "Original Experimental Data",  # Level 2
    "publication-class": "EXP",  # Level 1
    # ...
}
```

---

### 3.4 PubMed Transformer

**Файл:** `src/bioetl/application/pipelines/pubmed/transformer.py:366-386`

**Метод:**

```python
def -build-pubmed-classification(
    self, pub-types: list[str]
) -> dict[str, str | None]:
    """Build publication-type and classification fields for PubMed.

    Joins raw types with | for the raw publication-type field,
    then uses the unified classifier to pick the most specific match.

    Args:
        pub-types: List of raw publication type strings from XML.

    Returns:
        Dict with publication-type and the 3 classification fields.
    """
    raw-type = "|".join(pub-types) if pub-types else None
    classification = self.-classify-publication-type(
        "pubmed",
        raw-types-list=pub-types,
    )
    return {"publication-type": raw-type, **classification}
```

**Пример:**

Bronze record (parsed XML):
```python
pub-types = ["Journal Article", "Clinical Trial", "Randomized Controlled Trial"]
```

Silver record:
```python
{
    "pmid": "12345678",
    "publication-type": "Journal Article|Clinical Trial|Randomized Controlled Trial",  # Raw (joined)
    "publication-type-unified": "Randomized Controlled Trial",  # Level 3 (most specific)
    "publication-subclass": "Original Experimental Data",  # Level 2
    "publication-class": "EXP",  # Level 1
    # ...
}
```

**Алгоритм выбора:**
1. Iterate pub-types: ["Journal Article", "Clinical Trial", "Randomized Controlled Trial"]
2. Lookup each in `-PUBMED-LOOKUP`
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
publication-types = extract-publication-types(rec)

return {
    # ... other fields ...
    "publication-type": self.-resolve-publication-type(publication-types),
    **self.-classify-publication-type(
        "semanticscholar",
        raw-types-list=[
            str(t).strip()
            for t in publication-types
            if t is not None and str(t).strip()
        ]
        if isinstance(publication-types, list)
        else None,
    ),
    "publication-types": self.serialize-json(publication-types),
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
    "paper-id": "1234567890abcdef",
    "publication-type": "JournalArticle",  # First item (from -resolve-publication-type)
    "publication-type-unified": "Review",  # Level 3 (most specific)
    "publication-subclass": "Reviews & Syntheses",  # Level 2
    "publication-class": "REV",  # Level 1
    "publication-types": '["JournalArticle", "Review"]',  # JSON string
    # ...
}
```

**Алгоритм:**
1. `publication-type` = первый элемент списка (fallback логика)
2. `publication-type-unified` = most specific match from ["JournalArticle", "Review"]
3. `publication-types` = JSON-сериализованный исходный список

Row numbers:
- "JournalArticle" → row 2 (specificity=2)
- "Review" → row 39 (specificity=39) ← **Winner**

---

## Часть 4: Field Naming в Silver Schemas

### 4.1 Поля в Silver Layer (post-transformation)

Каждый provider schema содержит следующие поля:

| Field Name | Type | Description |
|------------|------|-------------|
| `publication-type` | `Series[str] \| None` | Raw provider-specific type (для backward compatibility) |
| `publication-type-unified` | `Series[str] \| None` | Level 3: унифицированный тип из 214 значений |
| `publication-subclass` | `Series[str] \| None` | Level 2: подкласс (~25 значений) |
| `publication-class` | `Series[str] \| None` | Level 1: class code (EXP/REV/PEER) |

**PubMed дополнительно:**
- `publication-type-list` — не используется (deprecated/placeholder)
- `publication-types` — не используется (deprecated/placeholder)

**SemanticScholar дополнительно:**
- `publication-types` — JSON string с исходным списком типов

---

### 4.2 Field Name Mapping (publication-fields.py)

**Файл:** `src/bioetl/domain/mapping/publication-fields.py:34-41`

**Цель:** Унификация field names между провайдерами для будущей интеграции.

**ChEMBL Mapping:**
```python
-CHEMBL-MAPPING: Final[dict[str, str]] = {
    "doc-type": "publication-type",  # ChEMBL doc-type → unified publication-type
    "year": "publication-year",
}
```

**Примечание:** Это mapping для field names, НЕ для значений. ChEMBL не участвует в unified classification (использует enum из 4 значений).

---

## Часть 5: Composite Publication Pipeline

### 5.1 Field Groups Configuration

**Файл:** `configs/composite/field-groups/publication.yaml:40-44, 496-514`

**Doc Type Group (line 40-44):**
```yaml
- base-name: publication-type
  columns:
    - chembl.publication.publication-type
    - pubmed.publication.publication-type
```

**Publication Types Group (line 496-514):**
```yaml
# ===== PUBLICATION-TYPES =====
- id: publication-types
  display-name: "Publication Types"
  include-in-gold: true
  fields:
    - base-name: publication-type-list
      columns:
        - pubmed.publication.publication-type-list

    - base-name: publication-types
      columns:
        - pubmed.publication.publication-types
        - semanticscholar.publication.publication-types

    - base-name: type
      columns:
        - crossref.publication.type
        - openalex.publication.type
```

**Интерпретация:**

1. `publication-type` — базовое поле (ChEMBL, PubMed)
2. `publication-type-list` — PubMed-specific (deprecated)
3. `publication-types` — PubMed + SemanticScholar (JSON списки)
4. `type` — CrossRef + OpenAlex (raw типы)

**Отсутствуют в field-groups:**
- `publication-type-unified` (Level 3)
- `publication-subclass` (Level 2)
- `publication-class` (Level 1)

Эти поля **сохраняются** с provider qualification (e.g., `crossref.publication.publication-type-unified`).

---

### 5.2 Merge Strategy (preserve-all-sources)

**Файл:** `configs/pipelines/composite/publication.yaml:132`

```yaml
merge:
  preserve-all-sources: true
  conflict-resolution: seed-priority
```

**Файл:** `src/bioetl/application/composite/merger.py:1334-1346`

```python
def -resolve-conflicts(
    self,
    df: pl.DataFrame,
    enricher-dfs: dict[str, pl.DataFrame],
    enrichers: Sequence[EnricherConfig],
    seed-pipeline: str | None = None,
) -> pl.DataFrame:
    """Apply conflict resolution based on configured strategy."""
    # Skip coalescing if preserve-all-sources is enabled
    if self.-config.preserve-all-sources:
        qualified-cols = [
            c for c in df.columns if "." in c and not c.startswith("-")
        ]
        self.-logger.info(
            "Skipping conflict resolution - preserve-all-sources=True",
            qualified-columns=len(qualified-cols),
        )
        return df
```

**Вывод:** С `preserve-all-sources: true`, **coalescing НЕ происходит**. Все поля сохраняются с квалификацией провайдера.

---

### 5.3 Результирующие Колонки в Composite Publication

**Пример для публикации, присутствующей во всех 5 провайдерах:**

| Column Name | Type | Example Value | Source |
|-------------|------|---------------|--------|
| `entity-id` | str | "pub-HASH123" | Unified PK |
| `doi` | str | "10.1038/nature12345" | Coalesced DOI |
| `pmid` | str | "12345678" | PubMed ID |
| **ChEMBL** |||
| `chembl.publication.publication-type` | str | "PUBLICATION" | Raw ChEMBL enum |
| **CrossRef** |||
| `crossref.publication.type` | str | "journal-article" | Raw CrossRef type |
| `crossref.publication.publication-type` | str | "journal-article" | Raw (duplicated) |
| `crossref.publication.publication-type-unified` | str | "Journal Article" | Level 3 |
| `crossref.publication.publication-subclass` | str | "Original Experimental Data" | Level 2 |
| `crossref.publication.publication-class` | str | "EXP" | Level 1 |
| **OpenAlex** |||
| `openalex.publication.type` | str | "article" | Raw OpenAlex type |
| `openalex.publication.publication-type` | str | "article" | Raw (duplicated) |
| `openalex.publication.publication-type-unified` | str | "Journal Article" | Level 3 |
| `openalex.publication.publication-subclass` | str | "Original Experimental Data" | Level 2 |
| `openalex.publication.publication-class` | str | "EXP" | Level 1 |
| **PubMed** |||
| `pubmed.publication.publication-type` | str | "Journal Article\|Clinical Trial" | Raw (pipe-joined) |
| `pubmed.publication.publication-type-unified` | str | "Clinical Trial" | Level 3 (most specific) |
| `pubmed.publication.publication-subclass` | str | "Original Experimental Data" | Level 2 |
| `pubmed.publication.publication-class` | str | "EXP" | Level 1 |
| `pubmed.publication.publication-type-list` | str? | NULL | Deprecated field |
| `pubmed.publication.publication-types` | str? | NULL | Deprecated field |
| **SemanticScholar** |||
| `semanticscholar.publication.publication-type` | str | "JournalArticle" | Raw (first item) |
| `semanticscholar.publication.publication-type-unified` | str | "Journal Article" | Level 3 |
| `semanticscholar.publication.publication-subclass` | str | "Original Experimental Data" | Level 2 |
| `semanticscholar.publication.publication-class` | str | "EXP" | Level 1 |
| `semanticscholar.publication.publication-types` | str | '["JournalArticle"]' | JSON list |

**Итого:** ~20 publication-type-related колонок (с provider qualification)

---

### 5.4 Column Ordering

**Файл:** `configs/pipelines/composite/publication.yaml:406-409`

```yaml
- name: doc-type
  fields:
    - publication-status
    - publication-type
    - publication-type-list
    - publication-types
```

**Интерпретация:**

Колонки группируются по `base-name` из field-groups, но фактически в DataFrame будут provider-qualified:
- `chembl.publication.publication-type`
- `pubmed.publication.publication-type`
- `crossref.publication.type`
- `openalex.publication.type`
- `pubmed.publication.publication-type-list`
- `pubmed.publication.publication-types`
- `semanticscholar.publication.publication-types`

**Дополнительно:**
- `*.publication.publication-type-unified`
- `*.publication.publication-subclass`
- `*.publication.publication-class`

Эти колонки НЕ перечислены в column-groups, но сохраняются в DataFrame.

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
│ ChEMBL:           doc-type: "PUBLICATION"                             │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    TRANSFORMATION (Silver Transformer)                 │
├──────────────────────────────────────────────────────────────────────┤
│ 1. Extract raw type(s) from Bronze record                             │
│ 2. Call -classify-publication-type(provider, raw-type/raw-types-list) │
│ 3. Lookup in provider-specific table (case-insensitive)              │
│ 4. Return PublicationTypeEntry:                                      │
│    - unified-type (Level 3)                                           │
│    - subclass (Level 2)                                               │
│    - class-code (Level 1)                                             │
│ 5. Multi-value providers: select most specific (highest row number)  │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                       SILVER LAYER (Per-Provider)                      │
├──────────────────────────────────────────────────────────────────────┤
│ CrossRef Silver:                                                      │
│   - publication-type: "journal-article" (raw)                         │
│   - publication-type-unified: "Journal Article"                       │
│   - publication-subclass: "Original Experimental Data"                │
│   - publication-class: "EXP"                                          │
│                                                                       │
│ OpenAlex Silver:                                                      │
│   - publication-type: "article" (raw)                                 │
│   - publication-type-unified: "Journal Article"                       │
│   - publication-subclass: "Original Experimental Data"                │
│   - publication-class: "EXP"                                          │
│                                                                       │
│ PubMed Silver:                                                        │
│   - publication-type: "Journal Article|Clinical Trial" (joined)       │
│   - publication-type-unified: "Clinical Trial" (most specific)        │
│   - publication-subclass: "Original Experimental Data"                │
│   - publication-class: "EXP"                                          │
│                                                                       │
│ SemanticScholar Silver:                                               │
│   - publication-type: "JournalArticle" (first item)                   │
│   - publication-type-unified: "Review" (most specific)                │
│   - publication-subclass: "Reviews & Syntheses"                       │
│   - publication-class: "REV"                                          │
│   - publication-types: '["JournalArticle", "Review"]' (JSON)          │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                   COMPOSITE PIPELINE (Merge Service)                   │
├──────────────────────────────────────────────────────────────────────┤
│ 1. Load seed (e.g., ChEMBL) and enrichers (CrossRef, OpenAlex, etc.)  │
│ 2. Apply qualified column renaming:                                  │
│    - crossref.publication.publication-type                            │
│    - openalex.publication.publication-type                            │
│    - pubmed.publication.publication-type                              │
│    - semanticscholar.publication.publication-type                     │
│    - crossref.publication.publication-type-unified                    │
│    - openalex.publication.publication-type-unified                    │
│    - pubmed.publication.publication-type-unified                      │
│    - semanticscholar.publication.publication-type-unified             │
│    - (same for publication-subclass, publication-class)               │
│ 3. Join on doi/pmid                                                   │
│ 4. preserve-all-sources=true → NO coalescing                          │
│ 5. Apply field-groups ordering (semantic grouping)                   │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                    COMPOSITE PUBLICATION (Gold Layer)                  │
├──────────────────────────────────────────────────────────────────────┤
│ Result DataFrame:                                                     │
│   - entity-id: "pub-HASH123"                                          │
│   - doi: "10.1038/nature12345"                                        │
│   - pmid: "12345678"                                                  │
│                                                                       │
│   # ChEMBL (seed)                                                     │
│   - chembl.publication.publication-type: "PUBLICATION"                │
│                                                                       │
│   # CrossRef (enricher)                                               │
│   - crossref.publication.type: "journal-article"                      │
│   - crossref.publication.publication-type: "journal-article"          │
│   - crossref.publication.publication-type-unified: "Journal Article"  │
│   - crossref.publication.publication-subclass: "Original..."          │
│   - crossref.publication.publication-class: "EXP"                     │
│                                                                       │
│   # OpenAlex (enricher)                                               │
│   - openalex.publication.type: "article"                              │
│   - openalex.publication.publication-type: "article"                  │
│   - openalex.publication.publication-type-unified: "Journal Article"  │
│   - openalex.publication.publication-subclass: "Original..."          │
│   - openalex.publication.publication-class: "EXP"                     │
│                                                                       │
│   # PubMed (enricher)                                                 │
│   - pubmed.publication.publication-type: "Journal Article|Clinical..."│
│   - pubmed.publication.publication-type-unified: "Clinical Trial"     │
│   - pubmed.publication.publication-subclass: "Original..."            │
│   - pubmed.publication.publication-class: "EXP"                       │
│                                                                       │
│   # SemanticScholar (enricher)                                        │
│   - semanticscholar.publication.publication-type: "JournalArticle"    │
│   - semanticscholar.publication.publication-type-unified: "Review"    │
│   - semanticscholar.publication.publication-subclass: "Reviews..."    │
│   - semanticscholar.publication.publication-class: "REV"              │
│   - semanticscholar.publication.publication-types: '["Journal..."]'   │
│                                                                       │
│   # ~20 publication-type-related columns total                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Часть 7: Ключевые Выводы

### 7.1 Нормализация Происходит в 2 Этапа

1. **Silver Layer** — провайдер-специфичные raw типы классифицируются через unified 3-level hierarchy (214 типов)
2. **Composite Layer** — все provider-qualified поля сохраняются (preserve-all-sources=true)

---

### 7.2 Unified Classification (214 Types)

- **Источник:** `domain/mapping/publication-type-classification.py`
- **Провайдеры:** OpenAlex, CrossRef, PubMed, SemanticScholar (ChEMBL НЕ участвует)
- **Структура:** 3 уровня (class-code → subclass → unified-type)
- **Алгоритм:** Multi-value провайдеры (PubMed, S2) выбирают most specific type (highest row number)

---

### 7.3 Silver Layer Output (4 поля)

Каждый трансформер создает:
1. `publication-type` — raw provider-specific type (backward compatibility)
2. `publication-type-unified` — Level 3 unified type
3. `publication-subclass` — Level 2 subclass
4. `publication-class` — Level 1 class code (EXP/REV/PEER)

---

### 7.4 Composite Layer Preservation

С `preserve-all-sources: true`:
- **НЕТ автоматического coalescing** полей
- **ВСЕ поля сохраняются** с provider qualification
- Результат: ~20 publication-type-related колонок для записи с 5 провайдерами

---

### 7.5 ChEMBL Отличие

ChEMBL:
- Использует ограниченный enum (4 значения): `PUBLICATION`, `PATENT`, `DATASET`, `BOOK`
- **НЕ участвует** в unified classification с 214 типами
- `doc-type` → `publication-type` mapping существует в `publication-fields.py`, но это field name mapping, не value classification

---

### 7.6 Field Naming Inconsistencies

**Внутри провайдеров (Bronze → Silver):**
- CrossRef: `type` (Bronze) → `type` + `publication-type` (Silver, duplicated)
- OpenAlex: `type` (Bronze) → `type` + `publication-type` (Silver, duplicated)
- PubMed: `PublicationType` (Bronze XML) → `publication-type` (Silver, joined with `|`)
- SemanticScholar: `publicationTypes` (Bronze) → `publication-type` + `publication-types` (Silver, resolved + JSON)

**В Composite:**
- `crossref.publication.type` vs `crossref.publication.publication-type` (оба содержат одинаковое значение)
- `openalex.publication.type` vs `openalex.publication.publication-type` (оба содержат одинаковое значение)

**Причина:** field-groups configuration сохраняет оба имени для backward compatibility.

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
    "openalex-id": "W2741809807",
    "publication-type": "article",
    "publication-type-unified": "Journal Article",
    "publication-subclass": "Original Experimental Data",
    "publication-class": "EXP",
}
```

**Composite:**
```
openalex.publication.type: "article"
openalex.publication.publication-type: "article"
openalex.publication.publication-type-unified: "Journal Article"
openalex.publication.publication-subclass: "Original Experimental Data"
openalex.publication.publication-class: "EXP"
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
    "publication-type": "Journal Article|Meta-Analysis|Review",  # Joined
    "publication-type-unified": "Meta-Analysis",  # Most specific (row 41)
    "publication-subclass": "Reviews & Syntheses",
    "publication-class": "REV",
}
```

**Алгоритм:**
- "Journal Article" → row 2 (specificity=2)
- "Meta-Analysis" → row 41 (specificity=41) ← **Winner**
- "Review" → row 39 (specificity=39)

**Composite:**
```
pubmed.publication.publication-type: "Journal Article|Meta-Analysis|Review"
pubmed.publication.publication-type-unified: "Meta-Analysis"
pubmed.publication.publication-subclass: "Reviews & Syntheses"
pubmed.publication.publication-class: "REV"
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
    "publication-type": "proceedings-article",
    "publication-type-unified": "Conference Paper",
    "publication-subclass": "Original Experimental Data",
    "publication-class": "EXP",
}
```

**Silver (OpenAlex):**
```python
{
    "openalex-id": "W3012345678",
    "publication-type": "article",
    "publication-type-unified": "Conference Paper",  # Secondary mapping
    "publication-subclass": "Original Experimental Data",
    "publication-class": "EXP",
}
```

**Примечание:** OpenAlex `"article"` может мапиться на "Journal Article" (row 2) ИЛИ "Conference Paper" (row 3, secondary with `*`). Classifier выбирает primary mapping (row 2).

---

## Часть 9: Архитектурные Инварианты

### 9.1 Domain Layer Purity

**Файл:** `domain/mapping/publication-type-classification.py`

✅ **Соответствует RULES.md:**
- Pure Python (no I/O)
- Lookup tables built at import time (no file reading)
- Value Objects (PublicationTypeEntry dataclass)
- Type-safe API (typing.Protocol not needed here, but consistent)

---

### 9.2 Template Method Pattern

**Файл:** `application/pipelines/common/base-publication-transformer.py`

✅ **Соответствует Pattern:**
- `-transform-impl()` — Template Method (base class)
- `-extract-business-data()` — Abstract (provider-specific)
- `-classify-publication-type()` — Reusable helper (base class)

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

### 10.1 Deduplicate `type` and `publication-type`

**Проблема:** CrossRef и OpenAlex имеют оба поля с одинаковым значением.

**Текущее состояние:**
```python
{
    "publication-type": rec.get("type"),  # Raw
    # ...
    "type": rec.get("type"),  # Duplicate via field-groups
}
```

**Решение:** Удалить дублирование, оставить только `publication-type` в Silver schemas.

**Impact:** Requires field-groups update and schema validation tests.

---

### 10.2 ChEMBL Integration в Unified Classification

**Проблема:** ChEMBL использует 4-value enum, не участвует в unified 214-type classification.

**Текущее состояние:**
- ChEMBL: `doc-type` ∈ {PUBLICATION, PATENT, DATASET, BOOK}
- No `publication-type-unified`, `publication-subclass`, `publication-class`

**Решение:** Add ChEMBL column to `-CLASSIFICATION-TABLE` for 4 types:

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

**Проблема:** `publication-type-unified`, `publication-subclass`, `publication-class` не перечислены в `column-groups`.

**Текущее состояние:**
```yaml
# configs/pipelines/composite/publication.yaml:406-409
- name: doc-type
  fields:
    - publication-status
    - publication-type
    - publication-type-list
    - publication-types
    # Missing: publication-type-unified, publication-subclass, publication-class
```

**Решение:** Add to column-groups for explicit ordering:

```yaml
- name: doc-type
  fields:
    - publication-status
    - publication-type
    - publication-type-unified  # Add
    - publication-subclass      # Add
    - publication-class         # Add
    - publication-type-list
    - publication-types
```

**Benefit:** Explicit control over column ordering in composite output.

---

### 10.4 Deprecate `publication-type-list` and `publication-types` (PubMed)

**Проблема:** PubMed Silver schema имеет deprecated placeholders:
- `publication-type-list` — always NULL
- `publication-types` — always NULL (not to be confused with SemanticScholar's field)

**Текущее состояние:**
```python
# pubmed/publication.py schema
publication-type-list: Series[str] | None = pa.Field(nullable=True, ...)
publication-types: Series[str] | None = pa.Field(nullable=True, ...)
```

**Решение:** Remove from schema, update field-groups, update skipped tests analysis.

**Benefit:** Reduce schema complexity, eliminate confusion with SemanticScholar's `publication-types`.

---

### 10.5 PyArrow Schema Missing Fields (RESOLVED - 2026-02-10)

**Проблема (ROOT CAUSE):** Classification fields (`publication-type-unified`, `publication-subclass`, `publication-class`) отсутствовали в PyArrow schemas для публикаций.

**Файл:** `src/bioetl/infrastructure/schemas/silver.py`

**Пострадавшие schemas:**
- `CHEMBL-PUBLICATION-SCHEMA`
- `PUBMED-PUBLICATION-SCHEMA`
- `SEMANTICSCHOLAR-PUBLICATION-SCHEMA`
- `CROSSREF-PUBLICATION-SCHEMA`
- `OPENALEX-PUBLICATION-SCHEMA`

**Симптомы:**

1. **Transformers создавали поля:** Все publication transformers вызывали `-classify-publication-type()` и добавляли classification fields в records
2. **Writer фильтровал поля:** `SilverWriter.-prepare-arrow-data()` (line 194) фильтровал records, оставляя только поля из PyArrow schema:
   ```python
   schema-fields = set(schema.names)
   filtered-records = [
       {k: v for k, v in record.items() if k in schema-fields}
       for record in records
   ]
   ```
3. **Result:** Classification fields НЕ попадали в Silver Delta tables и отсутствовали в Composite output

**Доказательства:**
- Pandera schemas (`domain/schemas/common/publication-base.py`) содержали поля (validation OK)
- Entity dataclasses (`domain/entities/publication-base.py`) содержали поля (types OK)
- PyArrow schemas НЕ содержали поля (write filtering!)

**Решение (2026-02-10):**

Добавлены 3 classification fields во все 5 PyArrow schemas после `publication-type` field:

```python
pa.field("publication-type", pa.string()),  # Raw provider type
pa.field("publication-type-unified", pa.string()),  # Level 3: "Journal Article", etc.
pa.field("publication-subclass", pa.string()),  # Level 2: "Original Experimental Data", etc.
pa.field("publication-class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
```

**Affected Lines:**
- CHEMBL-PUBLICATION-SCHEMA: lines 52-56
- PUBMED-PUBLICATION-SCHEMA: lines 347-351
- SEMANTICSCHOLAR-PUBLICATION-SCHEMA: lines 777-781
- CROSSREF-PUBLICATION-SCHEMA: lines 839-843
- OPENALEX-PUBLICATION-SCHEMA: lines 926-930

**Impact:**

✅ **Provider pipelines:** Classification fields теперь записываются в Silver Delta tables
✅ **Composite pipeline:** `write-silver-merged()` динамически выводит schema из records → classification fields автоматически включаются
✅ **Tests:** Добавлен `TestPublicationSchemaClassificationFields` в `tests/unit/infrastructure/schemas/test-silver.py`

**Verification:**

После перезапуска pipelines:
```bash
# Check Silver output
python -m pytest tests/unit/infrastructure/schemas/test-silver.py::TestPublicationSchemaClassificationFields -v

# Verify Delta tables contain new fields
# data/output/silver/{provider}/publication/*.parquet
```

**Status:** ✅ RESOLVED

---

## Заключение

**Нормализация publication-type полей в BioETL:**

1. ✅ **Unified 3-level classification** (214 types) применяется в Silver Layer для OpenAlex, CrossRef, PubMed, SemanticScholar
2. ✅ **Multi-value strategy** (PubMed, S2): выбор most specific type (highest row number)
3. ✅ **Preserve all sources** в Composite Layer: все provider-qualified колонки сохраняются
4. ✅ **PyArrow schemas updated** (2026-02-10): classification fields теперь присутствуют в Silver output
5. ⚠️ **ChEMBL не участвует** в unified classification (4-value enum)
6. ⚠️ **Дублирование полей** (`type` vs `publication-type` для CrossRef/OpenAlex)
7. ⚠️ **Classification fields не перечислены** в column-groups (неявный порядок)

**Метрики:**
- **214 unified types** (Level 3)
- **~25 subclasses** (Level 2)
- **3 class codes** (Level 1: EXP/REV/PEER)
- **4 провайдера** в unified classification (OpenAlex, CrossRef, PubMed, SemanticScholar)
- **5 провайдеров total** (+ ChEMBL с отдельным enum)
- **~20 publication-type columns** в composite output (для записи с 5 провайдерами)

---

**Дата создания:** 2026-02-10
**Автор:** Claude Code (AI-generated analysis)
**Статус:** ✅ Complete — ready for review
