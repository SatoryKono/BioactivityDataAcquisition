---
id: chembl-target-schema-fix
title: Fix chembl target schema timeout regression
task_id: chembl-target-schema-fix
created_at: '2026-06-01T05:58:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Added protein_classifications to chembl TargetSchema, updated the chembl_target
  silver schema snapshot, reran the failing advanced e2e selector, and refreshed module
  coverage source-tree/hash artifacts without changing runtime behavior outside schema
  acceptance.
---

# Episodic summary

## Task

- Title: Fix chembl target schema timeout regression

## Outcome

- Added protein_classifications to chembl TargetSchema, updated the chembl_target silver schema snapshot, reran the failing advanced e2e selector, and refreshed module coverage source-tree/hash artifacts without changing runtime behavior outside schema acceptance.

## Lessons learned

- Replace with durable follow-up if needed
