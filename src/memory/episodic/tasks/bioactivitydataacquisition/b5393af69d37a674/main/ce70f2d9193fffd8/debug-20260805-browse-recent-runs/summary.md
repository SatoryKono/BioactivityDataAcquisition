---
record_id: debug-20260805-browse-recent-runs
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 30b196e239141e519a4b26473cca5ad7ef1c1b4d
branch: main
worktree_id: b5393af69d37a674
task_id: DEBUG-20260805-browse-recent-runs
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-08-05T06:26:08.505840+00:00'
source_refs:
- docker-compose.yml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 0f8917c4bf3e38ea66585020e0fdf68be11a2791365fcbea1982909e5f146129
id: debug-20260805-browse-recent-runs
title: Diagnose missing new runs in Browse Recent Runs
ttl_days: 14
confidence: episodic
summary: Confirmed Grafana queries a healthy BioETL container launched from a different
  checkout; its /app/reports bind points to E:\g-drive\05_AI\github\BioactivityDataAcquisition2\reports
  while new run reports are written under E:\github\BioactivityDataAcquisition\reports.
---

# Episodic summary

## Task

- Title: Diagnose missing new runs in Browse Recent Runs

## Outcome

- Confirmed Grafana queries a healthy BioETL container launched from a different checkout; its /app/reports bind points to E:\g-drive\05_AI\github\BioactivityDataAcquisition2\reports while new run reports are written under E:\github\BioactivityDataAcquisition\reports.

## Lessons learned

- Replace with durable follow-up if needed
