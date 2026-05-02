______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-02'

______________________________________________________________________

# Publication Normalization Policy

This note defines the governance boundary for non-ChEMBL publication type
surfaces across PubMed, CrossRef, OpenAlex, and Semantic Scholar.

## Rule

Raw provider type fields are preserved as provider-native sidecars.

Examples:

- `crossref.publication.publication_type`
- `openalex.publication.publication_type`
- `openalex.publication.type_crossref`
- `pubmed.publication.publication_type`
- `semanticscholar.publication.publication_type`
- structured raw lists such as `publication_type_list` and `publication_types`

These fields are not strict enums. Unknown future provider values must survive
normalization when they are non-empty.

## Derived Taxonomy

Strict classification belongs only to the derived harmonized fields:

- `publication_type_unified`
- `publication_subclass`
- `publication_class`

These fields normalize against
`configs/enums/publication_type_classification.csv` and fail closed for
unknown values.

## DQ Guidance

DQ for raw provider type fields may enforce format or non-empty constraints,
but must not reject unknown provider-native labels solely because current
fixtures have low cardinality.

Conditional business rules should key off derived taxonomy fields, not raw
provider labels.
