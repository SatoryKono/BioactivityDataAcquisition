______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Identifier Family Policies

**Issue:** #6562
**Concise SSOT:** [reference-identifiers.md](reference-identifiers.md)
**Detailed families:** [reference-identifier-families.md](../../03-data-model/reference-identifier-families.md)

## Core rule

Identifiers are normalized by **family** (canonical form + collection semantics).
They are **not** closed enums unless an explicit enum SSOT exists for that field.

## Policy table (operator summary)

| Family | Canonical form | Collection | Fail mode |
| --- | --- | --- | --- |
| DOI | lowercase DOI string per profile rules | scalar / set | validate format; quarantine bad |
| PMID / PMCID | digits / PMC+digits per family rules | scalar / set | format check |
| ORCID | `0000-0000-0000-0000` | set-like array | format check |
| ROR | `https://ror.org/…` | set-like array | format check |
| OpenAlex | `W/A/I/T` + digits | scalar or set | prefix family rules |
| Semantic Scholar | lowercase hex ids | scalar / set | length/charset |
| UniProt accession | uppercase accession | scalar / set | pattern |
| GO / InterPro / Pfam / … | family prefixes | set-like JSON/array | pattern |

## Governance rules

1. Canonicalize **before** identity hashing.
2. Arrays are set-like: sort + dedupe per family semantics.
3. Do not invent a second mapping table in transformers.
4. Cross-provider publication fields share taxonomy helpers when available.
5. Document new families in the detailed data-model page + this summary.

## Testing

- Edge fixtures for empty, null, malformed, mixed-case inputs
- Composite boundaries must not re-break canonical forms

## Related

- [publication processing workflows](../publications/publication-processing-workflows.md)
- [non-chembl-normalization-overview](non-chembl-normalization-overview.md)
