# Сравнение нормализации данных по пайплайнам

*Дата: 2026-02-16 | Источник: анализ Pandera-схем и трансформеров*

Документ сравнивает валидацию и нормализацию **одноименных (или семантически эквивалентных) полей** в разных пайплайнах BioETL.

---

## 1. Молекулярные/соединения поля (ChEMBL Molecule vs PubChem Compound)

Сравнение полей, описывающих одни и те же химические свойства в двух провайдерах.

| Поле (смысл) | Имя в ChEMBL | Имя в PubChem | ChEMBL: тип + валидация | PubChem: тип + валидация | Нормализация (трансформер) |
|---|---|---|---|---|---|
| **Primary Key** | `molecule-id` | `molecule-id` | `str`, NOT NULL, `^CHEMBL\d+$` | `str`, NOT NULL, `^[1-9]\d*$` (CID) | ChEMBL: из API напрямую; PubChem: str(CID) |
| **Canonical SMILES** | `canonical-smiles` | `canonical-smiles` | `str \| None`, nullable, без ограничений длины | `str \| None`, nullable, **max 10 000 chars** (custom check) | Оба: из вложенного JSON/dict, без трансформации строки |
| **InChI Key** | `inchi-key` | `inchi-key` | `str \| None`, `^[A-Z]{14}-[A-Z]{10}-[A-Z]$` | `str \| None`, `^[A-Z]{14}-[A-Z]{10}-[A-Z]$` (custom check) | **Идентичная** валидация regex. ChEMBL: str-matches в Field; PubChem: @pa.check метод |
| **Molecular Weight** | `molecular-weight` | `molecular-weight` | `float \| None`, nullable, **без bounds** | `float \| None`, nullable, **ge=0, le=100 000** | Оба: `safe-float()`. ChEMBL: rename `full-mwt` → `molecular-weight`; PubChem: из API напрямую |
| **Molecular Formula** | `molecular-formula` | `molecular-formula` | `str \| None`, nullable, без проверок | `str \| None`, nullable, без проверок | ChEMBL: rename `full-molformula`; PubChem: напрямую |
| **LogP / XLogP** | `logp` | `xlogp` | `float \| None`, nullable, **без bounds**; + `logp-method` ∈ {alogp, xlogp} | `float \| None`, nullable, **[-20, 20]** (custom check) | ChEMBL: rename `property-alogp` → `logp`, `safe-float()`; PubChem: `safe-float()` |
| **H-Bond Acceptors** | `hba-count` | `h-bond-acceptor-count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[0, 50]** (custom check) | ChEMBL: rename `property-hba`, `safe-int()`; PubChem: `safe-int()` |
| **H-Bond Donors** | `hbd-count` | `h-bond-donor-count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[0, 50]** (custom check) | ChEMBL: rename `property-hbd`, `safe-int()`; PubChem: `safe-int()` |
| **Rotatable Bonds** | `rotatable-bond-count` | `rotatable-bond-count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[0, 100]** (custom check) | ChEMBL: rename `property-rtb`, `safe-int()`; PubChem: `safe-int()` |
| **Polar Surface Area** | `polar-surface-area` | `tpsa` | `float \| None`, **ge=0** | `float \| None`, **ge=0** (custom check) | ChEMBL: rename `property-psa`, `safe-float()`; PubChem: `safe-float()` |
| **Heavy Atom Count** | `heavy-atom-count` | `heavy-atom-count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[1, 500]** (custom check) | ChEMBL: rename `property-heavy-atoms`, `safe-int()`; PubChem: `safe-int()` |
| **Aromatic Ring Count** | `aromatic-ring-count` | — | `int \| None`, ge=0 | *Нет в PubChem* | ChEMBL: `safe-int()` |
| **QED Score** | `qed-score` | — | `float \| None`, [0, 1] | *Нет в PubChem* | ChEMBL: rename `qed-weighted`, `safe-float()` |
| **RO5 Violations** | `ro5-violation-count` | — | `int \| None`, [0, 4] | *Нет в PubChem* | ChEMBL: rename `num-ro5-violations`, `safe-int()` |
| **Standard InChI** | `standard-inchi` | `inchi` | `str \| None`, без проверок | `str \| None`, **starts with "InChI="** (custom check) | PubChem: @pa.check validates prefix |
| **Isomeric SMILES** | — | `isomeric-smiles` | *Нет в ChEMBL* | `str \| None`, **max 10 000 chars** | PubChem-only |
| **Exact Mass** | — | `exact-mass` | *Нет в ChEMBL* | `float \| None`, **ge=0** | PubChem-only |
| **Complexity** | — | `complexity` | *Нет в ChEMBL* | `float \| None`, **ge=0** | PubChem-only |
| **Charge** | — | `charge` | *Нет в ChEMBL* | `Int64Dtype \| None`, **[-10, 10]** | PubChem-only |

### Ключевые различия (молекулы)

1. **Naming**: ChEMBL использует сокращения (`hba-count`, `tpsa` → `polar-surface-area`), PubChem — полные имена (`h-bond-acceptor-count`).
2. **Bounds**: PubChem задаёт явные верхние границы (50 для HBA/HBD, 100 для rotatable bonds, 500 для heavy atoms). ChEMBL ограничивает только `ge=0`.
3. **Nullable Int**: PubChem использует `pd.Int64Dtype` (nullable integer), ChEMBL — `Series[int] | None` (coerced).
4. **InChI**: PubChem валидирует prefix "InChI=", ChEMBL — нет.
5. **SMILES**: PubChem ограничивает длину 10 000 chars, ChEMBL — без ограничений.

---

## 2. Публикационные поля (5 провайдеров)

Все публикационные схемы наследуют `PublicationBaseSchema`. Ниже указаны **отличия от базы** и специфика каждого провайдера.

### 2.1 Идентификаторы

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **pmid** | `str`, nullable, `^[1-9]\d*$` | **NOT NULL**, `^[1-9]\d*$` (PK) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **doi** | `str`, nullable, `^10\.\d{4,}/\S+$` | nullable, тот же regex | **NOT NULL**, тот же regex (PK) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **pmc-id** | `str`, nullable, `^PMC\d+$` | nullable + custom `@pa.check` | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **Provider PK** | — | `pmid` | `doi` | `openalex-id`: `^W\d+$` | `paper-id`: `^[a-f0-9]{40}$` | `publication-id`: `^CHEMBL\d+$` |

**Нормализация идентификаторов (трансформеры):**
- `doi`: `normalize-doi()` → lowercase, strip — **все 5 провайдеров**
- `pmc-id`: `normalize-pmc-id()` → uppercase, prefix "PMC" — PubMed, OpenAlex
- `pmid`: str conversion + regex validation — PubMed (PK), остальные при наличии

### 2.2 Контент

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **title** | `str`, nullable | **NOT NULL** | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **abstract** | `str`, nullable | nullable (наследует) | nullable (override) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **authors** | `str` (JSON array), nullable | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **affiliation-list** | `str` (JSON array), nullable | nullable (наследует) | nullable (override) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **author-orcids** | `str` (JSON array), nullable | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |

**Нормализация контента (трансформеры):**

| Операция | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| `strip-html-tags()` для title | Да | Нет | Нет | Нет | Нет |
| `strip-html-tags()` для abstract | Да (JATS XML) | Нет | Нет | Нет | — |
| `normalize-string()` для title | Да | Да | Да | Да | Да |
| PII hashing для authors | `hash-pii-list()` | `hash-pii-list()` | `hash-pii-list()` | `hash-pii-list()` | `hash-pii-list()` |
| `parse-authors-to-list()` | Через `AuthorExtractor` | `extract-authors()` | из authorships | `-extract-author-metadata()` | из API напрямую |
| Abstract из structured sections | `AbstractExtractor` (NLM) | Нет | inverted-abstract reconstruction | Нет | — |

### 2.3 Метаданные публикации

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **journal** | `str`, nullable | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **publication-year** | `Int64Dtype`, nullable, **[1950, 2050]** | наследует bounds | наследует bounds | наследует bounds | наследует bounds | наследует bounds |
| **publication-date** | `str`, nullable, `^\d{4}-\d{2}-\d{2}$` | наследует | наследует | наследует | наследует | *не предоставляется* |
| **publication-type** | `str`, nullable | nullable (наследует) | nullable (override) | nullable (override) | nullable (override) | `isin` = {PUBLICATION, PATENT, DATASET, BOOK} |
| **publication-type-unified** | `str`, nullable | наследует | наследует | наследует | наследует | наследует |
| **publication-class** | `str`, nullable, `isin` = [EXP, REV, PEER] | наследует | наследует | наследует | наследует | наследует |
| **language** | `str`, nullable, len 2-3 | наследует | наследует | наследует | *S2 не возвращает* | *не предоставляется* |

**Нормализация дат (трансформеры):**

| Операция | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| Источник даты | XML: Year/Month/Day | `date-parts` [[Y,M?,D?]] | `publication-date` (ISO) | `publicationDate` (ISO) | `year` (int) |
| Парсинг | `DateExtractor` (month map, partial dates) | `format-date-parts()` (end-of-period norm.) | прямое извлечение ISO | прямое извлечение ISO | только year |
| End-of-period norm. | Нет | **Да**: month-only → last day; year-only → Dec 31 | Нет | Нет | Нет |
| `validate-publication-year()` | Да (+ DQ warning) | Да (+ DQ warning) | Да (+ DQ warning) | Да (+ DQ warning) | Да |

### 2.4 Пагинация

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **page-first** | `str`, nullable | наследует | наследует | наследует | *нет* (есть `page-range`) | наследует |
| **page-last** | `str`, nullable | наследует | наследует | наследует | *нет* (есть `page-range`) | наследует |
| **page-range** | *нет в базе* | Да (unified + medline-pgn) | *нет* | *нет* | Да (legacy format) | *нет* |

**Нормализация пагинации (трансформеры):**

| Операция | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| `parse-page-range()` | **Да** (dash norm., abbreviated expand, e-pages) | **Да** | Из `biblio.first-page/last-page` | Не разбирает | Из `first-page`/`last-page` напрямую |
| Abbreviated page expand | 737-9 → 739, 199-3 → 203 | То же | Нет | Нет | Нет |
| En/em-dash → hyphen | Да (–/— → -) | Да | Нет | Нет | Нет |
| Electronic pages (e-123) | Обработка: first=e-123, last=None | То же | Нет | Нет | Нет |

### 2.5 Метрики цитирования

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **citations-received** | `Int64Dtype`, nullable, ge=0 | *не предоставляется* | наследует (из `is-referenced-by-count`) | наследует (из `cited-by-count`) | наследует (из `citationCount`) | *не предоставляется* |
| **citations-made** | `Int64Dtype`, nullable, ge=0 | *не предоставляется* | наследует (из `references-count`) | наследует (из `referenced-works-count`) | наследует (из `referenceCount`) | *не предоставляется* |
| **is-oa** | `bool`, nullable | *не предоставляется* | наследует | наследует | наследует | *не предоставляется* |
| **oa-status** | *нет в базе* | — | — | `isin` = [gold, green, hybrid, bronze, closed] | `isin` = [gold, green, hybrid, bronze, closed] | — |

### 2.6 ISSN

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| **issn** | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` (ISSN-L) | *нет* | *нет* |
| **issn-list** | *нет* | Да (JSON array) | *нет* | *нет* | *нет* |
| **issn-print** | *нет* | `^\d{4}-\d{3}[\dX]$` | *нет* | *нет* | *нет* |
| **issn-electronic** | *нет* | `^\d{4}-\d{3}[\dX]$` | *нет* | *нет* | *нет* |
| **journal-issn-type** | `isin` = [Print, Electronic, Linking] | *нет* | *нет* | *нет* | *нет* |

### 2.7 Системные поля (lookup tracking)

| Поле | Base Schema | Все провайдеры |
|---|---|---|
| **-lookup-method** | `str`, NOT NULL, `isin` = [direct, doi, pmid, title-fallback, title-only, unknown] | Все 5 одинаково |
| **-original-id** | `str`, nullable | Все 5 одинаково |
| **-source** | `str`, nullable | PubMed: eq="pubmed"; CrossRef: eq="crossref"; OpenAlex: eq="openalex"; S2: eq="semanticscholar"; ChEMBL: eq="chembl" |

### 2.8 Классификация / предметные области

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| **subject-mesh** | Да (JSON array, descriptor/qualifier) | *нет* | Да (JSON array, descriptor names) | *нет* | *нет* |
| **subject-keywords** | Да (JSON array, author keywords) | Да (JSON array, subject areas) | Да (JSON array) | *нет* | *нет* |
| **subject-fields** | *нет* | *нет* | *нет* | Да (JSON array, fields of study) | *нет* |
| **subject-topics** | *нет* | *нет* | Да (JSON array, hierarchical topics) | *нет* | *нет* |
| **chemicals** | Да (JSON array, name/registry) | *нет* | *нет* | *нет* | *нет* |
| **gene-symbols** | Да (JSON array) | *нет* | *нет* | *нет* | *нет* |

---

## 3. Перекрёстные ID (ChEMBL-entities)

ID полей, встречающихся в нескольких ChEMBL-сущностях.

| ID поле | Сущности, где используется | Тип | Валидация |
|---|---|---|---|
| **molecule-id** | Molecule (PK), Activity (FK), CompoundRecord (FK), PubChem Compound (PK) | `str`, NOT NULL | ChEMBL: `^CHEMBL\d+$`; PubChem: `^[1-9]\d*$` |
| **target-id** | Target (PK), Assay (FK, nullable), Activity (FK, nullable), UniProt IDMapping (FK) | `str` | `^CHEMBL\d+$` |
| **assay-id** | Assay (PK), Activity (FK), AssayParameters (FK) | `str`, NOT NULL | `^CHEMBL\d+$` |
| **publication-id** | Publication (PK), Activity (FK, nullable), Assay (FK, nullable), CompoundRecord (FK), PublicationTerm (composite PK) | `str` | `^CHEMBL\d+$` |

---

## 4. Общие функции нормализации

Центральные функции из `domain/normalization.py` и `domain/validation.py`, используемые несколькими пайплайнами:

| Функция | Описание | Используется в пайплайнах |
|---|---|---|
| `safe-int()` | `Any → int \| None` (None при NaN/Inf/invalid) | Все |
| `safe-float()` | `Any → float \| None` (round 10 decimals, None при NaN/Inf) | Все |
| `normalize-string()` | strip + None для пустых | Все |
| `normalize-doi()` | lowercase + strip | PubMed, CrossRef, OpenAlex, S2, ChEMBL |
| `normalize-pmc-id()` | uppercase + prefix "PMC" | PubMed, OpenAlex |
| `strip-html-tags()` | remove HTML/JATS + decode entities + normalize whitespace | PubMed |
| `parse-page-range()` | split + expand abbreviated + dash norm + e-pages | PubMed, CrossRef |
| `parse-authors-to-list()` | list/JSON/delimited → list[str] | Все publication pipelines |
| `format-date-parts()` | CrossRef date-parts → ISO YYYY-MM-DD | CrossRef |
| `validate-publication-year()` | [1950, 2050] range check + DQ warning | Все publication pipelines |
| `validate-molecular-weight()` | float conversion + range (0, 100 000) | ChEMBL Molecule, PubChem Compound |
| `validate-smiles()` | basic regex syntax check | ChEMBL Molecule |
| `hash-pii-list()` | SHA-256 hashing авторов (PII protection) | Все publication pipelines |
| `normalize-for-hash()` | exclude META-FIELDS, normalize types, round floats | Все (content-hash computation) |

---

## 5. Сводка ключевых различий

| Аспект | Описание |
|---|---|
| **Naming conventions** | ChEMBL использует сокращения (`hba`, `hbd`, `psa`, `rtb`), PubChem — полные имена. Publication fields унифицированы через base schema. |
| **Bounds strictness** | PubChem задаёт **явные верхние границы** для chemical counts (50, 100, 500). ChEMBL — только `ge=0`. |
| **Nullable int strategy** | PubChem: `pd.Int64Dtype` (modern nullable int). ChEMBL: `Series[int] \| None` (coerced by Pandera). |
| **Schema strictness** | ChEMBL Molecule: `strict=True` (запрещены лишние колонки). PubChem, все publications: `strict=False`. |
| **Date normalization** | CrossRef — end-of-period normalization (unique). PubMed — month name mapping. Остальные — прямой ISO парсинг. |
| **HTML cleanup** | Только PubMed применяет `strip-html-tags()` к title/abstract (JATS XML source). |
| **Page range processing** | PubMed и CrossRef: полный парсинг (`parse-page-range()`). Остальные: прямое извлечение или без обработки. |
| **PII protection** | `hash-pii-list()` применяется ко всем publication pipelines одинаково. |
| **Content hash** | `normalize-for-hash()` + SHA-256 — единый для всех пайплайнов (RULES.md §2.8.1). |
