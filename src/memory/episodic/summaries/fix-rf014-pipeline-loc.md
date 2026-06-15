---
id: fix-rf014-pipeline-loc
title: Fix RF-014 pipeline bootstrap LOC regression
task_id: fix-rf014-pipeline-loc
created_at: '2026-06-15T17:52:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/runtime/pipeline.py
summary: Reduced composition/bootstrap/runtime/pipeline.py back under the RF-014 LOC
  ratchet by compressing import and export formatting without changing runtime behavior
  or helper ownership.
---

# Episodic summary

## Task

- Title: Fix RF-014 pipeline bootstrap LOC regression

## Outcome

- Reduced composition/bootstrap/runtime/pipeline.py back under the RF-014 LOC ratchet by compressing import and export formatting without changing runtime behavior or helper ownership.

## Lessons learned

- Replace with durable follow-up if needed
