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
| activity | 55 | YES | YES | YES | YES | 2 MISSING-DOC+GOLD (manual-curation-flag, original-activity-id); 3 MISSING-CODE (publication-doi/pmid/pmc-id — enrichment fields) |
| assay | 37 | YES | YES | YES | YES | Clean |
| assay-parameters | 13 | YES | YES | YES | YES | Clean |
| cell-line | 11 | YES | YES | YES | YES | 2 MISSING-DOC+GOLD (cell-type, clo-id) |
| compound-record | 7 | YES | YES | YES | YES | Clean; no dedicated entity DTO |
| molecule | 53 | YES | YES | YES | YES | Clean; heavy RENAME/NESTED mappings |
| protein-class | 10 | YES | YES | YES | YES | Clean |
| publication | 21 | YES | YES | MISSING | YES | No chembl-specific Silver schema (uses PublicationBaseSchema) |
| publication-similarity | 9 | YES | YES | YES | YES | Clean |
| publication-term | 5 | YES | YES | YES | YES | Clean; PK = entity-id (SHA256 composite) |
| subcellular-fraction | 3 | YES | YES | MISSING | YES | No Silver schema file; no dedicated entity DTO |
| target | 17 | YES | YES | YES | YES | component-descriptions in Silver but not Gold (intentional) |
| target-component | 11 | YES | YES | YES | YES | Clean |
| **tissue** | **7** | **YES (cfg/transformer)** | **MISSING** | **MISSING** | **PK-MISMATCH** | Gold uses `tissue-chembl-id`, transformer uses `tissue-id`. No doc spec. No Silver schema. |

### 1.2. Publication Providers (4 entities)

| Provider | Entity | Fields | PK | PK Match | Issues |
|----------|--------|--------|----|----------|--------|
| crossref | publication | 35 | `doi` | YES | 6 MISSING-TRANSFORMER (content-domain-*, issn-print/electronic, published-print/online) |
| openalex | publication | 37 | `openalex-id` | YES | ~15 MISSING-DOC (institution/author IDs, grants, fwci, etc.) |
| pubmed | publication | 53 | `pmid` | YES | ~35 MISSING-DOC (largest provider, many derived/nested fields) |
| semanticscholar | publication | 33 | `paper-id` | YES | ~12 MISSING-DOC (dblp-id, author-s2-ids, citation-contexts, etc.) |

### 1.3. PubChem + UniProt (3 entities)

| Provider | Entity | Fields | PK | PK Match | Issues |
|----------|--------|--------|----|----------|--------|
| **pubchem** | **compound** | **40** | **molecule-id** | **PK-MISMATCH (fixed)** | Doc spec said `cid`, code uses `molecule-id`. 12 undocumented 3D fields. 25+ Silver-only fields (by design). |
| uniprot | protein | 82 | `accession` | YES | ~50 MISSING-DOC. Dead fields: `publication-count`, `pharmaceutical-use` (never populated). |
| **uniprot** | **idmapping** | **14** | **target-id** | **PK-MISMATCH (fixed)** | Doc spec said `target-chembl-id`, code uses `target-id`. 6 undocumented fields. |

---

## 2. PK Mismatch Details

### 2.1. FIXED: pubchem/compound

| Layer | Before | After |
|-------|--------|-------|
| Doc spec §4.1 | `cid` | `molecule-id` |
| Doc spec §5.1 (Pandera) | `cid` | `molecule-id` |
| Doc spec §6 (Cross-Provider) | `cid` | `molecule-id` |
| Doc spec §7 (Pipeline Config) | `cid` | `molecule-id` |

**Commit:** `8d3c438`

### 2.2. FIXED: uniprot/idmapping

| Layer | Before | After |
|-------|--------|-------|
| Doc spec PK | `target-chembl-id` | `target-id` |
| Doc spec field names | Various API names | Code-aligned names |

**Commit:** `8d3c438`

### 2.3. OPEN: chembl/tissue (Gold schema)

| Layer | Current Value | Expected |
|-------|---------------|----------|
| Pipeline config | `tissue-id` | OK |
| Transformer | `tissue-id` | OK |
| **Gold schema** | **`tissue-chembl-id`** | Should be `tissue-id` |

**Action required:** Fix `src/bioetl/domain/contracts/gold/chembl.py` — rename `tissue-chembl-id` → `tissue-id` in `ChEMBLTissueGoldSchema`.

---

## 3. Cross-Cutting Findings

### 3.1. Schema Config Files (cfg-schema)

**ALL** `configs/entities/{provider}/{entity}.yaml` files contain only `column-groups: []`. This makes the `cfg-schema` column EMPTY for every field across all 22 entities. Either:
- These configs are intentionally unused (remove or document as deprecated)
- They need to be populated with actual column definitions

### 3.2. Documentation Gaps

| Severity | Count | Description |
|----------|-------|-------------|
| MISSING-DOC (no spec file) | 1 | chembl/tissue |
| MISSING-DOC (fields) | ~120+ | Fields present in code but undocumented in spec |
| MISSING-TRANSFORMER | ~10 | Fields defined in entity but not populated by transformer |

### 3.3. Gold vs Silver Intentional Differences

Gold schemas are curated subsets. Fields in Silver but not Gold are intentional omissions, **not** bugs. Examples:
- `component-descriptions` (chembl/target) — in Silver only
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

1. **Fix tissue Gold schema PK** — `tissue-chembl-id` → `tissue-id` in `ChEMBLTissueGoldSchema`
2. **Create tissue doc spec** — No spec file exists for chembl/tissue

### Priority: High

3. **Address MISSING-TRANSFORMER fields in crossref** — `content-domain-*`, `issn-print/electronic`, `published-print/online` defined in entity but not set by transformer
4. **Remove dead fields in uniprot/protein** — `publication-count` and `pharmaceutical-use` never populated
5. **VCR test gaps** — Create integration tests for 8 ChEMBL entities, pubchem, crossref

### Priority: Medium

6. **Document ~120 MISSING-DOC fields** across all providers
7. **Resolve cfg-schema emptiness** — Decide whether to populate or deprecate
8. **Create Silver schema for tissue, subcellular-fraction** — Currently MISSING

### Priority: Low

9. **Add Silver schema for chembl/publication** — Currently uses shared PublicationBaseSchema
10. **Verify 3 potential orphan VCR cassettes** at root level

---

## 6. Xwalk Column Legend

| Column | Description |
|--------|-------------|
| `field` | Canonical field name in Silver/Gold layer |
| `doc-spec` | Reference section in doc spec (e.g., §3.2, S2.1) |
| `cfg-pipeline` | Present in pipeline YAML config |
| `cfg-schema` | Present in schema YAML config (all EMPTY) |
| `code-transformer` | File:line in transformer code |
| `code-entity` | File:line in domain entity dataclass |
| `code-silver-schema` | File:line in Silver Pandera schema |
| `code-gold-schema` | File:line in Gold Pandera schema |
| `json-type` | JSON/Python type |
| `nullable` | Whether field allows NULL |
| `primary-key` | Whether field is part of PK |

### Notes Vocabulary

| Tag | Meaning |
|-----|---------|
| OK | Field consistent across all layers |
| MISSING-DOC | Not in doc spec |
| MISSING-CODE | Not in transformer/entity |
| MISSING-GOLD | Not in Gold schema (may be intentional) |
| PK-MISMATCH | Primary key name differs between layers |
| RENAME | API field → code field name mapping |
| NESTED | Extracted from nested JSON structure |
| DENORM | Denormalized from related entity |
| DERIVED | Computed field, not direct API mapping |
| EMPTY | Config exists but has no content |
