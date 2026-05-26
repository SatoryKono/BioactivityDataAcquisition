---
id: fix-uuid-seam-test
title: Fix runtime UUID seam inventory git ls-files fallback
task_id: fix-uuid-seam-test
created_at: '2026-05-26T12:06:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_runtime_uuid_seam_inventory.py
summary: Added resilient fallback in runtime UUID seam inventory test when git ls-files
  fails in mixed Windows/WSL environments; validated targeted architecture tests.
---

# Episodic summary

## Task

- Title: Fix runtime UUID seam inventory git ls-files fallback

## Outcome

- Added resilient fallback in runtime UUID seam inventory test when git ls-files fails in mixed Windows/WSL environments; validated targeted architecture tests.

## Lessons learned

- Replace with durable follow-up if needed
