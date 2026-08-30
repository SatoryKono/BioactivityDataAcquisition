---
record_id: fix-observability-api-runtime-imports-20260825
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 9136bd376e19a92e755eea25daf885cdcb41c060
branch: fix/obs-fill-pipeline-runs-presence
worktree_id: 7360d78d97884e9f
task_id: fix-observability-api-runtime-imports-20260825
actor:
  runtime: codex
  agent: codex
  model: gpt-5
created_at: '2026-08-25T10:01:00.864392+00:00'
source_refs:
- src/bioetl/composition/observability_api.py
- tests/unit/composition/test_observability_api.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: d7d3f0fe6583a31fd8c0377ac29ad9491f3adeeed3632e7ec20c66137a77a4a0
id: fix-observability-api-runtime-imports-20260825
title: Fix observability API runtime imports
ttl_days: 14
confidence: episodic
summary: Replaced TYPE_CHECKING-only observability dependencies with runtime module
  seams, routed every service getter to its correct owner, updated tests and source-tree
  hashes; targeted Ruff/unit/architecture checks passed while unrelated global governance/debt
  gates remained red.
---

# Episodic summary

## Task

- Title: Fix observability API runtime imports

## Outcome

- Replaced TYPE_CHECKING-only observability dependencies with runtime module seams, routed every service getter to its correct owner, updated tests and source-tree hashes; targeted Ruff/unit/architecture checks passed while unrelated global governance/debt gates remained red.

## Lessons learned

- Replace with durable follow-up if needed
