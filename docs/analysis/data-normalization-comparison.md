# Сравнение нормализации данных по пайплайнам

*Дата: 2026-02-16 | Источник: анализ Pandera-схем и трансформеров*

Документ сравнивает валидацию и нормализацию **одноименных (или семантически эквивалентных) полей** в разных пайплайнах BioETL.

---

## 1. Молекулярные/соединения поля (ChEMBL Molecule vs PubChem Compound)

Сравнение полей, описывающих одни и те же химические свойства в двух провайдерах.

| Поле (смысл) | Имя в ChEMBL | Имя в PubChem | ChEMBL: тип + валидация | PubChem: тип + валидация | Нормализация (трансформер) |
|---|---|---|---|---|---|
| **Primary Key** | `molecule_id` | `molecule_id` | `str`, NOT NULL, `^CHEMBL\d+$` | `str`, NOT NULL, `^[1-9]\d*$` (CID) | ChEMBL: из API напрямую; PubChem: str(CID) |
| **Canonical SMILES** | `canonical_smiles` | `canonical_smiles` | `str \| None`, nullable, без ограничений длины | `str \| None`, nullable, **max 10 000 chars** (custom check) | Оба: из вложенного JSON/dict, без трансформации строки |
| **InChI Key** | `inchi_key` | `inchi_key` | `str \| None`, `^[A-Z]{14}-[A-Z]{10}-[A-Z]$` | `str \| None`, `^[A-Z]{14}-[A-Z]{10}-[A-Z]$` (custom check) | **Идентичная** валидация regex. ChEMBL: str_matches в Field; PubChem: @pa.check метод |
| **Molecular Weight** | `molecular_weight` | `molecular_weight` | `float \| None`, nullable, **без bounds** | `float \| None`, nullable, **ge=0, le=100 000** | Оба: `safe_float()`. ChEMBL: rename `full_mwt` → `molecular_weight`; PubChem: из API напрямую |
| **Molecular Formula** | `molecular_formula` | `molecular_formula` | `str \| None`, nullable, без проверок | `str \| None`, nullable, без проверок | ChEMBL: rename `full_molformula`; PubChem: напрямую |
| **LogP / XLogP** | `logp` | `xlogp` | `float \| None`, nullable, **без bounds**; + `logp_method` ∈ {alogp, xlogp} | `float \| None`, nullable, **[-20, 20]** (custom check) | ChEMBL: rename `property_alogp` → `logp`, `safe_float()`; PubChem: `safe_float()` |
| **H-Bond Acceptors** | `hba_count` | `h_bond_acceptor_count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[0, 50]** (custom check) | ChEMBL: rename `property_hba`, `safe_int()`; PubChem: `safe_int()` |
| **H-Bond Donors** | `hbd_count` | `h_bond_donor_count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[0, 50]** (custom check) | ChEMBL: rename `property_hbd`, `safe_int()`; PubChem: `safe_int()` |
| **Rotatable Bonds** | `rotatable_bond_count` | `rotatable_bond_count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[0, 100]** (custom check) | ChEMBL: rename `property_rtb`, `safe_int()`; PubChem: `safe_int()` |
| **Polar Surface Area** | `polar_surface_area` | `tpsa` | `float \| None`, **ge=0** | `float \| None`, **ge=0** (custom check) | ChEMBL: rename `property_psa`, `safe_float()`; PubChem: `safe_float()` |
| **Heavy Atom Count** | `heavy_atom_count` | `heavy_atom_count` | `int \| None`, **ge=0** | `Int64Dtype \| None`, **[1, 500]** (custom check) | ChEMBL: rename `property_heavy_atoms`, `safe_int()`; PubChem: `safe_int()` |
| **Aromatic Ring Count** | `aromatic_ring_count` | — | `int \| None`, ge=0 | *Нет в PubChem* | ChEMBL: `safe_int()` |
| **QED Score** | `qed_score` | — | `float \| None`, [0, 1] | *Нет в PubChem* | ChEMBL: rename `qed_weighted`, `safe_float()` |
| **RO5 Violations** | `ro5_violation_count` | — | `int \| None`, [0, 4] | *Нет в PubChem* | ChEMBL: rename `num_ro5_violations`, `safe_int()` |
| **Standard InChI** | `standard_inchi` | `inchi` | `str \| None`, без проверок | `str \| None`, **starts with "InChI="** (custom check) | PubChem: @pa.check validates prefix |
| **Isomeric SMILES** | — | `isomeric_smiles` | *Нет в ChEMBL* | `str \| None`, **max 10 000 chars** | PubChem-only |
| **Exact Mass** | — | `exact_mass` | *Нет в ChEMBL* | `float \| None`, **ge=0** | PubChem-only |
| **Complexity** | — | `complexity` | *Нет в ChEMBL* | `float \| None`, **ge=0** | PubChem-only |
| **Charge** | — | `charge` | *Нет в ChEMBL* | `Int64Dtype \| None`, **[-10, 10]** | PubChem-only |

### Ключевые различия (молекулы)

1. **Naming**: ChEMBL использует сокращения (`hba_count`, `tpsa` → `polar_surface_area`), PubChem — полные имена (`h_bond_acceptor_count`).
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
| **pmc_id** | `str`, nullable, `^PMC\d+$` | nullable + custom `@pa.check` | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **Provider PK** | — | `pmid` | `doi` | `openalex_id`: `^W\d+$` | `paper_id`: `^[a-f0-9]{40}$` | `publication_id`: `^CHEMBL\d+$` |

**Нормализация идентификаторов (трансформеры):**
- `doi`: `normalize_doi()` → lowercase, strip — **все 5 провайдеров**
- `pmc_id`: `normalize_pmc_id()` → uppercase, prefix "PMC" — PubMed, OpenAlex
- `pmid`: str conversion + regex validation — PubMed (PK), остальные при наличии

### 2.2 Контент

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **title** | `str`, nullable | **NOT NULL** | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **abstract** | `str`, nullable | nullable (наследует) | nullable (override) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **authors** | `str` (JSON array), nullable | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **affiliation_list** | `str` (JSON array), nullable | nullable (наследует) | nullable (override) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **author_orcids** | `str` (JSON array), nullable | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |

**Нормализация контента (трансформеры):**

| Операция | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| `strip_html_tags()` для title | Да | Нет | Нет | Нет | Нет |
| `strip_html_tags()` для abstract | Да (JATS XML) | Нет | Нет | Нет | — |
| `normalize_string()` для title | Да | Да | Да | Да | Да |
| PII hashing для authors | `hash_pii_list()` | `hash_pii_list()` | `hash_pii_list()` | `hash_pii_list()` | `hash_pii_list()` |
| `parse_authors_to_list()` | Через `AuthorExtractor` | `extract_authors()` | из authorships | `_extract_author_metadata()` | из API напрямую |
| Abstract из structured sections | `AbstractExtractor` (NLM) | Нет | inverted_abstract reconstruction | Нет | — |

### 2.3 Метаданные публикации

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **journal** | `str`, nullable | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) | nullable (наследует) |
| **publication_year** | `Int64Dtype`, nullable, **[1950, 2050]** | наследует bounds | наследует bounds | наследует bounds | наследует bounds | наследует bounds |
| **publication_date** | `str`, nullable, `^\d{4}-\d{2}-\d{2}$` | наследует | наследует | наследует | наследует | *не предоставляется* |
| **publication_type** | `str`, nullable | nullable (наследует) | nullable (override) | nullable (override) | nullable (override) | `isin` = {PUBLICATION, PATENT, DATASET, BOOK} |
| **publication_type_unified** | `str`, nullable | наследует | наследует | наследует | наследует | наследует |
| **publication_class** | `str`, nullable, `isin` = [EXP, REV, PEER] | наследует | наследует | наследует | наследует | наследует |
| **language** | `str`, nullable, len 2-3 | наследует | наследует | наследует | *S2 не возвращает* | *не предоставляется* |

**Нормализация дат (трансформеры):**

| Операция | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| Источник даты | XML: Year/Month/Day | `date-parts` [[Y,M?,D?]] | `publication_date` (ISO) | `publicationDate` (ISO) | `year` (int) |
| Парсинг | `DateExtractor` (month map, partial dates) | `format_date_parts()` (end-of-period norm.) | прямое извлечение ISO | прямое извлечение ISO | только year |
| End-of-period norm. | Нет | **Да**: month-only → last day; year-only → Dec 31 | Нет | Нет | Нет |
| `validate_publication_year()` | Да (+ DQ warning) | Да (+ DQ warning) | Да (+ DQ warning) | Да (+ DQ warning) | Да |

### 2.4 Пагинация

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **page_first** | `str`, nullable | наследует | наследует | наследует | *нет* (есть `page_range`) | наследует |
| **page_last** | `str`, nullable | наследует | наследует | наследует | *нет* (есть `page_range`) | наследует |
| **page_range** | *нет в базе* | Да (unified + medline_pgn) | *нет* | *нет* | Да (legacy format) | *нет* |

**Нормализация пагинации (трансформеры):**

| Операция | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| `parse_page_range()` | **Да** (dash norm., abbreviated expand, e-pages) | **Да** | Из `biblio.first_page/last_page` | Не разбирает | Из `first_page`/`last_page` напрямую |
| Abbreviated page expand | 737-9 → 739, 199-3 → 203 | То же | Нет | Нет | Нет |
| En/em-dash → hyphen | Да (–/— → -) | Да | Нет | Нет | Нет |
| Electronic pages (e-123) | Обработка: first=e-123, last=None | То же | Нет | Нет | Нет |

### 2.5 Метрики цитирования

| Поле | Base Schema | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|---|
| **citations_received** | `Int64Dtype`, nullable, ge=0 | *не предоставляется* | наследует (из `is-referenced-by-count`) | наследует (из `cited_by_count`) | наследует (из `citationCount`) | *не предоставляется* |
| **citations_made** | `Int64Dtype`, nullable, ge=0 | *не предоставляется* | наследует (из `references-count`) | наследует (из `referenced_works_count`) | наследует (из `referenceCount`) | *не предоставляется* |
| **is_oa** | `bool`, nullable | *не предоставляется* | наследует | наследует | наследует | *не предоставляется* |
| **oa_status** | *нет в базе* | — | — | `isin` = [gold, green, hybrid, bronze, closed] | `isin` = [gold, green, hybrid, bronze, closed] | — |

### 2.6 ISSN

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| **issn** | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` | `^\d{4}-\d{3}[\dX]$` (ISSN-L) | *нет* | *нет* |
| **issn_list** | *нет* | Да (JSON array) | *нет* | *нет* | *нет* |
| **issn_print** | *нет* | `^\d{4}-\d{3}[\dX]$` | *нет* | *нет* | *нет* |
| **issn_electronic** | *нет* | `^\d{4}-\d{3}[\dX]$` | *нет* | *нет* | *нет* |
| **journal_issn_type** | `isin` = [Print, Electronic, Linking] | *нет* | *нет* | *нет* | *нет* |

### 2.7 Системные поля (lookup tracking)

| Поле | Base Schema | Все провайдеры |
|---|---|---|
| **_lookup_method** | `str`, NOT NULL, `isin` = [direct, doi, pmid, title_fallback, title_only, unknown] | Все 5 одинаково |
| **_original_id** | `str`, nullable | Все 5 одинаково |
| **_source** | `str`, nullable | PubMed: eq="pubmed"; CrossRef: eq="crossref"; OpenAlex: eq="openalex"; S2: eq="semanticscholar"; ChEMBL: eq="chembl" |

### 2.8 Классификация / предметные области

| Поле | PubMed | CrossRef | OpenAlex | Semantic Scholar | ChEMBL |
|---|---|---|---|---|---|
| **subject_mesh** | Да (JSON array, descriptor/qualifier) | *нет* | Да (JSON array, descriptor names) | *нет* | *нет* |
| **subject_keywords** | Да (JSON array, author keywords) | Да (JSON array, subject areas) | Да (JSON array) | *нет* | *нет* |
| **subject_fields** | *нет* | *нет* | *нет* | Да (JSON array, fields of study) | *нет* |
| **subject_topics** | *нет* | *нет* | Да (JSON array, hierarchical topics) | *нет* | *нет* |
| **chemicals** | Да (JSON array, name/registry) | *нет* | *нет* | *нет* | *нет* |
| **gene_symbols** | Да (JSON array) | *нет* | *нет* | *нет* | *нет* |

---

## 3. Перекрёстные ID (ChEMBL-entities)

ID полей, встречающихся в нескольких ChEMBL-сущностях.

| ID поле | Сущности, где используется | Тип | Валидация |
|---|---|---|---|
| **molecule_id** | Molecule (PK), Activity (FK), CompoundRecord (FK), PubChem Compound (PK) | `str`, NOT NULL | ChEMBL: `^CHEMBL\d+$`; PubChem: `^[1-9]\d*$` |
| **target_id** | Target (PK), Assay (FK, nullable), Activity (FK, nullable), UniProt IDMapping (FK) | `str` | `^CHEMBL\d+$` |
| **assay_id** | Assay (PK), Activity (FK), AssayParameters (FK) | `str`, NOT NULL | `^CHEMBL\d+$` |
| **publication_id** | Publication (PK), Activity (FK, nullable), Assay (FK, nullable), CompoundRecord (FK), PublicationTerm (composite PK) | `str` | `^CHEMBL\d+$` |

---

## 4. Общие функции нормализации

Центральные функции из `domain/normalization.py` и `domain/validation.py`, используемые несколькими пайплайнами:

| Функция | Описание | Используется в пайплайнах |
|---|---|---|
| `safe_int()` | `Any → int \| None` (None при NaN/Inf/invalid) | Все |
| `safe_float()` | `Any → float \| None` (round 10 decimals, None при NaN/Inf) | Все |
| `normalize_string()` | strip + None для пустых | Все |
| `normalize_doi()` | lowercase + strip | PubMed, CrossRef, OpenAlex, S2, ChEMBL |
| `normalize_pmc_id()` | uppercase + prefix "PMC" | PubMed, OpenAlex |
| `strip_html_tags()` | remove HTML/JATS + decode entities + normalize whitespace | PubMed |
| `parse_page_range()` | split + expand abbreviated + dash norm + e-pages | PubMed, CrossRef |
| `parse_authors_to_list()` | list/JSON/delimited → list[str] | Все publication pipelines |
| `format_date_parts()` | CrossRef date-parts → ISO YYYY-MM-DD | CrossRef |
| `validate_publication_year()` | [1950, 2050] range check + DQ warning | Все publication pipelines |
| `validate_molecular_weight()` | float conversion + range (0, 100 000) | ChEMBL Molecule, PubChem Compound |
| `validate_smiles()` | basic regex syntax check | ChEMBL Molecule |
| `hash_pii_list()` | SHA-256 hashing авторов (PII protection) | Все publication pipelines |
| `normalize_for_hash()` | exclude META_FIELDS, normalize types, round floats | Все (content_hash computation) |

---

## 5. Сводка ключевых различий

| Аспект | Описание |
|---|---|
| **Naming conventions** | ChEMBL использует сокращения (`hba`, `hbd`, `psa`, `rtb`), PubChem — полные имена. Publication fields унифицированы через base schema. |
| **Bounds strictness** | PubChem задаёт **явные верхние границы** для chemical counts (50, 100, 500). ChEMBL — только `ge=0`. |
| **Nullable int strategy** | PubChem: `pd.Int64Dtype` (modern nullable int). ChEMBL: `Series[int] \| None` (coerced by Pandera). |
| **Schema strictness** | ChEMBL Molecule: `strict=True` (запрещены лишние колонки). PubChem, все publications: `strict=False`. |
| **Date normalization** | CrossRef — end-of-period normalization (unique). PubMed — month name mapping. Остальные — прямой ISO парсинг. |
| **HTML cleanup** | Только PubMed применяет `strip_html_tags()` к title/abstract (JATS XML source). |
| **Page range processing** | PubMed и CrossRef: полный парсинг (`parse_page_range()`). Остальные: прямое извлечение или без обработки. |
| **PII protection** | `hash_pii_list()` применяется ко всем publication pipelines одинаково. |
| **Content hash** | `normalize_for_hash()` + SHA-256 — единый для всех пайплайнов (RULES.md §2.8.1). |
