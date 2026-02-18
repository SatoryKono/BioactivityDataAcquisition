# BioETL Schema Audit (all ingestion pipelines)

Date: 2026-02-18
Scope: 21 ingestion pipelines registered in `PIPELINE_CONFIGS`.

## Method

- Pipeline registry, binding Silver/Pandera/Gold schemas: `src/bioetl/composition/factories/pipeline_factories.py`.
- Layer rules, drift/hash/validation policy: `docs/00-project/RULES.md`, ADR-018, ADR-027, ADR-029, ADR-034.
- Physical Silver schemas: `src/bioetl/infrastructure/schemas/silver.py`.
- Gold contracts: `src/bioetl/domain/contracts/gold/*.py`.
- Silver Pandera schemas: `src/bioetl/domain/schemas/**/*.py`.
- Pipeline PK/write/partition settings: `configs/pipelines/*/*.yaml`.
- DQ externalized rules: `configs/quality/entities/*/*.yaml` + `configs/quality/_defaults.yaml`.
- Content hash algorithm and metadata exclusions: `src/bioetl/domain/transformations.py`, `src/bioetl/domain/constants.py`, and BaseTransformer delegation.

______________________________________________________________________

## I. Карта схем пайплайна

### 1) Общая карта (Provider / Entity / PK / Write mode / Partition)

| Pipeline                      | Provider        | Entity                 | Primary keys     | Silver mode | Gold mode | Silver partition_by |
| ----------------------------- | --------------- | ---------------------- | ---------------- | ----------- | --------- | ------------------- |
| chembl_activity               | chembl          | activity               | activity_id      | merge       | append    | []                  |
| chembl_assay                  | chembl          | assay                  | assay_id         | merge       | scd2      | [assay_type]        |
| chembl_assay_parameters       | chembl          | assay_parameters       | assay_param_id   | merge       | scd2      | [type]              |
| chembl_cell_line              | chembl          | cell_line              | cell_id          | merge       | scd2      | []                  |
| chembl_compound_record        | chembl          | compound_record        | record_id        | merge       | scd2      | []                  |
| chembl_molecule               | chembl          | molecule               | molecule_id      | merge       | scd2      | [molecule_type]     |
| chembl_protein_class          | chembl          | protein_class          | protein_class_id | merge       | scd2      | [class_level]       |
| chembl_publication            | chembl          | publication            | publication_id   | merge       | scd2      | []                  |
| chembl_publication_similarity | chembl          | publication_similarity | sim_id           | merge       | overwrite | []                  |
| chembl_publication_term       | chembl          | publication_term       | entity_id        | merge       | overwrite | [term_type]         |
| chembl_subcellular_fraction   | chembl          | subcellular_fraction   | entity_id        | merge       | scd2      | []                  |
| chembl_target                 | chembl          | target                 | target_id        | merge       | scd2      | [target_type]       |
| chembl_target_component       | chembl          | target_component       | component_id     | merge       | scd2      | [organism]          |
| chembl_tissue                 | chembl          | tissue                 | tissue_id        | merge       | scd2      | []                  |
| pubchem_compound              | pubchem         | compound               | molecule_id      | merge       | scd2      | [batch_date]        |
| uniprot_protein               | uniprot         | protein                | accession        | merge       | scd2      | [organism]          |
| uniprot_idmapping             | uniprot         | idmapping              | target_id        | merge       | scd2      | []                  |
| pubmed_publication            | pubmed          | publication            | pmid             | merge       | scd2      | []                  |
| crossref_publication          | crossref        | publication            | doi              | merge       | scd2      | []                  |
| openalex_publication          | openalex        | publication            | openalex_id      | merge       | scd2      | []                  |
| semanticscholar_publication   | semanticscholar | publication            | paper_id         | merge       | scd2      | []                  |

### 2) Bronze layer (фактический JSON shape)

**Storage format**: JSONL (zstd), append-only by RULES Medallion.

**Metadata policy in Bronze/Silver lineage** (stable across pipelines):
`entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`, `_index`, and DQ flags `_dq_warn`/`_dq_error` in Silver.

**Provider-specific Bronze shape profile**:

- **ChEMBL**: dense flat JSON + nested blocks (`action_type`, `ligand_efficiency`, molecule hierarchy/properties), high rename/flatten pressure.
- **PubChem**: strongly numeric descriptor payload (many optional numeric metrics); nullable-int coercion risk.
- **UniProt**: highly nested annotations/features/xrefs arrays; strongest flattening pressure and widest semantic spread.
- **Publication providers (PubMed/CrossRef/OpenAlex/SemanticScholar/ChEMBL publication)**: semi-structured bibliographic records, mixed optionality, source-specific naming.

**Schema drift hotspots in Bronze**:

1. Nested object optional presence (ChEMBL/PubChem/UniProt).
1. Optional arrays/maps with unstable element shape (UniProt/publications).
1. Provider field evolution (publication metadata subsets differ across providers).

### 3) Silver schema (Pandera + Delta)

#### Silver completeness snapshot

| Pipeline                      | Silver fields | Pandera fields | Gold fields | Notes                                    |
| ----------------------------- | ------------: | -------------: | ----------: | ---------------------------------------- |
| chembl_activity               |            62 |             65 |          61 | Gold close to Silver, + metadata aliases |
| chembl_assay                  |            46 |             46 |          44 | Balanced                                 |
| chembl_assay_parameters       |            22 |             22 |          20 | Balanced                                 |
| chembl_cell_line              |            18 |             20 |          16 | Pandera stricter than physical schema    |
| chembl_compound_record        |            16 |             16 |          14 | Balanced                                 |
| chembl_molecule               |            61 |             61 |          59 | Balanced                                 |
| chembl_protein_class          |            19 |             19 |          17 | Balanced                                 |
| chembl_publication            |            40 |             39 |          33 | Clear semantic reduction in Gold         |
| chembl_publication_similarity |            18 |             18 |          16 | Overwrite Gold                           |
| chembl_publication_term       |            14 |             14 |          12 | Composite-key surrogate in practice      |
| chembl_subcellular_fraction   |            12 |            n/a |          10 | Missing dedicated Pandera Silver model   |
| chembl_target                 |            27 |             27 |          24 | Balanced                                 |
| chembl_target_component       |            20 |             20 |          18 | Balanced                                 |
| chembl_tissue                 |            15 |            n/a |          11 | Missing dedicated Pandera Silver model   |
| pubchem_compound              |            35 |             49 |          17 | Heavy contraction Silver→Gold            |
| uniprot_protein               |            59 |             91 |          35 | Very wide semantic loss Silver→Gold      |
| uniprot_idmapping             |            23 |             23 |          22 | Balanced                                 |
| pubmed_publication            |            63 |             65 |          62 | Near 1:1                                 |
| crossref_publication          |            51 |             49 |          44 | Moderate contraction                     |
| openalex_publication          |            52 |             51 |          48 | Moderate contraction                     |
| semanticscholar_publication   |            47 |             47 |          44 | Moderate contraction                     |

#### Silver engineering checks (cross-pipeline)

- **Type coercion**: deliberate int→float in contracts for nullable ints is used broadly (documented in contracts and RULES).
- **Nullable consistency**: mostly consistent, but large Pandera-vs-Delta gaps in `uniprot_protein` and `pubchem_compound` indicate over-flexible logical schemas.
- **DQ flags**: `_dq_warn`/`_dq_error` standardized in Silver, but Gold inclusion differs by contract.
- **Hash exclusions**: metadata excluded through `META_FIELDS` in domain hash generation.
- **Ordering policy**: Silver schemas follow prefix(system) → business → DQ suffix convention.
- **Drift tolerance**: Silver write mode `merge` + schema evolve default; risk of silent widening when Pandera is absent.
- **Merge key correctness**: key logic depends on pipeline primary_keys and entity_id; publication_term/subcellular_fraction rely on derived IDs.

### 4) Gold schema (контракты)

- **Contract strictness**: ADR-018 enforced by `strict = True` in Gold Pandera contracts.
- **Gold mode**: predominantly `scd2`; explicit exceptions: `chembl_activity` (`append`), `chembl_publication_similarity` and `chembl_publication_term` (`overwrite`).
- **Backward compatibility risk profile**:
  - Low: assay/target-like entities (small, stable taxonomies).
  - Medium: publication contracts (cross-provider harmonization pressure).
  - High: uniprot/pubchem due heavy field contraction and semantic flattening.

### 5) Domain ↔ Schema соответствие

- **Strong alignment** in most ChEMBL core entities and publication pipelines where mapper+contract are explicit.
- **Drift candidates**:
  - `chembl_subcellular_fraction`, `chembl_tissue`: no dedicated Pandera Silver model in factory binding.
  - `uniprot_protein`: logical schema significantly wider than Silver physical and much wider than Gold API.
  - `pubchem_compound`: many Silver descriptors omitted from Gold contract.
- **Single Source of Truth pressure** appears in publication normalization where similar fields are redefined across provider contracts.

______________________________________________________________________

## II. Архитектурные проблемы (по пайплайнам)

| ID  | Pipeline                                   | Категория                                    | Проблема                                                               | Риск                                            | Приоритет |
| --- | ------------------------------------------ | -------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------- | --------- |
| P1  | chembl_subcellular_fraction                | Schema duplication / Domain drift            | Нет Pandera Silver-модели в factory binding                            | Soft drift may pass to Delta                    | P1        |
| P2  | chembl_tissue                              | Schema duplication / Domain drift            | Нет Pandera Silver-модели в factory binding                            | Soft drift may pass to Delta                    | P1        |
| P3  | uniprot_protein                            | Over-denormalization / Overloaded Gold layer | 91 logical fields vs 59 Silver vs 35 Gold                              | Потеря семантики, нестабильный API контракт     | P1        |
| P4  | pubchem_compound                           | Over-denormalization                         | 35 Silver fields vs 17 Gold fields                                     | Аналитики теряют физико-химические метрики      | P1        |
| P5  | chembl_publication & publication providers | Inconsistent naming / Hidden coupling        | Разные поля для одной семантики (pmid/doi/issue/volume/classification) | Сложность унифицированных gold views            | P2        |
| P6  | all                                        | Nullable ambiguity                           | Массовый int→float nullable coercion в Gold                            | Риск неявных cast-ошибок и BI ambiguity         | P2        |
| P7  | all publications                           | Weak primary key                             | PK провайдер-специфичны, без unified publication identity strategy     | Дубликаты между провайдерами                    | P2        |
| P8  | all                                        | Content hash instability risk                | Exclusion set не включает `_source` (а field есть не везде)            | Потенциальная hash-нестабильность при источнике | P2        |
| P9  | all                                        | Inconsistent naming                          | `_content_hash` в global DQ defaults, но в схемах поле `content_hash`  | DQ-правило может не сработать                   | P1        |
| P10 | partitioning                               | Inconsistent partition strategy              | Разнородные partition keys без общей policy по cardinality             | Фрагментация/скью Delta tables                  | P2        |

______________________________________________________________________

## III. Общесистемные проблемы

1. **Повторяющиеся publication поля** во всех publication pipeline-контрактах, но с разной полнотой и optionality.
1. **Несогласованные типы**: особенно nullable-int через float coercion в Gold.
1. **Metadata унификация неполная**: `_source` присутствует не во всех Silver/Pandera; `content_hash` vs `_content_hash` mismatch в DQ defaults.
1. **Output Metadata unification (ADR-029)** в основном соблюдается по run/ingestion полям, но частично расходится по source lineage.
1. **Избыточная ширина**: `uniprot_protein` logical schema.
1. **Provider-qualified duplication pressure**: в publication harmonization много частично дублируемых полей.
1. **SCD2 consistency**: mixed Gold modes (append/overwrite/scd2) требуют явной, документированной политики по entity class.
1. **Partition strategy inconsistency**: часть таблиц без partition, часть — по полям с потенциально высокой кардинальностью.

______________________________________________________________________

## IV. План улучшений

### 1) Немедленные (Low Risk)

| Change                                                                              | Impact                                    | Breaking                                 | ADR                        | Migration                              |
| ----------------------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------- | -------------------------- | -------------------------------------- |
| Добавить Pandera Silver schemas для `chembl_tissue` и `chembl_subcellular_fraction` | Повышение drift контроля                  | Non-breaking                             | Нет (patch)                | Добавить классы + подключить в factory |
| Исправить DQ default field `_content_hash` → `content_hash`                         | Восстановление обязательной проверки hash | Non-breaking                             | Нет                        | Обновить defaults + smoke-test DQ      |
| Унифицировать `_source` policy во всех Silver schemas                               | Консистентная lineage трассировка         | Potentially breaking (if strict readers) | Да (короткий ADR addendum) | staged rollout with nullable add       |
| Нормализовать nullable policy doc (где int→float допустим)                          | Ясность для BI/API                        | Non-breaking                             | Нет                        | doc + contract comments                |

### 2) Среднесрочные (Refactoring)

| Change                                                                           | Impact                                  | Breaking             | ADR      | Migration                          |
| -------------------------------------------------------------------------------- | --------------------------------------- | -------------------- | -------- | ---------------------------------- |
| Пересборка publication Gold contracts в shared base + provider extensions        | Снижение дублирования и drift           | Potentially breaking | Да       | dual-write contracts vN/vN+1       |
| Унификация PK strategy (business key + provider namespace + optional global key) | Лучшая dedup/cross-provider joinability | Potentially breaking | Да       | backfill with bridge keys          |
| Упростить rename chains Silver→Gold (config-driven mappings registry)            | Меньше hidden coupling                  | Non-breaking         | Нет/опц. | incremental per provider           |
| Вынос повторяющихся полей в shared contracts (publication/molecule identity)     | SSOT усиление                           | Potentially breaking | Да       | compatibility aliases in API layer |

### 3) Архитектурные (Breaking)

| Change                                                                                          | Impact                                          | Breaking                     | ADR        | Migration                           |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------- | ---------- | ----------------------------------- |
| Перепроектировать `uniprot_protein` в нормализованный набор таблиц (core + annotations + xrefs) | Сильное улучшение управляемости схемы           | Breaking                     | Да (обяз.) | versioned datasets + semantic views |
| Изменить hash policy: зафиксировать canonical exclusion registry и contract-level tests         | Стабильная dedup/versioning                     | Breaking (historical hashes) | Да         | rehash backfill + compatibility map |
| Перейти на единый SCD2 ключевой шаблон (business_key + valid_from + hash)                       | Консистентный temporal behavior                 | Breaking                     | Да         | dual-run + reconciliation           |
| Декомпозировать чрезмерно широкие Gold таблицы (PubChem/UniProt)                                | Улучшение API стабильности и стоимости хранения | Breaking                     | Да         | medallion v2 namespaces             |

______________________________________________________________________

## V. Target Schema Architecture (целевая модель)

### Bronze (standardized)

- JSONL envelope: `{provider, entity, payload, source_meta, ingest_meta}`.
- Payload retains original raw shape; source_meta mandatory (`source_endpoint`, `api_version`, `retrieval_ts`).
- Drift captured as additive metadata (not silent field loss).

### Silver (unified contract)

- Mandatory system prefix: `entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id`, `_source`, `_ingestion_ts`, `_index`.
- Mandatory DQ suffix: `_dq_warn`, `_dq_error`.
- Every pipeline must have Pandera Silver schema bound in factory.
- Partition strategy template: `{none | low-card dimension | year/month}` with documented cardinality budget.

### Gold (strict API contracts)

- Versioned shared base contracts by domain family (publication, molecule, target, activity).
- Provider extensions only for truly provider-specific semantics.
- Compatibility policy: additive fields only in minor versions; removals/renames only major.

### Unified metadata policy

- One canonical field dictionary for hash/run/lineage.
- One DQ config naming dictionary shared across all rules (`content_hash`, no prefixed variants unless layer-specific and explicit).

### Unified key strategy

- `entity_id` = provider-scoped stable key.
- `business_key` (optional global) for cross-provider resolution.
- SCD2 keys standardized and documented as contract invariant.

### Типовая структура таблиц (для всех провайдеров)

1. **System columns** (fixed order).
1. **Core business columns** (shared domain contract).
1. **Provider extension columns** (namespaced or extension block).
1. **DQ columns** (fixed suffix).
1. Optional lineage extension block (composite pipelines).

______________________________________________________________________

## Критерии качества (status against target)

- Нет дублирования бизнес-полей: **частично выполнено**.
- Типы стабильны между слоями: **частично** (nullable-int coercion remains).
- Nullable policy консистентна: **частично**.
- Primary key семантически корректен: **выполнено для intra-provider, частично для cross-provider**.
- Content hash детерминирован: **выполнено**, но есть naming/policy risks.
- Нет hidden coupling: **частично** (rename chains and publication harmonization).
- Breaking изменения контролируемы: **частично** (versioning есть, но needs stricter contract governance).
- Schema drift управляем: **частично**, с явными gap для двух chembl pipelines без Pandera binding.
