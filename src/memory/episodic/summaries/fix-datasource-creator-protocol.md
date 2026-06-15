---
id: fix-datasource-creator-protocol
title: Fix datasource creator protocol mismatch
task_id: fix-datasource-creator-protocol
created_at: '2026-06-15T17:33:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/datasource/data_source_factory.py
summary: Restored explicit DataSourceCreatorProtocol parameter names on the lazy datasource
  creator wrapper in data_source_factory.py so protocol introspection tests no longer
  see only args/kwargs.
---

# Episodic summary

## Task

- Title: Fix datasource creator protocol mismatch

## Outcome

- Restored explicit DataSourceCreatorProtocol parameter names on the lazy datasource creator wrapper in data_source_factory.py so protocol introspection tests no longer see only args/kwargs.

## Lessons learned

- Replace with durable follow-up if needed
