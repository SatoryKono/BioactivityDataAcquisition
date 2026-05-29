# [dq] Align governed OA and identifier-array DQ with profile normalization

**Status**: active
**Priority**: P0 (Critical)
**Labels**: `dq`, `normalization`, `contracts`, `publication`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

> Audit basis: several non-ChEMBL publication surfaces are already governed in
> profiles and Gold schemas, but DQ enforcement is still uneven.

## Problem

The repo already has shared normalization for publication-family governed
surfaces such as `oa_status`, identifier arrays, and canonical structured
payloads, but DQ does not consistently enforce the same semantics at the
entity-config layer.

This creates governance drift:

- Gold/schema may reject or constrain values differently than DQ;
- normalization may canonicalize a field that DQ still treats as free-form;
- composite pipelines may rely on normalized identifiers without equivalent
  DQ visibility.

## Evidence

- `src/bioetl/domain/normalization/open_access.py`
- `src/bioetl/domain/contracts/gold/publications_openalex.py`
- `src/bioetl/domain/contracts/gold/publications_semanticscholar.py`
- `configs/entities/openalex/publication.yaml`
- `configs/entities/semanticscholar/publication.yaml`
- `configs/entities/crossref/publication.yaml`
- `src/bioetl/domain/normalization/profiles/openalex_publication.py`
- `src/bioetl/domain/normalization/profiles/semanticscholar_publication.py`

## Current Fact Base

- `oa_status` is normalized through a shared registry and constrained in Gold
  contracts for OpenAlex and Semantic Scholar.
- Crossref and publication-family pipelines already canonicalize identifier
  arrays such as `issn_list`.
- Semantic Scholar raw `publication_type` is only regex-checked in DQ.
- Crossref raw `publication_type` is validated only as non-empty when present.

## Required Outcome

- DQ posture matches the governed semantics already present in profiles and
  Gold schemas.
- Identifier-array fields and governed OA status fields have explicit DQ rules
  instead of implicit trust in profile normalization.
- Preserve-unknown raw provider vocabularies remain preserve-unknown rather
  than being over-tightened into strict enums.

## Implementation Plan

1. Inventory governed publication-family fields with profile-owned
   normalization but weak DQ parity:
   - `oa_status`
   - `issn_list`
   - selected identifier arrays and canonical JSON companions
2. Add or tighten entity-level DQ rules where semantics are already governed.
3. Keep raw provider-native publication type fields preserve-unknown and avoid
   converting them into strict enums.
4. Add parity tests that compare:
   - profile governance
   - entity DQ config
   - Gold contract constraints
5. Reconcile generated normalization matrix rows and validation-table outputs
   so the new DQ posture is visible in governance artifacts.

## Suggested File Targets

- `configs/entities/openalex/publication.yaml`
- `configs/entities/semanticscholar/publication.yaml`
- `configs/entities/crossref/publication.yaml`
- `src/bioetl/domain/normalization/open_access.py`
- `tests/integration/config/`
- `tests/contract/`

## Testing Expectations

- Extend `tests/integration/config/test_non_chembl_identifier_dq_parity.py`
  so OA-status and identifier-array DQ parity is asserted for OpenAlex,
  Semantic Scholar, Crossref, and PubMed where applicable.
- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` so
  profile/DQ/Gold alignment is explicit for:
  - `oa_status`
  - `issn_list`
  - selected identifier-array surfaces
- Extend provider contract tests as needed:
  - `tests/contract/test_openalex_contract.py`
  - `tests/contract/test_semanticscholar_contract.py`
  - `tests/contract/test_crossref_contract.py`
  - `tests/contract/test_pubmed_contract.py`
- Re-run relevant E2E slices:
  - `tests/e2e/test_openalex_publication_e2e.py`
  - `tests/e2e/test_semanticscholar_publication_e2e.py`
  - `tests/e2e/test_crossref_publication_e2e.py`
  - `tests/e2e/test_pubmed_publication_e2e.py`
- Re-run `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`
  because the field-matrix output already encodes DQ posture for these
  governed surfaces.

## Documentation Updates

- Update `docs/03-data-model/reference-identifier-families.md` if any
  identifier-array canonicalization posture changes.
- Update `docs/03-data-model/json-field-typing-inventory.md` when DQ posture
  changes for canonical JSON companions.
- Update publication provider reference docs if they currently under-specify
  governed OA or identifier semantics:
  - `docs/04-reference/providers/openalex/publication.md`
  - `docs/04-reference/providers/crossref/publication.md`
- Refresh generated contract docs if Gold surface constraints change:
  - `docs/04-reference/contracts/gold/openalex_publication_v1.0.json`
  - `docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json`
  - `docs/04-reference/contracts/gold/crossref_publication_v1.0.json`
  - `docs/04-reference/contracts/gold/pubmed_publication_v1.0.json`
- Refresh governance reports under:
  - `docs/reports/generated/pipeline_normalization_field_matrix/`
  - `docs/reports/generated/pipeline_normalization_validation_table/`

## Done When

- OpenAlex and Semantic Scholar `oa_status` semantics are explicit in both DQ
  and Gold layers.
- Canonical identifier-array surfaces have consistent DQ posture.
- Preserve-unknown raw provider vocabularies remain documented as such.
- Parity tests fail on future drift between profile, DQ, and Gold semantics.
- Generated normalization/governance docs reflect the tightened DQ posture.

## Dependencies

- Related to `NONCHEMBL-004`.
