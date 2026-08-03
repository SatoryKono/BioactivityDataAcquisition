# BioETL ETL Semantic Audit

Generated: `2026-05-15`

## Executive Summary

- Scope validated against active semantic-audit tooling and current tracked artifacts.
- Covered surfaces: `configs/entities/**`, `configs/composites/**`, `configs/base/**`, normalization profiles, DQ visibility, Pandera-derived Gold contracts, reviewed semantic cluster registry, and pipeline transformer paths declared by the audit generator.
- Semantic clusters: `287`
- Pairwise semantic rows: `3248`
- Base config files covered: `5`
- Base config semantic surfaces: `286`
- CRITICAL drift risks: `0`
- HIGH drift risks: `0`
- Normalization mismatches: `0`
- Validation strictness mismatches: `0`
- Typing conflicts: `0`
- Reviewed PARTIAL rows: `67`
- Reviewed WEAK inventory rows: `439`
- Reviewed generic collision rows: `20`
- Residual blocking tasks: `0`

## Canonical Outputs

- Full markdown audit snapshot: `reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-05-15.md`
- Full pair matrix UTF-8 CSV: `reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv`
- Semantic cluster registry: `reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-15.json`
- Critical inconsistencies list: `reports/semantic_pipeline_audit/critical_inconsistencies_2026-05-15.md`
- Recommended canonical fields: `reports/semantic_pipeline_audit/recommended_canonical_fields_2026-05-15.csv`
- Base-config semantic coverage manifest: `reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-05-15.json`
- Residual backlog: `reports/semantic_pipeline_audit/semantic_residual_backlog_2026-05-15.md`

## Method And Coverage

- The project ships a dedicated semantic audit command: `python -m scripts.engineering.qa report-semantic-pipeline-audit` via [scripts/engineering/qa/__main__.py](scripts/engineering/qa/__main__.py:22).
- The semantic inventory loader binds pipeline descriptors to config path, quality path, transformer paths, schema module, and Gold contract module through [audit_pipeline_semantics.py](scripts/engineering/qa/audit_pipeline_semantics.py:64).
- Transformer coverage is explicit for all active entity providers, including ChEMBL, Crossref, OpenAlex, PubChem, PubMed, Semantic Scholar, and UniProt via [audit_pipeline_semantics.py](scripts/engineering/qa/audit_pipeline_semantics.py:375).
- The generated markdown audit summarizes evidence from active pipeline configs, base config defaults, normalization profiles, DQ visibility, Pandera-derived Gold contracts, and the reviewed semantic cluster registry in [generate_semantic_pipeline_audit.py](scripts/engineering/qa/generate_semantic_pipeline_audit.py:1219).
- Base config coverage includes `bronze_fixture_gaps.yaml`, `bronze_fixture_manifest.yaml`, `contract_registry.yaml`, and other tracked base governance surfaces in [semantic_pipeline_audit_manifest_2026-05-15.json](reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-05-15.json:14).

## Semantic Cluster Catalog

### Cluster: ASSAY_IDENTIFIER

- Canonical field: `assay_id`
- Status: `EXACT`
- Representative pipelines:
  - `chembl_activity.assay_id`
  - `chembl_assay.assay_id`
  - `chembl_assay_parameters.assay_id`
  - `composite_activity.assay_id`
  - `composite_assay.assay_id`
- Evidence: provider-facing alias `assay_chembl_id` remains boundary-only, while internal config/DQ/join/contract semantics are normalized to `assay_id` in [recommended_canonical_fields_2026-05-15.csv](reports/semantic_pipeline_audit/recommended_canonical_fields_2026-05-15.csv:3) and [semantic_cluster_registry_2026-05-15.json](reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-15.json:157).
- Normalization: shared `normalize_profile_chembl_id` in [\_profile_reference_normalizers.py](src/bioetl/domain/normalization/profiles/_profile_reference_normalizers.py:227).
- Join semantics: PK/FK/merge-key/lineage-anchor combinations are explicit in the pair matrix sample row for `chembl_assay_identifier` in [semantic_pair_matrix_2026-05-15.csv](reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv:25).

### Cluster: CANONICAL_SMILES_IDENTIFIER

- Canonical field: `canonical_smiles`
- Status: `PARTIAL`
- Representative pipelines:
  - `chembl_activity.canonical_smiles`
  - `chembl_molecule.canonical_smiles`
  - `pubchem_compound.canonical_smiles`
  - `composite_activity.canonical_smiles`
  - `composite_molecule.canonical_smiles`
- Why PARTIAL:
  - entity pipelines own normalized structure text;
  - `composite_molecule` uses the field as join-key and lineage anchor;
  - `composite_activity` inherits molecule context rather than owning the identifier.
- Evidence: [semantic_cluster_registry_2026-05-15.json](reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-15.json:7).
- Normalization: `normalize_profile_canonical_smiles` defined in [\_profile_textual_normalizers.py](src/bioetl/domain/normalization/profiles/_profile_textual_normalizers.py:116).
- Composite lineage semantics: `canonical_smiles` is a join key and merge-priority field in [configs/composites/molecule.yaml](configs/composites/molecule.yaml:73).

### Cluster: MOLECULE_DESCRIPTOR_ALIASES

- Canonical fields: `hba_count`, `hbd_count`, `polar_surface_area`, `logp`, `standard_inchi`
- Status: `EXACT`
- Representative alias collapses:
  - `pubchem.h_bond_acceptor_count -> hba_count`
  - `pubchem.h_bond_donor_count -> hbd_count`
  - `pubchem.tpsa -> polar_surface_area`
  - `pubchem.xlogp -> logp`
  - `pubchem.inchi -> standard_inchi`
- Evidence: canonical mappings are codified directly in [configs/composites/molecule.yaml](configs/composites/molecule.yaml:82) and emitted as EXACT clusters in [recommended_canonical_fields_2026-05-15.csv](reports/semantic_pipeline_audit/recommended_canonical_fields_2026-05-15.csv:8).

### Cluster: PUBLICATION_IDENTITY

- Canonical fields: `doi`, `pmid`, `pmc_id`, `title`, `publication_year`, `publication_type`
- Status:
  - `doi`: `EXACT`
  - `pmid`: `EXACT`
  - `pmc_id`: `PARTIAL`
  - `title`: `EXACT`
  - `publication_year`: `EXACT`
  - `publication_type`: `EXACT`
- Composite join semantics:
  - primary join keys: `doi`, `pmid`
  - fallback join key: `title`
- Evidence: [configs/composites/publication.yaml](configs/composites/publication.yaml:38).
- Cross-source pair evidence for `title` shows EXACT semantics with IDENTICAL normalization and COMPATIBLE validation across composite and provider pipelines in [semantic_pair_matrix_2026-05-15.csv](reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv:3).

### Cluster: PUBLICATION_SUBJECT_SEMANTICS

- Canonical fields:
  - `subject_keywords`
  - `subject_mesh`
  - `subject_topics`
  - `subject_fields`
- Status: all `EXACT`, but intentionally separated into distinct clusters.
- Architectural significance:
  - generic publication keywords are not collapsed into MeSH or OpenAlex topic semantics;
  - ontology meaning remains source-aware and lineage-safe.
- Evidence: [recommended_canonical_fields_2026-05-15.csv](reports/semantic_pipeline_audit/recommended_canonical_fields_2026-05-15.csv:27).

### Cluster: UNIPROT_ACCESSION_IDENTIFIER

- Canonical field: `accession`
- Status: `PARTIAL`
- Representative pipelines:
  - `chembl_target_component.accession`
  - `uniprot_protein.accession`
- Why PARTIAL:
  - identical identifier normalization;
  - different business ownership: ChEMBL component reference vs UniProt primary entity.
- Evidence: pair row in [semantic_pair_matrix_2026-05-15.csv](reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv:15).
- Normalization: `normalize_profile_uniprot_accession` in [\_profile_reference_normalizers.py](src/bioetl/domain/normalization/profiles/_profile_reference_normalizers.py:182).

## Pairwise Matrix

- The exhaustive matrix is the UTF-8 CSV [semantic_pair_matrix_2026-05-15.csv](reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-15.csv:1).
- Columns include:
  - `Semantic Status`
  - `Normalization`
  - `Validation`
  - `Typing`
  - `Drift Risk`
  - `Join Semantics A/B`
  - `Normalizer A/B`
  - `Validation Evidence A/B`
  - `Type A/B`
  - `Gold Contract A/B`
  - `Evidence A/B`
- Current aggregate counts:
  - `EXACT`: `2722`
  - `PARTIAL`: `67`
  - `WEAK`: `439`
  - `CONFLICTING`: `20`
  - `IDENTICAL normalization`: `2348`
  - `COMPATIBLE normalization`: `900`
  - `IDENTICAL validation`: `2195`
  - `COMPATIBLE validation`: `1053`
  - `IDENTICAL typing`: `2584`
  - `COMPATIBLE typing`: `664`

## Divergence Report

### Normalization

- No `DIFFERENT` or `CONFLICTING` normalization rows remain in the current generated audit summary: [semantic_pipeline_audit_2026-05-15.md](reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-05-15.md:13).
- The strongest remaining non-identical state is `COMPATIBLE`, usually when composite fields inherit normalized upstream values or apply `join_key_policy` rather than a provider-owned profile normalizer.

### Validation

- No `STRICTNESS_MISMATCH` rows remain in the current snapshot: [semantic_pipeline_audit_2026-05-15.md](reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-05-15.md:14).
- `COMPATIBLE` validation rows are expected where composites intentionally expose upstream-inherited or join-policy fields without reasserting full provider-side DQ strictness.

### Typing

- No `LOSSY` or `CONFLICTING` typing rows remain in the current summary: [semantic_pipeline_audit_2026-05-15.md](reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-05-15.md:15).
- `COMPATIBLE` typing rows are concentrated in composite surfaces with `unknown` schema typing versus stricter provider/entity schemas, not in provider-to-provider business collisions.

### Generic Collision Inventory

- Reviewed `CONFLICTING` clusters are lexical collisions, not active schema drift:
  - `shared_description`
  - `shared_relation`
  - `shared_score`
  - `shared_type`
  - `shared_value`
- Governance rationale is explicit in [semantic_audit_review_registry.yaml](configs/field_registry/semantic_audit_review_registry.yaml:42).

## Architectural Findings

### Confirmed

- No CRITICAL or HIGH semantic inconsistencies are present in the generated risk report: [critical_inconsistencies_2026-05-15.md](reports/semantic_pipeline_audit/critical_inconsistencies_2026-05-15.md:5).
- No residual blocking semantic tasks remain open: [semantic_residual_backlog_2026-05-15.md](reports/semantic_pipeline_audit/semantic_residual_backlog_2026-05-15.md:7).
- Composite join-key semantics are explicit and deterministic for:
  - activity composite dual-key enrichment by `molecule_id + publication_id` in [configs/composites/activity.yaml](configs/composites/activity.yaml:63)
  - molecule composite enrichment by `inchi_key` with `canonical_smiles` fallback in [configs/composites/molecule.yaml](configs/composites/molecule.yaml:73)
  - publication composite identity join policy with `doi/pmid` primary and `title` fallback in [configs/composites/publication.yaml](configs/composites/publication.yaml:38)

### Residual Semantic Debt

- `67` PARTIAL rows remain by policy, not by unresolved drift.
- `439` WEAK rows remain as inventory-only same-name occurrences.
- `20` generic lexical collisions remain intentionally non-canonicalized.

### ADR Alignment

- `ADR-018`: no Gold strict validation mismatches are reported in current artifacts.
- `ADR-026`: composite join keys, field priorities, and seed/enricher lineage semantics are explicit and deterministic in shipped composite configs.
- `ADR-035`: no typing conflicts remain; JSON/string normalization policy is reflected in the normalization matrix and pairwise typing outcomes.
- `ADR-039`: unified entity configs are the source layer for field semantics, while composites stay under `configs/composites/`.
- `ADR-045`: DQ evidence is carried into the semantic matrix as `dq_rules`, `dq_coverage`, and Gold compatibility rather than remaining external to semantic comparison.

## Recommended Canonical Fields

Priority canonical fields already evidenced by the audit:

- `assay_id`
- `molecule_id`
- `target_chembl_id`
- `doi`
- `pmid`
- `pmc_id`
- `canonical_smiles`
- `inchi_key`
- `standard_inchi`
- `hba_count`
- `hbd_count`
- `polar_surface_area`
- `logp`
- `title`
- `publication_year`
- `publication_type`
- `subject_keywords`
- `subject_mesh`
- `subject_topics`
- `subject_fields`

The authoritative machine-readable registry for this list is [recommended_canonical_fields_2026-05-15.csv](reports/semantic_pipeline_audit/recommended_canonical_fields_2026-05-15.csv:1).

## Refactoring Recommendations

1. Do not promote reviewed PARTIAL clusters such as `canonical_smiles_identifier`, `uniprot_accession_identifier`, `pmc_identifier`, and `chembl_target_identifier` to EXACT without first adding explicit ownership metadata for provider-owned identity versus composite lineage anchor semantics.
2. Keep generic lexical fields `description`, `score`, `type`, `value`, and `relation` outside canonical aliasing until an owner-specific registry entry exists; current review policy correctly treats them as collisions rather than shared business concepts.
3. For composite surfaces currently typed as `unknown` in pair rows, prefer explicit schema metadata only where that improves Gold-facing guarantees without duplicating upstream validation logic.
4. Preserve the publication subject split between `subject_keywords`, `subject_mesh`, `subject_topics`, and `subject_fields`; collapsing them would introduce ontology drift and violate semantic specificity.
5. Keep molecule composite aliasing in config, not transformer-local ad hoc code. The explicit alias block in [configs/composites/molecule.yaml](configs/composites/molecule.yaml:95) is the correct canonicalization seam.
6. Continue enforcing semantic drift through the existing gates:
   - `check-semantic-pair-budget`
   - `check-semantic-registry-drift`
   - `check-generic-field-ownership`
   - `report-semantic-pipeline-audit --check`

## Audit Verdict

The current BioETL pipeline estate is semantically governed rather than semantically fragmented. The active risk is not unresolved hard drift, but accidental future over-canonicalization of reviewed PARTIAL and generic-collision clusters. The correct next step is to preserve the current registry-driven model and only promote additional canonical fields when ownership, lineage role, and DQ/Gold semantics remain explicit.
