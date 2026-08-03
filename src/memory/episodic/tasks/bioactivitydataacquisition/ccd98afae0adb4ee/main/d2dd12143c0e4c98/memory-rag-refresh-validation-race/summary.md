---
record_id: memory-rag-refresh-validation-race
record_type: working
repo_id: bioactivitydataacquisition
git_commit: d378315604d934330b593cdf2f355012ef2afa26
branch: main
worktree_id: ccd98afae0adb4ee
task_id: memory-rag-refresh-validation-race
actor:
  runtime: codex
  agent: root
  model: null
created_at: '2026-07-31T06:38:29.122323+00:00'
source_refs:
- src/memory/rag/indexing.py
- src/memory/rag/_validation_model.py
- tests/unit/memory/test_rag_indexing.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: df67830a8e3f2be55ba13f986aa5a2576da5a30f60f749d93f3ba34cd3d3c964
id: memory-rag-refresh-validation-race
title: Fix immediate RAG manifest drift
ttl_days: 14
confidence: episodic
summary: Detected concurrent source edits and deletion during full RAG generation.
  RAG indexing now hashes captured per-source identities, verifies the source surface
  remained stable, retries a bounded maximum of three times on content changes or
  disappearance, and publishes only a coherent manifest pair. Added mutation and deletion
  race regression tests.
---

# Episodic summary

## Task

- Title: Fix immediate RAG manifest drift

## Outcome

- Detected concurrent source edits and deletion during full RAG generation. RAG indexing now hashes captured per-source identities, verifies the source surface remained stable, retries a bounded maximum of three times on content changes or disappearance, and publishes only a coherent manifest pair. Added mutation and deletion race regression tests.

## Lessons learned

- Replace with durable follow-up if needed
