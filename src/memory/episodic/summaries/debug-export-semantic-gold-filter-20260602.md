---
id: debug-export-semantic-gold-filter-20260602
title: Add structured diagnostics for semantic gold filter exclusions
task_id: debug-export-semantic-gold-filter-20260602
created_at: '2026-06-02T16:29:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Semantic gold filter exclusions now preserve FilterDecision diagnostics in
  debug export. Batch transformer extracts filter decision details from bound gold
  filter callbacks, debug export collector writes failed_field/failed_value/expected_constraint
  for SEMANTIC_FILTER_EXCLUDED rows, and unit tests cover both the helper and the
  resulting gold_rejected rows.
---

# Episodic summary

## Task

- Title: Add structured diagnostics for semantic gold filter exclusions

## Outcome

- Semantic gold filter exclusions now preserve FilterDecision diagnostics in debug export. Batch transformer extracts filter decision details from bound gold filter callbacks, debug export collector writes failed_field/failed_value/expected_constraint for SEMANTIC_FILTER_EXCLUDED rows, and unit tests cover both the helper and the resulting gold_rejected rows.

## Lessons learned

- Replace with durable follow-up if needed
