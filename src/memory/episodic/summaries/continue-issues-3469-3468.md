---
id: continue-issues-3469-3468
title: Complete GitHub issues 3469 and 3468
task_id: continue-issues-3469-3468
created_at: '2026-04-30T18:30:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- github-issues-3469-3468
summary: 'Implemented #3469 by routing effective-config stable_hash through the shared
  domain canonical JSON serializer while preserving effective-config-specific to_jsonable
  coercion. Added tests for canonical serializer parity and non-finite float rejection.
  Implemented #3468 by adding bounded continuation_mode diagnostics for exact replay,
  ordinary checkpoint-only resume, composite checkpoint-plus-ledger-suffix resume,
  full-scan idempotent rebuild, and rebuild-only paths while keeping resume_mode backward-compatible.
  Propagated continuation_mode through diagnostics, identity graph, CLI output, docs,
  and golden fixtures. Validation passed: 111 focused effective-config/run-manifest/CLI
  tests, 19 layer dependency tests, and ruff on changed files.'
---

# Episodic summary

## Task

- Title: Complete GitHub issues 3469 and 3468

## Outcome

- Implemented #3469 by routing effective-config stable_hash through the shared domain canonical JSON serializer while preserving effective-config-specific to_jsonable coercion. Added tests for canonical serializer parity and non-finite float rejection. Implemented #3468 by adding bounded continuation_mode diagnostics for exact replay, ordinary checkpoint-only resume, composite checkpoint-plus-ledger-suffix resume, full-scan idempotent rebuild, and rebuild-only paths while keeping resume_mode backward-compatible. Propagated continuation_mode through diagnostics, identity graph, CLI output, docs, and golden fixtures. Validation passed: 111 focused effective-config/run-manifest/CLI tests, 19 layer dependency tests, and ruff on changed files.

## Lessons learned

- Replace with durable follow-up if needed
