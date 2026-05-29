# [composite] Harden composite boundaries against non-ChEMBL normalization drift

**Status**: completed_in_repo
**GitHub Issue**: [#4266](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4266)
**Issue State**: closed
**Synced**: 2026-05-29
**Priority**: P0 (Critical)
**Labels**: `composite`, `normalization`, `testing`, `lineage`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

> Audit basis: composite publication, molecule, and target flows already rely
> on normalized non-ChEMBL fields as join and validation boundaries.

## Problem

Non-ChEMBL normalization drift can already break composite enrichment without a
schema failure:

- publication composite depends on canonical `doi`, `pmid`, and fallback
  `title`;
- molecule composite depends on `inchi_key` and `canonical_smiles`;
- target composite depends on `mapping_status='found'` and canonical
  `uniprot_accession`.

Current architecture is correct, but boundary assertions are not yet elevated
into explicit normalization-drift safeguards.

## Evidence

- `configs/composites/publication.yaml`
- `configs/composites/molecule.yaml`
- `configs/composites/target.yaml`
- `src/bioetl/domain/contracts/gold/composite_publication.py`
- `src/bioetl/domain/contracts/gold/composite_molecule.py`
- `src/bioetl/domain/contracts/gold/composite_bioassay.py`
- `src/bioetl/domain/normalization/profiles/pubchem_compound.py`
- `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`

## Current Fact Base

- Publication composite primary join keys are `doi` and `pmid`; `title` is a
  canonical-cleaned fallback.
- Molecule composite joins on `inchi_key` and `canonical_smiles` and retains
  `standardized_inchi_key` as validation anchor.
- Target composite uses `normalized_output_anchor: uniprot_accession` and
  requires successful mapping semantics.

## Required Outcome

- Composite-critical normalized fields have explicit drift-detection tests.
- Join-key semantics are validated against the normalization layer, not only
  against final merge success.
- Provider-side normalization changes become visible before null enrichment
  silently increases.

## Implementation Plan

1. Enumerate composite-critical normalized fields for publication, molecule,
   and target flows.
2. Add targeted tests for join-key canonicalization invariants:
   - DOI/PMID/title publication boundaries
   - InChIKey/SMILES molecule boundaries
   - `mapping_status`/`uniprot_accession` target boundaries
3. Add config-level or contract-level assertions where a normalized boundary is
   already mandatory for enrichment.
4. Publish a boundary inventory for future regression tracking.
5. Reconcile composite-oriented generated docs so normalized boundary posture is
   visible alongside join and cross-validation policy.

## Suggested File Targets

- `configs/composites/publication.yaml`
- `configs/composites/molecule.yaml`
- `configs/composites/target.yaml`
- `tests/unit/application/composite/`
- `tests/integration/`
- generated normalization or boundary reports under `docs/reports/generated/`

## Testing Expectations

- Extend `tests/unit/application/composite/test_non_chembl_join_key_normalization.py`
  to cover all three active non-ChEMBL composite boundaries:
  publication, molecule, and target.
- Extend `tests/unit/config/test_non_chembl_composite_boundary_policy.py` so
  join-boundary invariants remain tied to:
  - `configs/composites/publication.yaml`
  - `configs/composites/molecule.yaml`
  - `configs/composites/target.yaml`
- Extend contract coverage for downstream Gold boundary fields:
  - `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
  - `tests/unit/application/composite/test_publication_schema_columns.py`
- Re-run or add composite-facing golden/DQ bundle checks where available:
  - `tests/fixtures/golden/gold/composite_publication_dq_bundle_v1.json`
  - `tests/fixtures/golden/gold/composite_molecule_dq_bundle_v1.json`
- If target composite lacks equivalent focused regression coverage, add it in
  `tests/unit/application/composite/` rather than relying only on runtime
  behavior.

## Documentation Updates

- Update `docs/04-reference/contracts/gold/composite_publication_v1.0.json`,
  `composite_molecule_v1.0.json`, and `composite_target_v1.0.json` if contract
  descriptions or required boundary semantics change.
- Update `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
  only if implementation clarifies normalized boundary policy beyond the
  current generic composite wording.
- Refresh generated governance artifacts that already report composite
  normalization posture:
  - `docs/reports/generated/pipeline_normalization_field_matrix/`
  - `docs/reports/generated/pipeline_normalization_validation_table/`
- Update `docs/04-reference/config_comparison_matrix.csv` if composite join or
  retained-anchor policy changes.

## Done When

- Composite-critical normalized fields are explicitly inventoried.
- Regression tests fail when canonical join-key semantics drift.
- Composite null-enrichment due to normalization drift becomes diagnosable from
  tests rather than only runtime observation.
- Generated composite governance docs show the normalized boundary posture
  explicitly.

## Dependencies

- Depends on `NONCHEMBL-002` for DQ parity.
