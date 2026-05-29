# [testing] Expand observed-value and fixture coverage for non-ChEMBL vocabularies

**Status**: deferred_by_priority
**Priority**: P2 (Medium)
**Labels**: `testing`, `fixtures`, `governance`, `vcr`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

## Problem

The non-ChEMBL audit was able to confirm major normalization semantics from
repo artifacts, but full observed-value extraction for provider vocabularies
and quasi-enums is still incomplete.

This limits confidence for:

- OpenAlex nested term families
- Semantic Scholar publication-type/topic variability
- PubMed publication-type long tail
- UniProt semantic payload value universes

## Evidence

- `tests/fixtures/vcr/pubmed/`
- `tests/fixtures/vcr/crossref/`
- `tests/fixtures/vcr/openalex/`
- `tests/fixtures/vcr/semanticscholar/`
- `tests/fixtures/vcr/pubchem/`
- `tests/fixtures/vcr/uniprot/`
- `tests/fixtures/golden/gold/`

## Current Fact Base

- All audited provider families have some VCR/sample coverage.
- Golden/generated governance artifacts are not equally rich across all
  non-ChEMBL families.
- Observed-value inventory is therefore fact-backed but still partial.

## Required Outcome

- The repo can produce an offline observed-value inventory for governed
  non-ChEMBL vocabularies.
- Fixture coverage is sufficient to detect vocabulary drift in CI without live
  provider calls.
- Confidence bounds for vocab/quasi-enum classification become explicit.

## Implementation Plan

1. Inventory the current fixture and VCR coverage by non-ChEMBL pipeline.
2. Add generated observed-value extraction for selected governed families.
3. Promote missing representative fixtures where current inventory is too thin.
4. Add tests or reports that fail when expected governed-value observation
   inputs disappear.
5. Update verification docs so fixture/VCR obligations match the expanded
   observed-value inventory.

## Suggested File Targets

- `tests/fixtures/vcr/`
- `tests/fixtures/golden/gold/`
- `tests/integration/config/`
- `scripts/engineering/qa/`
- generated artifacts under `docs/reports/generated/`

## Testing Expectations

- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
  observed-value assertions using
  `tests/fixtures/normalization/non_chembl_observed_values.yaml`.
- Extend or add fixture-governance tests around:
  - `tests/fixtures/bronze/openalex/publication/sample_edge_nested_vocab_2026-05-05.jsonl`
  - `tests/fixtures/bronze/crossref/publication/sample_edge_structured_payloads_2026-05-12.jsonl`
  - `tests/fixtures/bronze/pubmed/publication/sample_edge_publication_types_mesh_2026-05-05.jsonl`
  - `tests/fixtures/bronze/semanticscholar/publication/sample_edge_publication_types_citations_2026-05-05.jsonl`
  - `tests/fixtures/bronze/uniprot/protein/sample_edge_semantic_payloads_2026-05-12.jsonl`
  - `tests/fixtures/bronze/uniprot/idmapping/sample_edge_statuses_2026-05-05.jsonl`
- Re-run targeted E2E suites whose VCRs back the observed-value inventory:
  publication-family E2E plus UniProt E2E slices.
- If a generated observed-value report is added, cover it with a unit/integration
  script test in `tests/unit/scripts/`.

## Documentation Updates

- Update `docs/05-operations/verification/vcr-test-tasks.md`, which already
  tracks non-ChEMBL cassette expectations for UniProt and related families.
- If new fixture manifests or inventory reports are introduced, link them from
  `docs/05-engineering/normalization_plan_P0_P6.md`.
- Refresh generated normalization/governance artifacts if the observed-value
  inventory becomes a published report.

## Done When

- Non-ChEMBL observed-value inventory can run offline from repo artifacts.
- Coverage gaps for governed vocabularies are explicit rather than implicit.
- CI can detect drift in the bounded fixture universe.
- Verification docs identify which fixtures/VCRs are authoritative for that
  inventory.

## Dependencies

- Should follow the P0/P1 normalization fixes.
