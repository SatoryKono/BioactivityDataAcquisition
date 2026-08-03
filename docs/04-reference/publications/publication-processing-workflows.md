______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Publication Processing Workflows

**Issue:** #6560
**Normalization:** [publication-normalization.md](../normalization/publication-normalization.md)
**Validation guide:** [publication-validation-guide.md](../../03-guides/publication-validation-guide.md)

## Providers

| Provider | Spec root | Notes |
| --- | --- | --- |
| PubMed | `pipelines/pubmed/` | XML parse / search-fetch |
| CrossRef | `pipelines/crossref/` | DOI resolution |
| OpenAlex | `pipelines/openalex/` | works graph IDs |
| Semantic Scholar | `pipelines/semanticscholar/` | paper/author ids |
| ChEMBL publication | `pipelines/chembl/` publication specs | chembl-native pubs |

## Shared data model concerns

- Identifiers: DOI, PMID, PMCID (family canonicalization — not enums)
- Authors / ORCID / affiliations
- Venue (journal) metadata
- Dates (normalize to governed date policy)
- Citation / reference lists when present

## Processing stages

1. **Acquire** — provider adapter + ADR-032 HTTP resilience
2. **Bronze** — raw payload append-only
3. **Normalize** — publication profile + identifier families
4. **Validate** — Pandera + DQ hierarchy
5. **Silver/Gold** — deterministic sort + strict gold when configured
6. **Quarantine** — bad rows isolated for replay

## Cross-provider consistency

- Prefer shared publication taxonomy helpers over copy-paste mapping
- Identifier arrays use family policies ([reference-identifiers](../normalization/reference-identifiers.md))
- Composite publication entity: [composites.md](../pipelines/composites.md)

## Operator tips

- Start with one provider fixture before multi-provider merge
- Diff Bronze vs Silver on a single DOI/PMID when debugging
- Use publication validation runbook when bulk mismatches appear

## Related

- Runbook: [publication-validation-runbook](../../05-operations/runbooks/publication-validation-runbook.md)
