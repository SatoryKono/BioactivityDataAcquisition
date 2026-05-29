# [uniprot] Align reference-array DQ with profile-owned canonicalization

**Status**: completed_in_repo
**GitHub Issue**: [#4295](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4295)
**Issue State**: closed
**Synced**: 2026-05-29
**Priority**: P1 (High)
**Labels**: `provider:uniprot`, `data-quality`, `governance`, `quality`, `technical-debt`
**Epic**: Non-ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

`uniprot_protein` and `uniprot_idmapping` already canonicalize a broad set of
reference arrays and identifier-bearing JSON payloads, but DQ coverage still
lags that profile-owned semantics.

The remaining gap is not missing normalization. It is missing governance parity
for already-normalized surfaces such as:

- `secondary_accessions`
- `go_terms`
- `molecular_function`
- `cellular_component`
- `pdb_xrefs`
- `interpro_xrefs`
- `pfam_xrefs`
- `reactome_xrefs`
- `drugbank_ids`
- `chembl_ids`
- `reviewed`
- `taxonomy_id` parity across `uniprot_idmapping` and `uniprot_protein`

## Evidence

- `reports/quality/non_chembl_normalization_audit_2026-05-19.md`
- `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `configs/entities/uniprot/idmapping.yaml`
- `configs/entities/uniprot/protein.yaml`
- `configs/vocab/uniprot_semantic_payloads.yaml`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- `configs/composites/target.yaml`

## Current Fact Base

- `uniprot_idmapping` already canonicalizes `target_id`, `uniprot_accession`,
  `taxonomy_id`, `all_mappings`, `mapping_status`, and `reviewed`.
- `uniprot_protein` already canonicalizes multiple ontology/reference arrays
  and preserves raw sidecars for five semantic payload families.
- DQ config covers the strict enums and some list-like fields, but not the full
  breadth of canonical reference-array semantics already expressed in profiles.
- `composite_target` depends on this family as an explicit normalized bridge.

## Required Outcome

- UniProt DQ posture matches the normalization breadth already shipped in the
  profile layer.
- Bridge and protein taxonomy semantics are aligned.
- Canonical identifier/reference arrays are governed explicitly instead of only
  implicitly through profile behavior.

## Implementation Plan

1. Inventory hash-relevant canonical UniProt reference-array and JSON payload
   surfaces that currently lack DQ parity.
2. Add explicit DQ rules for canonical array shape and identifier family
   patterns where semantics are already stable.
3. Align `taxonomy_id` expectations between `uniprot_idmapping` and
   `uniprot_protein`.
4. Add explicit DQ treatment for `reviewed` in both families where needed.
5. Extend contract/matrix parity tests and refresh generated artifacts.

## Suggested File Targets

- `configs/entities/uniprot/idmapping.yaml`
- `configs/entities/uniprot/protein.yaml`
- `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` with
  explicit UniProt DQ/profile parity checks for canonical reference arrays.
- Extend UniProt normalization integration tests to cover canonical array shape
  and boolean/taxonomy parity.
- Re-run UniProt contract/E2E slices and target-composite slices that depend on
  normalized `uniprot_idmapping` output.
- Re-run field-matrix generation tests.

## Documentation Updates

- Update UniProt provider reference docs under `docs/04-reference/pipelines/uniprot/`.
- Update reference-identifier family docs if new canonical patterns are made
  explicit.
- Refresh generated normalization/governance artifacts.

## Done When

- UniProt DQ no longer trails behind shipped profile semantics.
- `taxonomy_id` and `reviewed` posture is explicit across bridge and protein
  pipelines.
- Canonical reference-array surfaces are regression-tested and explainable from
  config and contracts.

## Dependencies

- Independent P1 issue.
