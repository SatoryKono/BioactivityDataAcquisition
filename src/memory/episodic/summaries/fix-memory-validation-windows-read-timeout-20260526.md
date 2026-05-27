---
id: fix-memory-validation-windows-read-timeout-20260526
title: Fix memory validation Windows read timeout
task_id: fix-memory-validation-windows-read-timeout-20260526
created_at: '2026-05-26T10:30:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/notes.py
- tests/unit/memory/test_notes_workflow.py
summary: Changed memory note git fallback root detection so tracked repo memory notes
  can use packaged checkout root instead of rev-parse from a potentially slow Windows
  note directory; added regression coverage and validated memory tests.
---

# Episodic summary

## Task

- Title: Fix memory validation Windows read timeout

## Outcome

- Changed memory note git fallback root detection so tracked repo memory notes can use packaged checkout root instead of rev-parse from a potentially slow Windows note directory; added regression coverage and validated memory tests.

## Lessons learned

- For repo-local memory notes on Windows-backed drives, fallback root discovery
  should avoid probing from the note directory that already timed out.
