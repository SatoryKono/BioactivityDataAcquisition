---
id: fix-ruff-up037-datasource-factory
title: Fix ruff UP037 in datasource factory
task_id: fix-ruff-up037-datasource-factory
created_at: '2026-06-15T18:08:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/datasource/data_source_factory.py
summary: Removed unnecessary quoted future-style type annotations from the lazy datasource
  creator wrapper in data_source_factory.py so ruff UP037 budget returns to zero.
---

# Episodic summary

## Task

- Title: Fix ruff UP037 in datasource factory

## Outcome

- Removed unnecessary quoted future-style type annotations from the lazy datasource creator wrapper in data_source_factory.py so ruff UP037 budget returns to zero.

## Lessons learned

- Replace with durable follow-up if needed
