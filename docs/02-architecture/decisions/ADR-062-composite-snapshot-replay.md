Version: 1.0.0
Status: Added
Acceptance: Pending (RF-002 implementation and acceptance in progress)
Class: internal
Owner: BioETL Team
Last verified: '2026-10-03'

# ADR-062: Composite replay from verified child snapshots

## Context

Composite execution success does not establish replay readiness. The existing
rebuild-only boundary cannot be removed merely by changing a dashboard verdict.
RF-002 requires an executable replay path and evidence for every participating
source, with the normal execution and data-quality gates preserved.

## Decision

Provide `run-composite --replay-of-manifest-id` for completed composites with
verified child manifest bindings. Preserve the captured `--limit 1000` and
require the same clean source revision, dependency lock and composite config.
Reject resume, stage-selection overrides, user-selected caches and dry runs.

At successful completion, bind actual successful child runs to the parent.
Verify their saved effective configs, archived dependency locks and every Bronze
batch before publishing the bindings. Missing, partial or failed children cannot
be silently substituted with current provider responses.

At replay, validate the parent and every child again. Copy only the referenced
hash-verified batches to private staging directories, verify each copy, and run
the existing child transformations and composite merge against those snapshots.
Do not select all batches from a date directory. Missing bindings or changed
bytes fail before a live-provider fallback can occur. Explicit cache locations
must remain resolvable from persisted manifests, including Windows file URIs.

Family support is an engine capability. Per-run readiness additionally requires
the complete bound child envelope and current object verification. Older
composites without these bindings remain outside this execution path. Existing
immutable report revisions must not be rewritten to appear successful.

## Validation and acceptance

Unit coverage must exercise missing children, drifted config/code/lock, modified
Bronze bytes, absent seed bindings, foreign stages and the absence of live
fallback. Integration proof must replay into empty output tables with external
socket connections denied, then compare every output column and row with the
original execution. Run all five composite acceptance cases and the complete
54-case matrix on the final candidate SHA before closing RF-002–RF-016.

The first activity execution proof reproduced all 924 Gold rows, every column
and the schema with external network access denied. Its replay report exposed a
custom-cache URI defect; that finding must be fixed and revalidated before
acceptance. This evidence is intermediate, not completion of the matrix.

## Relationship to prior boundary

This decision proposes the scoped execution extension described as Option B in
the July 27 composite rebuild-only decision note. The prior boundary continues
to apply to historical composites without verified child bindings and to runs
whose exact code, config or saved objects are unavailable.

## Rollback

Disable the new replay option and retain the saved manifests and snapshot
objects for diagnosis. Do not reinterpret an incomplete run as successful and
do not lower Saved Evidence, Replay Readiness or data-quality requirements.

## Stable record ordinals

Bronze JSONL already sorts the canonical serialized records within each batch.
Live and replay transformations use that same order before assigning `_index`;
the ordinal identifies the record in the persisted batch, plus its batch start
offset. Provider response order cannot change this diagnostic column. This
preserves the all-column replay comparison instead of excluding `_index`.
