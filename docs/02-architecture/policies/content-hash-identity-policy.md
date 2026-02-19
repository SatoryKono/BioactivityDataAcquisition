# Content Hash Identity Policy (Canonical)

**Status:** Active canonical policy
**Owner:** Architecture / Domain
**Last updated:** 2026-02-18

## Scope

This document is the single canonical policy for determining which fields affect
`content-hash` and identity in BioETL.

Cross-reference:

- RULES.md §2.8.1, §6.1
- ADR-014 (determinism context)
- `src/bioetl/domain/constants.py` (`META-FIELDS`)
- `src/bioetl/domain/transformations.py` (`-should-include-field`)

## Canonical Rule

`content-hash` is computed as:

`sha256(provider + canonical-json-dumps(normalized-record))`

Before hashing:

1. Normalize values (`NaN/Inf -> null`, float rounding, date ISO, string strip).
1. Exclude all technical metadata fields from identity.

### Metadata exclusion policy (MUST)

A field **MUST NOT** affect identity/hash if its name starts with `-`.

This includes (non-exhaustive):

- `-ingestion-ts`
- `-run-id`
- `-run-type`
- `-dq-warn`, `-dq-error`, `-dq-*`
- `-source-batch-id`
- `-index`
- `-lookup-method`
- `-original-id`
- `-source`
- Future technical fields like `-new-field`

## Rationale

1. Prevents identity churn from operational metadata.
1. Preserves deterministic identity under schema drift when new technical fields
   are introduced.
1. Keeps dedup/version semantics tied to business content only.

## Contract tests

- Property-based determinism: metadata-only changes keep hash stable.
- Schema drift contract: adding new `-` fields keeps hash stable.
