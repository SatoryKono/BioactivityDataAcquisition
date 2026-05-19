# [configuration] Externalize non-ChEMBL vocabulary registries by family

**Status**: Draft
**Priority**: P1 (High)
**Labels**: `configuration`, `normalization`, `architecture`, `cross-pipeline`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

> Audit basis: the repo already externalizes publication-family vocabularies,
> but cross-family non-ChEMBL vocabulary governance is still uneven.

## Problem

Publication-family vocabularies already have explicit config surfaces, but the
same maturity is not yet present uniformly for other non-ChEMBL families,
especially UniProt semantic payload vocabularies and provider-specific nested
terms.

As a result, some controlled vocabularies are:

- config-backed and observable;
- some are profile-backed only;
- some are present only as structured payload conventions.

## Evidence

- `configs/vocab/publication_controlled.yaml`
- `configs/vocab/publication_nested.yaml`
- `configs/vocab/uniprot_semantic_payloads.yaml`
- `docs/02-architecture/decisions/ADR-038-enum-externalization.md`
- `src/bioetl/domain/normalization/profiles/_publication_classification_rules.py`

## Current Fact Base

- Publication-family raw vocabularies already use explicit config artifacts.
- ADR-038 explicitly preserves raw provider publication vocabularies as raw
  sidecars instead of forcing a strict enum.
- UniProt semantic payload vocabulary metadata exists, but not yet as a
  broader family-wide normalization registry with parity enforcement.

## Required Outcome

- Non-ChEMBL vocabulary governance is classified by family:
  - publication-like
  - compound/reference
  - protein/sequence
- Shared config registries exist where they add governance value.
- Raw provider-native values remain raw where ADR-038 requires preserve-unknown
  posture.

## Implementation Plan

1. Publish a family-level inventory of non-ChEMBL controlled vocabularies and
   quasi-enums.
2. Decide which vocabularies need explicit externalized registries versus
   provider-local profile rules.
3. Add parity tests so a newly governed vocabulary cannot appear in profile or
   config without matching registry posture.
4. Keep raw provider-native publication vocabularies out of strict enum SSOT.
5. Reconcile generated normalization matrix classification so new registry
   families surface as first-class governance seams.

## Suggested File Targets

- `configs/vocab/publication_controlled.yaml`
- `configs/vocab/publication_nested.yaml`
- `configs/vocab/uniprot_semantic_payloads.yaml`
- new `configs/vocab/non_chembl_*.yaml` surfaces as needed
- `tests/integration/config/`
- `docs/02-architecture/decisions/ADR-038-enum-externalization.md` if a
  follow-up addendum is needed

## Testing Expectations

- Extend `tests/integration/config/test_uniprot_semantic_payload_vocabulary_inventory.py`
  for any new UniProt family registry surfaces.
- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` so
  registry-backed posture is checked against profile/config/contract seams.
- Extend `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`
  so newly externalized non-ChEMBL registries are represented explicitly in the
  generated matrix.
- Re-run `tests/unit/scripts/test_report_observability_metric_inventory.py`
  if publication-family unknown-vocab observability metrics or naming change.
- If new registry files are added, include fixture-backed observed-value
  assertions using `tests/fixtures/normalization/non_chembl_observed_values.yaml`.

## Documentation Updates

- Update `docs/02-architecture/decisions/ADR-038-enum-externalization.md`
  only to the extent needed to document the non-ChEMBL family posture without
  weakening its current preserve-unknown publication guidance.
- Update `docs/05-engineering/normalization_plan_P0_P6.md`, which already has
  a non-ChEMBL vocabulary/governance section.
- Update `docs/03-data-model/json-field-typing-inventory.md` and
  `docs/03-data-model/reference-identifier-families.md` if the registry
  boundaries materially change those inventories.
- Refresh generated artifacts under:
  - `docs/reports/generated/pipeline_normalization_field_matrix/`
  - `docs/reports/generated/pipeline_normalization_validation_table/`

## Done When

- Every governed non-ChEMBL vocabulary family has explicit posture:
  strict enum, controlled vocabulary, preserve-unknown, or raw-only.
- Publication, PubChem, and UniProt families no longer mix registry and
  profile-only approaches arbitrarily.
- Drift tests exist for the newly externalized registries.
- Documentation and generated matrix artifacts point to the same registry seams
  as code.

## Dependencies

- Should follow `NONCHEMBL-001` and `NONCHEMBL-002`.
