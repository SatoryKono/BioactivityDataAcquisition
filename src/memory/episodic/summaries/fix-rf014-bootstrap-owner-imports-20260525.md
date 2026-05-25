---
id: fix-rf014-bootstrap-owner-imports-20260525
title: Fix RF014 bootstrap owner imports
task_id: fix-rf014-bootstrap-owner-imports-20260525
created_at: '2026-05-25T13:07:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/runtime/pipeline.py
summary: Restored pipeline.py to phase-helper bootstrap behavior while keeping RF-014
  required helper-owner imports visible; RF-014 and bootstrap unit checks pass.
---

# Episodic summary

## Task

- Title: Fix RF014 bootstrap owner imports

## Outcome

- Restored pipeline.py to phase-helper bootstrap behavior while keeping RF-014 required helper-owner imports visible; RF-014 and bootstrap unit checks pass.

## Lessons learned

- RF-014 import-governance checks can require explicit owner imports even when
  runtime behavior is delegated through narrower phase-helper seams.
