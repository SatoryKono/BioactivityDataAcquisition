# Docs↔Cfg↔Code Sync Report

*Generated: 2026-02-17 | BioETL unified sync workflow*

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Providers analyzed** | 7 (chembl, crossref, openalex, pubchem, pubmed, semanticscholar, uniprot) |
| **Entity pipelines** | 22 total |
| **Xwalk CSVs generated** | 21 (all entities) |
| **Total fields mapped** | ~550+ |
| **Critical PK mismatches** | 3 (pubchem/compound, uniprot/idmapping, chembl/tissue Gold) |
| **PK mismatches fixed** | 2/3 (pubchem + uniprot docs updated; tissue Gold pending code fix) |
| **VCR cassettes inventoried** | 63 |
| **VCR gaps identified** | 8+ entities missing integration tests |

---

## 1. Crosswalk Coverage Matrix

### 1.1. ChEMBL (14 entities)

| Entity | Fields | PK Match | Doc Spec | Silver Schema | Gold Schema | Issues |
|--------|--------|----------|----------|---------------|-------------|--------|
| activity | 55 | YES | YES | YES | YES | 2 MISSING_DOC+GOLD (manual_curation_flag, original_activity_id); 3 MISSING_CODE (publication_doi/pmid/pmc_id — enrichment fields) |
| assay | 37 | YES | YES | YES | YES | Clean |
| assay_parameters | 13 | YES | YES | YES | YES | Clean |
| cell_line | 11 | YES | YES | YES | YES | 2 MISSING_DOC+GOLD (cell_type, clo_id) |
| compound_record | 7 | YES | YES | YES | YES | Clean; no dedicated entity DTO |
| molecule | 53 | YES | YES | YES | YES | Clean; heavy RENAME/NESTED mappings |
| protein_class | 10 | YES | YES | YES | YES | Clean |
| publication | 21 | YES | YES | MISSING | YES | No chembl-specific Silver schema (uses PublicationBaseSchema) |
| publication_similarity | 9 | YES | YES | YES | YES | Clean |
| publication_term | 5 | YES | YES | YES | YES | Clean; PK = entity_id (SHA256 composite) |
| subcellular_fraction | 3 | YES | YES | MISSING | YES | No Silver schema file; no dedicated entity DTO |
| target | 17 | YES | YES | YES | YES | component_descriptions in Silver but not Gold (intentional) |
| target_component | 11 | YES | YES | YES | YES | Clean |
| **tissue** | **7** | **YES (cfg/transformer)** | **MISSING** | **MISSING** | **PK_MISMATCH** | Gold uses `tissue_chembl_id`, transformer uses `tissue_id`. No doc spec. No Silver schema. |

### 1.2. Publication Providers (4 entities)

| Provider | Entity | Fields | PK | PK Match | Issues |
|----------|--------|--------|----|----------|--------|
| crossref | publication | 35 | `doi` | YES | 6 MISSING_TRANSFORMER (content_domain_*, issn_print/electronic, published_print/online) |
| openalex | publication | 37 | `openalex_id` | YES | ~15 MISSING_DOC (institution/author IDs, grants, fwci, etc.) |
| pubmed | publication | 53 | `pmid` | YES | ~35 MISSING_DOC (largest provider, many derived/nested fields) |
| semanticscholar | publication | 33 | `paper_id` | YES | ~12 MISSING_DOC (dblp_id, author_s2_ids, citation_contexts, etc.) |

### 1.3. PubChem + UniProt (3 entities)

| Provider | Entity | Fields | PK | PK Match | Issues |
|----------|--------|--------|----|----------|--------|
| **pubchem** | **compound** | **40** | **molecule_id** | **PK_MISMATCH (fixed)** | Doc spec said `cid`, code uses `molecule_id`. 12 undocumented 3D fields. 25+ Silver-only fields (by design). |
| uniprot | protein | 82 | `accession` | YES | ~50 MISSING_DOC. Dead fields: `publication_count`, `pharmaceutical_use` (never populated). |
| **uniprot** | **idmapping** | **14** | **target_id** | **PK_MISMATCH (fixed)** | Doc spec said `target_chembl_id`, code uses `target_id`. 6 undocumented fields. |

---

## 2. PK Mismatch Details

### 2.1. FIXED: pubchem/compound

| Layer | Before | After |
|-------|--------|-------|
| Doc spec §4.1 | `cid` | `molecule_id` |
| Doc spec §5.1 (Pandera) | `cid` | `molecule_id` |
| Doc spec §6 (Cross-Provider) | `cid` | `molecule_id` |
| Doc spec §7 (Pipeline Config) | `cid` | `molecule_id` |

**Commit:** `8d3c438`

### 2.2. FIXED: uniprot/idmapping

| Layer | Before | After |
|-------|--------|-------|
| Doc spec PK | `target_chembl_id` | `target_id` |
| Doc spec field names | Various API names | Code-aligned names |

**Commit:** `8d3c438`

### 2.3. OPEN: chembl/tissue (Gold schema)

| Layer | Current Value | Expected |
|-------|---------------|----------|
| Pipeline config | `tissue_id` | OK |
| Transformer | `tissue_id` | OK |
| **Gold schema** | **`tissue_chembl_id`** | Should be `tissue_id` |

**Action required:** Fix `src/bioetl/domain/contracts/gold/chembl.py` — rename `tissue_chembl_id` → `tissue_id` in `ChEMBLTissueGoldSchema`.

---

## 3. Cross-Cutting Findings

### 3.1. Schema Config Files (cfg_schema)

**ALL** `configs/schemas/{provider}/{entity}.yaml` files contain only `column_groups: []`. This makes the `cfg_schema` column EMPTY for every field across all 22 entities. Either:
- These configs are intentionally unused (remove or document as deprecated)
- They need to be populated with actual column definitions

### 3.2. Documentation Gaps

| Severity | Count | Description |
|----------|-------|-------------|
| MISSING_DOC (no spec file) | 1 | chembl/tissue |
| MISSING_DOC (fields) | ~120+ | Fields present in code but undocumented in spec |
| MISSING_TRANSFORMER | ~10 | Fields defined in entity but not populated by transformer |

### 3.3. Gold vs Silver Intentional Differences

Gold schemas are curated subsets. Fields in Silver but not Gold are intentional omissions, **not** bugs. Examples:
- `component_descriptions` (chembl/target) — in Silver only
- 25+ 3D properties (pubchem/compound) — in Silver only
- Various intermediate/raw fields across providers

---

## 4. Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| **Xwalk CSVs** (21 files) | `docs/04-reference/pipelines/{provider}/{entity}-xwalk.csv` | Committed |
| **PK-fix: pubchem spec** | `docs/04-reference/pipelines/pubchem/01-compound-spec.md` | Committed |
| **PK-fix: uniprot/idmapping spec** | `docs/04-reference/pipelines/uniprot/02-idmapping-spec.md` | Committed |
| **Endpoint validation checklist** | `docs/05-operations/verification/endpoint-validation-checklist.md` | Committed |
| **VCR test tasks** | `docs/05-operations/verification/vcr-test-tasks.md` | Committed |
| **This sync report** | `docs/05-operations/verification/sync-report-2026-02-17.md` | This file |

---

## 5. Recommended Follow-up Actions

### Priority: Critical

1. **Fix tissue Gold schema PK** — `tissue_chembl_id` → `tissue_id` in `ChEMBLTissueGoldSchema`
2. **Create tissue doc spec** — No spec file exists for chembl/tissue

### Priority: High

3. **Address MISSING_TRANSFORMER fields in crossref** — `content_domain_*`, `issn_print/electronic`, `published_print/online` defined in entity but not set by transformer
4. **Remove dead fields in uniprot/protein** — `publication_count` and `pharmaceutical_use` never populated
5. **VCR test gaps** — Create integration tests for 8 ChEMBL entities, pubchem, crossref

### Priority: Medium

6. **Document ~120 MISSING_DOC fields** across all providers
7. **Resolve cfg_schema emptiness** — Decide whether to populate or deprecate
8. **Create Silver schema for tissue, subcellular_fraction** — Currently MISSING

### Priority: Low

9. **Add Silver schema for chembl/publication** — Currently uses shared PublicationBaseSchema
10. **Verify 3 potential orphan VCR cassettes** at root level

---

## 6. Xwalk Column Legend

| Column | Description |
|--------|-------------|
| `field` | Canonical field name in Silver/Gold layer |
| `doc_spec` | Reference section in doc spec (e.g., §3.2, S2.1) |
| `cfg_pipeline` | Present in pipeline YAML config |
| `cfg_schema` | Present in schema YAML config (all EMPTY) |
| `code_transformer` | File:line in transformer code |
| `code_entity` | File:line in domain entity dataclass |
| `code_silver_schema` | File:line in Silver Pandera schema |
| `code_gold_schema` | File:line in Gold Pandera schema |
| `json_type` | JSON/Python type |
| `nullable` | Whether field allows NULL |
| `primary_key` | Whether field is part of PK |

### Notes Vocabulary

| Tag | Meaning |
|-----|---------|
| OK | Field consistent across all layers |
| MISSING_DOC | Not in doc spec |
| MISSING_CODE | Not in transformer/entity |
| MISSING_GOLD | Not in Gold schema (may be intentional) |
| PK_MISMATCH | Primary key name differs between layers |
| RENAME | API field → code field name mapping |
| NESTED | Extracted from nested JSON structure |
| DENORM | Denormalized from related entity |
| DERIVED | Computed field, not direct API mapping |
| EMPTY | Config exists but has no content |
