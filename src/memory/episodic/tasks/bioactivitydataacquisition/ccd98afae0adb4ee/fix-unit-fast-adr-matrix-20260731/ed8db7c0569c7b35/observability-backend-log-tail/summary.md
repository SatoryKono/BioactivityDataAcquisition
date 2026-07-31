---
record_id: observability-backend-log-tail
record_type: working
repo_id: bioactivitydataacquisition
git_commit: ee50ef5a519bab9a89717f3576e5c7e43ac553a9
branch: fix/unit-fast-adr-matrix-20260731
worktree_id: ccd98afae0adb4ee
task_id: observability-backend-log-tail
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-07-31T06:23:32.675051+00:00'
source_refs:
- tests/unit/interfaces/cli/commands/test_observability_backend_runtime.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 0c3ce62e90cbca6e42c64836dd96e9dc133a2778b3f13959807b57d51d6a6455
id: observability-backend-log-tail
title: Fix missing backend startup log tail
ttl_days: 14
confidence: episodic
summary: Isolated the backend log-tail test to tmp_path, preventing parallel workers
  from racing on the shared port-based temp log.
---

# Episodic summary

## Task

- Title: Fix missing backend startup log tail

## Outcome

- Isolated the backend log-tail test to tmp_path, preventing parallel workers from racing on the shared port-based temp log.

## Lessons learned

- Replace with durable follow-up if needed
