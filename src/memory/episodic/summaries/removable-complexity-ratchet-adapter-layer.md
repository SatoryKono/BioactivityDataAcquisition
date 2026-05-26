---
id: removable-complexity-ratchet-adapter-layer
title: Fix adapter layer removable complexity ratchet
task_id: removable-complexity-ratchet-adapter-layer
created_at: '2026-05-26T12:17:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py
- src/bioetl/infrastructure/adapters/chembl/_fetch_resilience_error.py
summary: Extracted ChEMBL fetch error wrapping helper so adapter_layer >=250 LOC file
  count returns to the reviewed budget.
---

# Episodic summary

## Task

- Title: Fix adapter layer removable complexity ratchet

## Outcome

- Extracted ChEMBL fetch error wrapping helper so adapter_layer >=250 LOC file count returns to the reviewed budget.

## Lessons learned

- Replace with durable follow-up if needed
