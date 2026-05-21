---
id: composite-dry-run-fsm-20260521
title: Fix composite dry-run FSM regression
task_id: composite-dry-run-fsm-20260521
created_at: '2026-05-21T08:03:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/composite/state.py
summary: Allowed composite dry-run completion to transition directly from enrichment_completed
  to completed and codified the shortcut in FSM tests.
---

# Episodic summary

## Task

- Title: Fix composite dry-run FSM regression

## Outcome

- Allowed composite dry-run completion to transition directly from enrichment_completed to completed and codified the shortcut in FSM tests.

## Lessons learned

- Replace with durable follow-up if needed
