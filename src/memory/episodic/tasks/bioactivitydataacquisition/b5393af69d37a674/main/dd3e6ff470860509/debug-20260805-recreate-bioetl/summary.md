---
record_id: debug-20260805-recreate-bioetl
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 0c0b7ab076b4f18cf10d302ab32531ead7a24fc9
branch: main
worktree_id: b5393af69d37a674
task_id: DEBUG-20260805-recreate-bioetl
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-08-05T06:29:49.205383+00:00'
source_refs:
- docker-compose.yml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 9da223c11b3428bb7d43d717e28301c36b3fa539242865d417f6595fe3318b31
id: debug-20260805-recreate-bioetl
title: Recreate BioETL service from current checkout
ttl_days: 14
confidence: episodic
summary: Recreated only bioetl from current checkout; reports bind now targets /mnt/e/github/BioactivityDataAcquisition/reports,
  Docker health is healthy, and host plus Grafana-side endpoint calls return fresh
  2026-08-05 runs.
---

# Episodic summary

## Task

- Title: Recreate BioETL service from current checkout

## Outcome

- Recreated only bioetl from current checkout; reports bind now targets /mnt/e/github/BioactivityDataAcquisition/reports, Docker health is healthy, and host plus Grafana-side endpoint calls return fresh 2026-08-05 runs.

## Lessons learned

- Replace with durable follow-up if needed
