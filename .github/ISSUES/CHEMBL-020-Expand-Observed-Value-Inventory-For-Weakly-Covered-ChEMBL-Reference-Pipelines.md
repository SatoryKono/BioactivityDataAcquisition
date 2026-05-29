# [testing] Expand observed-value inventory for weakly covered ChEMBL reference pipelines

**Status**: active
**Priority**: P2 (Medium)
**Labels**: `provider:chembl`, `testing`, `governance`, `technical-debt`
**Epic**: ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

Observed-value confidence is uneven across the ChEMBL family. The core
pipelines already have stronger fixture-backed vocabulary evidence than some of
the smaller reference-like pipelines.

The 2026-05-19 audit confirmed that:

- `chembl_compound_record`
- `chembl_protein_class`
- `chembl_publication_similarity`

do not yet have the same observed-value inventory depth as the main
policy-bearing ChEMBL pipelines.

This is not a runtime determinism defect, but it weakens confidence in future
enum/vocabulary reviews and slows down evidence-backed governance work.

## Evidence

- `reports/quality/chembl_normalization_audit_2026-05-19.md`
- `tests/fixtures/normalization/chembl_observed_values.yaml`
- `tests/fixtures/normalization/chembl_bronze_observed_value_inventory_snapshot.json`
- `tests/integration/config/test_chembl_observed_value_fixtures.py`
- `tests/e2e/test_pipeline_matrix_e2e.py`

## Current Fact Base

- Current observed-value YAML already covers
  `activity`, `assay`, `assay_parameters`, `molecule`, `target`,
  `target_component`, `cell_line`, `tissue`, `publication`, and
  `publication_term`.
- Equivalent observed-value sections are thinner or absent for
  `compound_record`, `protein_class`, and `publication_similarity`.
- All three pipelines are active and registered; the gap is evidence depth, not
  pipeline completeness.

## Required Outcome

- Weakly covered ChEMBL reference-like pipelines gain bounded, repo-tracked
  observed-value evidence comparable to the rest of the family.
- Future enum/vocabulary decisions for these pipelines can rely on explicit
  offline evidence instead of incidental test payloads.

## Implementation Plan

1. Promote additional observed values from tracked fixtures or approved bronze
   samples for the three pipelines.
2. Extend the normalization observed-value YAML and inventory snapshot.
3. Add or tighten tests that fail when active reference-like pipelines lag
   behind on evidence coverage.
4. Refresh generated normalization matrix/governance artifacts if they consume
   the expanded inventory.

## Suggested File Targets

- `tests/fixtures/normalization/chembl_observed_values.yaml`
- `tests/fixtures/normalization/chembl_bronze_observed_value_inventory_snapshot.json`
- `tests/integration/config/test_chembl_observed_value_fixtures.py`
- `tests/integration/config/test_chembl_registry_fixture_contract_parity.py`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Re-run ChEMBL observed-value governance tests.
- Re-run any matrix-generation or inventory tests consuming these fixtures.
- Keep the new fixtures raw and bounded; do not move normalization semantics
  into the fixtures themselves.

## Documentation Updates

- Refresh generated normalization matrix artifacts if observed-value sections
  are surfaced there.
- If fixture coverage policy docs reference ChEMBL completeness, update them to
  reflect the stronger baseline.

## Done When

- The three weakly covered pipelines have explicit observed-value inventory
  depth comparable to the rest of the ChEMBL family.
- Governance tests fail on future coverage regressions.

## Dependencies

- Independent P2 follow-up from `reports/quality/chembl_normalization_audit_2026-05-19.md`.
