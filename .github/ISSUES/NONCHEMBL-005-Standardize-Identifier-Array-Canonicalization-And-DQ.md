# [normalization] Standardize identifier-array canonicalization and DQ

**Status**: deferred_by_priority
**Priority**: P1 (High)
**Labels**: `normalization`, `dq`, `identifiers`, `publication`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

## Problem

The repo already canonicalizes many identifier families consistently, but
array-like identifier surfaces remain only partially aligned between
normalization, DQ, and Gold contracts.

Affected families include:

- `issn_list`
- ORCID arrays
- ROR arrays
- OpenAlex author/institution identifier arrays
- UniProt xref/id arrays such as `chembl_ids`, `drugbank_ids`, `go_terms`

## Evidence

- `src/bioetl/domain/normalization/profiles/openalex_publication.py`
- `src/bioetl/domain/normalization/profiles/pubmed_publication.py`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `configs/entities/crossref/publication.yaml`
- `configs/entities/openalex/publication.yaml`
- `configs/entities/uniprot/protein.yaml`

## Current Fact Base

- Identifier canonicalization helpers already exist in the domain layer.
- OpenAlex extractor code already sorts and deduplicates some identifier arrays.
- `issn_list` has explicit DQ coverage in Crossref, but parity is not uniform
  across other identifier-array surfaces.

## Required Outcome

- Identifier-array semantics are consistently modeled as canonical JSON/string
  arrays where intended.
- DQ validates the same representation that profiles emit.
- Contract surfaces make the canonical representation explicit.

## Implementation Plan

1. Inventory non-ChEMBL identifier-array fields and their current
   representation.
2. Classify each as:
   - ordered list
   - unordered set-like array
   - raw payload requiring dual-field strategy
3. Align DQ and Gold expectations with the canonical representation.
4. Add focused tests for array ordering, deduplication, and hash stability.
5. Reconcile generated identifier-family and normalization-matrix artifacts so
   the canonical array posture is visible in docs.

## Suggested File Targets

- `src/bioetl/domain/normalization/profiles/openalex_publication.py`
- `src/bioetl/domain/normalization/profiles/pubmed_publication.py`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `configs/entities/crossref/publication.yaml`
- `configs/entities/openalex/publication.yaml`
- `configs/entities/pubmed/publication.yaml`
- `configs/entities/uniprot/protein.yaml`
- `tests/unit/domain/normalization/`
- `tests/integration/config/`

## Testing Expectations

- Extend `tests/integration/config/test_non_chembl_identifier_dq_parity.py`
  for identifier-array parity across publication and UniProt families.
- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` so
  array classification and canonical representation are asserted across layers.
- Extend `tests/unit/domain/value_objects/test_identifiers.py` and
  `tests/unit/domain/value_objects/test_chemical_identifiers.py` if new helper
  behavior is introduced for set-like identifier arrays.
- Extend `tests/unit/application/core/test_non_chembl_normalization_hash_golden.py`
  to prove array ordering/dedup changes do not create nondeterministic hashes.
- Re-run affected provider schema/unit suites:
  - `tests/unit/domain/schemas/openalex/test_openalex_publication_validation.py`
  - `tests/unit/domain/schemas/crossref/test_crossref_publication_validation.py`
  - `tests/unit/domain/schemas/pubmed/test_pubmed_publication_validation.py`
  - `tests/contract/test_uniprot_contract.py`

## Documentation Updates

- Update `docs/03-data-model/reference-identifier-families.md`, which already
  inventories non-ChEMBL identifier families and examples.
- Update `docs/03-data-model/json-field-typing-inventory.md` where
  identifier-array fields are represented as canonical JSON strings.
- Refresh provider contract exports if field descriptions or constraints change:
  - `docs/04-reference/contracts/gold/crossref_publication_v1.0.json`
  - `docs/04-reference/contracts/gold/openalex_publication_v1.0.json`
  - `docs/04-reference/contracts/gold/pubmed_publication_v1.0.json`
  - `docs/04-reference/contracts/gold/uniprot_protein_v1.0.json`
- Refresh generated governance artifacts under
  `docs/reports/generated/pipeline_normalization_field_matrix/`.

## Done When

- Identifier-array fields have explicit canonicalization posture.
- DQ, profile output, and Gold typing no longer drift for these surfaces.
- Hash stability tests cover set-like and ordered identifier arrays.
- Identifier-family docs describe the same canonical representation as code and
  tests.

## Dependencies

- Related to `NONCHEMBL-002`.
