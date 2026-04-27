# Residual Test/CI Debt — Implementation Backlog

Date: 2026-04-01
Status: active

## Scope

Tracks residual test and CI infrastructure debt items tied to structural
watchlist families.

## Active Items

1. **Fixture governance rollout** — VCR cassette metadata catalog backfill
   and age-policy enforcement.
1. **Environment-limited test skip budget** — Reduce max-skip-rate through
   targeted cassette recording for missing provider endpoints.
1. **Replay fixture governance** — Connect fixture governance ledger to
   architecture test ratchets for automated regression detection.

## Priority

- P0: Fixture governance (replay confidence directly impacts CI trust)
- P1: Skip budget reduction (environment-limited tests mask coverage gaps)
- P2: Structural watchlist automation (currently manual review)
