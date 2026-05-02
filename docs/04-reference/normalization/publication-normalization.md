______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-02'

______________________________________________________________________

# Publication Normalization

Scope: non-ChEMBL publication providers and the fields they feed into
`composite_publication`.

Covered pipelines:

- `pubmed_publication`
- `crossref_publication`
- `openalex_publication`
- `semanticscholar_publication`

Use the generated matrix for full field-by-field detail:
[pipeline_normalization_field_matrix.md](../../reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md).
Use representative fixtures for reviewed examples:
[non_chembl_observed_values.yaml](../../../tests/fixtures/normalization/non_chembl_observed_values.yaml)
and
[non_chembl_identifier_cases.yaml](../../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml).

## Identifier Families

| Fields | Governance category | Current rule |
| --- | --- | --- |
| `doi`, `pmid`, `pmc_id` | identifier namespace | canonical syntax/casing is governed; these are not strict enums |
| `openalex_id`, `paper_id` | provider identifier namespace | canonical provider ID syntax is governed; future IDs remain valid |
| `author_orcids` | canonical identifier array | ORCID values canonicalize through `domain.normalization.reference_ids` |
| `author_openalex_ids`, `institution_ids`, `ror_ids` | canonical identifier arrays | OpenAlex/ROR families canonicalize through the shared registry |
| `author_s2_ids` | canonical identifier array | Semantic Scholar IDs canonicalize through the shared registry |

Do not treat publication identifiers or author/source identifier families as
closed enums. The canonical boundary is syntax and namespace, not a frozen list
of known values.

## Raw Publication Types Vs Derived Taxonomy

Raw provider fields remain provider-native:

| Pipeline | Raw field(s) | Rule |
| --- | --- | --- |
| `crossref_publication` | `publication_type` | unknown provider labels survive after text normalization |
| `openalex_publication` | `publication_type`, `type_crossref` | provider-native type labels survive; `type_crossref` is still a raw sidecar |
| `pubmed_publication` | `publication_type`, `publication_type_list` | provider labels survive; list payload stays canonical JSON evidence |
| `semanticscholar_publication` | `publication_type`, `publication_types` | provider labels survive; structured list remains canonical JSON evidence |

Derived analytical fields are separate:

- `publication_type_unified`
- `publication_subclass`
- `publication_class`

Those fields normalize against the shared publication classification taxonomy in
`configs/enums/publication_type_classification.csv`.

Rule: downstream business logic should key off the derived taxonomy fields, not
the raw provider labels.

## OA Status

| Field | Governance category | Current rule |
| --- | --- | --- |
| `oa_status` in `openalex_publication` | strict enum | governed by shared OA-status registry |
| `oa_status` in `semanticscholar_publication` | strict enum | governed by shared OA-status registry; unknowns fail closed |
| PubMed / CrossRef OA signals | not canonical shared OA taxonomy | no provider-native raw label should be documented as a universal OA enum |

## Structured Publication Payloads

| Pipeline | Field | Collection semantics | Raw sidecar | Canonical sidecar |
| --- | --- | --- | --- | --- |
| `openalex_publication` | `grants` | unordered set | `grants_raw_json` | `grants_canonical_json` |
| `openalex_publication` | `primary_topic` | structured object | `primary_topic_raw_json` | `primary_topic_canonical_json` |
| `pubmed_publication` | `authors_with_affiliations` | ordered sequence | `authors_with_affiliations_raw_json` | `authors_with_affiliations_canonical_json` |
| `pubmed_publication` | `affiliation_structured` | unordered set | `affiliation_structured_raw_json` | `affiliation_structured_canonical_json` |
| `semanticscholar_publication` | `author_h_indices` | ordered sequence | `author_h_indices_raw_json` | `author_h_indices_canonical_json` |
| `semanticscholar_publication` | `citation_contexts` | ordered sequence | `citation_contexts_raw_json` | `citation_contexts_canonical_json` |
| `semanticscholar_publication` | `publication_types` | unordered set | `publication_types_raw_json` | `publication_types_canonical_json` |
| `semanticscholar_publication` | `subject_fields` | unordered set | `subject_fields_raw_json` | `subject_fields_canonical_json` |

These payloads are semantic-sensitive evidence surfaces. Canonical JSON is not a
drop-in replacement for the raw provider object/list when future semantic
extraction happens.

## Composite Publication Impact

`composite_publication` currently treats normalization as a join-key and
upstream-inheritance problem, not as a second full publication-field
normalization pass.

Current join-key contract:

- primary joins: `doi`, `pmid`
- fallback join: `title`

Current composite behavior:

- enrichment sources are `crossref_publication`, `openalex_publication`,
  `pubmed_publication`, and `semanticscholar_publication`
- provider-normalized non-key fields such as `publication_type_unified`,
  `publication_class`, `oa_status`, `grants`, and `primary_topic` remain
  upstream inherited in matrix evidence
- changing upstream publication normalization can therefore change composite
  outputs and `content_hash` indirectly even when composite code is untouched

Source of truth:
[configs/composites/publication.yaml](../../../configs/composites/publication.yaml).

## Related References

- [non-chembl-normalization-overview.md](non-chembl-normalization-overview.md)
- [reference-identifiers.md](reference-identifiers.md)
- [OpenAlex provider reference](../providers/openalex/publication.md)
- [PubMed provider reference](../providers/pubmed/publication.md)
- [CrossRef provider reference](../providers/crossref/publication.md)
- [Semantic Scholar provider reference](../providers/semanticscholar/publication.md)
