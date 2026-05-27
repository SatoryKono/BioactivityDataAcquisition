---
id: fix-registry-threading-pydantic-any
title: Fix registry threading Pydantic Any annotation
task_id: fix-registry-threading-pydantic-any
created_at: '2026-05-26T10:13:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/adapters/crossref/models.py
- tests/architecture/test_registry_threading.py
summary: Fixed CrossRef Pydantic response wrapper model_rebuild namespace so JsonDict/Any
  forward annotations resolve during register_all_pipelines imports; validated registry
  threading tests on WSL and Windows.
---

# Episodic summary

## Task

- Title: Fix registry threading Pydantic Any annotation

## Outcome

- Fixed CrossRef Pydantic response wrapper model_rebuild namespace so JsonDict/Any forward annotations resolve during register_all_pipelines imports; validated registry threading tests on WSL and Windows.

## Lessons learned

- Replace with durable follow-up if needed
