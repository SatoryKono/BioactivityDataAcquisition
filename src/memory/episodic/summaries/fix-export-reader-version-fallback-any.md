---
id: fix-export-reader-version-fallback-any
title: Fix export reader version fallback Any annotation
task_id: fix-export-reader-version-fallback-any
created_at: '2026-05-26T10:07:24Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/adapters/crossref/models.py
- tests/integration/infrastructure/storage/test_export_reader_version_fallback.py
summary: Fixed CrossRef Pydantic model_rebuild namespace for JsonDict/Any annotations
  and replaced export reader version fallback test native delta-rs writes with deterministic
  DeltaTable fake registry; validated WSL and Windows targeted tests.
---

# Episodic summary

## Task

- Title: Fix export reader version fallback Any annotation

## Outcome

- Fixed CrossRef Pydantic model_rebuild namespace for JsonDict/Any annotations and replaced export reader version fallback test native delta-rs writes with deterministic DeltaTable fake registry; validated WSL and Windows targeted tests.

## Lessons learned

- Replace with durable follow-up if needed
