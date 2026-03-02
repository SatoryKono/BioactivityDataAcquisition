# Pipeline Validation Matrix: Activity, Assay, Target, Molecule

*Версия: 1.0.0 | Дата: 2026-02-11*

Сводная таблица валидаций данных по четырём основным пайплайнам ChEMBL.

---

## 1. Архитектура валидации (слои)

Валидация происходит на нескольких уровнях:

| Слой | Источник | Описание |
|------|----------|----------|
| **Extraction** | `configs/filters/entities/chembl/{entity}.yaml` → `extraction-params` | Серверные фильтры API (query params). Только у Activity. |
| **Transformer** | `application/pipelines/chembl/{entity}-transformer.py` | Конвертация типов, Value Objects (InChIKey, SMILES, TaxonomyId), safe-float/safe-int |
| **Silver Schema** | `domain/schemas/chembl/{entity}.py` (Pandera) | Структурная валидация: типы, nullable, regex, enum, range. `strict=True` |
| **DQ Rules** | `configs/quality/entities/chembl/{entity}.yaml` | Бизнес-правила: required, range, enum, pattern, cross-field, conditional |
| **Silver Filter** | `configs/filters/entities/chembl/{entity}.yaml` → `silver-filters` | Доменные gates перед записью в Silver (только Activity) |
| **Gold Schema** | `domain/contracts/gold/chembl.py` (Pandera DataFrameModel) | Финальная структурная валидация. `strict=True`, int→float coercion |
| **Gold Filter** | `configs/filters/entities/chembl/{entity}.yaml` → `gold-filters` | Фильтры качества для Gold слоя |

**DQ thresholds** (наследование: `-defaults.yaml` → `providers/chembl.yaml` → `entities/chembl/{entity}.yaml`):
- **soft-fail**: >5% ошибок → Warning
- **hard-fail**: >15% ошибок → Fail Batch (ChEMBL строже дефолтных 20%)

---

## 2. Общие поля (все 4 пайплайна)

Эти поля наследуются от `ETLRecordSchema` (base) и присутствуют во всех пайплайнах.

| Поле | Тип | Nullable | Валидация |
|------|-----|----------|-----------|
| `entity-id` | str | No | Уникальный бизнес-идентификатор. Обязателен. |
| `content-hash` | str | No | SHA256 hex, regex `^[a-f0-9]{64}$`. DQ rule: required. |
| `-run-id` | str | No | Correlation ID пайплайн-рана. |
| `-run-type` | str | No | Enum: `incremental`, `backfill`, `rebuild`. |
| `-source-batch-id` | str | Yes | Batch context ID. |
| `-ingestion-ts` | str | No | ISO 8601 regex. DQ rule: pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`. |
| `-dq-warn` | bool | No | Default `False`. |
| `-dq-error` | bool | No | Default `False`. |
| `-index` | int | No | `ge=0`. Порядковый номер записи. |

**DQ Provider-level** (ChEMBL): паттерн `^CHEMBL\d+$` применяется к полям `molecule-chembl-id`, `target-chembl-id`, `assay-chembl-id`, `document-chembl-id` (nullable=true, применяется только при наличии значения).

---

## 3. Сводная таблица валидаций по полям и пайплайнам

Условные обозначения:
- **`—`** — поле отсутствует в пайплайне
- **req** — required (not null)
- **opt** — optional (nullable)
- Тип Silver / Gold через `/` если отличается

### 3.1 Primary Keys и Identifiers

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `activity-id` | **req**, str. Silver: PK. DQ: required. Filter: range 1..10^10 | — | — | — |
| `assay-chembl-id` | **req**, str, regex `^CHEMBL\d+$`. FK к Assay | **req**, str, regex `^CHEMBL\d+$`. Silver: PK. DQ: required | — | — |
| `molecule-chembl-id` | **req**, str, regex `^CHEMBL\d+$`. FK к Molecule. Transformer: `-get-required-field` | — | — | **req**, str, regex `^CHEMBL\d+$`. Silver: PK. DQ: required |
| `target-chembl-id` | **opt**, str, regex `^CHEMBL\d+$`. FK к Target. Conditional DQ: required if `assay-type=B`. Silver filter: required. Gold filter: required | **opt**, str, regex `^CHEMBL\d+$`. FK к Target | **req**, str, regex `^CHEMBL\d+$`. Silver: PK. DQ: required, enum `target-type` | — |
| `document-chembl-id` | **opt**, str, regex `^CHEMBL\d+$`. FK. Silver filter: required | **opt**, str, regex `^CHEMBL\d+$`. FK | — | — |
| `record-id` | **opt**, int (Silver) / float coerce (Gold). FK к compound-record | — | — | — |
| `src-id` | **opt**, int (Silver) / float coerce (Gold) | **opt**, int (Silver) / float coerce (Gold) | — | — |
| `src-assay-id` | — | **opt**, str | — | — |
| `cell-chembl-id` | — | **opt**, str. FK к cell-line | — | — |
| `tissue-chembl-id` | — | **opt**, str. FK к tissue | — | — |
| `aidx` | — | **opt**, str. Assay index | — | — |

### 3.2 Classification & Type Fields

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay-type` | **opt**, str. Silver context field. DQ: enum `B,F,A,T,P,U`. Extraction filter: `B,F`. Silver/Gold filter: `[B, F]` | **opt**, str, isin `ASSAY-TYPES` (B,F,A,T,P,U). DQ: enum. Gold filter: `[B, F]` | — | — |
| `assay-type-description` | — | **opt**, str | — | — |
| `assay-test-type` | — | **opt**, str, isin `ASSAY-TEST-TYPES` (In vivo, In vitro, Ex vivo) | — | — |
| `assay-category` | — | **opt**, str, isin `ASSAY-CATEGORIES` (screening, confirmatory, panel, summary, other) | — | — |
| `assay-group` | — | **opt**, str | — | — |
| `target-type` | — | — | **opt**, str, isin `TARGET-TYPES` (14 значений: SINGLE PROTEIN, PROTEIN COMPLEX, PROTEIN FAMILY, ORGANISM, TISSUE, CELL-LINE, SELECTIVITY GROUP, CHIMERIC PROTEIN, MACROMOLECULE, SMALL MOLECULE, LIPID, METAL, UNKNOWN, PROTEIN COMPLEX GROUP). DQ: enum (8 значений). Gold filter: `[SINGLE PROTEIN]` | — |
| `molecule-type` | — | — | — | **opt**, str, isin `MOLECULE-TYPES` (12 значений: Small molecule, Antibody, Protein, Oligonucleotide, etc.). Gold filter: `[Small molecule]` |
| `structure-type` | — | — | — | **opt**, str, isin `STRUCTURE-TYPES` (MOL, SEQ, BOTH, NONE). Gold filter: `[MOL]` |
| `max-phase` | — | — | — | **opt**, float, isin `(-1, 0, 0.5, 1, 2, 3, 4)` |

### 3.3 Standardized Activity Values (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `standard-type` | **opt**, str, isin `ACTIVITY-STANDARD-TYPES` (IC50, EC50, Ki, Kd, AC50, GI50, Potency, Inhibition, % Inhibition, Activity, Ratio, ED50, ID50). DQ: enum (9 значений). Extraction: `IC50,Ki`. Silver/Gold filter: `[IC50, Ki]`. Gold: required | — | — | — |
| `standard-value` | **opt**, float, `ge=0`. DQ: range min=0. Extraction: present (standardized). Silver filter: range `0 < x`. Gold filter: `>0`, required | — | — | — |
| `standard-units` | **opt**, str. DQ: enum (nM, uM, mM, pM, M, %). DQ cross-field: required when `standard-value` present. Extraction: `nM`. Silver/Gold filter: `[nM]`. Gold: required | — | — | — |
| `standard-relation` | **opt**, str, isin `STANDARD-RELATIONS` (=, <, <=, >, >=). Extraction: `=`. Silver/Gold filter: `[=]` | — | — | — |
| `standard-flag` | **opt**, int, isin `[0, 1]`. Gold: float coerce. Extraction: `1` | — | — | — |
| `standard-text-value` | **opt**, str | — | — | — |
| `standard-upper-value` | **opt**, float. Gold: float coerce | — | — | — |
| `pchembl-value` | **opt**, float, `ge=0, le=14` (Silver schema). DQ: range 0..15. Extraction: not null. Silver filter: range 3..10. Silver filter: required | — | — | — |

### 3.4 Raw Activity Values (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `type` | **opt**, str. Оригинальный тип измерения | — | — | — |
| `value` | **opt**, float. Gold: float coerce | — | — | — |
| `units` | **opt**, str | — | — | — |
| `relation` | **opt**, str | — | — | — |
| `text-value` | **opt**, str | — | — | — |
| `upper-value` | **opt**, float. Gold: float coerce | — | — | — |

### 3.5 Ligand Efficiency Metrics (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `ligand-efficiency-bei` | **opt**, float. Transformer: `safe-float` из nested dict `ligand-efficiency.bei`. Gold: float coerce | — | — | — |
| `ligand-efficiency-le` | **opt**, float. Transformer: `safe-float` из `ligand-efficiency.le` | — | — | — |
| `ligand-efficiency-lle` | **opt**, float. Transformer: `safe-float` из `ligand-efficiency.lle` | — | — | — |
| `ligand-efficiency-sei` | **opt**, float. Transformer: `safe-float` из `ligand-efficiency.sei` | — | — | — |

### 3.6 Action Type (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `action-type-action-type` | **opt**, str. Из nested `action-type.action-type` | — | — | — |
| `action-type-description` | **opt**, str. Из nested `action-type.description` | — | — | — |
| `action-type-parent-type` | **opt**, str. Из nested `action-type.parent-type` | — | — | — |

### 3.7 Quality & Data Validity (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `data-validity-comment` | **opt**, str, isin `DATA-VALIDITY-COMMENTS` (7 значений). Extraction: `isnull=true`. Silver filter: exclude-if-present | — | — | — |
| `data-validity-description` | **opt**, str | — | — | — |
| `activity-comment` | **opt**, str | — | — | — |
| `potential-duplicate` | **opt**, int, isin `[0, 1]`. Extraction: `0`. Silver/Gold filter: `[0]`. Gold: float coerce | — | — | — |
| `toid` | **opt**, float (nullable int) | — | — | — |
| `manual-curation-flag` | **opt**, float, isin `[0.0, 1.0]` | — | — | — |
| `original-activity-id` | **opt**, float (nullable int) | — | — | — |

### 3.8 Ontology Annotations

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `bao-endpoint` | **opt**, str, regex `^BAO[-:]\d+$` | — | — | — |
| `bao-format` | **opt**, str, regex `^BAO[-:]\d+$` (в Activity — просто str) | **opt**, str, regex `^BAO[-:]\d+$` | — | — |
| `bao-label` | **opt**, str | **opt**, str | — | — |
| `uo-units` | **opt**, str, regex `^UO[-:]\d+$` | — | — | — |
| `qudt-units` | **opt**, str | — | — | — |

### 3.9 Biological Context (Assay-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay-organism` | — | **opt**, str | — | — |
| `assay-taxonomy-id` | — | **opt**, float (nullable int). Transformer: `validate-taxonomy-id` из `assay-tax-id`. Gold: float coerce | — | — |
| `assay-cell-type` | — | **opt**, str | — | — |
| `assay-tissue` | — | **opt**, str | — | — |
| `assay-strain` | — | **opt**, str | — | — |
| `assay-subcellular-fraction` | — | **opt**, str | — | — |

### 3.10 Assay Relationship & Confidence

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `confidence-score` | — | **opt**, int, `ge=0, le=9`. Gold: float coerce. Gold filter: `[8, 9]` | — | — |
| `confidence-description` | — | **opt**, str | — | — |
| `relationship-type` | — | **opt**, str, isin `RELATIONSHIP-TYPES` (D, H, M, N, S, U). Gold filter: `[D]` | — | — |
| `relationship-description` | — | **opt**, str | — | — |
| `description` | — | **opt**, str. Gold filter: required | — | — |
| `assay-pref-name` | — | **opt**, str | — | — |
| `score` | — | **opt**, float. Transformer: `safe-float` | — | — |

### 3.11 Variant Information (Assay-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay-variant-accession` | **opt**, str (context field из Assay) | — | — | — |
| `assay-variant-mutation` | **opt**, str (context field из Assay) | — | — | — |
| `variant-accession` | — | **opt**, str. Transformer: `safe-str` из nested `variant-sequence.accession` | — | — |
| `variant-isoform` | — | **opt**, str. Transformer: `safe-str` | — | — |
| `variant-mutation` | — | **opt**, str. Transformer: `safe-str` | — | — |
| `variant-organism` | — | **opt**, str. Transformer: `safe-str` | — | — |
| `variant-sequence` | — | **opt**, str. Transformer: `safe-str` | — | — |
| `variant-taxonomy-id` | — | **opt**, float. Transformer: `validate-taxonomy-id` (rename `tax-id` → `taxonomy-id`). Gold: float coerce | — | — |
| `variant-sequence-json` | — | **opt**, str (JSON serialized nested object) | — | — |

### 3.12 Assay Complex Fields (JSON)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay-classifications` | — | **opt**, str (JSON). Serialized list of classifications | — | — |
| `assay-parameters` | — | **opt**, str (JSON). Serialized list of parameters | — | — |
| `activity-properties` | **opt**, str (JSON). Serialized list | — | — | — |

### 3.13 Target Core Fields

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `pref-name` | — | — | **opt**, str. Gold filter: required | **opt**, str |
| `target-pref-name` | **opt**, str (context из Target) | — | — | — |
| `target-organism` | **opt**, str (context из Target) | — | — | — |
| `target-taxonomy-id` | **opt**, str. Transformer: `validate-taxonomy-id-str` из `target-tax-id` | — | — | — |
| `organism` | — | — | **opt**, str. Gold filter: required | — |
| `taxonomy-id` | — | — | **opt**, float (nullable int). Transformer: `TaxonomyId.from-raw()` Value Object | — |
| `species-group-flag` | — | — | **opt**, bool | — |
| `downgraded` | — | — | **opt**, bool. Transformer: `safe-int` → `bool()`, default `False` | — |

### 3.14 Target Components (Target-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `target-components` | — | — | **opt**, str (JSON). Serialized list of components | — |
| `cross-references` | — | — | **opt**, str (JSON). Aggregated из `target-component-xrefs` | **opt**, str (JSON) |
| `pipeline-stages` | — | — | **opt**, str (JSON) | — |
| `target-component-synonyms` | — | — | **opt**, str (JSON). Aggregated synonyms из всех components | — |
| `component-accessions` | — | — | **opt**, object (list[str]). Gold filter: list-length min=1, max=1 (single protein) | — |
| `component-id` | — | — | **opt**, float, coerce. Primary component (first from list) | — |
| `component-ids` | — | — | **opt**, object (list[int]). Gold filter: list-length min=1 | — |
| `component-types` | — | — | **opt**, object (list[str]). Gold filter: list-contains `[PROTEIN]`, mode=all | — |
| `component-relationships` | — | — | **opt**, object (list[str]) | — |
| `component-descriptions` | — | — | **opt**, object (list[str]). Только в Transformer, нет в Silver/Gold schema | — |

### 3.15 Molecule Core Properties

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `first-approval` | — | — | — | **opt**, float (nullable int). Transformer: `int-fields` |
| `chirality` | — | — | — | **opt**, int, isin `[-1, 0, 1, 2]`. Gold: float coerce |
| `dosed-ingredient` | — | — | — | **opt**, int, isin `[0, 1]`. Gold: float coerce |
| `availability-type` | — | — | — | **opt**, float, isin `[-2, -1, 0, 1, 2]` |

### 3.16 Molecule Flags

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `therapeutic-flag` | — | — | — | **opt**, bool |
| `oral` | — | — | — | **opt**, bool |
| `parenteral` | — | — | — | **opt**, bool |
| `topical` | — | — | — | **opt**, bool |
| `black-box-warning` | — | — | — | **opt**, int, isin `[0, 1]`. Gold: float coerce |
| `natural-product` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold: float coerce |
| `first-in-class` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold: float coerce |
| `prodrug` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold: float coerce |
| `inorganic-flag` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold filter: `[0]`. Gold: float coerce |
| `polymer-flag` | — | — | — | **opt**, int, isin `[0, 1]`. Gold: float coerce |
| `withdrawn-flag` | — | — | — | **opt**, bool |

### 3.17 Molecule Physicochemical Properties (flattened from `molecule-properties`)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `property-alogp` | — | — | — | **opt**, float. Transformer: `safe-float`. DQ: range -15..20 |
| `property-mw-freebase` | — | — | — | **opt**, float. Transformer: `safe-float` |
| `property-full-mwt` | — | — | — | **opt**, float. Transformer: `safe-float`. DQ: range min=0 |
| `property-hba` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe-int`. Gold: float coerce |
| `property-hbd` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe-int`. Gold: float coerce |
| `property-psa` | — | — | — | **opt**, float, `ge=0`. Transformer: `safe-float` |
| `property-rtb` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe-int`. Gold: float coerce |
| `property-ro5-violations` | — | — | — | **opt**, int, `ge=0, le=4`. Transformer: `safe-int` (rename `num-ro5-violations`). Gold: float coerce |
| `property-heavy-atoms` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe-int`. Gold: float coerce |
| `property-aromatic-rings` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe-int`. Gold: float coerce |
| `property-qed-weighted` | — | — | — | **opt**, float, `ge=0, le=1`. Transformer: `safe-float` |
| `property-full-molformula` | — | — | — | **opt**, str |
| `property-ro3-pass` | — | — | — | **opt**, str, isin `[Y, N]` |

### 3.18 Molecule Structure Fields (flattened from `molecule-structures`)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `canonical-smiles` | **opt**, str (context из Molecule) | — | — | **opt**, str. Transformer: `SMILES.from-raw(is-canonical=True)` Value Object валидация |
| `standard-inchi` | — | — | — | **opt**, str |
| `inchikey` | — | — | — | **opt**, str, regex `^[A-Z]{14}-[A-Z]{10}-[A-Z]$`. Transformer: `InChIKey` Value Object валидация |
| `structure-standard-inchi-key` | — | — | — | **opt**, str, regex `^[A-Z]{14}-[A-Z]{10}-[A-Z]$` (дубль — top-level alias) |

### 3.19 Molecule Hierarchy (flattened from `molecule-hierarchy`)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `hierarchy-parent-chembl-id` | — | — | — | **opt**, str, regex `^CHEMBL\d+$` |
| `hierarchy-active-chembl-id` | — | — | — | **opt**, str, regex `^CHEMBL\d+$` |
| `hierarchy-child-chembl-id` | — | — | — | **opt**, str, regex `^CHEMBL\d+$`. Rename из `molecule-chembl-id` в hierarchy |

### 3.20 Molecule USAN & Other Metadata

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `usan-stem` | — | — | — | **opt**, str |
| `usan-substem` | — | — | — | **opt**, str |
| `usan-stem-definition` | — | — | — | **opt**, str |
| `usan-year` | — | — | — | **opt**, float (nullable int), range 1950..2050 |
| `helm-notation` | — | — | — | **opt**, str |
| `molecule-species` | — | — | — | **opt**, str |

### 3.21 Molecule JSON Complex Fields

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `molecule-hierarchy` | — | — | — | **opt**, str (JSON) |
| `molecule-properties` | — | — | — | **opt**, str (JSON) |
| `molecule-structures` | — | — | — | **opt**, str (JSON) |
| `molecule-synonyms` | — | — | — | **opt**, str (JSON) |
| `atc-classifications` | — | — | — | **opt**, str (JSON) |

### 3.22 Document/Publication Context (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `molecule-pref-name` | **opt**, str (context из Molecule) | — | — | — |
| `parent-molecule-chembl-id` | **opt**, str (context из Molecule) | — | — | — |
| `assay-description` | **opt**, str (context из Assay) | — | — | — |
| `document-journal` | **opt**, str | — | — | — |
| `document-year` | **opt**, int, range 1950..2050. Silver filter: range 1950..2050. Gold: float coerce | — | — | — |

---

## 4. Cross-Field и Conditional валидации

### 4.1 Activity

| Правило | Описание |
|---------|----------|
| `value-requires-units` | Если `standard-value` не null → `standard-units` обязателен |
| `binding-requires-target` | Если `assay-type = B` → `target-chembl-id` обязателен |

### 4.2 Assay, Target, Molecule

Нет entity-specific cross-field или conditional валидаций. Используются только common DQ rules и Silver/Gold schema constraints.

---

## 5. Extraction-Level фильтрация (только Activity)

Только пайплайн Activity имеет серверные фильтры API (`extraction-params`):

| Параметр | Значение | Эффект |
|----------|----------|--------|
| `standard-type--in` | `IC50,Ki` | Только IC50 и Ki |
| `standard-units` | `nM` | Только наномоляр |
| `standard-relation` | `=` | Только точные значения |
| `assay-type--in` | `B,F` | Binding и Functional |
| `potential-duplicate` | `0` | Исключить дубликаты |
| `data-validity-comment--isnull` | `true` | Без замечаний к данным |
| `pchembl-value--isnull` | `false` | Только с pChEMBL |
| `standard-flag` | `1` | Только стандартизованные |

---

## 6. Gold Filter Summary

| Критерий | Activity | Assay | Target | Molecule |
|----------|----------|-------|--------|----------|
| **columns** | `standard-type: [IC50, Ki]`, `standard-units: [nM]`, `standard-relation: [=]`, `assay-type: [B, F]`, `potential-duplicate: [0]` | `assay-type: [B, F]`, `confidence-score: [8, 9]`, `relationship-type: [D]` | `target-type: [SINGLE PROTEIN]` | `molecule-type: [Small molecule]`, `structure-type: [MOL]`, `inorganic-flag: [0]` |
| **ranges** | `standard-value: >0` | — | — | — |
| **list-lengths** | — | — | `component-accessions: 1..1`, `component-ids: min=1` | — |
| **list-contains** | — | — | `component-types: all=[PROTEIN]` | — |
| **required-fields** | `standard-type`, `standard-value`, `standard-units`, `target-chembl-id` | `assay-type`, `description` | `pref-name`, `organism` | `molecule-chembl-id` |

---

## 7. Transformer Value Object валидации

| Value Object | Пайплайн | Поле | Валидация |
|-------------|----------|------|-----------|
| `TaxonomyId.from-raw()` | Target | `taxonomy-id` | Конвертация str/int → int, валидация range |
| `validate-taxonomy-id` | Assay | `assay-taxonomy-id`, `variant-taxonomy-id` | Safe conversion + validation |
| `validate-taxonomy-id-str` | Activity | `target-taxonomy-id` | Конвертация `target-tax-id` → str representation |
| `InChIKey` | Molecule | `inchikey` | Regex `^[A-Z]{14}-[A-Z]{10}-[A-Z]$`, 27 символов |
| `SMILES.from-raw()` | Molecule | `canonical-smiles` | Regex `[A-Za-z0-9@+\-=#$()\[\]\\/%.*]+`, basic syntax check |
| `safe-float` | All | Multiple float fields | Safe str→float conversion, None on failure |
| `safe-int` | All | Multiple int fields | Safe str→int conversion, None on failure |

---

## 8. Количество валидируемых полей (без системных)

| Пайплайн | Silver Schema | Gold Schema | DQ Entity Rules | Gold Filter Criteria |
|----------|---------------|-------------|-----------------|---------------------|
| Activity | ~50 полей | ~52 поля | 5 field + 1 cross-field + 1 conditional | 5 column + 1 range + 4 required |
| Assay | ~40 полей | ~38 полей | 2 field rules | 3 column + 2 required |
| Target | ~17 полей | ~18 полей | 2 field rules | 1 column + 2 list-length + 1 list-contains + 2 required |
| Molecule | ~52 поля | ~56 полей | 3 field rules | 3 column + 1 required |

---

## Ссылки

- **Silver Schemas**: `src/bioetl/domain/schemas/chembl/{entity}.py`
- **Gold Schemas**: `src/bioetl/domain/contracts/gold/chembl.py`
- **DQ Rules**: `configs/quality/entities/chembl/{entity}.yaml`
- **Filter Rules**: `configs/filters/entities/chembl/{entity}.yaml`
- **Transformers**: `src/bioetl/application/pipelines/chembl/{entity}-transformer.py`
- **Schema Constants**: `src/bioetl/domain/schemas/constants.py`
- **Validation Functions**: `src/bioetl/domain/validation.py`
