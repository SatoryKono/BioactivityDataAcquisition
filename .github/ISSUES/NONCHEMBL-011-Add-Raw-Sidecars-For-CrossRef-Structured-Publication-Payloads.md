# [crossref] Add raw sidecars for semantic-sensitive structured publication payloads

**Status**: Draft
**Priority**: P1 (High)
**Labels**: `provider:crossref`, `governance`, `schema-evolution`, `technical-debt`, `data-lineage`, `quality`
**Epic**: Non-ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

CrossRef currently canonicalizes structured publication payloads such as
`author_details` and `references`, but unlike OpenAlex, PubMed, Semantic
Scholar, and UniProt, it does not retain raw JSON sidecars for those
semantic-sensitive surfaces.

This creates an avoidable asymmetry:

- canonical analytical representation exists;
- replay/debug cannot recover the exact source payload from persisted semantic
  sidecars for those fields;
- structured-field governance differs across otherwise similar publication
  providers.

## Evidence

- `reports/quality/non_chembl_normalization_audit_2026-05-19.md`
- `src/bioetl/domain/normalization/profiles/crossref_publication.py`
- `src/bioetl/domain/normalization/profiles/openalex_publication.py`
- `src/bioetl/domain/normalization/profiles/pubmed_publication.py`
- `src/bioetl/domain/normalization/profiles/semanticscholar_publication.py`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`

## Current Fact Base

- CrossRef marks `author_details` and `references` as canonical JSON-string
  payloads.
- OpenAlex, PubMed, Semantic Scholar, and UniProt already use explicit
  raw/canonical sidecar strategies on comparable semantic payload families.
- The current asymmetry is structural, not theoretical: the repo already has a
  preferred pattern for replay-safe structured-field preservation.

## Required Outcome

- CrossRef structured semantic payloads follow the same raw/canonical sidecar
  policy used elsewhere in non-ChEMBL normalization where source fidelity
  matters.
- Raw sidecars are excluded from hash when appropriate, while canonical fields
  remain the analytical/hash-safe representation.
- Contract and generated-governance artifacts make that posture explicit.

## Implementation Plan

1. Identify which CrossRef structured payloads need raw preservation:
   - `author_details`
   - `references`
2. Add raw JSON sidecar fields and explicit hash-exclusion posture.
3. Update schema/contract/config surfaces so the sidecars are first-class and
   documented.
4. Add regression tests that compare CrossRef policy with the already-shipped
   OpenAlex/PubMed/S2 sidecar pattern.
5. Refresh generated normalization/contract artifacts.

## Suggested File Targets

- `src/bioetl/domain/schemas/crossref/publication.py`
- `src/bioetl/domain/normalization/profiles/crossref_publication.py`
- CrossRef transformer/assembly code under `src/bioetl/application/pipelines/crossref/`
- `configs/entities/crossref/publication.yaml`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- CrossRef Gold contract artifacts under `docs/04-reference/contracts/gold/`

## Testing Expectations

- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` so
  CrossRef raw/canonical sidecar policy is asserted explicitly.
- Extend normalization integration tests with raw-vs-canonical CrossRef payload
  expectations.
- Re-run field-matrix generation tests and CrossRef contract/E2E slices.
- Add hash-governance regression coverage if sidecar introduction changes any
  persisted business payload handling.

## Documentation Updates

- Update CrossRef provider reference docs under
  `docs/04-reference/providers/crossref/`.
- Refresh JSON-field typing inventory docs if they enumerate CrossRef payload
  posture.
- Refresh generated contract and normalization-matrix artifacts.

## Done When

- CrossRef no longer remains the outlier publication provider on semantic raw
  sidecar preservation.
- Canonical analytical payloads and raw replay/debug payloads are both explicit.
- Hash posture and contract typing are documented and regression-tested.

## Dependencies

- Can proceed independently after the P0 publication taxonomy issue.
