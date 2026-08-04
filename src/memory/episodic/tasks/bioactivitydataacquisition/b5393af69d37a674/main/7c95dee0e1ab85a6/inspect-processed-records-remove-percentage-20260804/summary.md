---
record_id: inspect-processed-records-remove-percentage-20260804
record_type: working
repo_id: bioactivitydataacquisition
git_commit: a8db5157d49395990365fe618162c0c12a0525ad
branch: main
worktree_id: b5393af69d37a674
task_id: inspect-processed-records-remove-percentage-20260804
actor:
  runtime: codex
  agent: codex-dashboard-extension
  model: null
created_at: '2026-08-04T19:10:14.694188+00:00'
source_refs:
- grafana/dashboards/bioetl-dq-v2.json
- tests/integration/test_grafana_dashboard_metric_semantics.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 956af85dc8c79e1806419da5ce737960b3eb78c0d5961da30d98b2bac0ab1651
id: inspect-processed-records-remove-percentage-20260804
title: Hide percentage in Inspect Processed Records
ttl_days: 14
confidence: episodic
summary: Hid the canonical percentage field in the four panels titled Inspect Processed
  Records while preserving it in the two Review Processed Records panels; synchronized
  dashboard docs and added a title-sensitive regression contract.
---

# Episodic summary

## Task

- Title: Hide percentage in Inspect Processed Records

## Outcome

- Hid the canonical percentage field in the four panels titled Inspect Processed Records while preserving it in the two Review Processed Records panels; synchronized dashboard docs and added a title-sensitive regression contract.

## Lessons learned

- Replace with durable follow-up if needed
