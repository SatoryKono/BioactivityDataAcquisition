# Domain Objects
*Aligned with RULES.md v5.0*

## Обзор

Доменные объекты представляют бизнес-сущности системы BioETL. Каждый объект:
- Имеет **Entity ID** (Business Key) — стабильный идентификатор в реальном мире (§2.8)
- Имеет **Content Hash** — идентификатор конкретного состояния для дедупликации (§2.8.1)
- Содержит обязательные мета-поля для Backfill/Lineage (§2.4, §2.3)
- Проходит через Medallion layers: Bronze → Silver → Gold (§2.1)

---

## Обязательные Мета-поля (§2.4, §2.3)

Все доменные объекты наследуют базовые поля:

| Поле | Тип | Назначение | Правило |
|------|-----|------------|---------|
| `_run_id` | UUID | Идентификатор запуска пайплайна | §2.4 MUST |
| `_run_type` | Enum | `incremental` \| `backfill` \| `rebuild` | §2.4 MUST |
| `_source_batch_id` | UUID | FK на `sys.lineage_log` | §2.3 MUST |
| `_ingestion_ts` | Timestamp | Время загрузки (UTC) | §2.8.1 excluded from hash |
| `_dq_warn` | Boolean | Флаг предупреждения качества | §2.6 |

**Content Hash Exclusion (§2.8.1)**: Поля с префиксом `_` исключаются из расчёта `content_hash`.

---

## Activity

**Назначение**: Запись результата измерения биоактивности для Molecule в Assay.

### Entity ID vs Content Hash (§2.8)

| Тип ID | Поле | Стратегия |
|--------|------|-----------|
| **Entity ID** | `activity_id` | Из источника (`activity_chembl_id`) или composite key |
| **Content Hash** | `_content_hash` | `sha256(provider + canonical_json(data))` |

### Composite Business Key
```
hash_business_key = sha256(assay_id + molecule_id + target_id + standard_type + standard_value)
```

### Поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `activity_id` | String | No | Entity ID (Business Key) |
| `assay_id` | String | No | FK → Assay |
| `molecule_id` | String | No | FK → Molecule |
| `target_id` | String | Yes | FK → Target (nullable если не определена) |
| `standard_type` | String | No | Тип измерения (IC50, Ki, EC50) |
| `standard_value` | Float | Yes | Нормализованное значение |
| `standard_units` | String | Yes | Единицы (nM, μM) |
| `standard_relation` | String | Yes | Оператор (=, <, >) |
| `pchembl_value` | Float | Yes | -log10(activity) для сравнимости |
| `data_validity_comment` | String | Yes | DQ флаги из источника |
| `_content_hash` | String | No | §2.8.1 SHA256 для SCD Type 2 |

### Medallion Representation (§2.1)

| Layer | Формат | Валидация | Partition Key |
|-------|--------|-----------|---------------|
| Bronze | JSONL + zstd | Нет | `ingestion_date` |
| Silver | Delta Lake | Pandera (soft) | `year/month` |
| Gold | Delta Lake | Pandera (strict) | `target_id` или `date` |

---

## Assay

**Назначение**: Фиксирует условия биологического эксперимента.

### Entity ID

| Тип ID | Поле | Стратегия |
|--------|------|-----------|
| **Entity ID** | `assay_id` | Из источника (`assay_chembl_id`) |
| **Content Hash** | `_content_hash` | Для отслеживания изменений метаданных |

### Поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `assay_id` | String | No | Entity ID |
| `assay_type` | String | No | Binding, Functional, ADMET |
| `description` | String | Yes | Описание метода |
| `assay_organism` | String | Yes | Организм |
| `assay_strain` | String | Yes | Штамм |
| `assay_cell_type` | String | Yes | Тип клеток |
| `target_id` | String | Yes | FK → Target |
| `document_id` | String | Yes | FK → Publication |
| `src_id` | Integer | No | ID источника данных |
| `_content_hash` | String | No | SHA256 |

### Связи

- **Assay → Target**: M:N через mapping table или embedded list
- **Assay → Publication**: M:1 (один документ-источник)
- **Assay ← Activity**: 1:M (множество измерений)

---

## Target

**Назначение**: Биологическая мишень (белок, комплекс, организм).

### Entity ID

| Тип ID | Поле | Стратегия |
|--------|------|-----------|
| **Entity ID** | `target_id` | `target_chembl_id` или `uniprot_id` |
| **Content Hash** | `_content_hash` | Для отслеживания аннотаций |

### Поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `target_id` | String | No | Entity ID (ChEMBL или UniProt) |
| `target_type` | String | No | SINGLE PROTEIN, PROTEIN COMPLEX, ORGANISM |
| `pref_name` | String | Yes | Preferred name |
| `organism` | String | Yes | Таксономия |
| `tax_id` | Integer | Yes | NCBI Taxonomy ID |
| `uniprot_accessions` | List[String] | Yes | UniProt IDs |
| `gene_names` | List[String] | Yes | Gene symbols |
| `target_components` | List[String] | Yes | Компоненты комплекса |
| `_content_hash` | String | No | SHA256 |

### Cross-Source Mapping

| Источник | ID Field | Mapping Strategy |
|----------|----------|------------------|
| ChEMBL | `target_chembl_id` | Primary |
| UniProt | `uniprot_accession` | Enrichment |
| IUPHAR | `iuphar_id` | Classification |

---

## Molecule

**Назначение**: Тестируемое соединение (препарат, биологический агент).

### Entity ID

| Тип ID | Поле | Стратегия |
|--------|------|-----------|
| **Entity ID** | `molecule_id` | `molecule_chembl_id` или `pubchem_cid` |
| **Structural Key** | `inchi_key` | Для дедупликации структур |
| **Content Hash** | `_content_hash` | Полное состояние записи |

### Поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `molecule_id` | String | No | Entity ID |
| `pref_name` | String | Yes | Preferred name |
| `molecule_type` | String | No | Small molecule, Antibody, Protein |
| `max_phase` | Integer | Yes | Макс. фаза клинических испытаний |
| `canonical_smiles` | String | Yes | SMILES (§2.8.1: normalized) |
| `standard_inchi` | String | Yes | InChI |
| `standard_inchi_key` | String | Yes | InChI Key (для dedupe) |
| `molecular_formula` | String | Yes | Формула |
| `molecular_weight` | Float | Yes | MW |
| `parent_molecule_id` | String | Yes | FK → Molecule (parent) |
| `_content_hash` | String | No | SHA256 |

### Structure Normalization (§2.8.1)

```python
# SMILES нормализация для стабильного хэша
canonical_smiles = rdkit.Chem.MolToSmiles(mol, canonical=True)
```

---

## Publication

**Назначение**: Документ-источник данных (статья, патент).

### Entity ID

| Тип ID | Поле | Стратегия |
|--------|------|-----------|
| **Entity ID** | `document_id` | `document_chembl_id` или `doi` |
| **Content Hash** | `_content_hash` | Для отслеживания метаданных |

### Поля

| Поле | Тип | Nullable | Описание |
|------|-----|----------|----------|
| `document_id` | String | No | Entity ID |
| `doc_type` | String | No | PUBLICATION, PATENT, DATASET |
| `doi` | String | Yes | DOI |
| `pmid` | Integer | Yes | PubMed ID |
| `title` | String | Yes | Заголовок |
| `authors` | List[String] | Yes | Авторы |
| `journal` | String | Yes | Журнал |
| `year` | Integer | Yes | Год публикации |
| `volume` | String | Yes | Том |
| `first_page` | String | Yes | Первая страница |
| `abstract` | String | Yes | Аннотация |
| `_content_hash` | String | No | SHA256 |

### Cross-Source Enrichment

| Источник | Данные |
|----------|--------|
| PubMed | Metadata, Abstract, MeSH terms |
| CrossRef | DOI resolution, Citations |
| Semantic Scholar | Embeddings, Citation graph |
| OpenAlex | Concepts, Institutions |

---

## Связи между Объектами

```
┌─────────────┐     1:M      ┌─────────────┐
│ Publication │◄─────────────│    Assay    │
└─────────────┘              └──────┬──────┘
                                    │
                              M:N   │   1:M
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
             ┌──────────┐    ┌──────────┐    ┌──────────┐
             │  Target  │◄───│ Activity │───►│ Molecule │
             └──────────┘    └──────────┘    └──────────┘
                  ▲                               │
                  │         Parent/Child          │
                  └───────────────────────────────┘
```

### Cardinality

| Связь | Cardinality | Реализация |
|-------|-------------|------------|
| Assay → Target | M:N | `assay_target` mapping или embedded |
| Activity → Assay | M:1 | FK `assay_id` |
| Activity → Target | M:1 | FK `target_id` (nullable) |
| Activity → Molecule | M:1 | FK `molecule_id` |
| Molecule → Molecule | 1:1 | FK `parent_molecule_id` |
| Assay → Publication | M:1 | FK `document_id` |

---

## Quarantine Records (§2.6)

Записи, не прошедшие валидацию, направляются в Unified Quarantine:

```python
class QuarantineRecord:
    ingestion_ts: datetime      # Время инцидента
    pipeline: str               # chembl_activity
    error_code: str             # SCHEMA_VIOLATION, NULL_REQUIRED_FIELD
    payload: str                # Truncated to 64KB
    payload_hash: str           # Для дедупликации
    bronze_batch_id: UUID       # FK → lineage_log
    bronze_file_uri: str        # S3 path для replay
    dq_status: Literal["NEW", "IGNORED", "REPROCESSED"]
```

---

## Cross-Source Mapping

### Идентификаторы

| Entity | ChEMBL | PubChem | UniProt | IUPHAR |
|--------|--------|---------|---------|--------|
| Activity | `activity_id` | `aid` | — | — |
| Assay | `assay_chembl_id` | `aid` | — | — |
| Target | `target_chembl_id` | — | `accession` | `object_id` |
| Molecule | `molecule_chembl_id` | `cid` | — | `ligand_id` |
| Publication | `document_chembl_id` | — | — | — |

### Mapping Priority (§2.4)

При merge конфликтов:
1. `rebuild` > `backfill` > `incremental`
2. Более свежий `_ingestion_ts` при равном `_run_type`
3. Content Hash для SCD Type 2 версионирования
