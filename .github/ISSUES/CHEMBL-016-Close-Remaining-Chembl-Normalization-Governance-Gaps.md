# [normalization] Close remaining cross-family ChEMBL normalization governance gaps

**Status**: completed_in_repo
**Priority**: P0/P1
**Labels**: `normalization`, `dq`, `contracts`, `configs`, `testing`, `governance`
**Epic**: ChEMBL Normalization and DQ Alignment 2026Q2
**Last audited**: 2026-05-13

> This issue consolidates the remaining cross-family normalization governance
> gaps identified after the current `main` audit. The underlying normalization
> architecture is already centralized and deterministic; the remaining work is
> to align DQ, contracts, observed-value evidence, and generated governance
> artifacts with the normalization semantics that already exist in code.

## Problem

The current `chembl_*` normalization stack is architecture-correct and largely
deterministic, but governance closure is incomplete across the family.

The highest-risk remaining gaps are:

- operator fields are normalized but not uniformly governed in DQ/contracts;
- publication derived taxonomy fields are persisted and hash-relevant without
  equivalent DQ/contract enforcement;
- `chembl_target` controlled-vocabulary arrays remain normalization-governed
  but under-specified in DQ;
- strict scalar bool/flag families are centralized but not fully surfaced in
  DQ across `molecule`, `target`, and `protein_class`;
- observed-value fixture coverage remains incomplete for 4 active ChEMBL
  pipelines;
- the generated normalization matrix still derives ChEMBL classification
  indirectly instead of materializing it explicitly.

## Evidence

- `reports/codex/chembl_normalization_audit_20260513.md`
- `reports/codex/chembl_normalization_enum_inventory_20260513.csv`
- `src/bioetl/application/core/record_normalization_processor.py`
- `src/bioetl/application/core/_record_normalization_hash_support.py`
- `src/bioetl/domain/transformations/hashing.py`
- `src/bioetl/domain/normalization/profiles/_chembl_policy_registry.py`
- `src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py`
- `src/bioetl/domain/normalization/profiles/chembl_activity.py`
- `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
- `src/bioetl/domain/normalization/profiles/chembl_publication.py`
- `src/bioetl/domain/normalization/profiles/chembl_target.py`
- `src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py`
- `configs/enums/chembl.yaml`
- `configs/vocab/chembl_controlled.yaml`
- `configs/vocab/chembl_ontology.yaml`
- `tests/integration/config/test_chembl_policy_surface_parity.py`
- `tests/integration/config/test_chembl_observed_value_fixtures.py`
- `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.csv`

## Current Fact Base

- All 14 active `chembl_*` pipelines have shipped normalization profiles.
- Profile-backed fallback is blocked in application normalization.
- Hashing already runs on normalized canonical payloads.
- Reviewed JSON ordering policy already exists for ChEMBL structured fields.
- `167` governed/structured ChEMBL fields are currently surfaced in the
  generated normalization matrix.
- `52` governed fields remain without explicit `dq_rule`.
- Observed-value fixture entity coverage is missing for:
  - `chembl_compound_record`
  - `chembl_protein_class`
  - `chembl_publication_similarity`
  - `chembl_subcellular_fraction`

## Required Outcome

- Shared operator semantics are governed consistently across `activity` and
  `assay_parameters`.
- Publication derived taxonomy fields are explicitly governed as derived
  vocabulary surfaces.
- `chembl_target.component_types` and
  `chembl_target.component_relationships` are governed as explicit canonical
  controlled-vocabulary array fields.
- Shared strict bool/flag surfaces in `molecule`, `target`, and
  `protein_class` are aligned between profile normalization and DQ.
- Missing observed-value fixture coverage is promoted for the uncovered active
  pipelines.
- The generated normalization matrix materializes ChEMBL classification
  directly instead of forcing indirect reconstruction from
  `strictness + semantic_category`.

## Scope

This issue covers only the remaining governance closure work on top of the
existing normalization architecture. It is not a request to redesign the
normalization framework or move logic out of the current profile-centric model.

Out of scope:

- replacing the current profile registry architecture;
- moving canonicalization ownership back into entity transformers;
- changing hash identity policy away from normalized canonical payloads;
- broad schema redesign outside the governed fields identified by the audit.

## Implementation Plan

### P0

1. Align operator governance for:
   - `chembl_activity.relation`
   - `chembl_assay_parameters.relation`
   - and verify consistency with `standard_relation` surfaces.
2. Promote publication derived taxonomy governance for:
   - `publication_type_unified`
   - `publication_subclass`
   - `publication_class`
3. Align `chembl_target` controlled-vocabulary array governance for:
   - `component_types`
   - `component_relationships`
4. Reconcile every hash-relevant preserve-unknown vocabulary in the inventory
   with an explicit posture:
   - fail-closed strict enum;
   - preserve-unknown controlled vocabulary;
   - dual-field raw/canonical strategy.

### P1

5. Align DQ with shared strict-scalar policy for:
   - `chembl_molecule`
   - `chembl_target`
   - `chembl_protein_class`
6. Complete ontology companion governance where normalized status/version
   fields persist in Silver and influence Gold reasoning.
7. Close remaining structured-JSON governance gaps, including set-like
   identifier arrays such as `issn_list`.
8. Materialize ChEMBL classification directly in the generated normalization
   matrix.

### P2

9. Expand observed-value fixtures and tests for the uncovered active pipelines:
   - `chembl_compound_record`
   - `chembl_protein_class`
   - `chembl_publication_similarity`
   - `chembl_subcellular_fraction`
10. Re-run and publish the normalized field matrix after governance alignment.

## Suggested File Targets

- `src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py`
- `src/bioetl/domain/normalization/profiles/chembl_activity.py`
- `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
- `src/bioetl/domain/normalization/profiles/chembl_publication.py`
- `src/bioetl/domain/normalization/profiles/chembl_target.py`
- `src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py`
- `configs/entities/chembl/activity.yaml`
- `configs/entities/chembl/assay_parameters.yaml`
- `configs/entities/chembl/molecule.yaml`
- `configs/entities/chembl/publication.yaml`
- `configs/entities/chembl/protein_class.yaml`
- `configs/entities/chembl/target.yaml`
- `tests/integration/config/test_chembl_policy_surface_parity.py`
- `tests/integration/config/test_chembl_observed_value_fixtures.py`
- `tests/fixtures/normalization/chembl_observed_values.yaml`
- `scripts/docs/matrix/generate_pipeline_normalization_matrix.py`
- generated artifacts under
  `docs/reports/generated/pipeline_normalization_field_matrix/`

## Done When

- The P0 governed fields identified in the audit have explicit, consistent DQ
  and contract semantics.
- Publication derived taxonomy fields are treated as first-class governed
  derived vocabulary surfaces.
- Target component vocabulary arrays have explicit governed array-element
  semantics in both normalization and DQ.
- Shared strict bool/flag surfaces no longer drift between policy registry and
  DQ/config layers.
- Observed-value fixture coverage exists or is explicitly waived for every
  active `chembl_*` pipeline.
- The generated normalization matrix exposes direct ChEMBL classification for
  governed rows.
- Policy-surface parity tests, observed-value governance tests, and affected
  unit/integration test slices pass.

## Dependencies

- Follow-up to `reports/codex/chembl_normalization_audit_20260513.md`
- Related completed issues:
  - `CHEMBL-010`
  - `CHEMBL-011`
  - `CHEMBL-012`
  - `CHEMBL-013`
  - `CHEMBL-014`
  - `CHEMBL-015`
