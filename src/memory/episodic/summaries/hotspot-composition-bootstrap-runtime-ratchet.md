---
id: hotspot-composition-bootstrap-runtime-ratchet
title: Fix composition bootstrap runtime hotspot family ratchet regression
task_id: hotspot-composition-bootstrap-runtime-ratchet
created_at: '2026-06-03T08:10:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/runtime/_composite_plan_support.py
summary: Reduced composition_bootstrap_runtime files >=250 LOC from 3 to 2 by moving
  final composite runner plan delegation from _composite_plan_support.py into existing
  _composite_plan_runtime_support.py, preserving the files_ge_250_loc budget at 2.
  Refreshed hotspot-family baseline, module coverage inventory, and architecture dependency
  map; targeted runtime and architecture checks passed.
---

# Episodic summary

## Task

- Title: Fix composition bootstrap runtime hotspot family ratchet regression

## Outcome

- Reduced composition_bootstrap_runtime files >=250 LOC from 3 to 2 by moving final composite runner plan delegation from _composite_plan_support.py into existing _composite_plan_runtime_support.py, preserving the files_ge_250_loc budget at 2. Refreshed hotspot-family baseline, module coverage inventory, and architecture dependency map; targeted runtime and architecture checks passed.

## Lessons learned

- Replace with durable follow-up if needed
