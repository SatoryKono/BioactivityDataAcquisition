# BioETL ETL Semantic Audit

Generated: `2026-07-01`

## 1. Executive Summary

- Scope covers `26` active ETL pipeline surfaces across `configs/entities/**`, `configs/composites/**`, `configs/base/**`, domain contracts/schemas/mapping/normalization/validation registries, pipeline transformers, composite join/priority surfaces, and DQ / Gold-contract evidence.
- Current snapshot contains `290` semantic clusters and `3245` pairwise rows.
- Pairwise semantic status counts: `EXACT=2742`, `PARTIAL=68`, `WEAK=435`, `CONFLICTING=0`.
- Normalization status counts: `IDENTICAL=2358`, `COMPATIBLE=887`, `DIFFERENT=0`, `CONFLICTING=0`.
- Validation status counts: `IDENTICAL=2199`, `COMPATIBLE=1046`, `DIFFERENT=0`, `STRICTNESS_MISMATCH=0`.
- Typing status counts: `IDENTICAL=2581`, `COMPATIBLE=664`, `LOSSY=0`, `CONFLICTING=0`.
- Drift risk counts: `CRITICAL=0`, `HIGH=0`, `MEDIUM=0`, `LOW=3245`.
- Base-config semantic coverage increased from `286` to `340` surfaces compared with the reviewed `2026-05-22` snapshot.

Generated artifacts:

- Markdown report: `reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-07-01.md`
- Full pair matrix UTF-8 CSV: `reports/semantic_pipeline_audit/semantic_pair_matrix_2026-07-01.csv`
- Semantic cluster registry: `reports/semantic_pipeline_audit/semantic_cluster_registry_2026-07-01.json`
- Critical inconsistencies list: `reports/semantic_pipeline_audit/critical_inconsistencies_2026-07-01.md`
- Recommended canonical fields: `reports/semantic_pipeline_audit/recommended_canonical_fields_2026-07-01.csv`
- Base-config semantic coverage: `reports/semantic_pipeline_audit/base_config_semantic_coverage_2026-07-01.json`
- Residual backlog: `reports/semantic_pipeline_audit/semantic_residual_backlog_2026-07-01.md`

Audit verdict:

- No blocker-level architectural-semantic conflicts were confirmed.
- No ADR-018 / ADR-035 strict-validation or typing conflicts remain in the generated pair matrix.
- No ADR-026 composite join / lineage contradictions were confirmed; remaining `PARTIAL` clusters are reviewed owner-role distinctions, not runtime incompatibilities.
- The main operational change versus `2026-05-22` is inventory refinement plus contract-authority hardening: one weak cluster retired, one weak cluster contracted, base semantic coverage expanded, and composite assay now publishes explicit Gold typing evidence for `cell_type` and `clo_id`.

## 2. Semantic Cluster Catalog

### 2.1 Status distribution

| Status | Cluster Count | Interpretation |
| --- | ---: | --- |
| EXACT | 78 | Canonical business/system semantic identity with stable normalization and contract evidence |
| PARTIAL | 5 | Same concept family, but ownership/join/lineage semantics intentionally differ |
| WEAK | 207 | Same-name or reviewed lexical overlap only; not promoted to canonical cross-pipeline identity |
| CONFLICTING | 0 | No unresolved reviewed semantic collisions |

### 2.2 Canonical high-signal EXACT clusters

Identifier families:

- `chembl_assay_identifier` -> `assay_id`
- `chembl_molecule_identifier` -> `molecule_id`
- `pubchem_cid_identifier` -> `pubchem_cid`
- `pubmed_identifier` -> `pmid`
- `doi_identifier` -> `doi`

Publication canonical families:

- `publication_title` -> `title`
- `publication_abstract` -> `abstract`
- `publication_authors` -> `authors`
- `publication_publication_type` -> `publication_type`
- `publication_publication_type_unified` -> `publication_type_unified`
- `publication_publication_class` -> `publication_class`
- `publication_publication_subclass` -> `publication_subclass`
- `publication_publication_year` -> `publication_year`
- `publication_journal` -> `journal`
- `publication_page_first` -> `page_first`
- `publication_page_last` -> `page_last`
- `publication_subject_keywords` -> `subject_keywords`

System / deterministic identity families:

- `shared_entity_id`
- `shared_content_hash`
- `shared_run_id`
- `shared_run_type`
- `shared_source_batch_id`
- `shared_ingestion_ts`
- `shared_index`
- `shared_dq_error`
- `shared_dq_warn`

### 2.3 Reviewed PARTIAL clusters

| Cluster ID | Canonical Field | Why PARTIAL |
| --- | --- | --- |
| `canonical_smiles_identifier` | `canonical_smiles` | Provider-owned structure identifier vs composite join / lineage anchor |
| `chembl_target_identifier` | `target_chembl_id` / `target_id` | Target owner PK vs chained composite / activity lineage anchor |
| `inchi_key_identifier` | `inchi_key` | Provider-owned structure identifier vs composite primary join key |
| `pmc_identifier` | `pmc_id` | Optional publication identifier, not universal primary anchor |
| `uniprot_accession_identifier` | `accession` / `uniprot_accession` | UniProt PK vs component/reference anchor in ChEMBL/composite flows |

These clusters remain low risk because normalization, validation, and typing stay `IDENTICAL` or `COMPATIBLE`, while ownership and lineage semantics differ by design.

### 2.4 Weak-inventory change since `2026-05-22`

- Cluster `shared_pipeline_stages` disappeared from the current snapshot.
- Cluster `shared_downgraded` contracted from `3` members to `1`; it now remains only on `chembl_protein_class.downgraded`.
- Net effect: `WEAK` rows decreased from `439` to `435`.

## 3. Pairwise Matrix

### 3.1 Authoritative matrix artifact

- `reports/semantic_pipeline_audit/semantic_pair_matrix_2026-07-01.csv`

Columns:

- `Pipeline A`, `Field A`, `Pipeline B`, `Field B`
- `Semantic Status`
- `Normalization`
- `Validation`
- `Typing`
- `Drift Risk`
- `Join Semantics A`, `Join Semantics B`
- `Normalizer A`, `Normalizer B`
- `Validation Evidence A`, `Validation Evidence B`
- `Type A`, `Type B`
- `Gold Contract A`, `Gold Contract B`
- `Evidence A`, `Evidence B`
- `Row Key`

### 3.2 Pairwise deltas vs reviewed snapshot `2026-05-22`

| Metric | 2026-05-22 | 2026-07-01 | Delta |
| --- | ---: | ---: | ---: |
| Clusters | 291 | 290 | -1 |
| Fields | 1182 | 1245 | +63 |
| Pair rows | 3249 | 3245 | -4 |
| WEAK rows | 439 | 435 | -4 |
| Normalization `COMPATIBLE` | 891 | 887 | -4 |
| Validation `COMPATIBLE` | 1050 | 1046 | -4 |
| Typing `COMPATIBLE` | 668 | 664 | -4 |
| Base semantic surfaces | 286 | 340 | +54 |

Removed pair rows:

1. `shared_pipeline_stages`: `chembl_target.pipeline_stages` vs `composite_target.pipeline_stages`
2. `shared_downgraded`: `chembl_protein_class.downgraded` vs `chembl_target.downgraded`
3. `shared_downgraded`: `chembl_protein_class.downgraded` vs `composite_target.downgraded`
4. `shared_downgraded`: `chembl_target.downgraded` vs `composite_target.downgraded`

Changed-but-non-blocking rows:

1. `shared_organism`
   `chembl_target.organism` vs `composite_target.organism`
   validation evidence changed from `pattern:error` to `custom:error` on the target owner side.
2. `shared_organism`
   `chembl_target.organism` vs `chembl_target_component.organism`
   same validation-evidence shift as above.

Resolved closeout rows in current snapshot:

1. `shared_cell_type`
   `chembl_cell_line.cell_type` vs `composite_assay.cell_type`
   typing returned to `IDENTICAL` after explicit composite assay Gold optional-string evidence was published.
2. `shared_clo_id`
   `chembl_cell_line.clo_id` vs `composite_assay.clo_id`
   typing returned to `IDENTICAL` after explicit composite assay Gold optional-string evidence was published.

### 3.3 Join and lineage semantics

Observed stable role families:

- Provider-owned PK / contract fields:
  `assay_id`, `molecule_id`, `pmid`, `doi`, `accession`
- Composite join / dependency keys:
  `canonical_smiles`, `inchi_key`, `target_id`, `uniprot_accession`
- Lineage anchors:
  `publication_id`, `pmc_id`, `src_id`, `record_id`
- Deterministic identity inputs:
  `entity_id`, `content_hash`, join-key normalized identifiers

This is consistent with:

- ADR-026 composite orchestration and explicit join-key policy
- ADR-039 unified entity config ownership
- ADR-045 contract-based DQ policy resolution

## 4. Critical Findings

### CF-01. No confirmed blocker-level semantic conflicts

- `CRITICAL/HIGH/MEDIUM drift risk = 0`
- `STRICTNESS_MISMATCH = 0`
- `Typing CONFLICTING = 0`
- `Normalization DIFFERENT/CONFLICTING = 0`

### CF-02. Audit-tooling latest-contract resolution is now first-class governance

The semantic audit generator previously relied on a `*_v1.0.json` fallback path
that could mask newer published contract artifacts when both versions existed.
Current repo state already contains versioned contracts such as:

- `docs/04-reference/contracts/gold/chembl_target_v3.0.json`
- `docs/04-reference/contracts/gold/chembl_target_protein_classification_v2.2.json`

The generator now resolves the highest available versioned Gold contract for a
pipeline, and dedicated governance regression coverage asserts that active
registry surfaces resolve the same latest published artifact.

### CF-03. Base config semantic surface expanded materially

`configs/base/contract_registry.yaml` semantic-surface count increased from
`270` to `324`, pushing overall base-config semantic coverage from `286` to
`340`. This is not a blocker, but it means canonical semantic governance is now
more dependent on base contract-registry metadata than in the previous reviewed
snapshot.

## 5. Refactoring Recommendations

1. Keep version-aware Gold contract resolution in the semantic audit generator and treat contract-version bumps as first-class audit inputs.
2. Promote `configs/base/contract_registry.yaml` as an explicitly tracked semantic-governance hotspot, because it now owns `324` semantic surfaces and materially shapes normalization / DQ / artifact evidence.
3. Keep the `chembl_target.organism` custom validator under explicit regression coverage so the move from `pattern:error` to `custom:error` cannot silently weaken strictness.
4. Continue to keep `PARTIAL` identifier clusters unpromoted until ownership and lineage roles are split explicitly; current low drift risk does not justify collapsing them into `EXACT`.
