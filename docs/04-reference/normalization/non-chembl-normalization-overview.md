______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-02'

______________________________________________________________________

# Non-ChEMBL Normalization Overview

This section is the published entrypoint for non-ChEMBL normalization
governance across:

- `pubchem_compound`
- `uniprot_protein`
- `uniprot_idmapping`
- `pubmed_publication`
- `crossref_publication`
- `openalex_publication`
- `semanticscholar_publication`

Use this pack when you need the current rule boundary between raw provider
values, canonical normalized values, DQ expectations, and composite impact.

## Canonical Evidence Surfaces

- generated-matrix entrypoint:
  Historical: [Normalization Plan P0-P6](../../99-archive/engineering/normalization_plan_P0_P6.md)
  with generated artifact path
  `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
- observed values:
  [non_chembl_observed_values.yaml](../../../tests/fixtures/normalization/non_chembl_observed_values.yaml)
- published inventory page:
  [non-chembl-normalization-inventory.md](non-chembl-normalization-inventory.md)
- identifier cases:
  [non_chembl_identifier_cases.yaml](../../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml)
- shipped profile registry:
  [registry.py](../../../src/bioetl/domain/normalization/profiles/registry.py)
- identifier-family registry:
  [reference-identifier-families.md](../../03-data-model/reference-identifier-families.md)

## Shared Rules

1. Raw provider values survive when the field is a provider-native type label,
   identifier namespace, ontology-backed reference ID, or structured provider
   evidence payload.
1. Strict fail-closed vocabularies are limited to reviewed registries such as
   `mapping_status`, PubChem standardization statuses, or shared OA status.
1. Derived taxonomy fields may be strict even when the raw provider field is
   not. Publication raw types are the main example.
1. Reference identifiers are canonicalized by identifier family, not by
   enumerating currently observed values.
1. Semantic-sensitive structured payloads either keep reviewed raw and canonical
   JSON sidecars or explicitly ratify the persisted canonical JSON field as the
   governed evidence surface before any future semantic transform replaces the
   provider payload.
1. Composite pipelines normalize join keys explicitly, but non-key field
   semantics are upstream inherited from already normalized provider outputs.

## Governance Categories

| Category | Meaning | Typical examples |
| --- | --- | --- |
| Strict enum | Closed reviewed vocabulary; unknowns fail validation or canonicalization. | `chemical_standardization_status`, `chemical_standardization_policy_version`, `mapping_status`, governed `oa_status` |
| Controlled vocabulary | Reviewed canonicalizer exists, but the field is not necessarily exhaustive at the provider boundary. | selected UniProt descriptive evidence fields |
| Raw provider value | Trim/collapse/canonical text rules may apply, but unknown labels survive. | raw publication provider types |
| Identifier namespace | Canonical syntax and casing are governed; values are not treated as an exhaustive enum set. | DOI, PMID, PMCID, OpenAlex IDs, UniProt accessions |
| Ontology-backed ID | Canonical prefix or URL form is governed; new IDs remain valid without enum updates. | GO, InterPro, Pfam, Reactome, ROR |
| Derived vocabulary | Harmonized analytical field derived from raw values. | `publication_type_unified`, `publication_subclass`, `publication_class` |
| Structured JSON sidecar | Canonical JSON plus raw JSON companion fields are part of the contract. | `features_json`, `grants`, `primary_topic`, `authors_with_affiliations` |
| Structured JSON canonical-only | The persisted canonical JSON field is the reviewed evidence surface and no raw sidecar is shipped today. | `crossref_publication.references`, `crossref_publication.author_details`, selected UniProt comment projections |

## Anti-Patterns

Do not:

- convert reference identifiers into strict enums because fixtures currently show
  a small value set
- reject future raw publication type labels just because the current fixtures
  only show a few values
- replace raw structured provider payloads with only canonical JSON when the
  structured payload policy requires both raw and canonical sidecars
- invent an implicit raw sidecar for a field whose reviewed contract is
  canonical-only evidence
- document composite outputs as if they re-normalize every inherited non-key
  field locally

## Provider Groups

| Group | Current published detail |
| --- | --- |
| Publication providers | [publication-normalization.md](publication-normalization.md) |
| PubChem molecule normalization | [pubchem-normalization.md](pubchem-normalization.md) |
| UniProt protein and idmapping normalization | [uniprot-normalization.md](uniprot-normalization.md) |
| Shared identifier namespaces | [reference-identifiers.md](reference-identifiers.md) |

## Composite Impact

| Composite | Normalization boundary | Current evidence |
| --- | --- | --- |
| `composite_publication` | canonical join keys `doi`, `pmid`, fallback `title`; non-key publication fields remain upstream inherited | `configs/composites/publication.yaml`, generated matrix rows for `composite_publication` |
| `composite_molecule` | canonical join keys are molecule identity anchors; non-key PubChem fields stay upstream inherited | generated matrix rows plus `non_chembl_identifier_cases.yaml` |
| `composite_target` | `target_id` and `uniprot_accession` are normalized join/bridge anchors; UniProt evidence fields stay upstream inherited | generated matrix rows plus `non_chembl_identifier_cases.yaml` |

## Related Published References

- [Reference Index](../index.md)
- [Data Providers Documentation](../providers/README.md)
- Historical: [Normalization Plan P0-P6](../../99-archive/engineering/normalization_plan_P0_P6.md)
