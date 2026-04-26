______________________________________________________________________

Version: 1.0.0
Status: Active canonical policy
Class: published
Owner: Architecture / Domain
Reviewers:

- BioETL Team
  Last verified: '2026-04-09'

______________________________________________________________________

# Content Hash Identity Policy (Canonical)

**Last updated:** 2026-02-18

## Scope

This document is the single canonical policy for determining which fields affect
`content_hash` and identity in BioETL.

Cross-reference:

- RULES.md §2.8.1, §6.1
- `docs/05-engineering/normalization_plan_P0_P6.md`
- ADR-014 (determinism context)
- `src/bioetl/domain/constants.py` (`META_FIELDS`)
- `src/bioetl/domain/transformations/hashing.py` (`_should_include_field`)

This policy remains the canonical contract for `content_hash` field inclusion.
The broader normalization rollout across RunManifest, RunLedger, runtime
anchors, and ChemBL Activity is coordinated by
`docs/05-engineering/normalization_plan_P0_P6.md`.

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

## 2026-04 Evaluation Outcome

The repository intentionally keeps `content_hash` datetime semantics separate
from the broader canonical control-plane datetime normalization.

Decision:

1. Keep the current hash-identity split.
1. Do not migrate `content_hash` to UTC ISO-8601 `Z` normalization as part of
   routine cleanup work.
1. Treat any future convergence as an explicit breaking-change migration with
   versioning, golden-hash validation, and replay/dedup impact analysis.

Affected canonical consumers of the current hash-identity contract include:

- `src/bioetl/domain/transformations/hashing.py`
- `src/bioetl/infrastructure/storage/support/retention.py`
- `src/bioetl/infrastructure/storage/silver/validation_operations.py`
- `tests/unit/contracts/test_content_hash_contract.py`

Reasoning:

1. The current contract is already explicit, deterministic, and test-covered.
1. A silent datetime-semantics change would alter `content_hash` material for
   existing records and content-aware dedup paths.
1. The split is acceptable as long as it remains documented as a distinct
   hash-identity plane rather than being mistaken for a control-plane datetime
   rule.

## Contract tests

- Property-based determinism: metadata-only changes keep hash stable.
- Schema drift contract: adding new `_` fields keeps hash stable.
