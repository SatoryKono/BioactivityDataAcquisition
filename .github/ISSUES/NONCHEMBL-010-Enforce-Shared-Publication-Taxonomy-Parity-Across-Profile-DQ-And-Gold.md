# [dq] Enforce shared publication taxonomy parity across profile, DQ, and Gold

**Status**: active
**GitHub Issue**: [#4293](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4293)
**Issue State**: open
**Synced**: 2026-05-29
**Priority**: P0 (Critical)
**Labels**: `provider:crossref`, `provider:openalex`, `provider:pubmed`, `provider:semantic-scholar`, `data-quality`, `governance`, `quality`, `testing`
**Epic**: Non-ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

Publication-family normalization already derives shared analytical taxonomy
fields:

- `publication_type_unified`
- `publication_subclass`
- `publication_class`

Those fields are governed in the domain normalization layer and in shared Gold
contracts, but provider entity configs do not enforce the same semantics
consistently at the DQ layer.

That leaves a structural gap:

- raw provider-native publication type values are correctly preserve-unknown;
- derived shared taxonomy is already used for analytical semantics;
- but DQ does not consistently assert that the derived taxonomy fields stay
  within the governed shared set across all publication providers.

## Evidence

- `reports/quality/non_chembl_normalization_audit_2026-05-19.md`
- `src/bioetl/domain/normalization/profiles/_publication_classification_rules.py`
- `src/bioetl/application/pipelines/common/base_publication_transformer.py`
- `src/bioetl/domain/contracts/gold/_publication_common_schema.py`
- `configs/entities/crossref/publication.yaml`
- `configs/entities/openalex/publication.yaml`
- `configs/entities/pubmed/publication.yaml`
- `configs/entities/semanticscholar/publication.yaml`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`

## Current Fact Base

- Raw provider publication types remain open-world by design and should stay
  preserve-unknown.
- The shared derived taxonomy is already produced through the common
  classification seam.
- Gold publication contracts already depend on the shared taxonomy posture.
- Current provider DQ configs validate raw `publication_type` shape, but do not
  consistently assert the derived taxonomy fields themselves.

## Required Outcome

- Derived publication taxonomy is enforced consistently across profile, DQ, and
  Gold.
- Raw provider-native type vocabularies remain preserve-unknown and are not
  incorrectly collapsed into strict enums.
- Future drift in shared taxonomy semantics is caught by config/contract tests.

## Implementation Plan

1. Inventory all publication-family derived taxonomy fields already present in
   Silver/Gold schemas.
2. Add explicit DQ constraints for the shared derived taxonomy fields in all
   audited publication provider configs.
3. Preserve the current raw-vs-derived dual-field strategy:
   raw provider type remains open-world, derived taxonomy remains governed.
4. Extend cross-layer parity tests so matrix/profile/DQ/Gold agreement is
   checked on the derived taxonomy surfaces.
5. Refresh generated governance artifacts after the config changes.

## Suggested File Targets

- `configs/entities/crossref/publication.yaml`
- `configs/entities/openalex/publication.yaml`
- `configs/entities/pubmed/publication.yaml`
- `configs/entities/semanticscholar/publication.yaml`
- `src/bioetl/domain/contracts/gold/_publication_common_schema.py`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/config/`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` to
  assert parity for:
  - `publication_type_unified`
  - `publication_subclass`
  - `publication_class`
- Add or extend integration/config parity tests for publication-family DQ.
- Re-run publication provider contract suites and field-matrix generation tests.
- Re-run `tests/integration/test_cross_provider_doi_normalization.py` only as a
  safety check that publication shared-semantics hardening does not disturb the
  existing identifier layer.

## Documentation Updates

- Update publication provider reference docs under `docs/04-reference/providers/`
  if they under-specify the shared derived taxonomy semantics.
- Refresh generated publication Gold contract artifacts if needed.
- Refresh generated normalization/governance reports under
  `docs/reports/generated/`.

## Done When

- All four publication providers enforce the same derived taxonomy posture in
  DQ/config and Gold.
- Raw provider-native publication type fields remain preserve-unknown.
- Cross-layer parity tests fail on any future derived-taxonomy drift.

## Dependencies

- Independent P0 issue.
