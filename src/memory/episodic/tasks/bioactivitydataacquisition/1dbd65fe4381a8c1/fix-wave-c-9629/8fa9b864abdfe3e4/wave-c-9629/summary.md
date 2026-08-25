---
record_id: wave-c-9629
record_type: working
repo_id: bioactivitydataacquisition
git_commit: d9ac42612b6e0fd0f7efde5427dce70b413a5882
branch: fix/wave-c-9629
worktree_id: 1dbd65fe4381a8c1
task_id: wave-c-9629
actor:
  runtime: codex
  agent: py-config-bot
  model: null
created_at: '2026-08-25T14:05:42.634920+00:00'
source_refs:
- scripts/engineering/qa/refresh_governance_artifacts.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 46c1c898cad4eadbed20b1d2c18c3da403b82e28060a4c061936be21f17a9412
id: wave-c-9629
title: Make unified governance artifact refresh fail closed
ttl_days: 14
confidence: episodic
summary: Unified existing governance refresh/check path; propagated generator failures;
  added regression tests and docs; shrank assertless max from 102 to measured 87.
  Shared artifact regeneration remains blocked by source, depmap, governance, hotspot,
  and debt-gate drift.
---

# Episodic summary

## Task

- Title: Make unified governance artifact refresh fail closed

## Outcome

- Unified existing governance refresh/check path; propagated generator failures; added regression tests and docs; shrank assertless max from 102 to measured 87. Shared artifact regeneration remains blocked by source, depmap, governance, hotspot, and debt-gate drift.

## Lessons learned

- Replace with durable follow-up if needed
