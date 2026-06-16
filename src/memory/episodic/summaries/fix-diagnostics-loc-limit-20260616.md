---
id: fix-diagnostics-loc-limit-20260616
title: Fix diagnostics CLI file size limit regression
task_id: fix-diagnostics-loc-limit-20260616
created_at: '2026-06-16T17:21:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Reduced src/bioetl/interfaces/cli/commands/diagnostics.py back to the 420
  LOC interface limit with a behavior-preserving whitespace-only trim, refreshed reports/quality/module-coverage-inventory.json
  to update source_tree_sha256, and revalidated the LOC gate plus diagnostics command
  tests.
---

# Episodic summary

## Task

- Title: Fix diagnostics CLI file size limit regression

## Outcome

- Reduced src/bioetl/interfaces/cli/commands/diagnostics.py back to the 420 LOC interface limit with a behavior-preserving whitespace-only trim, refreshed reports/quality/module-coverage-inventory.json to update source_tree_sha256, and revalidated the LOC gate plus diagnostics command tests.

## Lessons learned

- Replace with durable follow-up if needed
