# [testing] Expand publication identifier and vocabulary edge-fixture inventory

**Status**: completed_in_repo
**GitHub Issue**: [#4296](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4296)
**Issue State**: closed
**Synced**: 2026-05-29
**Priority**: P2 (Medium)
**Labels**: `provider:crossref`, `provider:openalex`, `provider:pubmed`, `provider:semantic-scholar`, `testing`, `governance`, `quality`
**Epic**: Non-ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

The audit could prove the current publication-family normalization policy from
repo artifacts, but the fixture universe remains too shallow to treat observed
vocabulary and identifier edge coverage as exhaustive.

This especially affects confidence for:

- ORCID and ISSN edge canonicalization variants;
- publication-type long-tail vocabularies across providers;
- language/country/other code-like publication metadata;
- derived-vocabulary drift detection for Semantic Scholar and OpenAlex nested
  publication terms.

## Evidence

- `reports/quality/non_chembl_normalization_audit_2026-05-19.md`
- `tests/fixtures/normalization/non_chembl_observed_values.yaml`
- `tests/fixtures/normalization/non_chembl_identifier_cases.yaml`
- `tests/fixtures/bronze/crossref/publication/`
- `tests/fixtures/bronze/openalex/publication/`
- `tests/fixtures/bronze/pubmed/publication/`
- `tests/fixtures/bronze/semanticscholar/publication/`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- `tests/integration/test_cross_provider_doi_normalization.py`

## Current Fact Base

- The publication-family identifier foundation is strong for DOI/PMID/PMCID.
- The repo already has observed-value fixtures and bronze samples, but current
  bronze sample depth remains small.
- The remaining confidence gap is mostly about breadth of lexical observation,
  not about missing core normalization seams.

## Required Outcome

- Publication-family edge fixtures are rich enough to detect identifier and
  vocabulary drift without live provider calls.
- Observed-value inventory for governed publication surfaces becomes more
  explicit and regression-tested.
- Confidence bounds for quasi-enum and controlled-vocabulary classification are
  higher than they are today.

## Implementation Plan

1. Expand publication identifier edge fixtures for ORCID, ISSN, and provider
   title/type edge cases.
2. Add representative bronze/VCR-backed examples for publication-type long-tail
   values and nested topic/type payloads.
3. Promote the new examples into observed-value and identifier-case fixtures.
4. Add tests that fail when those authoritative edge examples disappear or stop
   matching canonical expectations.
5. Refresh generated normalization/governance artifacts if the observed-value
   inventory is published.

## Suggested File Targets

- `tests/fixtures/normalization/non_chembl_observed_values.yaml`
- `tests/fixtures/normalization/non_chembl_identifier_cases.yaml`
- `tests/fixtures/bronze/crossref/publication/`
- `tests/fixtures/bronze/openalex/publication/`
- `tests/fixtures/bronze/pubmed/publication/`
- `tests/fixtures/bronze/semanticscholar/publication/`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`

## Testing Expectations

- Extend publication-family edge-value assertions in the non-ChEMBL
  normalization integration suites.
- Add cross-provider ORCID/ISSN edge regressions if the repo still lacks them.
- Re-run publication contract/E2E suites touched by new authoritative fixtures.
- Re-run matrix/report generation tests if observed-value inventories are
  published as generated artifacts.

## Documentation Updates

- Update verification docs that define authoritative publication-family
  fixtures/VCRs if those obligations become more explicit.
- Refresh generated normalization reports if a richer observed-value inventory
  is emitted.

## Done When

- Publication-family fixture coverage is broad enough to detect the next layer
  of identifier/vocabulary drift in CI.
- The repo can point to authoritative offline examples for the main controlled
  publication edge cases.
- Confidence bounds in the audit move from medium to high for the covered
  edge families.

## Dependencies

- Best done after the P0/P1 publication governance issues land.
