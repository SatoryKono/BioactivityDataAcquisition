# Consolidated Schema Audit Report

Date: 2026-02-18
Status: consolidated from 4 parallel codex branches

## Meta: Source Branch Inventory

| # | Branch | File | Lines | Focus |
|---|--------|------|------:|-------|
| 1 | `codex/conduct-data-schema-audit-for-pipelines` | `docs/99-archive/reports/audit-2026-02-18/schema-audit-report.md` | 1791 | Per-pipeline deep-dive (Bronze/Silver/Gold field tables) + issues + plan |
| 2 | `codex/conduct-data-schema-audit-for-pipelines-wkhju1` | `docs/audits/schema-audit-report-2026-02-18.md` | 354 | Compact overview: pipeline matrix, composite map, Silver snapshot, issues P1-P10, plan |
| 3 | `codex/conduct-data-schema-audit-for-pipelines-e8duku` | `docs/audits/pipeline-schema-audit-2026-02-18.md` | 2496 | Full per-pipeline audit identical in structure to branch 1, issues A-01..A-08, plan |
| 4 | `codex/conduct-data-schema-audit-for-pipelines-hqg4s2` | `docs/audits/schema-audit-2026-02-18.md` | 237 | Compact overview: matrix, Bronze/Silver/Gold summaries, issues P1-P10, plan, target arch |

### Cross-Branch Consistency Assessment

All 4 branches agree on the factual inventory:
- **21 ingestion pipelines** registered in `PIPELINE_CONFIGS` + **5 composite pipelines**.
- Pipeline matrix data (provider, entity, PK, Silver/Gold write modes, partition keys) is **identical** across all branches.
- Composite pipeline map (seed/enrichers/join strategy) is **consistent** between branches 2-4 (branch 1 lists composites inline in per-pipeline sections).
- Gold contract classes, Silver Pandera schemas, and DQ config paths are **consistent**.

**Structural differences** are in scope and granularity only:
- Branches 1 and 3 contain full per-pipeline field-level Silver/Gold tables (1791/2496 lines).
- Branches 2 and 4 are compact summaries (354/237 lines) with the same conclusions.
- Issue IDs differ in naming (numeric IDs vs A-01..A-08 vs P1-P10) but refer to the same problems.

---

## I. Pipeline Schema Matrix (verified)

### 1) Ingestion Pipelines (21)

| Pipeline | Provider | Entity | Primary Keys | Silver mode | Gold mode | Partition | Pandera Silver | Gold Contract |
|----------|----------|--------|:-------------|:------------|:----------|:----------|:---------------|:--------------|
| chembl_activity | chembl | activity | activity_id | merge | append | [] | ActivitySchema | ChEMBLActivityGoldSchema |
| chembl_assay | chembl | assay | assay_id | merge | scd2 | [assay_type] | AssaySchema | ChEMBLAssayGoldSchema |
| chembl_assay_parameters | chembl | assay_parameters | assay_param_id | merge | scd2 | [type] | AssayParametersSchema | ChEMBLAssayParametersGoldSchema |
| chembl_cell_line | chembl | cell_line | cell_id | merge | scd2 | [] | CellLineSchema | ChEMBLCellLineGoldSchema |
| chembl_compound_record | chembl | compound_record | record_id | merge | scd2 | [] | CompoundRecordSchema | ChEMBLCompoundRecordGoldSchema |
| chembl_molecule | chembl | molecule | molecule_id | merge | scd2 | [molecule_type] | MoleculeSchema | ChEMBLMoleculeGoldSchema |
| chembl_protein_class | chembl | protein_class | protein_class_id | merge | scd2 | [class_level] | ProteinClassificationSchema | ChEMBLProteinClassGoldSchema |
| chembl_publication | chembl | publication | publication_id | merge | scd2 | [] | ChemblPublicationSchema | ChEMBLDocumentGoldSchema |
| chembl_publication_similarity | chembl | publication_similarity | sim_id | merge | overwrite | [] | PublicationSimilaritySchema | ChEMBLDocumentSimilarityGoldSchema |
| chembl_publication_term | chembl | publication_term | entity_id | merge | overwrite | [term_type] | PublicationTermSchema | ChEMBLDocumentTermGoldSchema |
| chembl_subcellular_fraction | chembl | subcellular_fraction | entity_id | merge | scd2 | [] | **MISSING** | ChEMBLSubcellularFractionGoldSchema |
| chembl_target | chembl | target | target_id | merge | scd2 | [target_type] | TargetSchema | ChEMBLTargetGoldSchema |
| chembl_target_component | chembl | target_component | component_id | merge | scd2 | [organism] | TargetComponentSchema | ChEMBLTargetComponentGoldSchema |
| chembl_tissue | chembl | tissue | tissue_id | merge | scd2 | [] | **MISSING** | ChEMBLTissueGoldSchema |
| crossref_publication | crossref | publication | doi | merge | scd2 | [] | PublicationEnrichedSchema | CrossRefPublicationGoldSchema |
| openalex_publication | openalex | publication | openalex_id | merge | scd2 | [] | OpenAlexPublicationSchema | OpenAlexPublicationGoldSchema |
| pubchem_compound | pubchem | compound | molecule_id | merge | scd2 | [batch_date] | PubchemMoleculeSchema | PubChemCompoundGoldSchema |
| pubmed_publication | pubmed | publication | pmid | merge | scd2 | [] | PubMedPublicationSchema | PubMedPublicationGoldSchema |
| semanticscholar_publication | semanticscholar | publication | paper_id | merge | scd2 | [] | SemanticScholarPublicationSchema | SemanticScholarPublicationGoldSchema |
| uniprot_idmapping | uniprot | idmapping | target_id | merge | scd2 | [] | IDMappingSchema | UniProtIDMappingGoldSchema |
| uniprot_protein | uniprot | protein | accession | merge | scd2 | [organism] | UniprotTargetSchema | UniProtProteinGoldSchema |

### 2) Composite Pipelines (5)

| Composite | Seed | Enrichers | Join | Key Policy |
|-----------|------|-----------|------|------------|
| composite_activity | chembl_activity | chembl_compound_record | left_outer | (molecule_id, publication_id) |
| composite_assay | chembl_assay | chembl_cell_line, chembl_tissue | left_outer | assay-linked keys |
| composite_molecule | chembl_molecule | pubchem_compound | left_outer | molecular identifiers |
| composite_target | chembl_target | chembl_target_component | left_outer | target_id/component linkage |
| composite_publication | chembl_publication | crossref, openalex, pubmed, semanticscholar | left_outer (priority) | provider-qualified + canonical |

### 3) Silver Completeness Snapshot

| Pipeline | Silver fields | Pandera fields | Gold fields | Delta |
|----------|:-------------|:--------------|:-----------|:------|
| chembl_activity | 62 | 65 | 61 | Balanced |
| chembl_assay | 46 | 46 | 44 | Balanced |
| chembl_assay_parameters | 22 | 22 | 20 | Balanced |
| chembl_cell_line | 18 | 20 | 16 | Pandera stricter |
| chembl_compound_record | 16 | 16 | 14 | Balanced |
| chembl_molecule | 61 | 61 | 59 | Balanced |
| chembl_protein_class | 19 | 19 | 17 | Balanced |
| chembl_publication | 40 | 39 | 33 | Semantic reduction in Gold |
| chembl_publication_similarity | 18 | 18 | 16 | Balanced |
| chembl_publication_term | 14 | 14 | 12 | Balanced |
| chembl_subcellular_fraction | 12 | n/a | 10 | **Missing Pandera** |
| chembl_target | 27 | 27 | 24 | Balanced |
| chembl_target_component | 20 | 20 | 18 | Balanced |
| chembl_tissue | 15 | n/a | 11 | **Missing Pandera** |
| pubchem_compound | 35 | 49 | 17 | **Heavy contraction** |
| uniprot_protein | 59 | 91 | 35 | **Very wide semantic loss** |
| uniprot_idmapping | 23 | 23 | 22 | Balanced |
| pubmed_publication | 63 | 65 | 62 | Near 1:1 |
| crossref_publication | 51 | 49 | 44 | Moderate contraction |
| openalex_publication | 52 | 51 | 48 | Moderate contraction |
| semanticscholar_publication | 47 | 47 | 44 | Moderate contraction |

---

## II. Consolidated Issue Registry

Issues below are de-duplicated and merged from all 4 branches with cross-reference.

| ID | Severity | Pipeline(s) | Category | Problem | Branches |
|:---|:---------|:------------|:---------|:--------|:---------|
| **S-01** | **P1** | chembl_subcellular_fraction, chembl_tissue | Schema gap | No Pandera Silver schema in factory binding. Drift can pass unchecked to Delta. | 1,2,3,4 |
| **S-02** | **P1** | all | DQ naming mismatch | `_content_hash` in `configs/quality/_defaults.yaml` but Gold schemas use `content_hash` (no underscore). DQ rule may silently skip. | 2,4 |
| **S-03** | **P1** | publication pipelines | Schema duplication | Publication pipelines maintain duplicated semantic fields (doi/pmid/title/authors/journal/year) with different optionality and naming across providers. | 1,2,3,4 |
| **S-04** | **P1** | composite_* | Hidden coupling | Composite configs tightly coupled to upstream provider-specific field names. High drift surface. | 2,3,4 |
| **S-05** | **P1** | all publications | Content hash instability | High nested-payload drift increases accidental hash variability when canonicalization is incomplete. | 3,4 |
| **S-06** | **P2** | uniprot_protein | Over-denormalization | 91 Pandera fields vs 59 Silver physical vs 35 Gold. Very wide semantic loss in Gold contract. | 1,2,3,4 |
| **S-07** | **P2** | pubchem_compound | Over-denormalization | 35 Silver fields contracted to 17 Gold. Analysts lose physicochemical descriptor metrics. | 1,2,3,4 |
| **S-08** | **P2** | all | Type inconsistency | Systemic nullable-int → float coercion in Gold contracts for identifiers and flags. | 1,2,3,4 |
| **S-09** | **P2** | all publications | Weak primary key | PKs are provider-specific without unified publication identity strategy. Cross-provider dedup risk. | 2,3,4 |
| **S-10** | **P2** | multiple | Inconsistent naming | taxonomy_id vs target_taxonomy_id, document_* vs publication_* aliases across pipelines. | 1,3,4 |
| **S-11** | **P2** | partitioning | Inconsistent partition strategy | Mixed partition keys without common cardinality policy. Some high-card, some none. | 2,3,4 |
| **S-12** | **P2** | all | Metadata unification | `_source` field presence inconsistent across Silver/Pandera schemas. ADR-029 partially met. | 2,4 |
| **S-13** | **P2** | all | SCD2 inconsistency | Mixed Gold modes (append/overwrite/scd2) without explicit documented entity-class policy. | 2,3,4 |
| **S-14** | **P3** | composite_* | Overloaded Gold | Wide composite tables with provider-qualified duplicate columns. | 1 |

### Cross-Reference to Original Branch IDs

| Consolidated | Branch 1 | Branch 2 (wkhju1) | Branch 3 (e8duku) | Branch 4 (hqg4s2) |
|:-------------|:---------|:-------------------|:-------------------|:-------------------|
| S-01 | inline | P1, P2 | A-03 | P1, P2 |
| S-02 | — | P9 | — | P9 |
| S-03 | inline | P5 | A-01 | P5 |
| S-04 | — | — | A-05 | — |
| S-05 | — | P8 | A-04 | P8 |
| S-06 | inline | P3 | A-06 (indirect) | P3 |
| S-07 | inline | P4 | A-06 | P4 |
| S-08 | #1-16 | P6 | A-02 | P6 |
| S-09 | — | P7 | A-08 | P7 |
| S-10 | — | — | A-07 | — |
| S-11 | — | P10 | — | P10 |
| S-12 | — | — | — | P8 (partial) |
| S-13 | — | — | — | — (system-level) |
| S-14 | #18-22 | — | — | — |

---

## III. Consolidated Improvement Plan

### Phase 1: Immediate (Non-Breaking)

| ID | Action | Impact | ADR | Migration |
|:---|:-------|:-------|:----|:----------|
| F-01 | Add Pandera Silver schemas for `chembl_tissue` and `chembl_subcellular_fraction`; bind in factory | Drift control for 2 pipelines | No | Add classes + factory binding |
| F-02 | Fix DQ default field `_content_hash` → `content_hash` (or add alias) | Restore mandatory hash DQ check | No | Update defaults + smoke-test |
| F-03 | Normalize nullable-int fields documentation (where int→float is intentional per EXC-007) | BI clarity | No | Doc + contract comments |
| F-04 | Unify `_source` policy across all Silver schemas | Consistent lineage tracing | ADR addendum | Staged rollout with nullable add |

### Phase 2: Refactoring (Controlled Breaking)

| ID | Action | Impact | ADR | Migration |
|:---|:-------|:-------|:----|:----------|
| F-05 | Refactor publication Gold contracts into shared base + provider extensions | Reduce duplication and drift | Yes | Dual-write contracts vN/vN+1 |
| F-06 | Unify PK strategy (business key + provider namespace + optional global key) | Better cross-provider joinability | Yes | Backfill with bridge keys |
| F-07 | Simplify rename chains Silver→Gold (config-driven mapping registry) | Reduce hidden coupling | Optional | Incremental per provider |
| F-08 | Add Pandera soft→strict for tissue/subcellular_fraction | Progressive drift control | No | Activate soft then strict |

### Phase 3: Architectural (Breaking)

| ID | Action | Impact | ADR | Migration |
|:---|:-------|:-------|:----|:----------|
| F-09 | Redesign `uniprot_protein` into normalized tables (core + annotations + xrefs) | Schema manageability | Mandatory | Versioned datasets + views |
| F-10 | Fix hash policy: canonical exclusion registry + contract-level tests | Stable dedup/versioning | Mandatory | Rehash backfill + compat map |
| F-11 | Standardize SCD2 key template (business_key + valid_from + hash) | Consistent temporal behavior | Mandatory | Dual-run + reconciliation |
| F-12 | Decompose wide Gold/composite tables (PubChem/UniProt) | API stability, storage cost | Mandatory | Semantic adapters + phased cutover |
| F-13 | Restructure Silver publication tables: extract normalized sub-entities (authors, mesh, citations) | Reduce width and improve normalization | Mandatory | Parallel model + CDC backfill |

---

## IV. Target Schema Architecture (consensus from all branches)

### Bronze (standardized)
- JSONL envelope: `{provider, entity, payload, source_meta, ingest_meta}`.
- Payload retains original raw shape; `source_meta` mandatory.
- Drift captured as additive metadata, not silent field loss.

### Silver (unified contract)
- Mandatory system prefix: `entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id`, `_source`, `_ingestion_ts`, `_index`.
- Mandatory DQ suffix: `_dq_warn`, `_dq_error`.
- Every pipeline **must** have Pandera Silver schema bound in factory.
- Partition strategy template: `{none | low-card dimension | year/month}` with documented cardinality budget.

### Gold (strict API contracts)
- Versioned shared base contracts by domain family (publication, molecule, target, activity).
- Provider extensions only for truly provider-specific semantics.
- Compatibility policy: additive fields in minor versions; removals/renames only in major.

### Unified metadata policy
- One canonical field dictionary for hash/run/lineage.
- One DQ config naming dictionary shared across all rules.
- No prefixed variants unless layer-specific and explicit.

### Unified key strategy
- `entity_id` = provider-scoped stable key.
- `business_key` (optional global) for cross-provider resolution.
- SCD2 keys standardized and documented as contract invariant.

### Table structure template
1. **System columns** (fixed order)
2. **Core business columns** (shared domain contract)
3. **Provider extension columns** (namespaced)
4. **DQ columns** (fixed suffix)
5. Optional lineage extension block (composite pipelines)

---

## V. Branch Disposition Recommendation

| Branch | Recommendation | Reason |
|--------|---------------|--------|
| `codex/conduct-data-schema-audit-for-pipelines` | **Archive** | Superseded by this consolidation. Per-pipeline tables preserved in this report's references. |
| `codex/conduct-data-schema-audit-for-pipelines-wkhju1` | **Archive** | Compact summary; all findings captured here. |
| `codex/conduct-data-schema-audit-for-pipelines-e8duku` | **Archive** | Most detailed per-pipeline audit; field tables superseded. |
| `codex/conduct-data-schema-audit-for-pipelines-hqg4s2` | **Archive** | Compact summary with target architecture; merged into section IV. |

All 4 branches can be safely closed after this consolidated report is merged.

---

## Verification Sources

```
src/bioetl/composition/factories/pipeline_factories.py   — PIPELINE_CONFIGS registry (lines 214-389)
src/bioetl/domain/schemas/chembl/                         — Pandera Silver schemas (12 of 14 entities)
src/bioetl/domain/contracts/gold/                         — Gold contract schemas (23 classes in 5 files)
src/bioetl/infrastructure/schemas/silver.py               — PyArrow Silver schemas
configs/pipelines/                                        — 27 YAML pipeline configs
configs/quality/_defaults.yaml                            — DQ defaults (field: _content_hash at line 22)
configs/quality/entities/                                 — Per-entity DQ rules
```
