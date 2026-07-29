---
record_id: grafana-id-processed-records-layout
record_type: working
repo_id: bioactivitydataacquisition
git_commit: d60d245202c066ac964b89d6aa07aecd2647aeff
branch: main
worktree_id: ccd98afae0adb4ee
task_id: grafana-id-processed-records-layout
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-29T18:11:00.410810+00:00'
source_refs:
- working-tree
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 86e3c536eca970b4a57498e285d2172e9f658aaba4d0a2f57233f56c6b7a1e45
id: grafana-id-processed-records-layout
title: Unify ID and Processed Records table layout
ttl_days: 14
confidence: episodic
summary: Verified all six shipped dashboards use gridPos.h=6 and cellHeight=sm for
  ID and Processed Records; hid row_status and deprecated percintage while retaining
  canonical percentage; updated contract tests and dashboard documentation.
---

# Episodic summary

## Task

- Title: Unify ID and Processed Records table layout

## Outcome

- Verified all six shipped dashboards use gridPos.h=6 and cellHeight=sm for ID and Processed Records; hid row_status and deprecated percintage while retaining canonical percentage; updated contract tests and dashboard documentation.

## Lessons learned

- Replace with durable follow-up if needed
