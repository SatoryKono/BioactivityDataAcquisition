# Pipeline Validation Matrix: Activity, Assay, Target, Molecule

*Версия: 1.0.0 | Дата: 2026-02-11*

Сводная таблица валидаций данных по четырём основным пайплайнам ChEMBL.

---

## 1. Архитектура валидации (слои)

Валидация происходит на нескольких уровнях:

| Слой | Источник | Описание |
|------|----------|----------|
| **Extraction** | `configs/filters/entities/chembl/{entity}.yaml` → `extraction_params` | Серверные фильтры API (query params). Только у Activity. |
| **Transformer** | `application/pipelines/chembl/{entity}_transformer.py` | Конвертация типов, Value Objects (InChIKey, SMILES, TaxonomyId), safe_float/safe_int |
| **Silver Schema** | `domain/schemas/chembl/{entity}.py` (Pandera) | Структурная валидация: типы, nullable, regex, enum, range. `strict=True` |
| **DQ Rules** | `configs/quality/entities/chembl/{entity}.yaml` | Бизнес-правила: required, range, enum, pattern, cross-field, conditional |
| **Silver Filter** | `configs/filters/entities/chembl/{entity}.yaml` → `silver_filters` | Доменные gates перед записью в Silver (только Activity) |
| **Gold Schema** | `domain/contracts/gold/chembl.py` (Pandera DataFrameModel) | Финальная структурная валидация. `strict=True`, int→float coercion |
| **Gold Filter** | `configs/filters/entities/chembl/{entity}.yaml` → `gold_filters` | Фильтры качества для Gold слоя |

**DQ thresholds** (наследование: `_defaults.yaml` → `providers/chembl.yaml` → `entities/chembl/{entity}.yaml`):
- **soft_fail**: >5% ошибок → Warning
- **hard_fail**: >15% ошибок → Fail Batch (ChEMBL строже дефолтных 20%)

---

## 2. Общие поля (все 4 пайплайна)

Эти поля наследуются от `ETLRecordSchema` (base) и присутствуют во всех пайплайнах.

| Поле | Тип | Nullable | Валидация |
|------|-----|----------|-----------|
| `entity_id` | str | No | Уникальный бизнес-идентификатор. Обязателен. |
| `content_hash` | str | No | SHA256 hex, regex `^[a-f0-9]{64}$`. DQ rule: required. |
| `_run_id` | str | No | Correlation ID пайплайн-рана. |
| `_run_type` | str | No | Enum: `incremental`, `backfill`, `rebuild`. |
| `_source_batch_id` | str | Yes | Batch context ID. |
| `_ingestion_ts` | str | No | ISO 8601 regex. DQ rule: pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`. |
| `_dq_warn` | bool | No | Default `False`. |
| `_dq_error` | bool | No | Default `False`. |
| `_index` | int | No | `ge=0`. Порядковый номер записи. |

**DQ Provider-level** (ChEMBL): паттерн `^CHEMBL\d+$` применяется к полям `molecule_chembl_id`, `target_chembl_id`, `assay_chembl_id`, `document_chembl_id` (nullable=true, применяется только при наличии значения).

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
| `activity_id` | **req**, str. Silver: PK. DQ: required. Filter: range 1..10^10 | — | — | — |
| `assay_chembl_id` | **req**, str, regex `^CHEMBL\d+$`. FK к Assay | **req**, str, regex `^CHEMBL\d+$`. Silver: PK. DQ: required | — | — |
| `molecule_chembl_id` | **req**, str, regex `^CHEMBL\d+$`. FK к Molecule. Transformer: `_get_required_field` | — | — | **req**, str, regex `^CHEMBL\d+$`. Silver: PK. DQ: required |
| `target_chembl_id` | **opt**, str, regex `^CHEMBL\d+$`. FK к Target. Conditional DQ: required if `assay_type=B`. Silver filter: required. Gold filter: required | **opt**, str, regex `^CHEMBL\d+$`. FK к Target | **req**, str, regex `^CHEMBL\d+$`. Silver: PK. DQ: required, enum `target_type` | — |
| `document_chembl_id` | **opt**, str, regex `^CHEMBL\d+$`. FK. Silver filter: required | **opt**, str, regex `^CHEMBL\d+$`. FK | — | — |
| `record_id` | **opt**, int (Silver) / float coerce (Gold). FK к compound_record | — | — | — |
| `src_id` | **opt**, int (Silver) / float coerce (Gold) | **opt**, int (Silver) / float coerce (Gold) | — | — |
| `src_assay_id` | — | **opt**, str | — | — |
| `cell_chembl_id` | — | **opt**, str. FK к cell_line | — | — |
| `tissue_chembl_id` | — | **opt**, str. FK к tissue | — | — |
| `aidx` | — | **opt**, str. Assay index | — | — |

### 3.2 Classification & Type Fields

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay_type` | **opt**, str. Silver context field. DQ: enum `B,F,A,T,P,U`. Extraction filter: `B,F`. Silver/Gold filter: `[B, F]` | **opt**, str, isin `ASSAY_TYPES` (B,F,A,T,P,U). DQ: enum. Gold filter: `[B, F]` | — | — |
| `assay_type_description` | — | **opt**, str | — | — |
| `assay_test_type` | — | **opt**, str, isin `ASSAY_TEST_TYPES` (In vivo, In vitro, Ex vivo) | — | — |
| `assay_category` | — | **opt**, str, isin `ASSAY_CATEGORIES` (screening, confirmatory, panel, summary, other) | — | — |
| `assay_group` | — | **opt**, str | — | — |
| `target_type` | — | — | **opt**, str, isin `TARGET_TYPES` (14 значений: SINGLE PROTEIN, PROTEIN COMPLEX, PROTEIN FAMILY, ORGANISM, TISSUE, CELL-LINE, SELECTIVITY GROUP, CHIMERIC PROTEIN, MACROMOLECULE, SMALL MOLECULE, LIPID, METAL, UNKNOWN, PROTEIN COMPLEX GROUP). DQ: enum (8 значений). Gold filter: `[SINGLE PROTEIN]` | — |
| `molecule_type` | — | — | — | **opt**, str, isin `MOLECULE_TYPES` (12 значений: Small molecule, Antibody, Protein, Oligonucleotide, etc.). Gold filter: `[Small molecule]` |
| `structure_type` | — | — | — | **opt**, str, isin `STRUCTURE_TYPES` (MOL, SEQ, BOTH, NONE). Gold filter: `[MOL]` |
| `max_phase` | — | — | — | **opt**, float, isin `(-1, 0, 0.5, 1, 2, 3, 4)` |

### 3.3 Standardized Activity Values (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `standard_type` | **opt**, str, isin `ACTIVITY_STANDARD_TYPES` (IC50, EC50, Ki, Kd, AC50, GI50, Potency, Inhibition, % Inhibition, Activity, Ratio, ED50, ID50). DQ: enum (9 значений). Extraction: `IC50,Ki`. Silver/Gold filter: `[IC50, Ki]`. Gold: required | — | — | — |
| `standard_value` | **opt**, float, `ge=0`. DQ: range min=0. Extraction: present (standardized). Silver filter: range `0 < x`. Gold filter: `>0`, required | — | — | — |
| `standard_units` | **opt**, str. DQ: enum (nM, uM, mM, pM, M, %). DQ cross-field: required when `standard_value` present. Extraction: `nM`. Silver/Gold filter: `[nM]`. Gold: required | — | — | — |
| `standard_relation` | **opt**, str, isin `STANDARD_RELATIONS` (=, <, <=, >, >=). Extraction: `=`. Silver/Gold filter: `[=]` | — | — | — |
| `standard_flag` | **opt**, int, isin `[0, 1]`. Gold: float coerce. Extraction: `1` | — | — | — |
| `standard_text_value` | **opt**, str | — | — | — |
| `standard_upper_value` | **opt**, float. Gold: float coerce | — | — | — |
| `pchembl_value` | **opt**, float, `ge=0, le=14` (Silver schema). DQ: range 0..15. Extraction: not null. Silver filter: range 3..10. Silver filter: required | — | — | — |

### 3.4 Raw Activity Values (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `type` | **opt**, str. Оригинальный тип измерения | — | — | — |
| `value` | **opt**, float. Gold: float coerce | — | — | — |
| `units` | **opt**, str | — | — | — |
| `relation` | **opt**, str | — | — | — |
| `text_value` | **opt**, str | — | — | — |
| `upper_value` | **opt**, float. Gold: float coerce | — | — | — |

### 3.5 Ligand Efficiency Metrics (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `ligand_efficiency_bei` | **opt**, float. Transformer: `safe_float` из nested dict `ligand_efficiency.bei`. Gold: float coerce | — | — | — |
| `ligand_efficiency_le` | **opt**, float. Transformer: `safe_float` из `ligand_efficiency.le` | — | — | — |
| `ligand_efficiency_lle` | **opt**, float. Transformer: `safe_float` из `ligand_efficiency.lle` | — | — | — |
| `ligand_efficiency_sei` | **opt**, float. Transformer: `safe_float` из `ligand_efficiency.sei` | — | — | — |

### 3.6 Action Type (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `action_type_action_type` | **opt**, str. Из nested `action_type.action_type` | — | — | — |
| `action_type_description` | **opt**, str. Из nested `action_type.description` | — | — | — |
| `action_type_parent_type` | **opt**, str. Из nested `action_type.parent_type` | — | — | — |

### 3.7 Quality & Data Validity (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `data_validity_comment` | **opt**, str, isin `DATA_VALIDITY_COMMENTS` (7 значений). Extraction: `isnull=true`. Silver filter: exclude_if_present | — | — | — |
| `data_validity_description` | **opt**, str | — | — | — |
| `activity_comment` | **opt**, str | — | — | — |
| `potential_duplicate` | **opt**, int, isin `[0, 1]`. Extraction: `0`. Silver/Gold filter: `[0]`. Gold: float coerce | — | — | — |
| `toid` | **opt**, float (nullable int) | — | — | — |
| `manual_curation_flag` | **opt**, float, isin `[0.0, 1.0]` | — | — | — |
| `original_activity_id` | **opt**, float (nullable int) | — | — | — |

### 3.8 Ontology Annotations

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `bao_endpoint` | **opt**, str, regex `^BAO[_:]\d+$` | — | — | — |
| `bao_format` | **opt**, str, regex `^BAO[_:]\d+$` (в Activity — просто str) | **opt**, str, regex `^BAO[_:]\d+$` | — | — |
| `bao_label` | **opt**, str | **opt**, str | — | — |
| `uo_units` | **opt**, str, regex `^UO[_:]\d+$` | — | — | — |
| `qudt_units` | **opt**, str | — | — | — |

### 3.9 Biological Context (Assay-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay_organism` | — | **opt**, str | — | — |
| `assay_taxonomy_id` | — | **opt**, float (nullable int). Transformer: `validate_taxonomy_id` из `assay_tax_id`. Gold: float coerce | — | — |
| `assay_cell_type` | — | **opt**, str | — | — |
| `assay_tissue` | — | **opt**, str | — | — |
| `assay_strain` | — | **opt**, str | — | — |
| `assay_subcellular_fraction` | — | **opt**, str | — | — |

### 3.10 Assay Relationship & Confidence

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `confidence_score` | — | **opt**, int, `ge=0, le=9`. Gold: float coerce. Gold filter: `[8, 9]` | — | — |
| `confidence_description` | — | **opt**, str | — | — |
| `relationship_type` | — | **opt**, str, isin `RELATIONSHIP_TYPES` (D, H, M, N, S, U). Gold filter: `[D]` | — | — |
| `relationship_description` | — | **opt**, str | — | — |
| `description` | — | **opt**, str. Gold filter: required | — | — |
| `assay_pref_name` | — | **opt**, str | — | — |
| `score` | — | **opt**, float. Transformer: `safe_float` | — | — |

### 3.11 Variant Information (Assay-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay_variant_accession` | **opt**, str (context field из Assay) | — | — | — |
| `assay_variant_mutation` | **opt**, str (context field из Assay) | — | — | — |
| `variant_accession` | — | **opt**, str. Transformer: `safe_str` из nested `variant_sequence.accession` | — | — |
| `variant_isoform` | — | **opt**, str. Transformer: `safe_str` | — | — |
| `variant_mutation` | — | **opt**, str. Transformer: `safe_str` | — | — |
| `variant_organism` | — | **opt**, str. Transformer: `safe_str` | — | — |
| `variant_sequence` | — | **opt**, str. Transformer: `safe_str` | — | — |
| `variant_taxonomy_id` | — | **opt**, float. Transformer: `validate_taxonomy_id` (rename `tax_id` → `taxonomy_id`). Gold: float coerce | — | — |
| `variant_sequence_json` | — | **opt**, str (JSON serialized nested object) | — | — |

### 3.12 Assay Complex Fields (JSON)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `assay_classifications` | — | **opt**, str (JSON). Serialized list of classifications | — | — |
| `assay_parameters` | — | **opt**, str (JSON). Serialized list of parameters | — | — |
| `activity_properties` | **opt**, str (JSON). Serialized list | — | — | — |

### 3.13 Target Core Fields

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `pref_name` | — | — | **opt**, str. Gold filter: required | **opt**, str |
| `target_pref_name` | **opt**, str (context из Target) | — | — | — |
| `target_organism` | **opt**, str (context из Target) | — | — | — |
| `target_taxonomy_id` | **opt**, str. Transformer: `validate_taxonomy_id_str` из `target_tax_id` | — | — | — |
| `organism` | — | — | **opt**, str. Gold filter: required | — |
| `taxonomy_id` | — | — | **opt**, float (nullable int). Transformer: `TaxonomyId.from_raw()` Value Object | — |
| `species_group_flag` | — | — | **opt**, bool | — |
| `downgraded` | — | — | **opt**, bool. Transformer: `safe_int` → `bool()`, default `False` | — |

### 3.14 Target Components (Target-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `target_components` | — | — | **opt**, str (JSON). Serialized list of components | — |
| `cross_references` | — | — | **opt**, str (JSON). Aggregated из `target_component_xrefs` | **opt**, str (JSON) |
| `pipeline_stages` | — | — | **opt**, str (JSON) | — |
| `target_component_synonyms` | — | — | **opt**, str (JSON). Aggregated synonyms из всех components | — |
| `component_accessions` | — | — | **opt**, object (list[str]). Gold filter: list_length min=1, max=1 (single protein) | — |
| `component_id` | — | — | **opt**, float, coerce. Primary component (first from list) | — |
| `component_ids` | — | — | **opt**, object (list[int]). Gold filter: list_length min=1 | — |
| `component_types` | — | — | **opt**, object (list[str]). Gold filter: list_contains `[PROTEIN]`, mode=all | — |
| `component_relationships` | — | — | **opt**, object (list[str]) | — |
| `component_descriptions` | — | — | **opt**, object (list[str]). Только в Transformer, нет в Silver/Gold schema | — |

### 3.15 Molecule Core Properties

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `first_approval` | — | — | — | **opt**, float (nullable int). Transformer: `int_fields` |
| `chirality` | — | — | — | **opt**, int, isin `[-1, 0, 1, 2]`. Gold: float coerce |
| `dosed_ingredient` | — | — | — | **opt**, int, isin `[0, 1]`. Gold: float coerce |
| `availability_type` | — | — | — | **opt**, float, isin `[-2, -1, 0, 1, 2]` |

### 3.16 Molecule Flags

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `therapeutic_flag` | — | — | — | **opt**, bool |
| `oral` | — | — | — | **opt**, bool |
| `parenteral` | — | — | — | **opt**, bool |
| `topical` | — | — | — | **opt**, bool |
| `black_box_warning` | — | — | — | **opt**, int, isin `[0, 1]`. Gold: float coerce |
| `natural_product` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold: float coerce |
| `first_in_class` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold: float coerce |
| `prodrug` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold: float coerce |
| `inorganic_flag` | — | — | — | **opt**, int, isin `[-1, 0, 1]`. Gold filter: `[0]`. Gold: float coerce |
| `polymer_flag` | — | — | — | **opt**, int, isin `[0, 1]`. Gold: float coerce |
| `withdrawn_flag` | — | — | — | **opt**, bool |

### 3.17 Molecule Physicochemical Properties (flattened from `molecule_properties`)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `property_alogp` | — | — | — | **opt**, float. Transformer: `safe_float`. DQ: range -15..20 |
| `property_mw_freebase` | — | — | — | **opt**, float. Transformer: `safe_float` |
| `property_full_mwt` | — | — | — | **opt**, float. Transformer: `safe_float`. DQ: range min=0 |
| `property_hba` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe_int`. Gold: float coerce |
| `property_hbd` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe_int`. Gold: float coerce |
| `property_psa` | — | — | — | **opt**, float, `ge=0`. Transformer: `safe_float` |
| `property_rtb` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe_int`. Gold: float coerce |
| `property_ro5_violations` | — | — | — | **opt**, int, `ge=0, le=4`. Transformer: `safe_int` (rename `num_ro5_violations`). Gold: float coerce |
| `property_heavy_atoms` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe_int`. Gold: float coerce |
| `property_aromatic_rings` | — | — | — | **opt**, int, `ge=0`. Transformer: `safe_int`. Gold: float coerce |
| `property_qed_weighted` | — | — | — | **opt**, float, `ge=0, le=1`. Transformer: `safe_float` |
| `property_full_molformula` | — | — | — | **opt**, str |
| `property_ro3_pass` | — | — | — | **opt**, str, isin `[Y, N]` |

### 3.18 Molecule Structure Fields (flattened from `molecule_structures`)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `canonical_smiles` | **opt**, str (context из Molecule) | — | — | **opt**, str. Transformer: `SMILES.from_raw(is_canonical=True)` Value Object валидация |
| `standard_inchi` | — | — | — | **opt**, str |
| `inchikey` | — | — | — | **opt**, str, regex `^[A-Z]{14}-[A-Z]{10}-[A-Z]$`. Transformer: `InChIKey` Value Object валидация |
| `structure_standard_inchi_key` | — | — | — | **opt**, str, regex `^[A-Z]{14}-[A-Z]{10}-[A-Z]$` (дубль — top-level alias) |

### 3.19 Molecule Hierarchy (flattened from `molecule_hierarchy`)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `hierarchy_parent_chembl_id` | — | — | — | **opt**, str, regex `^CHEMBL\d+$` |
| `hierarchy_active_chembl_id` | — | — | — | **opt**, str, regex `^CHEMBL\d+$` |
| `hierarchy_child_chembl_id` | — | — | — | **opt**, str, regex `^CHEMBL\d+$`. Rename из `molecule_chembl_id` в hierarchy |

### 3.20 Molecule USAN & Other Metadata

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `usan_stem` | — | — | — | **opt**, str |
| `usan_substem` | — | — | — | **opt**, str |
| `usan_stem_definition` | — | — | — | **opt**, str |
| `usan_year` | — | — | — | **opt**, float (nullable int), range 1950..2050 |
| `helm_notation` | — | — | — | **opt**, str |
| `molecule_species` | — | — | — | **opt**, str |

### 3.21 Molecule JSON Complex Fields

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `molecule_hierarchy` | — | — | — | **opt**, str (JSON) |
| `molecule_properties` | — | — | — | **opt**, str (JSON) |
| `molecule_structures` | — | — | — | **opt**, str (JSON) |
| `molecule_synonyms` | — | — | — | **opt**, str (JSON) |
| `atc_classifications` | — | — | — | **opt**, str (JSON) |

### 3.22 Document/Publication Context (Activity-specific)

| Поле | Activity | Assay | Target | Molecule |
|------|----------|-------|--------|----------|
| `molecule_pref_name` | **opt**, str (context из Molecule) | — | — | — |
| `parent_molecule_chembl_id` | **opt**, str (context из Molecule) | — | — | — |
| `assay_description` | **opt**, str (context из Assay) | — | — | — |
| `document_journal` | **opt**, str | — | — | — |
| `document_year` | **opt**, int, range 1950..2050. Silver filter: range 1950..2050. Gold: float coerce | — | — | — |

---

## 4. Cross-Field и Conditional валидации

### 4.1 Activity

| Правило | Описание |
|---------|----------|
| `value_requires_units` | Если `standard_value` не null → `standard_units` обязателен |
| `binding_requires_target` | Если `assay_type = B` → `target_chembl_id` обязателен |

### 4.2 Assay, Target, Molecule

Нет entity-specific cross-field или conditional валидаций. Используются только common DQ rules и Silver/Gold schema constraints.

---

## 5. Extraction-Level фильтрация (только Activity)

Только пайплайн Activity имеет серверные фильтры API (`extraction_params`):

| Параметр | Значение | Эффект |
|----------|----------|--------|
| `standard_type__in` | `IC50,Ki` | Только IC50 и Ki |
| `standard_units` | `nM` | Только наномоляр |
| `standard_relation` | `=` | Только точные значения |
| `assay_type__in` | `B,F` | Binding и Functional |
| `potential_duplicate` | `0` | Исключить дубликаты |
| `data_validity_comment__isnull` | `true` | Без замечаний к данным |
| `pchembl_value__isnull` | `false` | Только с pChEMBL |
| `standard_flag` | `1` | Только стандартизованные |

---

## 6. Gold Filter Summary

| Критерий | Activity | Assay | Target | Molecule |
|----------|----------|-------|--------|----------|
| **columns** | `standard_type: [IC50, Ki]`, `standard_units: [nM]`, `standard_relation: [=]`, `assay_type: [B, F]`, `potential_duplicate: [0]` | `assay_type: [B, F]`, `confidence_score: [8, 9]`, `relationship_type: [D]` | `target_type: [SINGLE PROTEIN]` | `molecule_type: [Small molecule]`, `structure_type: [MOL]`, `inorganic_flag: [0]` |
| **ranges** | `standard_value: >0` | — | — | — |
| **list_lengths** | — | — | `component_accessions: 1..1`, `component_ids: min=1` | — |
| **list_contains** | — | — | `component_types: all=[PROTEIN]` | — |
| **required_fields** | `standard_type`, `standard_value`, `standard_units`, `target_chembl_id` | `assay_type`, `description` | `pref_name`, `organism` | `molecule_chembl_id` |

---

## 7. Transformer Value Object валидации

| Value Object | Пайплайн | Поле | Валидация |
|-------------|----------|------|-----------|
| `TaxonomyId.from_raw()` | Target | `taxonomy_id` | Конвертация str/int → int, валидация range |
| `validate_taxonomy_id` | Assay | `assay_taxonomy_id`, `variant_taxonomy_id` | Safe conversion + validation |
| `validate_taxonomy_id_str` | Activity | `target_taxonomy_id` | Конвертация `target_tax_id` → str representation |
| `InChIKey` | Molecule | `inchikey` | Regex `^[A-Z]{14}-[A-Z]{10}-[A-Z]$`, 27 символов |
| `SMILES.from_raw()` | Molecule | `canonical_smiles` | Regex `[A-Za-z0-9@+\-=#$()\[\]\\/%.*]+`, basic syntax check |
| `safe_float` | All | Multiple float fields | Safe str→float conversion, None on failure |
| `safe_int` | All | Multiple int fields | Safe str→int conversion, None on failure |

---

## 8. Количество валидируемых полей (без системных)

| Пайплайн | Silver Schema | Gold Schema | DQ Entity Rules | Gold Filter Criteria |
|----------|---------------|-------------|-----------------|---------------------|
| Activity | ~50 полей | ~52 поля | 5 field + 1 cross-field + 1 conditional | 5 column + 1 range + 4 required |
| Assay | ~40 полей | ~38 полей | 2 field rules | 3 column + 2 required |
| Target | ~17 полей | ~18 полей | 2 field rules | 1 column + 2 list_length + 1 list_contains + 2 required |
| Molecule | ~52 поля | ~56 полей | 3 field rules | 3 column + 1 required |

---

## Ссылки

- **Silver Schemas**: `src/bioetl/domain/schemas/chembl/{entity}.py`
- **Gold Schemas**: `src/bioetl/domain/contracts/gold/chembl.py`
- **DQ Rules**: `configs/quality/entities/chembl/{entity}.yaml`
- **Filter Rules**: `configs/filters/entities/chembl/{entity}.yaml`
- **Transformers**: `src/bioetl/application/pipelines/chembl/{entity}_transformer.py`
- **Schema Constants**: `src/bioetl/domain/schemas/constants.py`
- **Validation Functions**: `src/bioetl/domain/validation.py`
