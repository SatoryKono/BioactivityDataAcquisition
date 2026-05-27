---
id: fix-uuid-seam-test
title: Fix runtime UUID seam inventory git ls-files fallback
task_id: fix-uuid-seam-test
created_at: '2026-05-27T05:51:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_boundary_assertions.py
summary: Resolved subsequent architecture governance regression by adding explicit
  architecture marker to tests/architecture/test_boundary_assertions.py, restoring
  markerless budget compliance while keeping oversized module inventory checks green.
---

# Episodic summary

## Task

- Title: Fix runtime UUID seam inventory git ls-files fallback

## Outcome

- Resolved subsequent architecture governance regression by adding explicit architecture marker to tests/architecture/test_boundary_assertions.py, restoring markerless budget compliance while keeping oversized module inventory checks green.

## Lessons learned

- Replace with durable follow-up if needed
