# ADR-030: Publication Field Naming Unification

**Status:** Superseded (archived; canonical ADR-030: `docs/02-architecture/decisions/ADR-030-publication-pagination-strategy.md`)
**Date:** 2026-01-29
**Decision makers:** @BioETL-Team
**Relates to:** ADR-024 (Entity Naming Unification), configs/composite/field-groups/publication.yaml, configs/schemas/composite/publication.yaml

> **Note**: This is a draft outside the ADR registry. ADR-030 is reserved for the publication pagination strategy in `ADR-030-publication-pagination-strategy.md`. Track current work in `PUBLICATION-FIELD-UNIFICATION-PROGRESS.md`.

## Context

Publication transformers and schemas for ChEMBL, CrossRef, OpenAlex, PubMed, and SemanticScholar expose overlapping
fields with inconsistent naming. The composite pipeline configuration currently consumes these names directly,
which makes cross-provider aggregation fragile and adds redundant storage:

- `author-orcids` is a JSON list but is not named as a list.
- `publication-type-list` duplicates `publication-types`.
- `authors-with-affiliations` overlaps with `authors`, `affiliation-list`, and `affiliation-structured`.
- `references` is ambiguous next to `citations-made` and does not match the composite group name.

## Decision

Unify publication field names across provider transformers, provider schemas, and composite configuration.

| Current name | Target name | Providers / locations | Change type |
| --- | --- | --- | --- |
| `author-orcids` | `author-orcid-list` | CrossRef, OpenAlex, SemanticScholar transformers and schemas; composite config | Breaking rename with 14-day deprecation |
| `publication-type-list` | remove (use `publication-types`) | PubMed transformer and schema; composite config | Removal of redundant field |
| `authors-with-affiliations` | deprecate (use `authors`, `affiliation-list`, `affiliation-structured`) | PubMed transformer and schema; composite config | Deprecation due to redundancy |
| `references` | `citation-references` | CrossRef transformer; composite config | Non-breaking alias (canonical rename) |

## Justification

- `author-orcids` -> `author-orcid-list`: makes list semantics explicit, aligns with existing `*-list` fields
  (e.g., `issn-list`), and reduces schema ambiguity for JSON array validators.
- `publication-type-list` removal: the same data already exists as `publication-types`, so keeping both creates
  redundant storage and ambiguous source-of-truth for downstream analytics.
- `authors-with-affiliations` deprecation: it duplicates hashed author data plus structured affiliations that are
  already available as `authors`, `affiliation-list`, and `affiliation-structured`, and it inflates record size.
- `references` -> `citation-references`: clarifies that the field contains detailed citation references, avoids
  confusion with citation counts, and matches the composite group name `citation-references`.

## Backward Compatibility Plan (14-day deprecation)

Day 0 (release):
- Emit new canonical fields from transformers while still emitting legacy names.
- Add schema aliases: `author-orcids` -> `author-orcid-list`, `references` -> `citation-references`.
- Mark `authors-with-affiliations` and `publication-type-list` as deprecated in docs and pipeline metadata.
- Update composite merge rules to prefer new names when both exist.

Days 1-13:
- Monitor downstream usage and warn on legacy field access in analytics queries and validation outputs.
- Update consumer code and dashboards to read canonical fields only.

Day 14:
- Remove legacy fields from transformers, schemas, and composite configs.
- Drop legacy columns from Silver and Gold tables after data backfill is complete.

## Migration Path for Existing Data

1. Add new columns to Silver and Gold tables:
   - `author-orcid-list` populated from `author-orcids` where present.
   - `citation-references` populated from `references` where present.
2. For PubMed records, keep `publication-types` as the canonical list. If historical rows only have
   `publication-type-list`, backfill `publication-types` from it and then drop `publication-type-list`.
3. Leave `authors-with-affiliations` in place during the deprecation window. Consumers should migrate to
   `authors`, `affiliation-list`, and `affiliation-structured` without relying on a backfill.
4. After 14 days, remove legacy columns and any compatibility views or aliases.

## Consequences

### Positive

- Clear, consistent naming across providers and composite aggregation.
- Reduced schema ambiguity for JSON list fields.
- Lower data redundancy and smaller Silver/Gold storage footprint.

### Negative

- Short-term breaking change for `author-orcids` consumers.
- Requires coordinated migration of stored data and downstream queries.

## Implementation

Update the following areas in one coordinated release:

- `configs/composite/field-groups/publication.yaml`
- `configs/pipelines/composite/publication.yaml`
- `configs/schemas/{provider}/publication.yaml` for chembl, crossref, openalex, pubmed, semanticscholar
- `src/bioetl/application/pipelines/{provider}/transformer.py` for the same providers
- Any schema validators and tests that reference legacy field names

## Tests

- Update unit tests for provider transformers to assert canonical field names.
- Update composite pipeline tests and fixtures to use `author-orcid-list` and `citation-references`.

## References

- `configs/composite/field-groups/publication.yaml`
- `configs/pipelines/composite/publication.yaml`
- `configs/schemas/composite/publication.yaml`
- `src/bioetl/application/pipelines/crossref/transformer.py`
