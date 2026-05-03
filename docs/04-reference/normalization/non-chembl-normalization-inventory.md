______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-03'

______________________________________________________________________

# Non-ChEMBL Normalization Inventory

This page is the human-readable index for the non-ChEMBL observed-value
inventory that backs the generated normalization evidence matrix.

## Canonical Sources

- observed-value inventory:
  [non_chembl_observed_values.yaml](../../../tests/fixtures/normalization/non_chembl_observed_values.yaml)
- identifier and raw-type policy cases:
  [non_chembl_identifier_cases.yaml](../../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml)
- generated non-ChEMBL matrix slice:
  [non_chembl_normalization_field_matrix.md](../../reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md)
- full generated matrix:
  [pipeline_normalization_field_matrix.md](../../reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)

## What The Inventory Records

Each non-ChEMBL pipeline inventory row is expected to capture:

- representative observed values
- representative raw provider values when raw-label preservation matters
- expected normalized values
- expected controlled or derived values when a reviewed registry exists
- field classification
- identifier family when applicable
- collection semantics for arrays and structured payloads
- raw and canonical sidecar requirements for semantic-sensitive JSON
- composite usage impact
- explicit evidence source location

## Classification Contract

Use the following interpretation consistently:

| Classification | Meaning |
| --- | --- |
| `strict_enum` | Reviewed closed vocabulary; unknown values are not silently accepted. |
| `strict_boolean` | Canonical boolean surface, not a provider free-text label. |
| `raw_provider_value` | Raw provider label survives normalization after canonical text cleanup. |
| `identifier_namespace` | Canonical syntax/casing is governed, but values are not enumerated. |
| `ontology_backed_id` | Identifier namespace is ontology-backed and open-ended. |
| `derived_vocabulary` | Harmonized analytical taxonomy derived from raw provider values. |
| `structured_json_collection` | Canonical JSON collection is governed, often with a raw sidecar anchor. |
| `structured_json_sidecar` | Raw and canonical JSON sidecars are both part of the contract. |

## Review Boundaries

- Do not infer strict enums from a short observed-value list alone.
- Raw publication provider types remain open-world provider labels.
- Reference identifiers remain namespace-governed, not enum-governed.
- Structured payload rows must keep the documented raw/canonical sidecars.
- Composite usage must reflect whether a field is a join key or only upstream inherited.

## Provider Coverage

The published inventory currently covers:

- `pubchem_compound`
- `uniprot_protein`
- `uniprot_idmapping`
- `pubmed_publication`
- `crossref_publication`
- `openalex_publication`
- `semanticscholar_publication`
