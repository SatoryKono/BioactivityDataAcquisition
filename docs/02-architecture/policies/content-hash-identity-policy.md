---
Version: 1.0.0
Status: Active canonical policy
Class: published
Owner: Architecture / Domain
Reviewers:
- BioETL Team
Last verified: '2026-04-09'
---

# Content Hash Identity Policy (Canonical)

**Last updated:** 2026-02-18

## Scope

This document is the single canonical policy for determining which fields affect
`content_hash` and identity in BioETL.

Cross-reference:

- RULES.md §2.8.1, §6.1
- `docs/05-engineering/normalization-plan-P0-P6.md`
- ADR-014 (determinism context)
- `src/bioetl/domain/constants.py` (`META_FIELDS`)
- `src/bioetl/domain/transformations/hashing.py` (`_should_include_field`)

This policy remains the canonical contract for `content_hash` field inclusion.
The broader normalization rollout across RunManifest, RunLedger, runtime
anchors, and ChemBL Activity is coordinated by
`docs/05-engineering/normalization-plan-P0-P6.md`.

## Canonical Rule

`content_hash` is computed as:

`sha256(provider + canonical_json(normalized_record)).hexdigest()`

The resulting lexical form is plain lowercase 64-character hex without a
`sha256:` prefix.

Before hashing:

1. Normalize values (`NaN/Inf -> null`, float rounding, date ISO, string strip).
1. Exclude all technical metadata fields from identity.
1. Serialize only through the canonical JSON helper in
   `src/bioetl/domain/serialization.py` /
   `src/bioetl/domain/normalization/json.py`.

### Metadata exclusion policy (MUST)

A field **MUST NOT** affect identity/hash if its name starts with `_`.

This includes (non-exhaustive):

- `_ingestion_ts`
- `_run_id`
- `_run_type`
- `_dq_warn`, `_dq_error`, `_dq_*`
- `_source_batch_id`
- `_index`
- `_lookup_method`
- `_original_id`
- `_source`
- Future technical fields like `_new_field`

## Rationale

1. Prevents identity churn from operational metadata.
1. Preserves deterministic identity under schema drift when new technical fields
   are introduced.
1. Keeps dedup/version semantics tied to business content only.

## Contract tests

- Property-based determinism: metadata-only changes keep hash stable.
- Schema drift contract: adding new `_` fields keeps hash stable.
