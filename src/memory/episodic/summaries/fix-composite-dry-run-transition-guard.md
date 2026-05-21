---
id: fix-composite-dry-run-transition-guard
title: Fix composite dry-run transition guard
task_id: fix-composite-dry-run-transition-guard
created_at: '2026-05-21T09:58:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/composite/state.py
summary: Restored strict domain composite FSM by removing ENRICHMENT_COMPLETED->COMPLETED,
  and moved the dry-run merge-skip shortcut into an explicit application-layer recovery
  transition guarded by runtime.dry_run.
---

# Episodic summary

## Task

- Title: Fix composite dry-run transition guard

## Outcome

- Restored strict domain composite FSM by removing ENRICHMENT_COMPLETED->COMPLETED, and moved the dry-run merge-skip shortcut into an explicit application-layer recovery transition guarded by runtime.dry_run.

## Lessons learned

- Replace with durable follow-up if needed
