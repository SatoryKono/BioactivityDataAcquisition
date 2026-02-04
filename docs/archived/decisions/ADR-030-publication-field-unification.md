# ADR-030: Publication Field Naming Unification

**Status:** Proposed
**Date:** 2026-01-29
**Decision makers:** @BioETL-Team
**Relates to:** ADR-024 (Entity Naming Unification), configs/composite/field_groups/publication.yaml, configs/data_schema/composite/publication.yaml

> **Note**: This is a draft outside the ADR registry. ADR-030 is reserved for the publication pagination strategy in `ADR-030-publication-pagination-strategy.md`. Track current work in `PUBLICATION_FIELD_UNIFICATION_PROGRESS.md`.

## Context

Publication transformers and schemas for ChEMBL, CrossRef, OpenAlex, PubMed, and SemanticScholar expose overlapping
fields with inconsistent naming. The composite pipeline configuration currently consumes these names directly,
which makes cross-provider aggregation fragile and adds redundant storage:

- `author_orcids` is a JSON list but is not named as a list.
- `publication_type_list` duplicates `publication_types`.
- `authors_with_affiliations` overlaps with `authors`, `affiliation_list`, and `affiliation_structured`.
- `references` is ambiguous next to `citations_made` and does not match the composite group name.

## Decision

Unify publication field names across provider transformers, provider schemas, and composite configuration.

| Current name | Target name | Providers / locations | Change type |
| --- | --- | --- | --- |
| `author_orcids` | `author_orcid_list` | CrossRef, OpenAlex, SemanticScholar transformers and schemas; composite config | Breaking rename with 14-day deprecation |
| `publication_type_list` | remove (use `publication_types`) | PubMed transformer and schema; composite config | Removal of redundant field |
| `authors_with_affiliations` | deprecate (use `authors`, `affiliation_list`, `affiliation_structured`) | PubMed transformer and schema; composite config | Deprecation due to redundancy |
| `references` | `citation_references` | CrossRef transformer; composite config | Non-breaking alias (canonical rename) |

## Justification

- `author_orcids` -> `author_orcid_list`: makes list semantics explicit, aligns with existing `*_list` fields
  (e.g., `issn_list`), and reduces schema ambiguity for JSON array validators.
- `publication_type_list` removal: the same data already exists as `publication_types`, so keeping both creates
  redundant storage and ambiguous source-of-truth for downstream analytics.
- `authors_with_affiliations` deprecation: it duplicates hashed author data plus structured affiliations that are
  already available as `authors`, `affiliation_list`, and `affiliation_structured`, and it inflates record size.
- `references` -> `citation_references`: clarifies that the field contains detailed citation references, avoids
  confusion with citation counts, and matches the composite group name `citation_references`.

## Backward Compatibility Plan (14-day deprecation)

Day 0 (release):
- Emit new canonical fields from transformers while still emitting legacy names.
- Add schema aliases: `author_orcids` -> `author_orcid_list`, `references` -> `citation_references`.
- Mark `authors_with_affiliations` and `publication_type_list` as deprecated in docs and pipeline metadata.
- Update composite merge rules to prefer new names when both exist.

Days 1-13:
- Monitor downstream usage and warn on legacy field access in analytics queries and validation outputs.
- Update consumer code and dashboards to read canonical fields only.

Day 14:
- Remove legacy fields from transformers, schemas, and composite configs.
- Drop legacy columns from Silver and Gold tables after data backfill is complete.

## Migration Path for Existing Data

1. Add new columns to Silver and Gold tables:
   - `author_orcid_list` populated from `author_orcids` where present.
   - `citation_references` populated from `references` where present.
2. For PubMed records, keep `publication_types` as the canonical list. If historical rows only have
   `publication_type_list`, backfill `publication_types` from it and then drop `publication_type_list`.
3. Leave `authors_with_affiliations` in place during the deprecation window. Consumers should migrate to
   `authors`, `affiliation_list`, and `affiliation_structured` without relying on a backfill.
4. After 14 days, remove legacy columns and any compatibility views or aliases.

## Consequences

### Positive

- Clear, consistent naming across providers and composite aggregation.
- Reduced schema ambiguity for JSON list fields.
- Lower data redundancy and smaller Silver/Gold storage footprint.

### Negative

- Short-term breaking change for `author_orcids` consumers.
- Requires coordinated migration of stored data and downstream queries.

## Implementation

Update the following areas in one coordinated release:

- `configs/composite/field_groups/publication.yaml`
- `configs/pipelines/composite/publication.yaml`
- `configs/data_schema/{provider}/publication.yaml` for chembl, crossref, openalex, pubmed, semanticscholar
- `src/bioetl/application/pipelines/{provider}/transformer.py` for the same providers
- Any schema validators and tests that reference legacy field names

## Tests

- Update unit tests for provider transformers to assert canonical field names.
- Update composite pipeline tests and fixtures to use `author_orcid_list` and `citation_references`.

## References

- `configs/composite/field_groups/publication.yaml`
- `configs/pipelines/composite/publication.yaml`
- `configs/data_schema/composite/publication.yaml`
- `src/bioetl/application/pipelines/crossref/transformer.py`
