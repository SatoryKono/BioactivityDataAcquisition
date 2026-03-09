# Data Lineage

*Updated: 2026-03-09 | Aligned with RULES.md v5.23 | Version 1.0.0*

This document traces the path of data from external provider APIs through
BioETL's Bronze → Silver → Gold Medallion layers to final consumers.
It covers all 7 supported providers and their entity pipelines.

For field-level documentation see the [Data Dictionary](data-dictionary.md).
For publication-specific field lineage see the
[Publication Fields Reference](publication-fields-reference.md).

---

## Contents

1. [Medallion Architecture Overview](#1-medallion-architecture-overview)
2. [Lineage by Provider](#2-lineage-by-provider)
   - [ChEMBL](#21-chembl)
   - [UniProt](#22-uniprot)
   - [PubChem](#23-pubchem)
   - [PubMed](#24-pubmed)
   - [CrossRef](#25-crossref)
   - [OpenAlex](#26-openalex)
   - [Semantic Scholar](#27-semantic-scholar)
3. [Composite Pipelines](#3-composite-pipelines)
4. [System-Field Lineage](#4-system-field-lineage)
5. [Cross-Provider Identity Resolution](#5-cross-provider-identity-resolution)
6. [Downstream Consumers](#6-downstream-consumers)

---

## 1. Medallion Architecture Overview

BioETL uses a three-layer Medallion architecture (ADR-002):

```
External API  ──►  Bronze (raw)  ──►  Silver (normalised)  ──►  Gold (curated)
                   JSONL+zstd        Delta Lake                  Delta Lake
                   Immutable         UPSERT/MERGE                Strict validation
```

### Layer Properties

| Layer | Format | Write mode | Retention | Schema enforcement |
|-------|--------|-----------|-----------|-------------------|
| **Bronze** | JSONL + Zstandard | Append-only | 90 days | None (raw) |
| **Silver** | Delta Lake | UPSERT (merge on `entity_id`) | Indefinite | Pandera schema |
| **Gold** | Delta Lake | UPSERT / SCD-2 | Indefinite | Strict (fail on violation) |

### Storage Paths

```
data/output/
├── bronze/{provider}/{entity}/          ← raw API responses (.jsonl.zst)
├── silver/{provider}/{entity}/          ← normalised Delta tables
├── gold/{provider}/{entity}/            ← curated Delta tables
├── checkpoints/{pipeline_name}.json     ← run state
└── quarantine/{provider}/{entity}/      ← failed records
```

---

## 2. Lineage by Provider

### 2.1 ChEMBL

**Source:** ChEMBL REST API (EMBL-EBI) · `https://www.ebi.ac.uk/chembl/api/data/`
**Rate limit:** 3 req/sec (public)

#### Activity

```
ChEMBL API /activity
  └─► Bronze: data/output/bronze/chembl/activity/batch-*.jsonl.zst
        (raw activity records; all API fields preserved)
      └─► Silver: data/output/silver/chembl/activity/
            Transform: snake_case field names, numeric type coercion,
                       ligand efficiency calculation, FK resolution
            UPSERT on: entity_id (derived from activity_id)
            └─► Gold: data/output/gold/chembl/activity/
                  Validation: Pandera schema + DQ rules
                  Enriched with: molecule SMILES, target organism,
                                 publication DOI/PMID
```

**Key transformations:**
- Field rename: `activity_id` → `activity_id` (no-op; already snake_case)
- Type coercion: `standard_value` string → float
- Derived: `pchembl_value` = −log₁₀(IC50_molar) when `standard_units = nM`
- Denormalised: molecule SMILES from `/molecule/{id}`, target organism from `/target/{id}`

---

#### Assay

```
ChEMBL API /assay
  └─► Bronze: data/output/bronze/chembl/assay/
      └─► Silver: data/output/silver/chembl/assay/
            UPSERT on: entity_id (derived from assay_id)
            └─► Gold: data/output/gold/chembl/assay/
```

**Key transformations:**
- JSON expansion: `target_id` extracted from nested `target_chembl_id`
- Confidence score: integer (0–9) coerced from string

---

#### Molecule

```
ChEMBL API /molecule
  └─► Bronze: data/output/bronze/chembl/molecule/
      └─► Silver: data/output/silver/chembl/molecule/
            UPSERT on: entity_id (derived from molecule_id / chembl_id)
            └─► Gold: data/output/gold/chembl/molecule/
```

**Key transformations:**
- Structural properties: `molecule_properties` object unpacked to top-level fields
- Synonyms: nested `molecule_synonyms` array serialised to JSON
- Cross-references: nested `cross_references` array serialised to JSON

---

#### Target

```
ChEMBL API /target
  └─► Bronze: data/output/bronze/chembl/target/
      └─► Silver: data/output/silver/chembl/target/
            UPSERT on: entity_id (derived from target_id)
            └─► Gold: data/output/gold/chembl/target/
```

**Key transformations:**
- Nested arrays: `target_components`, `cross_references`, `protein_classifications`
  serialised as JSON columns
- UniProt accessions extracted from `target_components[].accession` (cross-provider key)

---

### 2.2 UniProt

**Source:** UniProt REST API · `https://rest.uniprot.org/`
**Rate limit:** 100 req/sec; API key optional

#### Protein

```
UniProt REST API /uniprotkb
  └─► Bronze: data/output/bronze/uniprot/protein/
        (full UniProt flat-file equivalent in JSON)
      └─► Silver: data/output/silver/uniprot/protein/
            Transform: nested objects flattened, sequence extracted,
                       GO terms / cross-refs / features serialised to JSON
            UPSERT on: entity_id (derived from accession)
            └─► Gold: data/output/gold/uniprot/protein/
```

**Key transformations:**
- `accession`: primary accession (first element of `accessions` array)
- `entry_type`: derived from `entryType` (reviewed/unreviewed)
- `go_terms`: `uniProtKBCrossReferences` filtered to `GO` database, serialised to JSON
- `features`: protein feature annotations serialised to JSON array

---

#### ID Mapping

```
UniProt ID Mapping API /idmapping
  └─► Bronze: data/output/bronze/uniprot/idmapping/
      └─► Silver: data/output/silver/uniprot/idmapping/
            Transform: one row per accession, all external IDs
                       collected into JSON columns
            UPSERT on: entity_id (derived from accession)
```

**Key transformations:**
- Multiple mapping records per accession grouped: `chembl_ids`, `pdb_ids`, etc.
- Enables cross-provider joins: UniProt ↔ ChEMBL, UniProt ↔ PDB

---

### 2.3 PubChem

**Source:** PubChem REST API (NCBI) · `https://pubchem.ncbi.nlm.nih.gov/rest/pug/`
**Rate limit:** 5 req/sec (public)

#### Compound

```
PubChem PUG REST API /compound
  └─► Bronze: data/output/bronze/pubchem/compound/
      └─► Silver: data/output/silver/pubchem/compound/
            Transform: JSON properties array pivoted to columns,
                       synonyms list serialised to JSON
            UPSERT on: entity_id (derived from cid)
            └─► Gold: data/output/gold/pubchem/compound/
```

**Key transformations:**
- `properties`: flat JSON object from PubChem's property API unpacked to columns
- `synonyms`: first N synonyms from the synonyms endpoint, serialised to JSON
- `inchi_key`: cross-provider join key with ChEMBL `standard_inchi_key`

---

### 2.4 PubMed

**Source:** NCBI E-utilities · `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
**Rate limit:** 3 req/sec (10 req/sec with NCBI API key)

#### Publication

```
NCBI Entrez EFetch API /efetch (XML → JSON)
  └─► Bronze: data/output/bronze/pubmed/publication/
      └─► Silver: data/output/silver/pubmed/publication/
            Transform: XML-derived nested structure flattened,
                       author list serialised to JSON,
                       MeSH terms extracted to JSON
            UPSERT on: entity_id (derived from pmid)
            └─► Gold: data/output/gold/pubmed/publication/
```

**Key transformations:**
- `pmid`: PubMed unique identifier (integer → string)
- `doi`: extracted from `ArticleIdList` where `IdType=doi`
- `authors`: `AuthorList` array serialised: `{last, first, initials, affiliation}`
- `mesh_terms`: `MeshHeadingList` serialised to JSON
- `publication_types`: `PublicationTypeList` serialised to JSON

---

### 2.5 CrossRef

**Source:** CrossRef REST API · `https://api.crossref.org/`
**Rate limit:** Polite pool (add `mailto:` header); ~50 req/sec

#### Publication

```
CrossRef REST API /works
  └─► Bronze: data/output/bronze/crossref/publication/
      └─► Silver: data/output/silver/crossref/publication/
            Transform: nested author/affiliation arrays serialised,
                       multi-value fields (subject, license) serialised
            UPSERT on: entity_id (derived from DOI)
            └─► Gold: data/output/gold/crossref/publication/
```

**Key transformations:**
- `DOI` → `doi` (lowercase normalisation)
- `author`: nested array with affiliation objects serialised to JSON
- `published-print`/`published-online` → `publication_date` (preferred: print)
- `abstract`: stripped of JATS XML markup
- `is-referenced-by-count` → `citation_count`

---

### 2.6 OpenAlex

**Source:** OpenAlex API · `https://api.openalex.org/`
**Rate limit:** ~10 req/sec (no key); email polite pool recommended

#### Publication

```
OpenAlex REST API /works
  └─► Bronze: data/output/bronze/openalex/publication/
      └─► Silver: data/output/silver/openalex/publication/
            Transform: concepts/topics serialised, authorships flattened,
                       open-access status extracted
            UPSERT on: entity_id (derived from openalex_id)
            └─► Gold: data/output/gold/openalex/publication/
```

**Key transformations:**
- `id` → `openalex_id` (strip prefix `https://openalex.org/`)
- `authorships`: nested array → JSON column with author name, ORCID, institution
- `concepts`: JSON array with `wikidata_id`, `display_name`, `score`
- `open_access.is_oa` → `is_open_access` (boolean)
- `pmid` extracted from `ids.pmid` (cross-provider join key)

---

### 2.7 Semantic Scholar

**Source:** Semantic Scholar Academic Graph API · `https://api.semanticscholar.org/`
**Rate limit:** 0.1 req/sec without key; 1.0 req/sec with API key

#### Publication

```
Semantic Scholar Graph API /paper
  └─► Bronze: data/output/bronze/semanticscholar/publication/
      └─► Silver: data/output/silver/semanticscholar/publication/
            Transform: author/field-of-study arrays serialised,
                       citation counts extracted
            UPSERT on: entity_id (derived from paper_id)
            └─► Gold: data/output/gold/semanticscholar/publication/
```

**Key transformations:**
- `paperId` → `paper_id` (camelCase → snake_case)
- `authors`: nested array → JSON with `authorId`, `name`
- `fieldsOfStudy`: list → JSON array
- `doi`, `pmid`: extracted from `externalIds` object (cross-provider join keys)
- `citationCount`, `referenceCount`: integers

---

## 3. Composite Pipelines

Composite pipelines merge Silver/Gold records from multiple providers into a
single unified entity (ADR-026).

```
Silver layer (multiple providers)
  └─► Composite merge logic (configs/composites/{entity}.yaml)
        - Deduplication on content_hash
        - Priority-ordered source selection
        - Field-level provenance annotation (_source field)
      └─► Gold: data/output/gold/composite/{entity}/
```

### Composite Entity Map

| Composite | Primary source | Secondary sources | Join key |
|-----------|---------------|-------------------|----------|
| `composite_publication` | ChEMBL | PubMed, CrossRef, OpenAlex, S2 | DOI, PMID |
| `composite_molecule` | ChEMBL | PubChem | InChI Key |
| `composite_target` | ChEMBL | UniProt | UniProt accession |
| `composite_activity` | ChEMBL | — | activity_id |
| `composite_assay` | ChEMBL | — | assay_id |

---

## 4. System-Field Lineage

System fields are injected by the pipeline framework and are **not** sourced from
provider APIs.

| Field | Set by | Value |
|-------|--------|-------|
| `entity_id` | `HashService` | SHA-256 of business primary key(s) |
| `content_hash` | `HashService` | SHA-256 of all business field values |
| `_run_id` | `PipelineRunner` | UUID generated at run start |
| `_run_type` | `PipelineRunner` | `full` / `incremental` / `backfill` from CLI |
| `_source_batch_id` | `BronzeWriter` | Basename of the Bronze batch file |
| `_ingestion_ts` | `SilverWriter` / `GoldWriter` | `datetime.utcnow()` at write time |
| `_index` | `BronzeWriter` | Sequential record index within the batch |

**`entity_id` stability guarantee:** The same business record from the same
provider always produces the same `entity_id` regardless of when it is
ingested. This enables idempotent upserts and stable downstream joins.

---

## 5. Cross-Provider Identity Resolution

To join records across providers, use the following identifier fields:

| Identity concept | ChEMBL | UniProt | PubChem | PubMed | CrossRef | OpenAlex | S2 |
|-----------------|--------|---------|---------|--------|----------|----------|----|
| Compound structure | `standard_inchi_key` | — | `inchi_key` | — | — | — | — |
| Protein/target | `target_component.accession` | `accession` | — | — | — | — | — |
| Publication DOI | `document.doi` | — | — | `doi` | `doi` | `doi` | `doi` |
| Publication PMID | `document.pubmed_id` | — | — | `pmid` | — | `pmid` | `pmid` |
| NCBI Taxonomy | `target_taxonomy_id` | `organism_taxonomy_id` | — | — | — | — | — |

### Resolution Strategy

1. **Exact match**: join on identical identifier values (e.g. DOI exact match)
2. **Normalisation**: lowercase DOIs, strip URL prefixes from OpenAlex IDs
3. **Composite key**: when no single ID matches, use (title, year, journal) fuzzy join
4. **Content hash**: identical `content_hash` values indicate semantic duplicates
   regardless of provider

---

## 6. Downstream Consumers

Gold-layer Delta tables are designed for consumption by analytics and ML systems.

| Consumer | Recommended format | Join strategy |
|----------|-------------------|---------------|
| **BI / Dashboards** | Delta Lake (native read via `deltalake` Python lib or Spark) | Entity IDs |
| **ML model training** | Parquet export (via `delta.to_pandas()` or `to_polars()`) | Content hash dedup |
| **REST API** | Delta Lake time-travel queries | `entity_id` lookup |
| **Data science notebooks** | Polars / pandas from Delta | Field-level filters |

### Time-Travel Queries

Delta Lake preserves all historical versions. To query data as of a specific run:

```python
from deltalake import DeltaTable

dt = DeltaTable("data/output/gold/chembl/activity")
# Query at specific version
df = dt.to_pandas(version=5)
# Query at specific timestamp
df = dt.to_pandas(timestamp="2026-01-15T00:00:00Z")
```

---

## Related Documents

- [Data Dictionary](data-dictionary.md) — Field-level documentation
- [Publication Fields Reference](publication-fields-reference.md) — Publication fields (191 fields)
- [Pipeline Catalog](pipelines/README.md) — All pipelines with specs
- [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md) — Delta Lake decision
- [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md) — Medallion Architecture
- [ADR-012](../02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md) — Storage contract
- [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md) — Deterministic writes
- [Local Storage Layout](../03-guides/local-storage-layout.md) — File system structure
