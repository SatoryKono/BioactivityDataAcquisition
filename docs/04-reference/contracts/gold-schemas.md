______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-21'

______________________________________________________________________

# Gold Layer Data Contracts

Контракты данных для Gold-слоя BioETL.

> Source of truth для Gold-контрактов находится в
> `src/bioetl/domain/contracts/gold/`.
> JSON-файлы в `docs/04-reference/contracts/gold/*.json` публикуются из этих
> кодовых контрактов скриптом `scripts/schema/generation/generate_contracts.py`.
> Ниже применяется snake_case нотация полей, синхронизированная с автогенерацией контрактов.

> **Версия**: 1.1.0
> **Последнее обновление**: 2026-07-07
> **Связанные ADR**: [ADR-018](../../02-architecture/decisions/ADR-018-gold-strict-validation.md), [ADR-014](../../02-architecture/decisions/ADR-014-deterministic-writes.md), [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)

______________________________________________________________________

## Содержание

1. [Обзор](#обзор)
1. [Архитектура Gold-слоя](#архитектура-gold-слоя)
1. [Фильтрация Silver → Gold](#фильтрация-silver-gold)
1. [Контракты по провайдерам](#контракты-по-провайдерам)
   - [ChEMBL](#chembl)
   - [PubChem](#pubchem)
   - [UniProt](#uniprot)
   - [PubMed](#pubmed)
   - [CrossRef](#crossref)
   - [OpenAlex](#openalex)
   - [Semantic Scholar](#semantic-scholar)
   - [Composite](#composite)
1. [Системные поля](#системные-поля)
1. [Режимы записи](#режимы-записи)
1. [Примеры запросов](#примеры-запросов)
1. [Валидация](#валидация)

______________________________________________________________________

## Обзор

Gold-слой содержит **бизнес-готовые данные** с:

- Строгой валидацией через Pandera (`strict=True`)
- Фильтрацией по бизнес-правилам (качество, релевантность)
- Детерминистичной записью (сортировка по primary key)
- ACID-транзакциями через Delta Lake

### Принципы Gold-слоя

| Принцип               | Описание                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Strict Validation** | Все поля валидируются перед записью (REQ-DATA-009)                                                                   |
| **Business Filters**  | Только качественные данные проходят в Gold                                                                           |
| **Idempotency**       | Повторный запуск даёт идентичный результат                                                                           |
| **Traceability**      | Каждая запись содержит `entity_id`, `content_hash`; occurrence-scoped provenance публикуется в sidecar/control-plane |

Текущее уточнение по traceability:

- strict Gold validation обеспечивается Pandera-based Gold validator-ами с `strict=True` по умолчанию;
- Gold sidecars сохраняют `dq_report_path` и schema metadata (`contract_path`, `version`, `validation`);
- единый contract-driven DQ provenance c глобальными `contract_version` и `rule_id` для всех DQ artefacts пока не является завершённым runtime contract и не должен предполагаться downstream tooling.

Отдельно фиксируем policy boundary для `#4768`:

- `strict_dq_validation` в entity contract YAML под `configs/contracts/{provider}/{entity}.yaml` остаётся DQ-only флагом и не управляет Gold runtime strictness;
- canonical Gold strictness для composite outputs обеспечивается registered Pandera Gold schema и merged Gold write path;
- любые composite-специфические исключения по этой границе должны быть явно заведены в `configs/quality/composite_gold_strictness_waivers.yaml` с owner, rationale, linked issue, approved_on и expires_on.

### Snapshot governance

Published JSON contracts в `docs/04-reference/contracts/gold/*.json` остаются
review/export surface, но canonical test baselines для drift detection теперь
живут отдельно:

- full Gold schema snapshot registry:
  `tests/fixtures/golden/gold/schema_registry.v1.json`
- helper/update surface:
  `tests/contract/_gold_schema_snapshot_registry.py`
- contract drift suite:
  `tests/contract/test_gold_schema_snapshot_registry.py`
- bounded DQ-sensitive output bundles:
  `tests/fixtures/golden/gold/*_dq_bundle_v1.json`

Update path для intentional Gold schema change:

```bash
UPDATE_SNAPSHOTS=1 pytest tests/contract/test_gold_schema_snapshot_registry.py
```

Bounded DQ golden bundles обновляются вместе с изменением output contract и
должны оставаться перечисленными в
`configs/quality/test_matrix.yaml -> fixture_governance.gold_snapshot_registry`.

DQ bundle coverage policy is intentionally bounded. The registry field
`dq_bundle_policy.scope` is `dq_sensitive_outputs`; bundle snapshots are
required for outputs listed in `dq_sensitive_outputs`, not for every Gold
entity in `entities`. An output belongs in this bounded subset when it carries
DQ flags or DQ-sensitive provenance consumed by downstream checks, represents a
high-value provider or composite contract surface, and has snapshot rows that
exercise at least one warning or error DQ state. Contract tests enforce that
required subset and do not imply entity-wide DQ bundle generation. This is not a
blanket snapshot-expansion policy: adding a new Gold bundle requires registry
membership and DQ-sensitive rationale, not only the existence of a Gold entity.

### Nullable Numeric Compatibility

Gold JSON contracts intentionally publish selected nullable numeric fields as
`["number", "null"]` even when upstream Silver/runtime semantics are
integer-like or provider-native values are parsed from strings. This convention
keeps strict Gold validation compatible with Pandera nullable numeric columns
while preserving semantic meaning in field names, DQ rules, filters and
transformers.

The guardrail is
`python3 scripts/engineering/qa/check_gold_nullable_numeric_compatibility.py --check`.
It verifies the published Gold JSON contracts, source Pandera markers, and this
documentation section for the compatibility families below.

#### Publication Nullable Integer Compatibility

Publication Silver/common schemas keep `publication_year` as nullable integer
semantics (`Series[pd.Int64Dtype]`) so provider transformers preserve the
business meaning of a year. Gold publication contracts intentionally export the
same field as nullable `number` (`Series[float]`, `coerce=True`) because Pandera
uses float compatibility for nullable numeric columns in strict Gold outputs.

This is a compatibility convention, not a semantic rename: `publication_year`
remains an integer-like year constrained to the configured 1500-2100 range.
Published JSON contracts for ChEMBL, CrossRef, OpenAlex, PubMed and
SemanticScholar publication Gold schemas must therefore continue to expose
`publication_year` as `["number", "null"]` while Silver/runtime schemas keep
the integer intent explicit.

Publication citation counters such as `citations_received` and
`citations_made` follow the same nullable `number` convention in Gold. They
remain count semantics with non-negative DQ/Pandera constraints where the
provider contract exposes the field.

#### Molecule Descriptor Numeric Compatibility

ChEMBL and PubChem molecule descriptors use nullable `number` in Gold for
computed or provider-supplied descriptor families such as `molecular_weight`,
`logp`/`xlogp`, `polar_surface_area`/`tpsa`, `hba_count`, and `hbd_count`.
Canonical registry aliases preserve semantic identity across provider naming,
while the Gold JSON surface remains provider-contract specific.

#### Activity Measurement Numeric Compatibility

ChEMBL activity measurements and derived metrics such as `value`,
`standard_value`, `standard_upper_value`, `pchembl_value`, and
`ligand_efficiency_*` are nullable `number` in Gold. They remain measurement
semantics constrained by DQ filters, units policy, ontology mapping policy, and
activity-specific Pandera checks; the nullable numeric representation is a Gold
compatibility surface, not a relaxation of activity measurement meaning.

______________________________________________________________________

## Архитектура Gold-слоя

```
Silver Layer                     Gold Layer
┌─────────────────┐             ┌─────────────────┐
│  All Records    │             │ Filtered        │
│  (validated)    │──────────►  │ (business-ready)│
│                 │  Filters    │                 │
│  ~100% данных   │             │  ~20-60% данных │
└─────────────────┘             └─────────────────┘
        │                               │
        ▼                               ▼
   Delta Lake                      Delta Lake
   (forensic)                      (analytics)
```

### Путь данных

1. **Silver Record** → Все провалидированные записи из Bronze
1. **Gold Filters** → Применение бизнес-фильтров из YAML-конфига
1. **Schema Validation** → Проверка Pandera-схемой (`strict=True`)
1. **Deterministic Write** → Сортировка по PK, запись в Delta Lake

______________________________________________________________________

## Фильтрация Silver → Gold

Gold-фильтры определяются в YAML-конфигах пайплайнов.

### Типы фильтров

| Тип фильтра            | Описание              | Пример                                   |
| ---------------------- | --------------------- | ---------------------------------------- |
| **columns**            | Inclusion list (IN)   | `standard_type: [IC50, Ki]`              |
| **ranges**             | Числовой диапазон     | `standard_value: {min: 0}`               |
| **list_lengths**       | Длина списка          | `component_accessions: {min: 1, max: 1}` |
| **list_contains**      | Содержимое списка     | `component_types: {values: [PROTEIN]}`   |
| **required_fields**    | Обязательные поля     | `[target_id, standard_value]`            |
| **exclude_if_present** | Исключение по наличию | `[deprecated_field]`                     |

### Пример конфигурации

```yaml
# configs/entities/chembl/activity.yaml
gold_filters:
  columns:
    standard_type: [IC50, Ki]
    standard_units: [nM]
    assay_type: [B, F]
  ranges:
    standard_value:
      min: 0
      include_min: false
  required_fields:
    - standard_type
    - standard_value
    - target_id
```

______________________________________________________________________

## Контракты по провайдерам

### ChEMBL

#### chembl_activity

**Primary Key**: `activity_id`
**Назначение**: Биоактивность соединений (IC50, Ki, EC50)

##### Gold-фильтры (Бизнес-логика)

| Фильтр                | Значения     | Обоснование                                   |
| --------------------- | ------------ | --------------------------------------------- |
| `standard_type`       | `[IC50, Ki]` | Только стандартизированные метрики связывания |
| `standard_units`      | `[nM]`       | Единый масштаб для сравнения                  |
| `standard_relation`   | `["="]`      | Точные значения, не диапазоны                 |
| `assay_type`          | `[B, F]`     | Binding/Functional assays                     |
| `potential_duplicate` | `["0"]`      | Исключение дубликатов                         |
| `standard_value`      | `> 0`        | Положительные значения активности             |

##### Ключевые поля

| Поле                 | Тип   | Nullable | Описание                     |
| -------------------- | ----- | -------- | ---------------------------- |
| `entity_id`          | str   | No       | Уникальный идентификатор     |
| `activity_id`        | str   | No       | ChEMBL Activity ID           |
| `molecule_id`        | str   | No       | ID молекулы                  |
| `target_id`          | str   | Yes      | ID мишени                    |
| `assay_id`           | str   | Yes      | ID эксперимента              |
| `publication_doi`    | str   | Yes      | DOI публикации               |
| `publication_pmid`   | str   | Yes      | PubMed ID публикации         |
| `publication_pmc_id` | str   | Yes      | PubMed Central ID публикации |
| `standard_type`      | str   | Yes      | Тип метрики (IC50, Ki)       |
| `standard_value`     | float | Yes      | Значение активности          |
| `standard_units`     | str   | Yes      | Единицы измерения            |
| `pchembl_value`      | float | Yes      | -log10(IC50)                 |
| `canonical_smiles`   | str   | Yes      | SMILES молекулы              |
| `content_hash`       | str   | No       | SHA256 хэш записи            |

##### Лиганд-эффективность

| Поле                    | Описание                     |
| ----------------------- | ---------------------------- |
| `ligand_efficiency_bei` | Binding Efficiency Index     |
| `ligand_efficiency_le`  | Ligand Efficiency            |
| `ligand_efficiency_lle` | Lipophilic Ligand Efficiency |
| `ligand_efficiency_sei` | Surface Efficiency Index     |

______________________________________________________________________

#### chembl_molecule

**Primary Key**: `molecule_id`
**Назначение**: Химические соединения и их свойства

##### Gold-фильтры

| Фильтр           | Значения           | Обоснование                  |
| ---------------- | ------------------ | ---------------------------- |
| `molecule_type`  | `[Small molecule]` | Drug-like молекулы           |
| `structure_type` | `[MOL]`            | Структурированные соединения |
| `inorganic_flag` | `["0"]`            | Только органические          |

##### Ключевые поля

| Поле                           | Тип   | Nullable | Описание                         |
| ------------------------------ | ----- | -------- | -------------------------------- |
| `molecule_id`                  | str   | No       | ChEMBL Molecule ID               |
| `pref_name`                    | str   | Yes      | Предпочтительное название        |
| `molecule_type`                | str   | Yes      | Тип молекулы                     |
| `max_phase`                    | float | Yes      | Фаза клинических испытаний (0-4) |
| `canonical_smiles`             | str   | Yes      | Каноническая SMILES              |
| `standard_inchi`               | str   | Yes      | InChI                            |
| `inchi_key`                    | str   | Yes      | InChIKey                         |

##### Физико-химические свойства

| Поле                      | Описание                   |
| ------------------------- | -------------------------- |
| `logp`                  | Расчётный logP             |
| `mw_freebase`           | Молекулярная масса         |
| `hba_count`             | Hydrogen Bond Acceptors    |
| `hbd_count`             | Hydrogen Bond Donors       |
| `polar_surface_area`    | Polar Surface Area         |
| `rotatable_bond_count`  | Rotatable Bonds            |
| `ro5_violation_count`   | Нарушения правила Lipinski |

______________________________________________________________________

#### chembl_assay

**Primary Key**: `assay_id`
**Назначение**: Биологические эксперименты

##### Gold-фильтры

| Фильтр              | Значения     | Обоснование                     |
| ------------------- | ------------ | ------------------------------- |
| `assay_type`        | `[B, F]`     | Binding, Functional             |
| `confidence_score`  | `["8", "9"]` | Высокая уверенность (шкала 0-9) |
| `relationship_type` | `[D]`        | Direct interaction only         |

##### Ключевые поля

| Поле               | Тип   | Nullable | Описание            |
| ------------------ | ----- | -------- | ------------------- |
| `assay_id`         | str   | No       | ChEMBL Assay ID     |
| `target_id`        | str   | Yes      | ID мишени           |
| `assay_type`       | str   | Yes      | Тип эксперимента    |
| `description`      | str   | Yes      | Описание            |
| `confidence_score` | float | Yes      | Уровень уверенности |
| `bao_format`       | str   | Yes      | BAO Format ID       |
| `assay_organism`   | str   | Yes      | Организм            |

______________________________________________________________________

#### chembl_target

**Primary Key**: `target_id`
**Назначение**: Биологические мишени (белки)

##### Gold-фильтры

| Фильтр                 | Значения              | Обоснование            |
| ---------------------- | --------------------- | ---------------------- |
| `target_type`          | `[SINGLE PROTEIN]`    | Единичные белки        |
| `component_accessions` | length: 1             | Один UniProt accession |
| `component_types`      | contains: `[PROTEIN]` | Тип компонента — белок |

##### Ключевые поля

| Поле                   | Тип       | Nullable | Описание           |
| ---------------------- | --------- | -------- | ------------------ |
| `target_id`            | str       | No       | ChEMBL Target ID   |
| `pref_name`            | str       | Yes      | Название           |
| `target_type`          | str       | Yes      | Тип мишени         |
| `organism`             | str       | Yes      | Организм           |
| `taxonomy_id`          | float     | Yes      | NCBI Taxonomy ID   |
| `target_protein_synonyms` | str    | Yes      | Pipe-delimited UNIPROT synonyms or `unknown` |
| `target_gene_synonyms` | str       | Yes      | Pipe-delimited GENE_SYMBOL synonyms or `unknown` |
| `target_ec_numbers`    | str       | Yes      | Pipe-delimited EC numbers or `unknown` |
| `component_accessions` | list[str] | Yes      | UniProt accessions |

`target_component_synonyms` remains a forensic JSON string, while the three
derived synonym fields above expose normalized analytic projections with
first-seen dedupe ordering and `\|` escaping for embedded pipe characters.

______________________________________________________________________

#### chembl_target_component

**Primary Key**: `component_id`
**Назначение**: Компоненты мишеней (белковые последовательности)

##### Gold-фильтры

| Фильтр           | Значения    | Обоснование               |
| ---------------- | ----------- | ------------------------- |
| `component_type` | `[PROTEIN]` | Только белки              |
| required         | `accession` | Наличие UniProt accession |

##### Ключевые поля

| Поле                      | Тип   | Nullable | Описание           |
| ------------------------- | ----- | -------- | ------------------ |
| `component_id`            | float | No       | Component ID       |
| `accession`               | str   | Yes      | UniProt accession  |
| `component_type`          | str   | Yes      | Тип компонента     |
| `organism`                | str   | Yes      | Организм           |
| `protein_classifications` | str   | Yes      | JSON классификации |

______________________________________________________________________

#### chembl_publication

**Primary Key**: `publication_id`
**Назначение**: Научные публикации из ChEMBL API (silver-table/gold-table: `chembl_publication`)

##### Gold-фильтры

| Фильтр             | Значения                                   | Обоснование                          |
| ------------------ | ------------------------------------------ | ------------------------------------ |
| `publication_type` | `[journal-article, book, dataset, patent]` | Канонические типы публикаций         |
| `publication_year` | `>= 1500`                                  | Базовая временная валидация          |
| required           | `publication_id, title`                    | Базовые метаданные для записи в Gold |

##### Ключевые поля

| Поле               | Тип   | Nullable | Описание              |
| ------------------ | ----- | -------- | --------------------- |
| `publication_id`   | str   | No       | ChEMBL Publication ID |
| `publication_pmid` | str   | Yes      | PubMed ID             |
| `publication_doi`  | str   | Yes      | DOI                   |
| `publication_pmc_id` | str | Yes      | Canonical PMC identifier |
| `doi`              | str   | Yes      | Raw DOI alias retained for compatibility |
| `pmid`             | str   | Yes      | Raw PubMed ID alias retained for compatibility |
| `title`            | str   | Yes      | Заголовок             |
| `journal`          | str   | Yes      | Журнал                |
| `publication_year` | float | Yes      | Год публикации        |
| `authors`          | str   | Yes      | Авторы                |
| `author_keys`      | str   | Yes      | Pipe-delimited author keys |
| `publication_type` | str   | Yes      | Canonical publication type subset for ChEMBL |
| `src_id`           | float | Yes      | ChEMBL source identifier |

Поля `pmc_id`, `publication_type_unified`, `publication_subclass`,
`publication_class`, `publication_date`, `language`, `is_oa`,
`citations_received`, `citations_made`, `affiliation_list`, и
`author_orcids` intentionally do not belong to the current ChEMBL Gold export
surface. They may still exist in broader publication normalization or Silver
surfaces, but they are excluded from the live ChEMBL Gold contract.

______________________________________________________________________

#### chembl_compound_record

**Primary Key**: `record_id`
**Назначение**: Связь молекула-документ

##### Gold-фильтры

| Фильтр   | Значения                      | Обоснование    |
| -------- | ----------------------------- | -------------- |
| required | `molecule_id, publication_id` | Полнота связей |

##### Ключевые поля

| Поле             | Тип   | Nullable | Описание              |
| ---------------- | ----- | -------- | --------------------- |
| `record_id`      | float | No       | Record ID             |
| `molecule_id`    | str   | No       | ChEMBL Molecule ID    |
| `publication_id` | str   | No       | ChEMBL Publication ID |
| `compound_key`   | str   | Yes      | Название в публикации |
| `compound_name`  | str   | Yes      | Полное название       |

______________________________________________________________________

#### chembl_cell_line

**Primary Key**: `cell_id`
**Назначение**: Клеточные линии

##### Gold-фильтры

| Фильтр   | Значения    | Обоснование      |
| -------- | ----------- | ---------------- |
| required | `cell_name` | Наличие названия |

##### Ключевые поля

| Поле                   | Тип | Nullable | Описание            |
| ---------------------- | --- | -------- | ------------------- |
| `cell_id`              | str | No       | ChEMBL Cell Line ID |
| `cell_name`            | str | No       | Название            |
| `cell_description`     | str | Yes      | Описание            |
| `cell_source_tissue`   | str | Yes      | Ткань-источник      |
| `cell_source_organism` | str | Yes      | Организм            |
| `cellosaurus_id`       | str | Yes      | Cellosaurus ID      |

______________________________________________________________________

### PubChem

#### pubchem_compound

**Primary Key**: `molecule_id`
**Назначение**: Химические соединения PubChem

##### Gold-фильтры

| Фильтр   | Значения                         | Обоснование        |
| -------- | -------------------------------- | ------------------ |
| required | `molecule_id, molecular_formula` | Минимальные данные |

##### Ключевые поля

| Поле                | Тип   | Nullable | Описание             |
| ------------------- | ----- | -------- | -------------------- |
| `entity_id`         | str   | No       | Уникальный ID        |
| `molecule_id`       | str   | No       | PubChem Compound ID  |
| `molecular_formula` | str   | Yes      | Молекулярная формула |
| `molecular_weight`  | float | Yes      | Молекулярная масса   |
| `canonical_smiles`  | str   | Yes      | Каноническая SMILES  |
| `isomeric_smiles`   | str   | Yes      | Изомерная SMILES     |
| `inchi`             | str   | Yes      | InChI                |
| `inchi_key`         | str   | Yes      | InChIKey             |
| `iupac_name`        | str   | Yes      | IUPAC название       |

______________________________________________________________________

### UniProt

#### uniprot_protein

**Primary Key**: `accession`
**Назначение**: Белки UniProt

##### Gold-фильтры

| Фильтр     | Значения                          | Обоснование                  |
| ---------- | --------------------------------- | ---------------------------- |
| `reviewed` | `["true"]`                        | Только Swiss-Prot (reviewed) |
| required   | `accession, entry_name, organism_scientific` | Полнота данных               |

##### Ключевые поля

| Поле              | Тип       | Nullable | Описание                 |
| ----------------- | --------- | -------- | ------------------------ |
| `entity_id`       | str       | No       | Уникальный ID            |
| `accession`       | str       | No       | UniProt Accession        |
| `entry_name`      | str       | Yes      | Entry name               |
| `protein_name`    | str       | Yes      | Название белка           |
| `gene_primary`    | str       | Yes      | Основное название гена   |
| `gene_synonyms`   | str       | Yes      | Синонимы названия гена   |
| `taxonomy_id`     | float     | Yes      | NCBI Taxonomy ID         |
| `sequence_length` | float     | Yes      | Длина последовательности |

______________________________________________________________________

### PubMed

#### pubmed_publication

**Primary Key**: `pmid`
**Назначение**: Публикации PubMed

##### Gold-фильтры

| Фильтр   | Значения      | Обоснование            |
| -------- | ------------- | ---------------------- |
| required | `pmid, title` | Минимальные метаданные |

##### Ключевые поля

| Поле               | Тип   | Nullable | Описание                                  |
| ------------------ | ----- | -------- | ----------------------------------------- |
| `entity_id`        | str   | No       | Уникальный ID                             |
| `pmid`             | str   | No       | PubMed ID                                 |
| `doi`              | str   | Yes      | DOI                                       |
| `pmc_id`           | str   | Yes      | PubMed Central ID                         |
| `title`            | str   | Yes      | Заголовок                                 |
| `abstract`         | str   | Yes      | Абстракт                                  |
| `journal`          | str   | Yes      | Журнал                                    |
| `authors`          | str   | Yes      | Авторы (flattened representation)         |
| `publication_year` | float | Yes      | Год публикации                            |
| `subject_mesh`     | str   | Yes      | MeSH термины (flattened representation)   |
| `subject_keywords` | str   | Yes      | Ключевые слова (flattened representation) |

______________________________________________________________________

### CrossRef

#### crossref_publication

**Primary Key**: `doi`
**Схема**: `CrossRefPublicationGoldSchema` (`domain/contracts/gold/publications_crossref.py`)
**Назначение**: Научные публикации CrossRef с метаданными цитирования и издателя

##### Ключевые поля

| Поле                                   | Тип   | Nullable | Описание                                        |
| -------------------------------------- | ----- | -------- | ----------------------------------------------- |
| `entity_id`                            | str   | No       | Уникальный ID записи                            |
| `doi`                                  | str   | No       | DOI публикации (обязателен, валидируется regex) |
| `pmid`                                 | str   | Yes      | PubMed ID                                       |
| `pmc_id`                               | str   | Yes      | PubMed Central ID                               |
| `title`                                | str   | Yes      | Заголовок публикации                            |
| `abstract`                             | str   | Yes      | Аннотация                                       |
| `authors`                              | str   | Yes      | Авторы (JSON-сериализованный список)            |
| `affiliation_list`                     | str   | Yes      | Аффилиации авторов (JSON)                       |
| `journal`                              | str   | Yes      | Название журнала                                |
| `issn`                                 | str   | Yes      | Основной ISSN                                   |
| `issn_list`                            | str   | Yes      | Все ISSN журнала (JSON)                         |
| `issn_print`                           | str   | Yes      | ISSN печатного издания                          |
| `issn_electronic`                      | str   | Yes      | ISSN электронного издания                       |
| `journal_name_short`                   | str   | Yes      | Сокращённое название журнала                    |
| `publisher`                            | str   | Yes      | Издатель                                        |
| `volume`                               | str   | Yes      | Том                                             |
| `issue`                                | str   | Yes      | Номер выпуска                                   |
| `page_first`                           | str   | Yes      | Первая страница                                 |
| `page_last`                            | str   | Yes      | Последняя страница                              |
| `publication_year`                     | float | Yes      | Год публикации (диапазон 1500-2100)             |
| `publication_date`                     | str   | Yes      | Дата публикации                                 |
| `published_print`                      | str   | Yes      | Дата печатной публикации                        |
| `published_online`                     | str   | Yes      | Дата онлайн-публикации                          |
| `published`                            | str   | Yes      | Обобщённая дата публикации                      |
| `publication_type`                     | str   | Yes      | Тип публикации (raw из API)                     |
| `publication_type_unified`             | str   | Yes      | Унифицированный тип публикации                  |
| `publication_subclass`                 | str   | Yes      | Подкласс публикации                             |
| `publication_class`                    | str   | Yes      | Класс публикации                                |
| `citations_received`                   | float | Yes      | Количество цитирований (>= 0)                   |
| `citations_made`                       | float | Yes      | Количество исходящих ссылок (>= 0)              |
| `language`                             | str   | Yes      | Язык публикации                                 |
| `license_url`                          | str   | Yes      | URL лицензии                                    |
| `subject_keywords`                     | str   | Yes      | Ключевые слова / предметные области (JSON)      |
| `content_domain_domains`               | str   | Yes      | Домены контента CrossRef (JSON)                 |
| `content_domain_crossmark_restriction` | bool  | Yes      | Ограничение CrossMark                           |
| `alternative_id`                       | str   | Yes      | Альтернативные идентификаторы (JSON)            |
| `author_keys`                          | str   | Yes      | Ключи авторов (JSON)                            |
| `author_orcids`                        | str   | Yes      | ORCID авторов (JSON)                            |
| `author_details`                       | str   | Yes      | Детали авторов (JSON)                           |
| `references`                           | str   | Yes      | Список ссылок (JSON)                            |

______________________________________________________________________

### OpenAlex

#### openalex_publication

**Primary Key**: `openalex_id`
**Схема**: `OpenAlexPublicationGoldSchema` (`domain/contracts/gold/publications_openalex.py`)
**Назначение**: Научные публикации OpenAlex с данными об открытом доступе, институтах и темах

##### Ключевые поля

| Поле                        | Тип   | Nullable | Описание                                    |
| --------------------------- | ----- | -------- | ------------------------------------------- |
| `entity_id`                 | str   | No       | Уникальный ID записи                        |
| `openalex_id`               | str   | No       | OpenAlex Work ID (обязателен)               |
| `doi`                       | str   | Yes      | DOI публикации (валидируется regex)         |
| `pmid`                      | str   | Yes      | PubMed ID                                   |
| `pmc_id`                    | str   | Yes      | PubMed Central ID                           |
| `mag_id`                    | str   | Yes      | Microsoft Academic Graph ID                 |
| `title`                     | str   | Yes      | Заголовок публикации                        |
| `abstract`                  | str   | Yes      | Аннотация                                   |
| `authors`                   | str   | Yes      | Авторы (JSON-сериализованный список)        |
| `affiliation_list`          | str   | Yes      | Аффилиации авторов (JSON)                   |
| `author_keys`               | str   | Yes      | Ключи авторов (JSON)                        |
| `author_openalex_ids`       | str   | Yes      | OpenAlex ID авторов (JSON)                  |
| `author_orcids`             | str   | Yes      | ORCID авторов (JSON)                        |
| `journal`                   | str   | Yes      | Название журнала / источника                |
| `issn`                      | str   | Yes      | ISSN журнала                                |
| `publisher`                 | str   | Yes      | Издатель                                    |
| `volume`                    | str   | Yes      | Том                                         |
| `issue`                     | str   | Yes      | Номер выпуска                               |
| `page_first`                | str   | Yes      | Первая страница                             |
| `page_last`                 | str   | Yes      | Последняя страница                          |
| `publication_year`          | float | Yes      | Год публикации (диапазон 1500-2100)         |
| `publication_date`          | str   | Yes      | Дата публикации                             |
| `publication_type`          | str   | Yes      | Тип публикации (raw из API)                 |
| `publication_type_unified`  | str   | Yes      | Унифицированный тип публикации              |
| `publication_subclass`      | str   | Yes      | Подкласс публикации                         |
| `publication_class`         | str   | Yes      | Класс публикации                            |
| `is_oa`                     | bool  | Yes      | Признак открытого доступа                   |
| `oa_status`                 | str   | Yes      | Статус OA (gold/green/hybrid/bronze/closed) |
| `is_retracted`              | bool  | No       | Признак отозванной публикации               |
| `citations_received`        | float | Yes      | Количество цитирований (>= 0)               |
| `citations_made`            | float | Yes      | Количество исходящих ссылок (>= 0)          |
| `fwci`                      | float | Yes      | Field-Weighted Citation Impact (>= 0)       |
| `language`                  | str   | Yes      | Язык публикации                             |
| `subject_mesh`              | str   | Yes      | MeSH-термины (JSON)                         |
| `subject_keywords`          | str   | Yes      | Ключевые слова (JSON)                       |
| `subject_topics`            | str   | Yes      | Тематические области OpenAlex (JSON)        |
| `primary_topic`             | str   | Yes      | Основная тема (JSON)                        |
| `grants`                    | str   | Yes      | Гранты и финансирование (JSON)              |
| `institution_ids`           | str   | Yes      | OpenAlex ID институтов (JSON)               |
| `institution_country_codes` | str   | Yes      | Коды стран институтов (JSON)                |
| `ror_ids`                   | str   | Yes      | ROR идентификаторы институтов (JSON)        |

______________________________________________________________________

### Semantic Scholar

#### semanticscholar_publication

**Primary Key**: `paper_id`
**Схема**: `SemanticScholarPublicationGoldSchema` (`domain/contracts/gold/publications_semanticscholar.py`)
**Назначение**: Научные публикации Semantic Scholar с данными об авторах, цитировании и открытом доступе

##### Ключевые поля

| Поле                         | Тип   | Nullable | Описание                                    |
| ---------------------------- | ----- | -------- | ------------------------------------------- |
| `entity_id`                  | str   | No       | Уникальный ID записи                        |
| `paper_id`                   | str   | No       | Semantic Scholar Paper ID (обязателен)      |
| `doi`                        | str   | Yes      | DOI публикации (валидируется regex)         |
| `pmid`                       | str   | Yes      | PubMed ID                                   |
| `pmc_id`                     | str   | Yes      | PubMed Central ID                           |
| `corpus_id`                  | str   | Yes      | Semantic Scholar Corpus ID (decimal string; avoids float precision loss) |
| `dblp_id`                    | str   | Yes      | DBLP идентификатор                          |
| `title`                      | str   | Yes      | Заголовок публикации                        |
| `abstract`                   | str   | Yes      | Аннотация                                   |
| `tldr`                       | str   | Yes      | Автогенерированное краткое резюме (TL;DR)   |
| `authors`                    | str   | Yes      | Авторы (JSON-сериализованный список)        |
| `affiliation_list`           | str   | Yes      | Аффилиации авторов (JSON)                   |
| `author_keys`                | str   | Yes      | Ключи авторов (JSON)                        |
| `author_s2_ids`              | str   | Yes      | Semantic Scholar ID авторов (JSON)          |
| `author_orcids`              | str   | Yes      | ORCID авторов (JSON)                        |
| `author_h_indices`           | str   | Yes      | h-индексы авторов (JSON)                    |
| `journal`                    | str   | Yes      | Название журнала                            |
| `volume`                     | str   | Yes      | Том                                         |
| `issue`                      | str   | Yes      | Номер выпуска                               |
| `page_range`                 | str   | Yes      | Диапазон страниц (raw из API)               |
| `page_first`                 | str   | Yes      | Первая страница                             |
| `page_last`                  | str   | Yes      | Последняя страница                          |
| `publication_year`           | float | Yes      | Год публикации (диапазон 1500-2100)         |
| `publication_date`           | str   | Yes      | Дата публикации                             |
| `publication_type`           | str   | Yes      | Тип публикации (raw из API)                 |
| `publication_type_unified`   | str   | Yes      | Унифицированный тип публикации              |
| `publication_subclass`       | str   | Yes      | Подкласс публикации                         |
| `publication_class`          | str   | Yes      | Класс публикации                            |
| `publication_types`          | str   | Yes      | Все типы публикации (JSON)                  |
| `is_oa`                      | bool  | Yes      | Признак открытого доступа                   |
| `oa_status`                  | str   | Yes      | Статус OA (gold/green/hybrid/bronze/closed) |
| `open_access_url`            | str   | Yes      | URL открытого доступа                       |
| `citations_received`         | float | Yes      | Количество цитирований (>= 0)               |
| `citations_made`             | float | Yes      | Количество исходящих ссылок (>= 0)          |
| `influential_citation_count` | float | Yes      | Количество влиятельных цитирований (>= 0)   |
| `citation_contexts`          | str   | Yes      | Контексты цитирования (JSON)                |
| `subject_fields`             | str   | Yes      | Предметные области (JSON)                   |

______________________________________________________________________

### Composite

Composite-схемы объединяют данные из нескольких провайдеров в единую сущность.
Live shared base config uses `strict=True` and `coerce=True`. The shared base
declares persisted common metadata fields; concrete composite schemas explicitly
declare the current persisted lineage and selected business/provider-derived
fields.

**Файлы схем**:

| Схема                            | Файл                                             |
| -------------------------------- | ------------------------------------------------ |
| `CompositeActivityGoldSchema`    | `domain/contracts/gold/composite_bioassay.py`    |
| `CompositeAssayGoldSchema`       | `domain/contracts/gold/composite_bioassay.py`    |
| `CompositeTargetGoldSchema`      | `domain/contracts/gold/composite_bioassay.py`    |
| `CompositeMoleculeGoldSchema`    | `domain/contracts/gold/composite_molecule.py`    |
| `CompositePublicationGoldSchema` | `domain/contracts/gold/composite_publication.py` |

#### Общие поля для всех Composite-схем

Все composite-схемы гарантируют наличие следующих полей:

| Поле                 | Тип  | Nullable | Описание                                              |
| -------------------- | ---- | -------- | ----------------------------------------------------- |
| `entity_id`          | str  | No       | Стабильный бизнес-идентификатор объединённой сущности |
| `_source`            | str  | Yes      | Source-family lineage marker                          |
| `_dq_warn`           | bool | No       | Soft data-quality warning flag                        |
| `_dq_error`          | bool | No       | Hard data-quality error flag                          |
| `_index`             | int  | No       | Порядковый номер в batch/output                       |
| `_source_providers`  | str  | No       | Провайдеры-источники (JSON-список)                    |
| `_enrichment_status` | str  | No       | Статус обогащения (JSON/status payload)               |

#### Поля линейности (composite lineage)

Поля, специфичные для composite-слоя (хранятся с алиасом `_*`):

| Поле (alias)         | Тип | Nullable | Описание                                     |
| -------------------- | --- | -------- | -------------------------------------------- |
| `_source_providers`  | str | No       | Провайдеры-источники (JSON-список)           |
| `_enrichment_status` | str | No       | Статус обогащения (enriched/partial/missing) |

#### composite_publication (дополнительные поля)

`CompositePublicationGoldSchema` дополнительно содержит поля поиска публикации:

| Поле (alias)     | Тип | Nullable | Описание                         |
| ---------------- | --- | -------- | -------------------------------- |
| `_source`        | str | Yes      | Провайдер-источник публикации    |
| `_lookup_method` | str | Yes      | Метод поиска при cross-reference |
| `_original_id`   | str | Yes      | Исходный ID из провайдера        |

#### Примечание по composite-схемам

Composite-схемы используют `strict=True`: concrete classes under
`src/bioetl/domain/contracts/gold/composite_bioassay.py`,
`composite_molecule.py`, and `composite_publication.py` explicitly declare the
persisted common, lineage, and selected business fields that are allowed in
physical Gold rows. Occurrence-scoped lineage anchors (`run_id`,
`composite_run_id`, wall-clock timestamps) публикуются через
sidecar/control-plane artifacts, а не через физические Gold rows.

______________________________________________________________________

## Системные поля

Провайдерные Gold-таблицы содержат следующие persisted системные метаданные:

| Поле           | Alias | Тип | Nullable | Описание                                                                                               |
| -------------- | ----- | --- | -------- | ------------------------------------------------------------------------------------------------------ |
| `entity_id`    | —     | str | No       | Глобальный уникальный ID                                                                               |
| `content_hash` | —     | str | No\*     | SHA256 хэш содержимого (обязателен для провайдерных схем; composite-схемы могут не декларировать явно) |
| `_index`       | index | int | No       | Порядковый номер в batch                                                                               |

Occurrence-scoped provenance (`run_id`, `run_type`, `source_batch_id`, `ingestion_ts`, `composite_run_id`, runtime lineage timestamps) не входит в persisted Gold row contract. Эти anchors публикуются в audit, sidecar metadata, lineage fragments, run manifest и run ledger.

### Content Hash

Формула вычисления:

```python
sha256(provider + canonical_json(record))
```

**Нормализация перед хэшированием:**

- NaN/Inf → `null`
- Floats → `round(val, 10)`
- Dates → ISO `YYYY-MM-DD`
- Strings → `strip()`
- **Исключаются**: occurrence-scoped provenance (`_ingestion_ts`, `_run_id`, `_run_type`, `_source_batch_id`, `_composite_run_id`, `_lineage_created_at`) и DQ flags (`_dq_*`)

______________________________________________________________________

## Режимы записи

| Режим         | Enum                      | Поведение                         | Идемпотентность          |
| ------------- | ------------------------- | --------------------------------- | ------------------------ |
| **OVERWRITE** | `GoldWriteMode.OVERWRITE` | Полная замена таблицы             | Да                       |
| **APPEND**    | `GoldWriteMode.APPEND`    | Добавление записей                | Нет (возможны дубликаты) |
| **SCD2**      | `GoldWriteMode.SCD2`      | Slowly Changing Dimensions Type 2 | Да (upsert)              |

### SCD2 конфигурация

При использовании SCD2 добавляются поля:

| Поле         | Тип      | Описание                   |
| ------------ | -------- | -------------------------- |
| `valid_from` | datetime | Начало действия версии     |
| `valid_to`   | datetime | Окончание (NULL = текущая) |
| `is_current` | bool     | Текущая версия             |
| `version`    | int      | Номер версии               |

______________________________________________________________________

## Примеры запросов

### Polars

```python
import polars as pl
from deltalake import DeltaTable

# Загрузка Gold-таблицы
dt = DeltaTable("data/output/gold/chembl_activity")
df = pl.from_arrow(dt.to_pyarrow_table())

# Фильтрация активных IC50 для конкретной мишени
activities = df.filter(
    (pl.col("target_id") == "CHEMBL1234")
    & (pl.col("standard_type") == "IC50")
    & (pl.col("standard_value") < 100)  # nM
).select(["molecule_id", "standard_value", "pchembl_value", "canonical_smiles"])
```

### SQL (DuckDB)

```sql
-- Подключение к Delta Lake
INSTALL delta;
LOAD delta;

-- Топ-10 молекул по активности для мишени
SELECT
    molecule_id,
    standard_value,
    pchembl_value,
    canonical_smiles
FROM delta_scan('data/output/gold/chembl_activity')
WHERE target_id = 'CHEMBL1234'
  AND standard_type = 'IC50'
ORDER BY standard_value ASC
LIMIT 10;
```

### Связывание таблиц

```sql
-- Молекулы с активностью и свойствами
SELECT
    a.molecule_id,
    a.target_id,
    a.standard_value AS ic50_nm,
    m.logp,
    m.mw_freebase AS mw,
    m.canonical_smiles
FROM delta_scan('data/output/gold/chembl_activity') a
JOIN delta_scan('data/output/gold/chembl_molecule') m
  ON a.molecule_id = m.molecule_id
WHERE a.standard_type = 'IC50'
  AND a.standard_value < 100;
```

### Анализ по мишеням

```sql
-- Статистика активности по мишеням
SELECT
    t.pref_name AS target_name,
    t.organism,
    COUNT(*) AS activity_count,
    AVG(a.pchembl_value) AS avg_pchembl,
    MIN(a.standard_value) AS best_ic50_nm
FROM delta_scan('data/output/gold/chembl_activity') a
JOIN delta_scan('data/output/gold/chembl_target') t
  ON a.target_id = t.target_id
WHERE a.standard_type = 'IC50'
GROUP BY t.pref_name, t.organism
ORDER BY activity_count DESC
LIMIT 20;
```

### Time-travel запросы (Delta Lake)

```python
from deltalake import DeltaTable

# Версия на определённый timestamp
dt = DeltaTable("data/output/gold/chembl_activity")
df_historical = pl.from_arrow(
    dt.load_as_version(datetime(2025, 1, 1)).to_pyarrow_table()
)

# Сравнение версий
current_count = dt.to_pyarrow_table().num_rows
previous = dt.load_as_version(dt.version() - 1)
previous_count = previous.to_pyarrow_table().num_rows
print(f"Added {current_count - previous_count} records")
```

______________________________________________________________________

## Валидация

### Pandera Schema

Все Gold-схемы определены в `src/bioetl/domain/contracts/gold/`.

```python
class ChEMBLActivityGoldSchema(pa.DataFrameModel):
    entity_id: Series[str] = pa.Field(nullable=False)
    activity_id: Series[str] = pa.Field(nullable=False)
    molecule_id: Series[str] = pa.Field(nullable=False)
    # ... остальные поля

    class Config:
        strict = True  # REQ-DATA-009
```

### Проверка контракта

```python
from bioetl.domain.contracts.gold import ChEMBLActivityGoldSchema
import polars as pl

# Загрузка и валидация
df = pl.read_delta("data/output/gold/chembl_activity")
validated = ChEMBLActivityGoldSchema.validate(df.to_pandas())
```

### Data Quality пороги

Gold-schema validation participates in the same DQ threshold model documented in
[DQ Contracts](dq-contracts.md#threshold-semantics). BioETL does not maintain one
universal hard-fail default for every DQ surface:

| Surface | Default | Action |
| --- | --- | --- |
| Hierarchical `quality:` config / contract-loader omitted thresholds | `soft_fail=0.05`, `hard_fail=0.50` | warn above soft; reject/quarantine above hard according to active disposition policy |
| Inline DQ override normalization / Silver DQ request baseline | `soft_fail=0.05`, `hard_fail=0.20` | warn above soft; reject/quarantine above hard according to active disposition policy |

______________________________________________________________________

## Gold Schema Implementation

Gold-схемы реализованы как **Python Pandera DataFrameModel** классы в `src/bioetl/domain/contracts/gold/`.

Каждая Gold-схема определяет:

- Строгую валидацию типов (`strict=True`)
- Nullable/non-nullable поля
- Coercion rules (например, `int→float` для nullable integers)

### JSON Contract Exports

JSON exports для Gold-схем хранятся в `docs/04-reference/contracts/gold/`:

- `chembl_activity_v1.0.json`
- `chembl_assay_parameters_v1.0.json`
- `chembl_assay_parameters_v2.0.json`
- `chembl_assay_v1.0.json`
- `chembl_cell_line_v1.0.json`
- `chembl_compound_record_v1.0.json`
- `chembl_publication_similarity_v1.0.json`
- `chembl_publication_similarity_v2.0.json`
- `chembl_publication_term_v1.0.json`
- `chembl_publication_v1.0.json`
- `chembl_molecule_v1.0.json`
- `chembl_protein_class_v1.0.json`
- `chembl_subcellular_fraction_v1.0.json`
- `chembl_target_component_v1.0.json`
- `chembl_target_protein_classification_v2.2.json`
- `chembl_target_v3.0.json`
- `chembl_tissue_v1.0.json`
- `composite_activity_v1.0.json`
- `composite_assay_v1.0.json`
- `composite_molecule_v1.0.json`
- `composite_publication_v1.0.json`
- `composite_target_v1.0.json`
- `crossref_publication_v1.0.json`
- `openalex_publication_v1.0.json`
- `pubchem_compound_v1.0.json`
- `pubmed_publication_v1.0.json`
- `semanticscholar_publication_v1.0.json`
- `uniprot_idmapping_v1.0.json`
- `uniprot_protein_v1.0.json`

## Field Token Registry

Полный перечень output-токенов Pandera Gold-схем из
`src/bioetl/domain/contracts/gold/`. Имя колонки — ключ контракта (`alias`,
если он задан). Сводка «Ключевые поля» выше не заменяет этот реестр:
тест сверяет реестр с колонками схем в обе стороны, а narrative-токены
полей и фильтров обязаны быть подмножеством той же схемы.

### ChEMBLActivityGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `action_type`
- `action_type_description`
- `action_type_parent_type`
- `activity_comment`
- `activity_id`
- `activity_properties`
- `assay_description`
- `assay_id`
- `assay_type`
- `assay_variant_accession`
- `assay_variant_mutation`
- `bao_endpoint`
- `bao_endpoint_iri`
- `bao_endpoint_mapping_status`
- `bao_format`
- `bao_format_iri`
- `bao_format_mapping_status`
- `bao_label`
- `bao_ontology_version`
- `canonical_smiles`
- `content_hash`
- `data_validity_comment`
- `data_validity_description`
- `entity_id`
- `journal`
- `ligand_efficiency_bei`
- `ligand_efficiency_le`
- `ligand_efficiency_lle`
- `ligand_efficiency_sei`
- `manual_curation_flag`
- `molecule_id`
- `molecule_pref_name`
- `original_activity_id`
- `parent_molecule_id`
- `pchembl_value`
- `potential_duplicate`
- `publication_doi`
- `publication_id`
- `publication_pmc_id`
- `publication_pmid`
- `publication_year`
- `qudt_ontology_version`
- `qudt_unit_iri`
- `qudt_unit_mapping_status`
- `qudt_units`
- `record_id`
- `relation`
- `src_id`
- `standard_flag`
- `standard_relation`
- `standard_text_value`
- `standard_type`
- `standard_units`
- `standard_upper_value`
- `standard_value`
- `target_id`
- `target_organism`
- `target_pref_name`
- `target_taxonomy_id`
- `text_value`
- `toid`
- `type`
- `units`
- `uo_ontology_version`
- `uo_unit_iri`
- `uo_unit_mapping_status`
- `uo_units`
- `upper_value`
- `value`

### ChEMBLAssayGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `aidx`
- `assay_category`
- `assay_cell_type`
- `assay_classifications`
- `assay_group`
- `assay_id`
- `assay_organism`
- `assay_parameters`
- `assay_pref_name`
- `assay_strain`
- `assay_subcellular_fraction`
- `assay_taxonomy_id`
- `assay_test_type`
- `assay_tissue`
- `assay_type`
- `assay_type_description`
- `bao_format`
- `bao_label`
- `cell_id`
- `confidence_description`
- `confidence_score`
- `content_hash`
- `description`
- `entity_id`
- `publication_id`
- `relationship_description`
- `relationship_type`
- `score`
- `src_assay_id`
- `src_id`
- `target_id`
- `tissue_id`
- `variant_accession`
- `variant_isoform`
- `variant_mutation`
- `variant_organism`
- `variant_sequence`
- `variant_sequence_json`
- `variant_taxonomy_id`

### ChEMBLAssayParametersGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `assay_id`
- `assay_param_id`
- `comments`
- `content_hash`
- `entity_id`
- `parameter_relation`
- `parameter_type`
- `parameter_value`
- `qudt_ontology_version`
- `qudt_unit_iri`
- `qudt_unit_mapping_status`
- `qudt_units`
- `standard_relation`
- `standard_text_value`
- `standard_type`
- `standard_units`
- `standard_value`
- `text_value`
- `units`
- `uo_ontology_version`
- `uo_unit_iri`
- `uo_unit_mapping_status`
- `uo_units`

### ChEMBLCellLineGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `cell_description`
- `cell_id`
- `cell_name`
- `cell_source_organism`
- `cell_source_taxonomy_id`
- `cell_source_tissue`
- `cell_type`
- `cellosaurus_id`
- `cl_lincs_id`
- `clo_id`
- `content_hash`
- `efo_id`
- `entity_id`

### ChEMBLCompoundRecordGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `compound_key`
- `compound_name`
- `content_hash`
- `entity_id`
- `molecule_id`
- `publication_id`
- `record_id`
- `src_compound_id`
- `src_id`

### ChEMBLMoleculeGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `aromatic_ring_count`
- `atc_classifications`
- `availability_type`
- `black_box_warning`
- `canonical_smiles`
- `chirality`
- `content_hash`
- `cross_references`
- `dosed_ingredient`
- `entity_id`
- `first_approval`
- `first_in_class`
- `hba_count`
- `hbd_count`
- `heavy_atom_count`
- `helm_notation`
- `hierarchy_active_chembl_id`
- `hierarchy_child_chembl_id`
- `hierarchy_parent_chembl_id`
- `inchi_key`
- `inorganic_flag`
- `logp`
- `logp_method`
- `max_phase`
- `molecular_formula`
- `molecular_weight`
- `molecule_hierarchy`
- `molecule_id`
- `molecule_properties`
- `molecule_species`
- `molecule_structures`
- `molecule_synonyms`
- `molecule_type`
- `mw_freebase`
- `natural_product`
- `oral`
- `parenteral`
- `polar_surface_area`
- `polymer_flag`
- `pref_name`
- `prodrug`
- `qed_score`
- `ro3_pass`
- `ro5_violation_count`
- `rotatable_bond_count`
- `standard_inchi`
- `structure_type`
- `therapeutic_flag`
- `topical`
- `usan_stem`
- `usan_stem_definition`
- `usan_substem`
- `usan_year`
- `withdrawn_flag`

### ChEMBLProteinClassGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `class_level`
- `content_hash`
- `definition`
- `downgraded`
- `entity_id`
- `parent_id`
- `pref_name`
- `protein_class_desc`
- `protein_class_id`
- `replaced_by`
- `short_name`
- `sort_order`

### ChEMBLPublicationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `abstract`
- `author_keys`
- `authors`
- `chembl_release`
- `citations_made`
- `citations_received`
- `content_hash`
- `creation_date`
- `doi`
- `entity_id`
- `issue`
- `journal`
- `page_first`
- `page_last`
- `pmid`
- `publication_doi`
- `publication_id`
- `publication_pmc_id`
- `publication_pmid`
- `publication_type`
- `publication_year`
- `src_id`
- `title`
- `volume`

### ChEMBLPublicationSimilarityGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `avg_tani`
- `content_hash`
- `doc_1`
- `doc_2`
- `entity_id`
- `max_tani`
- `mol_tani`
- `publication_id1`
- `publication_id2`
- `pubmed_id1`
- `pubmed_id2`
- `sim_id`
- `tid_tani`

### ChEMBLPublicationTermGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `content_hash`
- `entity_id`
- `mesh_id`
- `publication_id`
- `qualifier`
- `term`
- `term_type`

### ChEMBLSubcellularFractionGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `assay_count`
- `content_hash`
- `entity_id`
- `example_assay_id`
- `subcellular_fraction`

### ChEMBLTargetComponentGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `accession`
- `component_id`
- `component_type`
- `content_hash`
- `description`
- `entity_id`
- `organism`
- `protein_classification_id`
- `protein_classification_ids`
- `protein_classifications`
- `target_component_synonyms`
- `target_component_xrefs`
- `taxonomy_id`

### ChEMBLTargetGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `component_accessions`
- `component_descriptions`
- `component_ids`
- `component_relationships`
- `component_types`
- `content_hash`
- `cross_references`
- `description`
- `entity_id`
- `organism`
- `organism_class`
- `pref_name`
- `primary_component_id`
- `species_group_flag`
- `target_component_synonyms`
- `target_components`
- `target_ec_numbers`
- `target_gene_synonyms`
- `target_id`
- `target_protein_synonyms`
- `target_type`
- `target_xref_go_component`
- `target_xref_go_function`
- `target_xref_go_process`
- `target_xref_hgnc_ids`
- `target_xref_pdb_ids`
- `target_xref_reactome_ids`
- `target_xref_uniprot_ids`
- `taxonomy_id`

### ChEMBLTargetProteinClassificationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `canonical_l1`
- `chembl_api_version`
- `chembl_release`
- `classification_status`
- `component_id`
- `content_hash`
- `dataset_version`
- `depth`
- `entity_id`
- `is_leaf`
- `l1_counts_for_target_type`
- `l1_desc`
- `l1_id`
- `l1_mapping_version`
- `l1_name`
- `l1_normalization_notes`
- `l1_normalization_status`
- `l2_desc`
- `l2_id`
- `l2_name`
- `l3_desc`
- `l3_id`
- `l3_name`
- `l4_desc`
- `l4_id`
- `l4_name`
- `l5_desc`
- `l5_id`
- `l5_name`
- `leaf_id`
- `path_ids`
- `path_labels`
- `path_names`
- `protein_class_snapshot_row_count`
- `root_id`
- `source_manifest_status`
- `source_snapshot_fingerprint`
- `source_url`
- `target_component_snapshot_row_count`
- `target_id`
- `target_snapshot_row_count`
- `target_type_rule_version`

### ChEMBLTissueGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `bto_id`
- `caloha_id`
- `content_hash`
- `efo_id`
- `entity_id`
- `pref_name`
- `tissue_id`
- `uberon_id`

### CompositeActivityGoldSchema

- `_dq_error`
- `_dq_warn`
- `_enrichment_status`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `_source_providers`
- `activity_id`
- `assay_id`
- `canonical_smiles`
- `entity_id`
- `molecule_id`
- `publication_id`
- `record_id`
- `relation`
- `src_id`
- `target_id`
- `taxonomy_id`
- `type`
- `value`

### CompositeAssayGoldSchema

- `_dq_error`
- `_dq_warn`
- `_enrichment_status`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `_source_providers`
- `assay_id`
- `cell_type`
- `clo_id`
- `description`
- `entity_id`
- `publication_id`
- `score`
- `src_id`
- `target_id`

### CompositeMoleculeGoldSchema

- `_dq_error`
- `_dq_warn`
- `_enrichment_status`
- `_index`
- `_source`
- `_source_providers`
- `canonical_smiles`
- `entity_id`
- `inchi_key`
- `molecule_id`
- `standardized_inchi_key`
- `structure_parent_key`

### CompositePublicationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_enrichment_status`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `_source_providers`
- `doi`
- `entity_id`
- `pmc_id`
- `pmid`
- `publication_id`
- `src_id`
- `title`

### CompositeTargetGoldSchema

- `_dq_error`
- `_dq_warn`
- `_enrichment_status`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `_source_providers`
- `canonical_top_levels`
- `counted_top_levels`
- `description`
- `entity_id`
- `ignored_top_levels`
- `l1_mapping_version`
- `major_family`
- `major_family_rule_version`
- `multifunctional_origin`
- `primary_top_level`
- `protein_classifications`
- `target_id`
- `target_protein_class_desc_L1`
- `target_protein_class_desc_L2`
- `target_protein_class_desc_L3`
- `target_protein_class_desc_L4`
- `target_protein_class_desc_L5`
- `target_protein_class_id_L1`
- `target_protein_class_id_L2`
- `target_protein_class_id_L3`
- `target_protein_class_id_L4`
- `target_protein_class_id_L5`
- `target_protein_class_name_L1`
- `target_protein_class_name_L2`
- `target_protein_class_name_L3`
- `target_protein_class_name_L4`
- `target_protein_class_name_L5`
- `target_protein_class_type`
- `target_type_reason_code`
- `target_type_rule_version`
- `taxonomy_id`
- `top_level_count`
- `uniprot_accession`

### CrossRefPublicationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `abstract`
- `affiliation_list`
- `alternative_id`
- `author_details`
- `author_details_canonical_json`
- `author_details_raw_json`
- `author_keys`
- `author_orcids`
- `authors`
- `citations_made`
- `citations_received`
- `content_domain_crossmark_restriction`
- `content_domain_domains`
- `content_hash`
- `doi`
- `entity_id`
- `issn`
- `issn_electronic`
- `issn_list`
- `issn_print`
- `issue`
- `journal`
- `journal_name_short`
- `language`
- `license_url`
- `page_first`
- `page_last`
- `pmc_id`
- `pmid`
- `publication_class`
- `publication_date`
- `publication_subclass`
- `publication_type`
- `publication_type_unified`
- `publication_year`
- `published`
- `published_online`
- `published_print`
- `publisher`
- `references`
- `references_canonical_json`
- `references_raw_json`
- `subject_keywords`
- `title`
- `volume`

### OpenAlexPublicationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `abstract`
- `affiliation_list`
- `author_keys`
- `author_openalex_ids`
- `author_orcids`
- `authors`
- `citations_made`
- `citations_received`
- `content_hash`
- `doi`
- `entity_id`
- `fwci`
- `grants`
- `grants_canonical_json`
- `grants_raw_json`
- `institution_country_codes`
- `institution_ids`
- `is_oa`
- `is_retracted`
- `issn`
- `issn_list`
- `issue`
- `journal`
- `language`
- `mag_id`
- `oa_status`
- `openalex_id`
- `page_first`
- `page_last`
- `pmc_id`
- `pmid`
- `primary_topic`
- `primary_topic_canonical_json`
- `primary_topic_raw_json`
- `publication_class`
- `publication_date`
- `publication_subclass`
- `publication_type`
- `publication_type_unified`
- `publication_year`
- `publisher`
- `ror_ids`
- `subject_keywords`
- `subject_mesh`
- `subject_topics`
- `title`
- `volume`

### PubChemCompoundGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `canonical_smiles`
- `chemical_standardization_policy_version`
- `chemical_standardization_status`
- `chemical_standardization_warnings`
- `complexity`
- `conformer_count_3d`
- `conformer_rmsd_3d`
- `content_hash`
- `effective_rotor_count_3d`
- `entity_id`
- `exact_mass`
- `feature_acceptor_count_3d`
- `feature_anion_count_3d`
- `feature_cation_count_3d`
- `feature_count_3d`
- `feature_donor_count_3d`
- `feature_hydrophobe_count_3d`
- `feature_ring_count_3d`
- `inchi`
- `inchi_key`
- `isomeric_smiles`
- `iupac_name`
- `molecular_formula`
- `molecular_weight`
- `molecule_id`
- `monoisotopic_mass`
- `standardized_canonical_smiles`
- `standardized_inchi`
- `standardized_inchi_key`
- `standardized_isomeric_smiles`
- `structure_parent_key`
- `tpsa`
- `x_steric_quadrupole_3d`
- `xlogp`
- `y_steric_quadrupole_3d`
- `z_steric_quadrupole_3d`

### PubMedPublicationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `abstract`
- `abstract_structured`
- `affiliation_list`
- `affiliation_structured`
- `affiliation_structured_canonical_json`
- `affiliation_structured_raw_json`
- `author_count`
- `author_keys`
- `authors`
- `authors_with_affiliations`
- `authors_with_affiliations_canonical_json`
- `authors_with_affiliations_raw_json`
- `chemical_count`
- `chemicals`
- `citation_subset`
- `citations_made`
- `content_hash`
- `country`
- `databanks`
- `date_completed`
- `date_revised`
- `doi`
- `entity_id`
- `gene_symbols`
- `grant_count`
- `issn`
- `issn_list`
- `issue`
- `journal`
- `journal_iso_abbrev`
- `journal_issn_type`
- `journal_name_short`
- `keyword_count`
- `language`
- `medline_pgn`
- `mesh_heading_count`
- `mid`
- `nlm_unique_id`
- `page_first`
- `page_last`
- `page_range`
- `pii`
- `pmc_id`
- `pmid`
- `pub_date`
- `pub_day`
- `pub_month`
- `publication_class`
- `publication_date`
- `publication_status`
- `publication_subclass`
- `publication_type`
- `publication_type_unified`
- `publication_types`
- `publication_year`
- `publisher_id`
- `subject_keywords`
- `subject_mesh`
- `title`
- `volume`

### SemanticScholarPublicationGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- `abstract`
- `affiliation_list`
- `author_h_indices`
- `author_h_indices_canonical_json`
- `author_h_indices_raw_json`
- `author_keys`
- `author_orcids`
- `author_s2_ids`
- `authors`
- `citation_contexts`
- `citation_contexts_canonical_json`
- `citation_contexts_raw_json`
- `citations_made`
- `citations_received`
- `content_hash`
- `corpus_id`
- `dblp_id`
- `doi`
- `entity_id`
- `influential_citation_count`
- `is_oa`
- `issn`
- `issn_list`
- `issue`
- `journal`
- `oa_status`
- `open_access_url`
- `page_first`
- `page_last`
- `page_range`
- `paper_id`
- `pmc_id`
- `pmid`
- `publication_class`
- `publication_date`
- `publication_subclass`
- `publication_type`
- `publication_type_unified`
- `publication_types`
- `publication_types_canonical_json`
- `publication_types_raw_json`
- `publication_year`
- `subject_fields`
- `subject_fields_canonical_json`
- `subject_fields_raw_json`
- `title`
- `tldr`
- `volume`

### UniProtIDMappingGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `all_mappings`
- `annotation_score`
- `content_hash`
- `entity_id`
- `gene_primary`
- `mapping_status`
- `organism_common`
- `organism_scientific`
- `protein_name`
- `reviewed`
- `sequence_length`
- `sequence_mass`
- `target_id`
- `taxonomy_id`
- `uniprot_accession`
- `uniprot_entry_name`

### UniProtProteinGoldSchema

- `_dq_error`
- `_dq_warn`
- `_index`
- `accession`
- `acetylation`
- `active_sites`
- `activity_regulation`
- `alternative_products`
- `alternative_products_canonical_json`
- `alternative_products_raw_json`
- `annotation_score`
- `binding_sites`
- `biophysicochemical_properties`
- `biophysicochemical_properties_canonical_json`
- `biophysicochemical_properties_raw_json`
- `catalytic_activity`
- `caution`
- `cellular_component`
- `chembl_ids`
- `cofactors`
- `cofactors_canonical_json`
- `cofactors_raw_json`
- `content_hash`
- `cross_reference_count`
- `disease_involvement`
- `disulfide_bond`
- `domains`
- `drugbank_ids`
- `entity_id`
- `entry_created`
- `entry_modified`
- `entry_name`
- `entry_type`
- `entry_version`
- `feature_count`
- `features_canonical_json`
- `features_json`
- `features_raw_json`
- `flag`
- `function_comment`
- `gene_orf_names`
- `gene_primary`
- `gene_synonyms`
- `genus`
- `glycosylation`
- `go_terms`
- `guidetopharmacology_ids`
- `induction`
- `interpro_xrefs`
- `intramembrane`
- `isoform_count`
- `isoform_ids`
- `isoform_names`
- `isoform_synonyms`
- `keyword_count`
- `keywords`
- `lineage`
- `lipidation`
- `modified_residue`
- `molecular_function`
- `organism_common`
- `organism_scientific`
- `pathway`
- `pdb_xrefs`
- `pfam_xrefs`
- `pharmaceutical_use`
- `phosphorylation`
- `phylum`
- `propeptide`
- `protein_alternative_names`
- `protein_ec_numbers`
- `protein_existence`
- `protein_name`
- `protein_short_names`
- `publication_count`
- `reaction_ec_numbers`
- `reactions`
- `reactions_canonical_json`
- `reactions_raw_json`
- `reactome_xrefs`
- `reviewed`
- `secondary_accessions`
- `sequence`
- `sequence_checksum`
- `sequence_length`
- `sequence_mass`
- `sequence_modified`
- `signal_peptide`
- `similarity_comment`
- `subcellular_location`
- `subunit`
- `superkingdom`
- `taxonomy_id`
- `tissue_specificity`
- `topology`
- `transmembrane`
- `ubiquitination`

## Связанные документы

- [ADR-018: Gold Strict Validation](../../02-architecture/decisions/ADR-018-gold-strict-validation.md)
- [ADR-014: Deterministic Writes](../../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-002: Medallion Architecture](../../02-architecture/decisions/ADR-002-medallion-architecture.md)
- [Data Layers](../../02-architecture/data-layers.md)
- `docs/04-reference/contracts/gold/` (JSON contract exports directory)

______________________________________________________________________

## Сводная таблица контрактов

| Provider | Entity           | Primary Key      | Filters                          | Fields |
| -------- | ---------------- | ---------------- | -------------------------------- | ------ |
| ChEMBL   | activity         | `activity_id`    | 5 column + 1 range               | ~100   |
| ChEMBL   | molecule         | `molecule_id`    | 3 column                         | ~60    |
| ChEMBL   | assay            | `assay_id`       | 3 column                         | ~45    |
| ChEMBL   | target           | `target_id`      | 1 col + list filters             | ~25    |
| ChEMBL   | target_component | `component_id`   | 1 column                         | ~13    |
| ChEMBL   | publication      | `publication_id` | required + enum/range validation | ~17    |
| ChEMBL   | compound_record  | `record_id`      | required only                    | ~8     |
| ChEMBL   | cell_line        | `cell_id`        | required only                    | ~12    |
| PubChem  | compound         | `molecule_id`    | required only                    | ~10    |
| UniProt  | protein          | `accession`      | 1 column                         | ~8     |
| PubMed   | publication      | `pmid`           | required only                    | ~24    |
