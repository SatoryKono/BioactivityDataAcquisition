---
record_id: debug-20260805-processed-records-panel
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 2ab75526dc6c22d71a7cd084b04cc6d2e8e15b4f
branch: agent/grafana-3cycle-20260805-r2
worktree_id: b5393af69d37a674
task_id: DEBUG-20260805-processed-records-panel
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-08-05T06:42:26.182962+00:00'
source_refs:
- src/bioetl/interfaces/http/processed_records_table.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: bdd977fd589f950a0ce322e08210cd16714cc3b289338390069e2789deb47d55
id: debug-20260805-processed-records-panel
title: Diagnose Review Processed Records columns
ttl_days: 14
confidence: episodic
summary: Confirmed dashboards expect canonical percentage and clean value, but running
  bioetl image from 2026-07-27 emits legacy percintage and parameter|value strings;
  recreate without --build preserved stale backend code.
---

# Episodic summary

## Task

- Title: Diagnose Review Processed Records columns

## Outcome

- Confirmed dashboards expect canonical percentage and clean value, but running bioetl image from 2026-07-27 emits legacy percintage and parameter|value strings; recreate without --build preserved stale backend code.

## Lessons learned

- Replace with durable follow-up if needed
