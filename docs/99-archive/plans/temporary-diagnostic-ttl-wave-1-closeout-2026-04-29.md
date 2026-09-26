# Temporary Diagnostic TTL Wave 1 Closeout 2026-04-29

## Scope

This note records the first bounded execution wave against the
`temporary_diagnostic` bucket after the TTL review plan was introduced.

## Decisions

### Deleted

- legacy Mistral image download helper under `scripts/ai/`
- `scripts/engineering/dev/python/fix_neo4j_memory_sync_http_uris.py`

Reason:

- both files had zero live references in the current inventory snapshot
- neither file had maintained docs, test, or router callers
- both were one-shot or legacy recovery helpers rather than stable workflows

### Reclassified

- `scripts/engineering/qa/hotspot_family_metrics.py`
  - from `temporary_diagnostic`
  - to `supporting`

Reason:

- the file is consumed by QA report generation and architecture ratchet tests
- the previous temporary-diagnostic classification was stale because the
  inventory scanner did not capture import-based usage strongly enough
- it is better modeled as a retained shared helper module than as a bounded
  troubleshooting script

## Updated Inventory Baseline

After this wave:

- `scripts=363`
- `active=319`
- `supporting=27`
- `temporary_diagnostic=17`
- `orphan=0`
- `unknown=0`
- `legacy=0`

## Follow-Up

The next TTL wave should stay bounded and continue avoiding the Neo4j/operator
troubleshooting bucket until the cheaper local repair and convenience helpers
are exhausted.
