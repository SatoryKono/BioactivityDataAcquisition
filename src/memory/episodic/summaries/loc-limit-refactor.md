---
id: loc-limit-refactor
title: Reduce LOC for composition and interfaces files
task_id: loc-limit-refactor
created_at: '2026-05-31T17:44:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_code_metrics.py
summary: Split composition and HTTP helper modules to bring composition and interfaces
  files back under LOC limits, shortened control-plane checkpoint freshness routing
  below the function-length gate, preserved public helper surfaces for tests, and
  refreshed module-coverage inventory source_tree_sha256 after touching src/bioetl.
---

# Episodic summary

## Task

- Title: Reduce LOC for composition and interfaces files

## Outcome

- Split composition and HTTP helper modules to bring composition and interfaces files back under LOC limits, shortened control-plane checkpoint freshness routing below the function-length gate, preserved public helper surfaces for tests, and refreshed module-coverage inventory source_tree_sha256 after touching src/bioetl.

## Lessons learned

- Replace with durable follow-up if needed
