---
id: gold-schema-drift-20260524
title: Investigate chembl_cell_line gold schema drift
task_id: gold-schema-drift-20260524
created_at: '2026-05-24T12:28:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_gold_schema_snapshot_registry.py
summary: Synchronized chembl_cell_line Gold published contract and snapshot registry
  with the current ChEMBLCellLineGoldSchema after detecting stale cell_type and clo_id
  omissions.
---

# Episodic summary

## Task

- Title: Investigate chembl_cell_line gold schema drift

## Outcome

- Synchronized chembl_cell_line Gold published contract and snapshot registry with the current ChEMBLCellLineGoldSchema after detecting stale cell_type and clo_id omissions.

## Lessons learned

- Replace with durable follow-up if needed
