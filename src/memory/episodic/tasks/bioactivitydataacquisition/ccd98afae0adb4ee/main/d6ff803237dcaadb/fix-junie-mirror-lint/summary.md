---
record_id: fix-junie-mirror-lint
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 406474ba7076645ac4f7b91fd31d9969fd4f7305
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-junie-mirror-lint
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T07:43:48.213775+00:00'
source_refs:
- scripts/ai/junie/check_junie_mirror.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 85ac4b27b208db7ad1c7b538e78a77646131cbe24849fb4a6f893436d4ed98d0
id: fix-junie-mirror-lint
title: Fix Junie mirror lint violations
ttl_days: 14
confidence: episodic
summary: Moved Iterable to collections.abc and made both shared-agent-doc zip calls
  strict; Ruff and mirror parity checks pass.
---

# Episodic summary

## Task

- Title: Fix Junie mirror lint violations

## Outcome

- Moved Iterable to collections.abc and made both shared-agent-doc zip calls strict; Ruff and mirror parity checks pass.

## Lessons learned

- Replace with durable follow-up if needed
